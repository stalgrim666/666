#!/usr/bin/env python3
"""Public-data check: Derive execution and incentives versus Deribit.

Reads only unauthenticated HTTP endpoints. Does not place orders.
Raw bodies go to raw/. Aggregates go to clean/. No API key is read.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import time
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
CLEAN = ROOT / "clean"
RAW.mkdir(parents=True, exist_ok=True)
CLEAN.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "research-bot/1.0 (derive-deribit-public; no orders)",
        "Accept": "application/json,text/plain,*/*",
    }
)

NOW_MS = int(time.time() * 1000)
DAY_MS = 86_400_000


def iso(ms: int | float | None) -> str:
    if ms is None:
        return ""
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_bytes(name: str, data: bytes) -> dict:
    path = RAW / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"file": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha256_bytes(data)}


def save_json(name: str, obj) -> dict:
    data = json.dumps(obj, ensure_ascii=False).encode()
    return save_bytes(name, data)


def save_gz_json(name: str, obj) -> dict:
    raw = json.dumps(obj, ensure_ascii=False).encode()
    path = RAW / name
    path.write_bytes(gzip.compress(raw, compresslevel=6))
    return {
        "file": str(path.relative_to(ROOT)),
        "gzip_bytes": path.stat().st_size,
        "plain_bytes": len(raw),
        "sha256_gzip": sha256_bytes(path.read_bytes()),
    }


def num(value) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def request(method: str, url: str, *, params=None, json_body=None, timeout=60, ok_status=(200,)) -> requests.Response:
    last = None
    for attempt in range(4):
        try:
            response = SESSION.request(method, url, params=params, json=json_body, timeout=timeout)
        except requests.RequestException as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
            continue
        if response.status_code in (429, 502, 503, 504):
            time.sleep(1.5 * (attempt + 1))
            last = requests.HTTPError(f"{response.status_code} {url}")
            continue
        if response.status_code not in ok_status:
            # Caller inspects error bodies for auth probes. Non-probe calls raise.
            if ok_status == (200,):
                response.raise_for_status()
        return response
    raise RuntimeError(f"failed {url}: {last}")


def derive_post(method: str, params: dict, timeout=90) -> dict:
    url = f"https://api.derive.xyz/v3/{method}"
    response = request("POST", url, json_body=params, timeout=timeout)
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"{method} {payload['error']}")
    return payload


def deribit_get(path: str, params: dict) -> dict:
    url = f"https://www.deribit.com/api/v2/{path}"
    response = request("GET", url, params=params, timeout=45)
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"{path} {payload['error']}")
    return payload


def percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (len(sorted_vals) - 1) * p
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    w = rank - lo
    return sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w


def dist(values: list[float]) -> dict:
    vals = sorted(v for v in values if v > 0)
    if not vals:
        return {"n": 0}
    total = sum(vals)
    buckets = [(0, 10_000), (10_000, 50_000), (50_000, 250_000), (250_000, 1_000_000), (1_000_000, None)]
    shares = {}
    for lo, hi in buckets:
        label = f"{lo:.0f}-{'inf' if hi is None else f'{hi:.0f}'}"
        chosen = [v for v in vals if v >= lo and (hi is None or v < hi)]
        shares[label] = {
            "n": len(chosen),
            "notional": sum(chosen),
            "notional_share": (sum(chosen) / total) if total else None,
        }
    return {
        "n": len(vals),
        "notional": total,
        "p50": percentile(vals, 0.50),
        "p90": percentile(vals, 0.90),
        "p99": percentile(vals, 0.99),
        "max": vals[-1],
        "buckets_usd": shares,
    }


def parse_deribit_option(name: str) -> tuple[str, str, str, str] | None:
    parts = name.split("-")
    if len(parts) != 4 or parts[-1] not in ("C", "P"):
        return None
    currency, dmy, strike, cp = parts
    try:
        expiry = datetime.strptime(dmy, "%d%b%y").date().isoformat()
    except ValueError:
        return None
    try:
        strike_key = format(float(strike), "f").rstrip("0").rstrip(".")
    except ValueError:
        return None
    return currency, expiry, strike_key, cp


def parse_derive_option(name: str) -> tuple[str, str, str, str] | None:
    parts = name.split("-")
    if len(parts) != 4 or parts[-1] not in ("C", "P"):
        return None
    currency, ymd, strike, cp = parts
    if len(ymd) != 8 or not ymd.isdigit():
        return None
    expiry = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
    try:
        strike_key = format(float(strike), "f").rstrip("0").rstrip(".")
    except ValueError:
        return None
    return currency, expiry, strike_key, cp


def probe_rfq() -> dict:
    """Two public paths: documented method, then one unauthenticated call.

    Docs used when this script was written:
    - https://docs.deribit.com/api-reference/block-rfq/public-get_block_rfq_trades
    - https://docs.deribit.com/api-reference/block-rfq/private-get_block_rfq_quotes
    - https://docs.derive.xyz/trading/rfq
    """
    record = {"paths": []}
    deribit_private = request(
        "GET",
        "https://www.deribit.com/api/v2/private/get_block_rfq_quotes",
        params={"currency": "BTC"},
        ok_status=(200, 400, 401, 403),
    )
    record["paths"].append(
        {
            "venue": "Deribit",
            "what": "live RFQ quotes",
            "method": "private/get_block_rfq_quotes",
            "auth": "none",
            "http_status": deribit_private.status_code,
            "body_excerpt": deribit_private.text[:500],
            "classified_as": "quote_request_rejected",
        }
    )
    deribit_public = request(
        "GET",
        "https://www.deribit.com/api/v2/public/get_block_rfq_trades",
        params={"currency": "BTC", "count": 10},
        ok_status=(200, 400),
    )
    public_body = deribit_public.json()
    save_json("deribit_btc_block_rfq_probe.json", public_body)
    sample = ((public_body.get("result") or {}).get("block_rfqs") or [None])[0]
    record["paths"].append(
        {
            "venue": "Deribit",
            "what": "completed block RFQ trades",
            "method": "public/get_block_rfq_trades",
            "auth": "none",
            "http_status": deribit_public.status_code,
            "sample_keys": sorted(sample.keys()) if isinstance(sample, dict) else None,
            "has_leg_execution_price": bool(sample and sample.get("legs") and "price" in sample["legs"][0]),
            "has_open_quote_book": False,
            "classified_as": "execution_print",
        }
    )
    derive_private = request(
        "POST",
        "https://api.derive.xyz/v3/private/poll_quotes",
        json_body={},
        ok_status=(200, 400, 401, 403),
    )
    record["paths"].append(
        {
            "venue": "Derive",
            "what": "live RFQ quotes",
            "method": "private/poll_quotes",
            "auth": "none",
            "http_status": derive_private.status_code,
            "body_excerpt": derive_private.text[:500],
            "classified_as": "quote_request_rejected",
        }
    )
    derive_public = request(
        "POST",
        "https://api.derive.xyz/v3/public/poll_quotes",
        json_body={},
        ok_status=(200, 404, 400),
    )
    record["paths"].append(
        {
            "venue": "Derive",
            "what": "public alias of quote poll",
            "method": "public/poll_quotes",
            "auth": "none",
            "http_status": derive_public.status_code,
            "body_excerpt": derive_public.text[:300],
            "classified_as": "no_public_method" if derive_public.status_code == 404 else "other",
        }
    )
    save_json("rfq_quote_probe.json", record)
    return record


def fetch_deribit_books() -> dict:
    books = {}
    for currency in ("BTC", "ETH"):
        payload = deribit_get("public/get_book_summary_by_currency", {"currency": currency, "kind": "option"})
        meta = save_json(f"deribit_{currency}_option_book_summary.json", payload)
        books[currency] = payload["result"]
        print(f"deribit book {currency} instruments={len(payload['result'])} bytes={meta['bytes']}", flush=True)
    volumes = deribit_get("public/get_trade_volumes", {"extended": "true"})
    save_json("deribit_trade_volumes.json", volumes)
    return {"books": books, "volumes": volumes["result"]}


def fetch_block_rfqs(currency: str, start_ms: int) -> dict:
    pages = []
    continuation = None
    for _ in range(40):
        params = {"currency": currency, "count": 50}
        if continuation:
            params["continuation"] = continuation
        payload = deribit_get("public/get_block_rfq_trades", params)
        pages.append(payload["result"])
        rows = payload["result"].get("block_rfqs") or []
        continuation = payload["result"].get("continuation")
        if not rows or not continuation:
            break
        oldest = min(row["timestamp"] for row in rows)
        if oldest < start_ms:
            break
    packages = []
    seen = set()
    for page in pages:
        for row in page.get("block_rfqs") or []:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            packages.append(row)
    in_window = [row for row in packages if row["timestamp"] >= start_ms]
    oldest = min((row["timestamp"] for row in packages), default=None)
    return {
        "packages_in_window": in_window,
        "pages": len(pages),
        "oldest_returned": oldest,
        "covered_start": oldest is not None and oldest <= start_ms,
        "truncated_by_page_cap": len(pages) >= 40 and (oldest is None or oldest > start_ms),
    }


def expand_block_legs(packages: list[dict], currency: str) -> list[dict]:
    legs = []
    index_key = f"{currency.lower()}_usd"
    for package in packages:
        index = num((package.get("index_prices") or {}).get(index_key))
        for leg in package.get("legs") or []:
            name = leg.get("instrument_name") or ""
            if not name.endswith(("-C", "-P")):
                continue
            ratio = num(leg.get("ratio") or 1)
            coin = num(package.get("amount")) * ratio
            price_coin = num(leg.get("price"))
            legs.append(
                {
                    "package_id": package.get("id"),
                    "timestamp": package.get("timestamp"),
                    "instrument_name": name,
                    "coin": coin,
                    "price_coin": price_coin,
                    "index": index,
                    "notional_usd": coin * index if index else None,
                    "premium_usd": coin * price_coin * index if index else None,
                }
            )
    return legs


def fetch_deribit_trades(currency: str, start_ms: int, end_ms: int) -> dict:
    trades = []
    seen = set()
    cursor = start_ms
    pages = 0
    stalled = False
    while pages < 80:
        payload = deribit_get(
            "public/get_last_trades_by_currency_and_time",
            {
                "currency": currency,
                "kind": "option",
                "start_timestamp": cursor,
                "end_timestamp": end_ms,
                "count": 1000,
                "sorting": "asc",
                "include_old": "true",
            },
        )
        result = payload["result"]
        batch = result.get("trades") or []
        pages += 1
        if not batch:
            break
        for trade in batch:
            trade_id = trade.get("trade_id")
            if trade_id in seen:
                continue
            seen.add(trade_id)
            trades.append(trade)
        last_ts = int(batch[-1]["timestamp"])
        has_more = bool(result.get("has_more"))
        print(f"deribit tape {currency} page={pages} batch={len(batch)} unique={len(trades)} last={iso(last_ts)} more={has_more}", flush=True)
        if not has_more:
            break
        if last_ts <= cursor:
            stalled = True
            break
        cursor = last_ts
    stamps = [int(trade["timestamp"]) for trade in trades]
    return {
        "trades": trades,
        "pages": pages,
        "stalled": stalled,
        "earliest": min(stamps) if stamps else None,
        "latest": max(stamps) if stamps else None,
        "hit_page_cap": pages >= 80 and (not stamps or max(stamps) < end_ms - 60_000),
    }


def fetch_derive_tickers() -> dict:
    live = derive_post("public/get_all_live_instruments", {})
    names = live["result"]
    save_json("derive_live_instrument_names.json", names)
    groups = set()
    for name in names:
        parsed = parse_derive_option(name)
        if not parsed or parsed[0] not in ("BTC", "ETH"):
            continue
        groups.add((parsed[0], name.split("-")[1]))

    def one(item: tuple[str, str]):
        currency, expiry = item
        payload = derive_post(
            "public/get_tickers",
            {"instrument_type": "option", "currency": currency, "expiry_date": int(expiry)},
        )
        return payload["result"]["tickers"]

    tickers = {}
    errors = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(one, item): item for item in groups}
        for future in as_completed(futures):
            item = futures[future]
            try:
                book = future.result()
            except Exception as exc:  # noqa: BLE001
                errors.append({"group": item, "error": str(exc)})
                continue
            tickers.update(book)
    save_gz_json("derive_btc_eth_option_tickers.json.gz", {"errors": errors, "n_groups": len(groups), "tickers": tickers})
    print(f"derive tickers groups={len(groups)} names={len(tickers)} errors={len(errors)}", flush=True)
    return {"tickers": tickers, "errors": errors, "groups": len(groups)}


def fetch_derive_trades(start_ms: int, end_ms: int) -> dict:
    first = derive_post(
        "public/get_trade_history",
        {
            "instrument_type": "option",
            "from_timestamp": start_ms,
            "to_timestamp": end_ms,
            "page": 1,
            "page_size": 1000,
        },
    )["result"]
    declared = int(first["pagination"]["count"])
    declared_pages = int(first["pagination"]["num_pages"])
    rows = list(first["trades"])
    print(f"derive tape declared count={declared} pages={declared_pages}", flush=True)
    page = 2
    while page <= declared_pages and page <= 200:
        payload = derive_post(
            "public/get_trade_history",
            {
                "instrument_type": "option",
                "from_timestamp": start_ms,
                "to_timestamp": end_ms,
                "page": page,
                "page_size": 1000,
            },
        )["result"]
        batch = payload["trades"]
        rows.extend(batch)
        if page % 10 == 0 or page == declared_pages:
            print(f"derive tape page={page}/{declared_pages} rows={len(rows)}", flush=True)
        if not batch:
            break
        page += 1
    return {
        "raw_rows": rows,
        "declared_count": declared,
        "declared_pages": declared_pages,
        "pages_fetched": page - 1,
    }


def channel_stats(trades: list[dict]) -> dict:
    taker = [trade for trade in trades if trade.get("liquidity_role") == "taker"]
    out = {}
    for label, subset in (
        ("RFQ", [trade for trade in taker if trade.get("rfq_id")]),
        ("CLOB", [trade for trade in taker if not trade.get("rfq_id")]),
        ("ALL", taker),
    ):
        by_wallet = defaultdict(float)
        days = defaultdict(set)
        legs = defaultdict(int)
        notional = 0.0
        premium = 0.0
        fee = 0.0
        rebate = 0.0
        rfqs = set()
        for trade in subset:
            amount = num(trade.get("trade_amount"))
            notion = amount * num(trade.get("index_price"))
            notional += notion
            premium += amount * num(trade.get("trade_price"))
            fee += num(trade.get("trade_fee"))
            rebate += num(trade.get("expected_rebate"))
            wallet = trade.get("wallet") or ""
            by_wallet[wallet] += notion
            legs[wallet] += 1
            days[wallet].add(datetime.fromtimestamp(int(trade["timestamp"]) / 1000, tz=timezone.utc).date().isoformat())
            if trade.get("rfq_id"):
                rfqs.add(trade["rfq_id"])
        ranked = sorted(by_wallet.items(), key=lambda item: item[1], reverse=True)
        ranked_vals = [value for _, value in ranked if value > 0]
        wallets = [wallet for wallet, _ in ranked if wallet]
        repeat = [wallet for wallet in wallets if legs[wallet] >= 2]
        multi_day = [wallet for wallet in wallets if len(days[wallet]) >= 2]

        def share(n: int) -> float | None:
            if notional <= 0:
                return None
            return sum(ranked_vals[:n]) / notional

        repeat_notional = sum(by_wallet[wallet] for wallet in repeat)
        out[label] = {
            "taker_legs": len(subset),
            "unique_rfq": len(rfqs) if label != "CLOB" else 0,
            "notional_usd": notional,
            "premium_usd": premium,
            "trade_fee_sum": fee,
            "expected_rebate_sum": rebate,
            "wallets": len(wallets),
            "top5_notional_share": share(5),
            "top10_notional_share": share(10),
            "repeat_address_ratio": (len(repeat) / len(wallets)) if wallets else None,
            "repeat_notional_share": (repeat_notional / notional) if notional else None,
            "multi_day_address_ratio": (len(multi_day) / len(wallets)) if wallets else None,
            "notional_distribution": dist(
                [num(trade.get("trade_amount")) * num(trade.get("index_price")) for trade in subset]
            ),
        }
    return out


def fee_rows(trades: list[dict]) -> dict:
    out = {}
    for role in ("taker", "maker"):
        subset = [trade for trade in trades if trade.get("liquidity_role") == role]
        out[role] = {
            "rows": len(subset),
            "trade_fee_sum": sum(num(trade.get("trade_fee")) for trade in subset),
            "expected_rebate_sum": sum(num(trade.get("expected_rebate")) for trade in subset),
            "nonzero_expected_rebate_rows": sum(1 for trade in subset if num(trade.get("expected_rebate")) != 0),
            "negative_trade_fee_rows": sum(1 for trade in subset if num(trade.get("trade_fee")) < 0),
        }
    return out


def summarize_books(books: dict, tickers: dict) -> dict:
    deribit_meta = {}
    for currency, rows in books.items():
        quote_counts = defaultdict(int)
        for row in rows:
            quote_counts[row.get("quote_currency") or ""] += 1
        deribit_meta[currency] = {
            "n": len(rows),
            "quote_currency_counts": dict(quote_counts),
            "asof": iso(rows[0]["creation_timestamp"]) if rows else None,
            "sample_keys": sorted(rows[0].keys()) if rows else [],
        }
    return {"deribit_meta": deribit_meta, "derive_ticker_n": len(tickers)}


def instrument_rows(books: dict, tickers: dict) -> tuple[list[dict], dict]:
    deribit = {}
    for currency, rows in books.items():
        for row in rows:
            parsed = parse_deribit_option(row.get("instrument_name") or "")
            if not parsed:
                continue
            quote = row.get("quote_currency") or ""
            underlying = num(row.get("underlying_price"))
            volume = num(row.get("volume"))
            oi = num(row.get("open_interest"))
            mark = num(row.get("mark_price"))
            linear = quote in ("USD", "USDC")
            notional = volume * underlying
            oi_notional = oi * underlying
            premium = volume * mark if linear else volume * mark * underlying
            deribit[parsed] = {
                "instrument_name": row.get("instrument_name"),
                "quote_currency": quote,
                "linear": linear,
                "volume_coin": volume,
                "oi_coin": oi,
                "notional_usd": notional,
                "oi_notional_usd": oi_notional,
                "premium_usd_from_mark": premium,
                "volume_usd_field": num(row.get("volume_usd")),
                "underlying": underlying,
                "mark_price": mark,
                "bid": num(row.get("bid_price")),
                "ask": num(row.get("ask_price")),
            }
    derive = {}
    for name, ticker in tickers.items():
        parsed = parse_derive_option(name)
        if not parsed:
            continue
        stats = ticker.get("stats") or {}
        oi = num(stats.get("oi"))
        index = num(ticker.get("I"))
        derive[parsed] = {
            "instrument_name": name,
            "notional_usd": num(stats.get("v")),
            "premium_usd": num(stats.get("pr")),
            "oi_coin": oi,
            "oi_notional_usd": oi * index,
            "mark_usd": num(ticker.get("M")),
            "index": index,
        }
    rows = []
    keys = set(deribit) | set(derive)
    for key in keys:
        left = deribit.get(key)
        right = derive.get(key)
        currency, expiry, strike, cp = key
        rows.append(
            {
                "currency": currency,
                "expiry": expiry,
                "strike": strike,
                "cp": cp,
                "on_deribit": bool(left),
                "on_derive": bool(right),
                "deribit_name": None if not left else left["instrument_name"],
                "derive_name": None if not right else right["instrument_name"],
                "deribit_notional_24h": None if not left else left["notional_usd"],
                "derive_notional_24h": None if not right else right["notional_usd"],
                "deribit_premium_mark_24h": None if not left else left["premium_usd_from_mark"],
                "deribit_volume_usd_field": None if not left else left["volume_usd_field"],
                "derive_premium_24h": None if not right else right["premium_usd"],
                "deribit_oi_notional": None if not left else left["oi_notional_usd"],
                "derive_oi_notional": None if not right else right["oi_notional_usd"],
                "deribit_linear": None if not left else left["linear"],
            }
        )
    return rows, {"deribit": deribit, "derive": derive}


def aggregate_listing(rows: list[dict]) -> dict:
    out = {}
    for currency in ("BTC", "ETH", "ALL"):
        chosen = rows if currency == "ALL" else [row for row in rows if row["currency"] == currency]
        both = [row for row in chosen if row["on_deribit"] and row["on_derive"]]
        only_d = [row for row in chosen if row["on_deribit"] and not row["on_derive"]]
        only_v = [row for row in chosen if row["on_derive"] and not row["on_deribit"]]

        def s(items, field):
            return sum(num(item.get(field)) for item in items)

        out[currency] = {
            "deribit_instruments": sum(1 for row in chosen if row["on_deribit"]),
            "derive_instruments": sum(1 for row in chosen if row["on_derive"]),
            "matched_instruments": len(both),
            "deribit_only": len(only_d),
            "derive_only": len(only_v),
            "deribit_notional_all": s([row for row in chosen if row["on_deribit"]], "deribit_notional_24h"),
            "derive_notional_all": s([row for row in chosen if row["on_derive"]], "derive_notional_24h"),
            "deribit_notional_on_matched": s(both, "deribit_notional_24h"),
            "derive_notional_on_matched": s(both, "derive_notional_24h"),
            "deribit_oi_all": s([row for row in chosen if row["on_deribit"]], "deribit_oi_notional"),
            "derive_oi_all": s([row for row in chosen if row["on_derive"]], "derive_oi_notional"),
            "deribit_oi_on_matched": s(both, "deribit_oi_notional"),
            "derive_oi_on_matched": s(both, "derive_oi_notional"),
            "deribit_premium_mark_all": s([row for row in chosen if row["on_deribit"]], "deribit_premium_mark_24h"),
            "deribit_volume_usd_field_all": s([row for row in chosen if row["on_deribit"]], "deribit_volume_usd_field"),
            "derive_premium_all": s([row for row in chosen if row["on_derive"]], "derive_premium_24h"),
            "deribit_premium_mark_matched": s(both, "deribit_premium_mark_24h"),
            "derive_premium_matched": s(both, "derive_premium_24h"),
        }
    return out


def deribit_tape_stats(trades: list[dict], meta_by_name: dict) -> dict:
    notionals = []
    premiums = []
    block_notional = 0.0
    rfq_notional = 0.0
    other_block_notional = 0.0
    total = 0.0
    premium_total = 0.0
    missing_index = 0
    for trade in trades:
        name = trade.get("instrument_name")
        meta = meta_by_name.get(name) or {}
        amount = num(trade.get("amount"))
        index = num(trade.get("index_price"))
        price = num(trade.get("price"))
        if index <= 0:
            missing_index += 1
            continue
        linear = bool(meta.get("linear"))
        notional = amount * index
        premium = amount * price if linear else amount * price * index
        total += notional
        premium_total += premium
        notionals.append(notional)
        premiums.append(premium)
        is_rfq = trade.get("block_rfq_id") not in (None, "", 0)
        is_block = is_rfq or trade.get("block_trade_id") not in (None, "", 0) or num(trade.get("block_trade_leg_count")) > 0
        if is_rfq:
            rfq_notional += notional
        elif is_block:
            other_block_notional += notional
        if is_block:
            block_notional += notional
    return {
        "prints": len(trades),
        "missing_index": missing_index,
        "notional_usd": total,
        "premium_usd": premium_total,
        "block_rfq_notional_usd": rfq_notional,
        "other_block_notional_usd": other_block_notional,
        "any_block_notional_usd": block_notional,
        "block_rfq_notional_share": (rfq_notional / total) if total else None,
        "any_block_notional_share": (block_notional / total) if total else None,
        "notional_distribution": dist(notionals),
        "prints_with_block_rfq_id": sum(1 for trade in trades if trade.get("block_rfq_id") not in (None, "", 0)),
        "prints_with_block_trade_id": sum(1 for trade in trades if trade.get("block_trade_id") not in (None, "", 0)),
        "prints_with_combo_id": sum(1 for trade in trades if trade.get("combo_id")),
    }


def match_prints(derive_trades: list[dict], deribit_trades: list[dict], deribit_meta: dict, window_ms: int) -> dict:
    """Pair single-instrument prints. Package trades stay out of the price diff."""
    derive_by = defaultdict(list)
    for trade in derive_trades:
        if trade.get("liquidity_role") != "taker":
            continue
        if trade.get("rfq_id"):
            continue
        parsed = parse_derive_option(trade.get("instrument_name") or "")
        if not parsed:
            continue
        derive_by[parsed].append(trade)
    deribit_by = defaultdict(list)
    for trade in deribit_trades:
        if trade.get("block_rfq_id") or trade.get("block_trade_id") or trade.get("combo_id"):
            continue
        parsed = parse_deribit_option(trade.get("instrument_name") or "")
        if not parsed:
            continue
        deribit_by[parsed].append(trade)
    pairs = []
    used = set()
    for key, left_rows in derive_by.items():
        right_rows = deribit_by.get(key) or []
        if not right_rows:
            continue
        right_rows = sorted(right_rows, key=lambda trade: int(trade["timestamp"]))
        for left in sorted(left_rows, key=lambda trade: int(trade["timestamp"])):
            left_ts = int(left["timestamp"])
            best = None
            best_dt = None
            for index, right in enumerate(right_rows):
                if (key, right.get("trade_id")) in used:
                    continue
                dt = abs(int(right["timestamp"]) - left_ts)
                if dt > window_ms:
                    continue
                if best_dt is None or dt < best_dt:
                    best = (index, right)
                    best_dt = dt
            if best is None:
                continue
            _, right = best
            used.add((key, right.get("trade_id")))
            meta = deribit_meta.get(right.get("instrument_name")) or {}
            amount_l = num(left.get("trade_amount"))
            amount_r = num(right.get("amount"))
            index_r = num(right.get("index_price"))
            linear = bool(meta.get("linear"))
            derive_usd = num(left.get("trade_price"))
            deribit_usd = num(right.get("price")) if linear else num(right.get("price")) * index_r
            if derive_usd <= 0 or deribit_usd <= 0 or amount_l <= 0 or amount_r <= 0:
                continue
            size_ratio = amount_l / amount_r
            pairs.append(
                {
                    "key": key,
                    "dt_ms": best_dt,
                    "derive_usd": derive_usd,
                    "deribit_usd": deribit_usd,
                    "abs_diff_usd": abs(derive_usd - deribit_usd),
                    "rel_diff": abs(derive_usd - deribit_usd) / deribit_usd,
                    "size_ratio": size_ratio,
                    "same_direction": left.get("direction") == right.get("direction"),
                    "derive_notional": amount_l * num(left.get("index_price")),
                    "deribit_notional": amount_r * index_r,
                }
            )
    def pack(items: list[dict]) -> dict:
        diffs = sorted(item["rel_diff"] for item in items)
        abs_diffs = sorted(item["abs_diff_usd"] for item in items)
        return {
            "n": len(items),
            "median_abs_usd": percentile(abs_diffs, 0.5),
            "median_rel": percentile(diffs, 0.5),
            "p90_rel": percentile(diffs, 0.9),
            "same_direction_n": sum(1 for item in items if item["same_direction"]),
        }
    close_size = [item for item in pairs if 0.5 <= item["size_ratio"] <= 2]
    return {"all_pairs": pack(pairs), "size_filtered": pack(close_size)}


def llama(path: str) -> dict:
    url = f"https://api.llama.fi/{path}"
    response = request("GET", url, timeout=60)
    payload = response.json()
    save_json("llama_" + path.replace("/", "_").replace("?", "_") + ".json", payload)
    return payload


def chart(payload: dict) -> list[tuple[int, float]]:
    rows = payload.get("totalDataChart") or []
    return [(int(ts), float(value)) for ts, value in rows]


def sum_days(points: list[tuple[int, float]], start_ms: int, end_ms: int) -> dict:
    by_day = {}
    for ts, value in points:
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        by_day[day] = value
    start_day = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).date()
    end_day = datetime.fromtimestamp((end_ms - 1) / 1000, tz=timezone.utc).date()
    total = 0.0
    present = []
    missing = []
    day = start_day
    while day <= end_day:
        if day in by_day:
            total += by_day[day]
            present.append(day.isoformat())
        else:
            missing.append(day.isoformat())
        day += timedelta(days=1)
    return {"sum": total, "present_days": len(present), "missing_days": missing}


def combine_adapter(v2: list[tuple[int, float]], v3: list[tuple[int, float]], start_ms: int, end_ms: int) -> dict:
    v2_days = {datetime.fromtimestamp(ts, tz=timezone.utc).date(): value for ts, value in v2}
    v3_days = {datetime.fromtimestamp(ts, tz=timezone.utc).date(): value for ts, value in v3}
    start_day = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).date()
    end_day = datetime.fromtimestamp((end_ms - 1) / 1000, tz=timezone.utc).date()
    total = 0.0
    missing = []
    both = []
    used = []
    day = start_day
    while day <= end_day:
        v2v = v2_days.get(day)
        v3v = v3_days.get(day)
        if v2v is not None and v3v is not None and v2v > 0 and v3v > 0:
            both.append(day.isoformat())
        elif v3v is not None and v3v > 0:
            total += v3v
            used.append(day.isoformat())
        elif v2v is not None:
            total += v2v
            used.append(day.isoformat())
        elif v3v is not None:
            total += v3v
            used.append(day.isoformat())
        else:
            missing.append(day.isoformat())
        day += timedelta(days=1)
    return {
        "sum": None if (missing or both) else total,
        "raw_sum_ignoring_conflicts": total,
        "missing_days": missing,
        "double_counted_days": both,
        "days_used": len(used),
    }


def write_csv(name: str, rows: list[dict]) -> None:
    path = CLEAN / name
    if not rows:
        path.write_text("")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    started = iso(NOW_MS)
    print("start", started, flush=True)
    probe = probe_rfq()
    books_payload = fetch_deribit_books()
    books = books_payload["books"]
    end_ms = int(time.time() * 1000)
    start_24h = end_ms - DAY_MS
    start_7d = end_ms - 7 * DAY_MS
    start_30d = end_ms - 30 * DAY_MS

    block = {}
    for currency in ("BTC", "ETH"):
        pulled = fetch_block_rfqs(currency, start_24h)
        legs = expand_block_legs(pulled["packages_in_window"], currency)
        block[currency] = {
            "packages_24h": len(pulled["packages_in_window"]),
            "pages": pulled["pages"],
            "covered_start": pulled["covered_start"],
            "truncated": pulled["truncated_by_page_cap"],
            "oldest_returned": iso(pulled["oldest_returned"]),
            "option_leg_coin": sum(leg["coin"] for leg in legs),
            "option_leg_notional_usd": sum(leg["notional_usd"] or 0 for leg in legs),
            "option_leg_premium_usd": sum(leg["premium_usd"] or 0 for leg in legs),
            "legs_missing_index": sum(1 for leg in legs if not leg["index"]),
            "notional_distribution": dist([leg["notional_usd"] or 0 for leg in legs]),
        }
        save_json(f"deribit_{currency}_block_rfq_24h_summary.json", block[currency])
        print("block", currency, block[currency]["packages_24h"], "covered", block[currency]["covered_start"], flush=True)

    tapes = {}
    for currency in ("BTC", "ETH"):
        tapes[currency] = fetch_deribit_trades(currency, start_24h, end_ms)
        save_gz_json(
            f"deribit_{currency}_option_trades_24h.json.gz",
            {
                "from": start_24h,
                "to": end_ms,
                "pages": tapes[currency]["pages"],
                "n": len(tapes[currency]["trades"]),
                "trades": tapes[currency]["trades"],
            },
        )

    derive_book = fetch_derive_tickers()
    listing_rows, maps = instrument_rows(books, derive_book["tickers"])
    write_csv("matched_instruments.csv", listing_rows)
    listing = aggregate_listing(listing_rows)

    name_meta = {}
    for key, row in maps["deribit"].items():
        name_meta[row["instrument_name"]] = row
    tape_stats = {}
    for currency, pulled in tapes.items():
        tape_stats[currency] = deribit_tape_stats(pulled["trades"], name_meta)
        tape_stats[currency]["pages"] = pulled["pages"]
        tape_stats[currency]["earliest"] = iso(pulled["earliest"])
        tape_stats[currency]["latest"] = iso(pulled["latest"])
        tape_stats[currency]["stalled"] = pulled["stalled"]
        tape_stats[currency]["hit_page_cap"] = pulled["hit_page_cap"]
        tape_stats[currency]["requested_from"] = iso(start_24h)
        tape_stats[currency]["requested_to"] = iso(end_ms)

    derive_pull = fetch_derive_trades(start_30d, end_ms)
    dedup = {}
    outside = 0
    non_option = 0
    for trade in derive_pull["raw_rows"]:
        ts = int(trade["timestamp"])
        if not (start_30d <= ts <= end_ms):
            outside += 1
            continue
        if not str(trade["instrument_name"]).endswith(("-C", "-P")):
            non_option += 1
            continue
        key = (trade["trade_id"], trade["liquidity_role"], trade.get("subaccount_id"))
        dedup[key] = trade
    clean = list(dedup.values())
    save_gz_json(
        "derive_option_trades_30d.json.gz",
        {
            "from": start_30d,
            "to": end_ms,
            "declared_count": derive_pull["declared_count"],
            "declared_pages": derive_pull["declared_pages"],
            "pages_fetched": derive_pull["pages_fetched"],
            "raw_rows": len(derive_pull["raw_rows"]),
            "dedup_rows": len(clean),
            "trades": clean,
        },
    )
    stamps = [int(trade["timestamp"]) for trade in clean]
    completeness = {
        "declared_count": derive_pull["declared_count"],
        "declared_pages": derive_pull["declared_pages"],
        "pages_fetched": derive_pull["pages_fetched"],
        "raw_rows": len(derive_pull["raw_rows"]),
        "dedup_rows": len(clean),
        "rows_outside_window": outside,
        "non_option_rows": non_option,
        "duplicate_rows": len(derive_pull["raw_rows"]) - outside - non_option - len(clean),
        "earliest": iso(min(stamps) if stamps else None),
        "latest": iso(max(stamps) if stamps else None),
        "requested_from": iso(start_30d),
        "requested_to": iso(end_ms),
        "pages_complete": derive_pull["pages_fetched"] == derive_pull["declared_pages"] and derive_pull["pages_fetched"] < 200,
        "count_matches_raw": len(derive_pull["raw_rows"]) == derive_pull["declared_count"],
    }

    def subset(start: int, currencies: set[str] | None) -> list[dict]:
        chosen = []
        for trade in clean:
            if int(trade["timestamp"]) < start:
                continue
            currency = str(trade["instrument_name"]).split("-", 1)[0]
            if currencies is not None and currency not in currencies:
                continue
            chosen.append(trade)
        return chosen

    flow = {}
    for label, currencies in (("ALL_OPTIONS", None), ("BTC", {"BTC"}), ("ETH", {"ETH"})):
        flow[label] = {
            "24h": channel_stats(subset(start_24h, currencies)),
            "7d": channel_stats(subset(start_7d, currencies)),
            "30d": channel_stats(subset(start_30d, currencies)),
            "fees_30d": fee_rows(subset(start_30d, currencies)),
            "fees_7d": fee_rows(subset(start_7d, currencies)),
        }

    derive_24h = [trade for trade in clean if int(trade["timestamp"]) >= start_24h]
    deribit_24h = tapes["BTC"]["trades"] + tapes["ETH"]["trades"]
    price_match = {
        "5min": match_prints(derive_24h, deribit_24h, name_meta, 5 * 60 * 1000),
        "15min": match_prints(derive_24h, deribit_24h, name_meta, 15 * 60 * 1000),
        "rule": "Derive taker CLOB only (rfq_id empty). Deribit prints with block_rfq_id, block_trade_id, or combo_id excluded. Nearest timestamp, one Deribit print used once. USD price: Derive trade_price; Deribit coin price times that print's index_price unless quote_currency is USD/USDC.",
    }

    programs = derive_post("public/get_maker_programs", {})["result"]
    save_json("derive_maker_programs.json", programs)
    maj = sorted([item for item in programs if item.get("name") == "OPTIONS-MAJ"], key=lambda item: item["start_timestamp"])
    epochs = []
    for index, item in enumerate(maj, start=1):
        epochs.append(
            {
                "epoch": index,
                "start_ms": int(item["start_timestamp"]),
                "end_ms": int(item["end_timestamp"]),
                "start": iso(item["start_timestamp"]),
                "end": iso(item["end_timestamp"]),
                "currencies": ",".join(item.get("currencies") or []),
                "drv_allocation": num((item.get("rewards") or {}).get("DRV")),
                "op_allocation": num((item.get("rewards") or {}).get("OP")),
                "min_notional": item.get("min_notional"),
                "closed": int(item["end_timestamp"]) <= end_ms,
            }
        )
    closed = [item for item in epochs if item["closed"]]
    last3 = closed[-3:]
    score_rows = []
    for item in last3:
        scores = derive_post(
            "public/get_maker_program_scores",
            {"program_name": "OPTIONS-MAJ", "epoch_start_timestamp": item["start_ms"]},
        )["result"]
        wallets = scores.get("scores") or []
        # Raw scores include wallets. Keep them as the API returned them.
        save_gz_json(f"derive_options_maj_epoch_{item['epoch']}_scores.json.gz", scores)
        positive = sum(1 for row in wallets if num(row.get("volume")) > 0)
        reward_keys = [key for key in (wallets[0].keys() if wallets else []) if "reward" in key.lower() or key.lower() in ("drv", "usdc", "op")]
        score_rows.append(
            {
                **item,
                "scored_volume_field": num(scores.get("total_volume")),
                "total_score": num(scores.get("total_score")),
                "wallets_returned": len(wallets),
                "wallets_positive_volume": positive,
                "reward_paid_fields": reward_keys,
            }
        )

    llama_sets = {
        "v2_notional": chart(llama("summary/options/derive-options?dataType=dailyNotionalVolume")),
        "v3_notional": chart(llama("summary/options/derive-v3-options?dataType=dailyNotionalVolume")),
        "v2_fees": chart(llama("summary/fees/derive-options?dataType=dailyFees")),
        "v2_revenue": chart(llama("summary/fees/derive-options?dataType=dailyRevenue")),
        "v3_fees": chart(llama("summary/fees/derive-v3-options?dataType=dailyFees")),
        "v3_revenue": chart(llama("summary/fees/derive-v3-options?dataType=dailyRevenue")),
    }
    # Reward-change epochs: previous allocation differs. Keep the change epoch and the one before it.
    change_ids = []
    for prev, curr in zip(epochs, epochs[1:]):
        if curr["drv_allocation"] != prev["drv_allocation"] or curr["op_allocation"] != prev["op_allocation"]:
            change_ids.extend([prev["epoch"], curr["epoch"]])
    wanted = {item["epoch"] for item in last3} | set(change_ids)
    economics = []
    for item in epochs:
        if item["epoch"] not in wanted:
            continue
        notional = combine_adapter(llama_sets["v2_notional"], llama_sets["v3_notional"], item["start_ms"], item["end_ms"])
        fees = combine_adapter(llama_sets["v2_fees"], llama_sets["v3_fees"], item["start_ms"], item["end_ms"])
        revenue = combine_adapter(llama_sets["v2_revenue"], llama_sets["v3_revenue"], item["start_ms"], item["end_ms"])
        rebate = None
        unit_bps = None
        if notional["sum"] is not None and fees["sum"] is not None and revenue["sum"] is not None and notional["sum"] > 0:
            rebate = fees["sum"] - revenue["sum"]
            unit_bps = rebate / notional["sum"] * 10_000
        economics.append(
            {
                "epoch": item["epoch"],
                "start": item["start"],
                "end": item["end"],
                "closed": item["closed"],
                "drv_allocation": item["drv_allocation"],
                "op_allocation": item["op_allocation"],
                "notional_usd": notional["sum"],
                "notional_missing_days": len(notional["missing_days"]),
                "notional_double_days": notional["double_counted_days"],
                "fees_usd": fees["sum"],
                "fees_missing_days": len(fees["missing_days"]),
                "revenue_usd": revenue["sum"],
                "revenue_missing_days": len(revenue["missing_days"]),
                "rebate_proxy_usd": rebate,
                "rebate_per_notional_bps": unit_bps,
                "fee_per_notional_bps": None
                if notional["sum"] in (None, 0) or fees["sum"] is None
                else fees["sum"] / notional["sum"] * 10_000,
            }
        )

    price = None
    price_error = None
    try:
        gecko = request(
            "GET",
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "derive", "vs_currencies": "usd"},
            timeout=30,
        ).json()
        save_json("coingecko_derive_price.json", gecko)
        price = num((gecko.get("derive") or {}).get("usd"))
    except Exception as exc:  # noqa: BLE001
        price_error = str(exc)

    rewards_doc = {"attempts": []}
    for url in (
        "https://docs.derive.xyz/integrators/programs/institutional-trading-rewards",
        "https://docs.derive.xyz/docs/institutional-trading-rewards-program-1",
    ):
        attempt = {"url": url}
        try:
            page = request("GET", url, timeout=30, ok_status=(200, 404, 403))
            attempt["status"] = page.status_code
            text = page.text
            attempt["body_chars"] = len(text)
            for needle in ("500,000", "1,000,000", "1000000", "500000"):
                attempt[f"contains_{needle}"] = needle in text
            if page.status_code == 200:
                save_bytes("derive_institutional_rewards.html", text.encode()[:2_000_000])
                rewards_doc["attempts"].append(attempt)
                break
        except Exception as exc:  # noqa: BLE001
            attempt["error"] = str(exc)
        rewards_doc["attempts"].append(attempt)

    volumes = []
    for row in books_payload["volumes"]:
        if row.get("currency") in ("BTC", "ETH"):
            volumes.append({key: row.get(key) for key in row})

    results = {
        "generated_at_utc": iso(end_ms),
        "script_start_utc": started,
        "rfq_probe": probe,
        "listing_24h": listing,
        "deribit_book_meta": summarize_books(books, derive_book["tickers"])["deribit_meta"],
        "derive_ticker_errors": derive_book["errors"],
        "derive_ticker_groups": derive_book["groups"],
        "deribit_block_rfq_24h": block,
        "deribit_tape_24h": tape_stats,
        "deribit_trade_volumes": volumes,
        "derive_tape_completeness_30d": completeness,
        "derive_flow": flow,
        "price_match_clob_only": price_match,
        "options_maj_epochs_kept": epochs,
        "options_maj_last3_scores": score_rows,
        "economics": economics,
        "drv_spot_usd": price,
        "drv_spot_error": price_error,
        "institutional_rewards_page": {key: value for key, value in rewards_doc.items() if key != "body"},
        "windows": {"24h": [iso(start_24h), iso(end_ms)], "7d": [iso(start_7d), iso(end_ms)], "30d": [iso(start_30d), iso(end_ms)]},
    }
    save_json("results.json", results)
    (CLEAN / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print("done", iso(end_ms), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
