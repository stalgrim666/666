#!/usr/bin/env python3
"""Pull the free public series that bear on three options questions.

A. TradFi participant role and open/close (Cboe is licensed; OCC and CFTC are
   fetched here and do not answer open/close).
B. Deribit / Coinbase option OI, volume, IV, Block RFQ.
C. Derive premium, notional, OI, RFQ flag, maker-program rewards.

Endpoints and field names below were read from live responses on 2026-10-21
before this script was written. CME is attempted and recorded if it times out.
No API key is used.
"""

from __future__ import annotations

import csv
import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "research-bot/1.0 (options-data-availability; public market data)",
        "Accept": "application/json,text/csv,*/*",
    }
)

OBSERVATIONS: list[dict] = []


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def ms_to_iso(ms: int | float | None) -> str:
    if ms is None:
        return ""
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def add(
    source: str,
    metric: str,
    entity: str,
    value,
    unit: str,
    *,
    asof: str = "",
    window: str = "",
    endpoint: str = "",
    notes: str = "",
) -> None:
    OBSERVATIONS.append(
        {
            "source": source,
            "metric": metric,
            "entity": entity,
            "asof": asof,
            "window": window,
            "value": value,
            "unit": unit,
            "endpoint": endpoint,
            "notes": notes,
        }
    )


def save_raw(name: str, content: bytes | str) -> Path:
    path = RAW / name
    if isinstance(content, str):
        path.write_text(content)
    else:
        path.write_bytes(content)
    return path


def save_json(name: str, obj) -> None:
    save_raw(name, json.dumps(obj, ensure_ascii=False))


def get(url: str, params: dict | None = None, timeout: int = 45) -> requests.Response:
    response = SESSION.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response


def derive_post(method: str, params: dict, timeout: int = 60) -> dict:
    """Derive v3 reads the JSON body as the method params, not a JSON-RPC envelope.

    Posting {"jsonrpc","method","params"} to the same path returns
    "missing field instrument_type" for get_tickers. Verified 2026-10-21.
    """
    url = f"https://api.derive.xyz/v3/{method}"
    response = SESSION.post(url, json=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"{method} {payload['error']}")
    return payload


def num(value) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def _occ_int(value: str) -> int:
    value = (value or "").strip().replace(",", "")
    if value == "":
        return 0
    return int(float(value))


def parse_occ_volume(text: str) -> list[dict]:
    rows = list(csv.reader(text.splitlines()))
    header_idx = next(i for i, row in enumerate(rows) if row and row[0] == "Date")
    header = [cell.strip() for cell in rows[header_idx] if cell.strip()]
    parsed = []
    for row in rows[header_idx + 1 :]:
        if row and row[0].strip() == "Date":
            break
        cells = [cell for cell in row if cell != ""]
        if not cells or not cells[0][:1].isdigit():
            continue
        parsed.append({header[i]: _occ_int(cells[i]) if i else cells[0] for i in range(min(len(header), len(cells)))})
    return parsed


def parse_occ_oi(text: str) -> list[dict]:
    rows = list(csv.reader(text.splitlines()))
    header_idx = next(i for i, row in enumerate(rows) if row and row[0] == "Date")
    top = rows[header_idx]
    sub = rows[header_idx + 1]
    names = ["Date"]
    group = ""
    width = max(len(top), len(sub))
    for i in range(1, width):
        if i < len(top) and top[i].strip():
            group = top[i].strip()
        side = sub[i].strip() if i < len(sub) else ""
        if group and side:
            names.append(f"{group}_{side}")
        elif group:
            names.append(group)
    parsed = []
    for row in rows[header_idx + 2 :]:
        if row and row[0].strip() == "Date":
            break
        cells = [cell for cell in row if cell != ""]
        if not cells or not cells[0][:1].isdigit():
            continue
        item = {"Date": cells[0]}
        for i, name in enumerate(names[1:], start=1):
            if i < len(cells):
                item[name] = _occ_int(cells[i])
        parsed.append(item)
    return parsed


def fetch_occ() -> None:
    source = "OCC"
    volume_url = "https://marketdata.theocc.com/daily-volume-statistics"
    oi_url = "https://marketdata.theocc.com/daily-open-interest"
    # File for a date inside the month returns the month-to-date table.
    report = utc_now().strftime("%Y%m%d")
    volume = get(volume_url, {"reportDate": report, "format": "csv"})
    save_raw(f"occ_volume_{report}.csv", volume.content)
    oi = get(
        oi_url,
        {"reportDate": utc_now().strftime("%m/%d/%Y"), "action": "download", "format": "csv"},
    )
    save_raw(f"occ_oi_{report}.csv", oi.content)
    volume_rows = parse_occ_volume(volume.text)
    oi_rows = parse_occ_oi(oi.text)
    latest_vol = volume_rows[0]
    latest_oi = oi_rows[0]
    asof = str(latest_vol["Date"])
    endpoint = volume_url
    for metric, column in (
        ("equity_contract_volume", "Equity"),
        ("index_other_contract_volume", "Index/Others"),
        ("debt_contract_volume", "Debt"),
        ("futures_contract_volume", "Futures"),
        ("occ_total_contract_volume", "OCC Total"),
    ):
        add(
            source,
            metric,
            "OCC listed options",
            int(latest_vol[column]),
            "contracts",
            asof=asof,
            window="exchange session date",
            endpoint=endpoint,
            notes="Aggregate contracts. No customer type, no open/close, no notional.",
        )
    asof_oi = str(latest_oi["Date"])
    for metric, column in (
        ("equity_call_oi", "Equity_Calls"),
        ("equity_put_oi", "Equity_Puts"),
        ("equity_total_oi", "Equity_Total"),
        ("index_other_call_oi", "Index/Other_Calls"),
        ("index_other_put_oi", "Index/Other_Puts"),
        ("index_other_total_oi", "Index/Other_Total"),
        ("futures_oi", "Futures_Total"),
        ("occ_total_oi", "OCC Total"),
    ):
        add(
            source,
            metric,
            "OCC listed options",
            int(float(latest_oi[column])),
            "contracts",
            asof=asof_oi,
            window="exchange session date",
            endpoint=oi_url,
            notes="Aggregate open interest in contracts. No customer type and no open/close.",
        )


def fetch_cftc() -> None:
    source = "CFTC TFF"
    datasets = {
        "combined": "https://publicreporting.cftc.gov/resource/yw9f-hn96.json",
        "futures_only": "https://publicreporting.cftc.gov/resource/gpe5-46if.json",
    }
    where = "contract_market_name in('BITCOIN','MICRO BITCOIN')"
    frames = []
    for label, url in datasets.items():
        response = get(
            url,
            {
                "$where": where,
                "$order": "report_date_as_yyyy_mm_dd DESC",
                "$limit": 8,
            },
        )
        rows = response.json()
        save_json(f"cftc_tff_{label}_bitcoin.json", rows)
        for row in rows:
            row["_dataset"] = label
        frames.extend(rows)
        add(
            source,
            "rows_returned",
            label,
            len(rows),
            "rows",
            endpoint=url,
            notes="SODA filter contract_market_name BITCOIN and MICRO BITCOIN. No API key.",
        )
    if not frames:
        raise RuntimeError("CFTC query returned no bitcoin rows")
    latest_date = max(row["report_date_as_yyyy_mm_dd"] for row in frames)
    categories = (
        ("dealer", "dealer_positions_long_all", "dealer_positions_short_all", "dealer_positions_spread_all", "pct_of_oi_dealer_long_all", "pct_of_oi_dealer_short_all", "pct_of_oi_dealer_spread_all"),
        ("asset_manager", "asset_mgr_positions_long", "asset_mgr_positions_short", "asset_mgr_positions_spread", "pct_of_oi_asset_mgr_long", "pct_of_oi_asset_mgr_short", "pct_of_oi_asset_mgr_spread"),
        ("leveraged_funds", "lev_money_positions_long", "lev_money_positions_short", "lev_money_positions_spread", "pct_of_oi_lev_money_long", "pct_of_oi_lev_money_short", "pct_of_oi_lev_money_spread"),
        ("other_reportables", "other_rept_positions_long", "other_rept_positions_short", "other_rept_positions_spread", "pct_of_oi_other_rept_long", "pct_of_oi_other_rept_short", "pct_of_oi_other_rept_spread"),
        ("nonreportable", "nonrept_positions_long_all", "nonrept_positions_short_all", None, "pct_of_oi_nonrept_long_all", "pct_of_oi_nonrept_short_all", None),
    )
    for row in frames:
        if row["report_date_as_yyyy_mm_dd"] != latest_date:
            continue
        entity = row["market_and_exchange_names"].strip()
        report = row.get("futonly_or_combined") or row["_dataset"]
        asof = row["report_date_as_yyyy_mm_dd"][:10]
        endpoint = datasets["combined" if row["_dataset"] == "combined" else "futures_only"]
        add(
            source,
            "open_interest_all",
            entity,
            num(row["open_interest_all"]),
            f"contracts; {row.get('contract_units','').strip()}",
            asof=asof,
            window="COT report week, positions as of Tuesday",
            endpoint=endpoint,
            notes=f"futonly_or_combined={report}. Combined is futures plus delta-adjusted options, not an options-only position. Not volume and not open/close.",
        )
        for name, long_col, short_col, spread_col, pct_long, pct_short, pct_spread in categories:
            add(source, f"{name}_long_contracts", entity, num(row[long_col]), "contracts", asof=asof, window=report, endpoint=endpoint, notes="Gross long bucket. Spread is a separate column and is already part of how CFTC builds each side.")
            add(source, f"{name}_short_contracts", entity, num(row[short_col]), "contracts", asof=asof, window=report, endpoint=endpoint, notes="Gross short bucket.")
            add(source, f"{name}_long_pct_of_oi", entity, num(row[pct_long]), "percent_of_open_interest", asof=asof, window=report, endpoint=endpoint, notes="Published percent. Do not add long and short into one share. Nonreportable is not retail.")
            add(source, f"{name}_short_pct_of_oi", entity, num(row[pct_short]), "percent_of_open_interest", asof=asof, window=report, endpoint=endpoint, notes="Published percent of the short side.")
            if spread_col and pct_spread and spread_col in row and row.get(spread_col) is not None:
                add(source, f"{name}_spread_contracts", entity, num(row[spread_col]), "contracts", asof=asof, window=report, endpoint=endpoint, notes="CFTC spreading bucket. This is not a measure of hedged-versus-independent option demand.")
                add(source, f"{name}_spread_pct_of_oi", entity, num(row[pct_spread]), "percent_of_open_interest", asof=asof, window=report, endpoint=endpoint, notes="Published spreading percent. Not an independent-versus-paired split.")
        add(
            source,
            "traders_total",
            entity,
            num(row["traders_tot_all"]),
            "reporting_and_nonreporting_trader_count",
            asof=asof,
            window=report,
            endpoint=endpoint,
            notes="Count of traders in the COT aggregation, not a retail census.",
        )


def fetch_cftc_options_only_probe() -> None:
    url = "https://www.cftc.gov/files/dea/history/opt_disagg_txt_2026.zip"
    try:
        response = SESSION.get(url, timeout=30)
        code = response.status_code
    except requests.RequestException as exc:
        code = f"error:{exc.__class__.__name__}"
    add(
        "CFTC",
        "options_only_history_zip_http_status",
        "opt_disagg_txt_2026.zip",
        code,
        "http_status",
        endpoint=url,
        notes="Conventional options-only filename. Public reporting catalog also has no Options-only COT view. Combined-minus-futures-only is not a substitute series.",
    )
    catalog_url = "https://publicreporting.cftc.gov/api/views.json?$limit=50"
    catalog = get("https://publicreporting.cftc.gov/api/views.json", {"$limit": 50})
    save_json("cftc_publicreporting_views.json", catalog.json())
    names = [item.get("name") for item in catalog.json()]
    add(
        "CFTC",
        "publicreporting_view_names",
        "catalog",
        " | ".join(names),
        "dataset_names",
        endpoint=catalog_url,
        notes="No view name contains Options Only. TFF and Disaggregated views are Futures Only or Combined.",
    )


def fetch_cme() -> None:
    url = "https://www.cmegroup.com/"
    started = time.time()
    try:
        response = SESSION.get(url, timeout=12)
        elapsed = round(time.time() - started, 2)
        save_raw("cme_homepage_status.txt", f"{response.status_code} {len(response.content)} {elapsed}\n")
        add(
            "CME",
            "homepage_http_status",
            "www.cmegroup.com",
            response.status_code,
            "http_status",
            endpoint=url,
            notes=f"Connected in {elapsed}s, {len(response.content)} bytes. This does not by itself yield BTC option versus future volume.",
        )
    except requests.RequestException as exc:
        elapsed = round(time.time() - started, 2)
        save_raw("cme_homepage_status.txt", f"ERROR {exc.__class__.__name__} {exc} after {elapsed}s\n")
        add(
            "CME",
            "homepage_fetch",
            "www.cmegroup.com",
            "failed",
            "status",
            endpoint=url,
            notes=f"{exc.__class__.__name__} after {elapsed}s. No CME volume or open-interest fields were observed. DataMine was not used.",
        )


def fetch_coinbase_instruments() -> None:
    url = "https://api.international.coinbase.com/api/v1/instruments"
    response = get(url, timeout=40)
    # Cache is large but it is the evidence that option instruments are absent.
    save_raw("coinbase_international_instruments.json", response.content)
    rows = response.json()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.get("type") or ""] = counts.get(row.get("type") or "", 0) + 1
    add(
        "Coinbase International",
        "instrument_count_by_type",
        "public instruments",
        json.dumps(counts, sort_keys=True),
        "count_by_type",
        endpoint=url,
        notes="No API key. Absence of type=OPTION means this endpoint does not publish option block, RFQ, OI, or customer-type data.",
    )


def fetch_deribit() -> None:
    book_url = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
    volumes_url = "https://www.deribit.com/api/v2/public/get_trade_volumes"
    block_url = "https://www.deribit.com/api/v2/public/get_block_rfq_trades"
    trades_url = "https://www.deribit.com/api/v2/public/get_last_trades_by_currency"

    summaries = {}
    for currency in ("BTC", "ETH"):
        response = get(book_url, {"currency": currency, "kind": "option"})
        payload = response.json()
        save_json(f"deribit_{currency}_option_book_summary.json", payload)
        summaries[currency] = payload["result"]
        rows = payload["result"]
        volume_coin = sum(num(row.get("volume")) for row in rows)
        oi_coin = sum(num(row.get("open_interest")) for row in rows)
        volume_usd_field = sum(num(row.get("volume_usd")) for row in rows)
        notional = sum(num(row.get("volume")) * num(row.get("underlying_price")) for row in rows)
        oi_notional = sum(num(row.get("open_interest")) * num(row.get("underlying_price")) for row in rows)
        iv_weight = 0.0
        iv_oi = 0.0
        for row in rows:
            oi = num(row.get("open_interest"))
            iv = row.get("mark_iv")
            if oi > 0 and iv is not None:
                iv_weight += oi * num(iv)
                iv_oi += oi
        asof = ms_to_iso(rows[0]["creation_timestamp"]) if rows else ""
        notes = (
            "Docs: option open_interest and volume are in underlying base-currency coin, one-sided contracts. "
            "volume_usd is documented only as 'Volume in USD' and is not equal to volume times underlying_price. "
            "Computed notional uses volume or open_interest times underlying_price. No customer type."
        )
        add("Deribit", "option_contracts", f"{currency} options", len(rows), "instruments", asof=asof, window="snapshot", endpoint=book_url, notes=notes)
        add("Deribit", "option_oi_base_coin", f"{currency} options", oi_coin, "base_currency_coin", asof=asof, window="open interest snapshot", endpoint=book_url, notes=notes)
        add("Deribit", "option_oi_notional_computed", f"{currency} options", oi_notional, "usd_notional_computed", asof=asof, window="open interest snapshot", endpoint=book_url, notes=notes)
        add("Deribit", "option_volume_24h_base_coin", f"{currency} options", volume_coin, "base_currency_coin", asof=asof, window="trailing 24h", endpoint=book_url, notes=notes)
        add("Deribit", "option_volume_usd_field_24h", f"{currency} options", volume_usd_field, "usd_as_returned", asof=asof, window="trailing 24h", endpoint=book_url, notes=notes)
        add("Deribit", "option_notional_24h_computed", f"{currency} options", notional, "usd_notional_computed", asof=asof, window="trailing 24h", endpoint=book_url, notes=notes)
        if iv_oi:
            add("Deribit", "oi_weighted_mark_iv", f"{currency} options", iv_weight / iv_oi, "percent_mark_iv", asof=asof, window="snapshot, weight=open_interest coin", endpoint=book_url, notes="mark_iv on this API is in percent, for the mark price. Not a tradable forecast.")

    btc_rows = summaries["BTC"]
    sample = max(btc_rows, key=lambda row: num(row.get("volume")))
    computed = num(sample.get("volume")) * num(sample.get("underlying_price"))
    add(
        "Deribit",
        "volume_usd_unit_check",
        sample.get("instrument_name"),
        json.dumps(
            {
                "volume_base": sample.get("volume"),
                "underlying_price": sample.get("underlying_price"),
                "volume_times_underlying": computed,
                "volume_usd_field": sample.get("volume_usd"),
                "mark_price_btc": sample.get("mark_price"),
            }
        ),
        "one_instrument",
        asof=ms_to_iso(sample.get("creation_timestamp")),
        endpoint=book_url,
        notes="Shows that volume_usd is not the coin notional. Do not relabel it.",
    )

    for currency in ("BTC", "ETH"):
        payload = get(book_url, {"currency": currency, "kind": "future"}).json()
        save_json(f"deribit_{currency}_future_book_summary.json", payload)
        rows = payload["result"]
        if not rows:
            continue
        perp = next((row for row in rows if row.get("instrument_name") == f"{currency}-PERPETUAL"), rows[0])
        add(
            "Deribit",
            "future_volume_24h_base",
            f"{currency} futures",
            sum(num(row.get("volume")) for row in rows),
            "base_currency_per_docs",
            asof=ms_to_iso(perp.get("creation_timestamp")),
            window="trailing 24h",
            endpoint=book_url + "?kind=future",
            notes=f"Sample {perp.get('instrument_name')} base={perp.get('base_currency')} quote={perp.get('quote_currency')}. Docs: volume is 24h volume in base currency. Sum of this field matches get_trade_volumes futures_volume for the same currency.",
        )
        add(
            "Deribit",
            "future_volume_usd_field_24h",
            f"{currency} futures",
            sum(num(row.get("volume_usd")) for row in rows),
            "usd_as_returned",
            asof=ms_to_iso(perp.get("creation_timestamp")),
            window="trailing 24h",
            endpoint=book_url + "?kind=future",
            notes="On futures this USD field is the same order of magnitude as base volume times mark price. On options the same field name is not base volume times underlying. Do not put the two volume_usd sums in one ratio.",
        )
        add(
            "Deribit",
            "future_open_interest_field",
            f"{currency} futures",
            sum(num(row.get("open_interest")) for row in rows),
            "open_interest_field",
            asof=ms_to_iso(perp.get("creation_timestamp")),
            window="snapshot",
            endpoint=book_url + "?kind=future",
            notes="Docs: perpetual and inverse future open interest is in USD; option open interest is in underlying coin. The two open-interest sums are not a ratio until that unit difference is applied. This row stores the raw sum.",
        )
        add(
            "Deribit",
            "perpetual_open_interest_field",
            perp.get("instrument_name"),
            perp.get("open_interest"),
            "open_interest_field",
            asof=ms_to_iso(perp.get("creation_timestamp")),
            endpoint=book_url + "?kind=future",
            notes="Single instrument inside the future sum. Inverse perpetual open interest is documented as USD.",
        )

    volumes = get(volumes_url, {"extended": "true"}).json()
    save_json("deribit_trade_volumes.json", volumes)
    for row in volumes["result"]:
        if row.get("currency") not in ("BTC", "ETH"):
            continue
        for field in (
            "calls_volume",
            "puts_volume",
            "futures_volume",
            "calls_volume_7d",
            "puts_volume_7d",
            "futures_volume_7d",
            "calls_volume_30d",
            "puts_volume_30d",
            "futures_volume_30d",
        ):
            add(
                "Deribit",
                field,
                row["currency"],
                row.get(field),
                "undocumented_unit",
                window=field,
                endpoint=volumes_url,
                notes="Docs say total trade volume for calls, puts, or futures and do not state the unit. Calls plus puts are the same order of magnitude as the option book-summary base-currency volume. Futures are not divided into an options/futures ratio.",
            )

    now_ms = int(time.time() * 1000)
    day_ago = now_ms - 24 * 60 * 60 * 1000
    for currency in ("BTC", "ETH"):
        pages = []
        continuation = None
        for _ in range(8):
            params = {"currency": currency, "count": 50}
            if continuation:
                params["continuation"] = continuation
            payload = get(block_url, params).json()
            pages.append(payload)
            block_rfqs = payload["result"]["block_rfqs"]
            if not block_rfqs:
                break
            oldest = min(item["timestamp"] for item in block_rfqs)
            continuation = payload["result"].get("continuation")
            if oldest < day_ago or not continuation:
                break
        save_json(f"deribit_{currency}_block_rfq_trades.json", pages)
        flat = [item for page in pages for item in page["result"]["block_rfqs"]]
        in_window = [item for item in flat if item["timestamp"] >= day_ago]
        timestamps = [item["timestamp"] for item in in_window]
        package_coin = sum(num(item.get("amount")) for item in in_window)
        add(
            "Deribit",
            "block_rfq_count",
            f"{currency} options",
            len(in_window),
            "block_rfq_packages",
            asof=iso(),
            window=f"{ms_to_iso(min(timestamps)) if timestamps else ''} .. {ms_to_iso(max(timestamps)) if timestamps else ''} within trailing 24h",
            endpoint=block_url,
            notes="Public Block RFQ prints only. count must be 10..50 on the live API even though the published schema says 1000. Package amount is not leg-expanded notional and is not an institutional volume share. Non-RFQ block trades are not in this endpoint.",
        )
        add(
            "Deribit",
            "block_rfq_package_amount",
            f"{currency} options",
            package_coin,
            "package_amount_field",
            asof=iso(),
            window="trailing 24h of returned pages",
            endpoint=block_url,
            notes="Sum of the RFQ amount field, not sum of leg sizes. A ratio to tape volume is not computed.",
        )

    for currency in ("BTC", "ETH"):
        payload = get(trades_url, {"currency": currency, "kind": "option", "count": 1000}).json()
        save_json(f"deribit_{currency}_last_option_trades.json", payload)
        trades = payload["result"]["trades"]
        flagged = 0
        for trade in trades:
            if trade.get("block_trade_id") or trade.get("block_rfq_id") or trade.get("block_trade_leg_count"):
                flagged += 1
        stamps = [trade["timestamp"] for trade in trades]
        add(
            "Deribit",
            "recent_option_trades",
            f"{currency} options",
            len(trades),
            "trades",
            asof=iso(),
            window=f"{ms_to_iso(min(stamps))} .. {ms_to_iso(max(stamps))}" if stamps else "",
            endpoint=trades_url,
            notes="Most recent trades returned with count=1000. Not a full day.",
        )
        add(
            "Deribit",
            "recent_option_trades_with_block_fields",
            f"{currency} options",
            flagged,
            "trades",
            asof=iso(),
            window="same recent page",
            endpoint=trades_url,
            notes="Count of trades whose payload includes block_trade_id, block_rfq_id, or block_trade_leg_count. Docs say those fields appear when the trade was part of a block. This page rate is not the day's block share and is not an institutional share.",
        )


def fetch_derive() -> None:
    ticker_url = "https://api.derive.xyz/v3/public/get_tickers"
    trade_url = "https://api.derive.xyz/v3/public/get_trade_history"
    program_url = "https://api.derive.xyz/v3/public/get_maker_programs"
    score_url = "https://api.derive.xyz/v3/public/get_maker_program_scores"
    live = derive_post("public/get_all_live_instruments", {})
    names = live["result"]
    save_json("derive_live_instrument_names.json", names)
    groups: dict[tuple[str, str], int] = {}
    for name in names:
        parts = name.split("-")
        if len(parts) < 4 or parts[-1] not in ("C", "P"):
            continue
        expiry = parts[1]
        if len(expiry) != 8 or not expiry.isdigit():
            continue
        key = (parts[0], expiry)
        groups[key] = groups.get(key, 0) + 1

    def one_group(item: tuple[str, str]) -> tuple[str, str, dict]:
        currency, expiry = item
        payload = derive_post(
            "public/get_tickers",
            {"instrument_type": "option", "currency": currency, "expiry_date": int(expiry)},
        )
        return currency, expiry, payload["result"]["tickers"]

    tickers: dict[str, dict] = {}
    errors = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(one_group, item) for item in groups]
        for future in as_completed(futures):
            try:
                currency, expiry, book = future.result()
            except Exception as exc:  # noqa: BLE001 - keep the rest of the pull
                errors.append(str(exc))
                continue
            for name, ticker in book.items():
                ticker["_currency"] = currency
                ticker["_expiry"] = expiry
                tickers[name] = ticker
    save_json(
        "derive_option_tickers.json",
        {"errors": errors, "n_groups": len(groups), "tickers": tickers},
    )
    add(
        "Derive",
        "ticker_groups_requested",
        "all listed options",
        len(groups),
        "currency_expiry_groups",
        endpoint=ticker_url,
        notes=f"Failed groups: {len(errors)}. Body is the params object, not a JSON-RPC envelope.",
    )

    ticker_totals = {}
    buckets = {"BTC": [], "ETH": [], "OTHER": [], "ALL": []}
    for name, ticker in tickers.items():
        buckets["ALL"].append(ticker)
        currency = ticker["_currency"]
        buckets["BTC" if currency == "BTC" else "ETH" if currency == "ETH" else "OTHER"].append(ticker)

    snapshot_ms = max((num(ticker.get("t")) for ticker in tickers.values()), default=0)
    asof = ms_to_iso(snapshot_ms) if snapshot_ms else iso()
    for label, rows in buckets.items():
        oi = sum(num((row.get("stats") or {}).get("oi")) for row in rows)
        notional = sum(num((row.get("stats") or {}).get("v")) for row in rows)
        premium = sum(num((row.get("stats") or {}).get("pr")) for row in rows)
        contracts = sum(num((row.get("stats") or {}).get("c")) for row in rows)
        oi_notional = 0.0
        iv_weight = 0.0
        iv_base = 0.0
        for row in rows:
            stats = row.get("stats") or {}
            oi_i = num(stats.get("oi"))
            notion = oi_i * num(row.get("I"))
            oi_notional += notion
            iv = (row.get("option_pricing") or {}).get("i")
            if notion > 0 and iv is not None:
                iv_weight += notion * num(iv)
                iv_base += notion
        base_notes = (
            "stats.v is documented as notional volume over the last 24h; stats.pr as premium volume; "
            "stats.oi as current total open interest; stats.c as contracts traded. "
            "Contract counts are not comparable across currencies: altcoins can show very large oi with a small index. "
            "OI notional is oi times index field I. IV is weighted by that notional, and option_pricing.i is a decimal. "
            "No customer type and no independent-versus-hedge split."
        )
        add("Derive", "instruments", f"{label} options", len(rows), "instruments", asof=asof, window="snapshot", endpoint=ticker_url, notes=base_notes)
        add("Derive", "open_interest_contracts", f"{label} options", oi, "contracts_field_oi", asof=asof, window="snapshot", endpoint=ticker_url, notes=base_notes)
        add("Derive", "open_interest_notional_computed", f"{label} options", oi_notional, "usd_notional_computed", asof=asof, window="snapshot", endpoint=ticker_url, notes=base_notes)
        add("Derive", "notional_volume_24h", f"{label} options", notional, "usd_field_stats_v", asof=asof, window="trailing 24h per ticker", endpoint=ticker_url, notes=base_notes)
        add("Derive", "premium_volume_24h", f"{label} options", premium, "usd_field_stats_pr", asof=asof, window="trailing 24h per ticker", endpoint=ticker_url, notes=base_notes)
        add("Derive", "contracts_traded_24h", f"{label} options", contracts, "contracts_field_stats_c", asof=asof, window="trailing 24h per ticker", endpoint=ticker_url, notes=base_notes)
        ticker_totals[label] = {"notional": notional, "premium": premium}
        if iv_base:
            add("Derive", "notional_weighted_iv", f"{label} options", iv_weight / iv_base, "decimal_iv", asof=asof, window="snapshot, weight=oi*index", endpoint=ticker_url, notes=base_notes)

    now_ms = int(time.time() * 1000)
    start_ms = now_ms - 24 * 60 * 60 * 1000
    trades = []
    page = 1
    num_pages = 1
    while page <= num_pages and page <= 20:
        payload = derive_post(
            "public/get_trade_history",
            {
                "instrument_type": "option",
                "from_timestamp": start_ms,
                "to_timestamp": now_ms,
                "page": page,
                "page_size": 1000,
            },
        )
        result = payload["result"]
        num_pages = int(result["pagination"]["num_pages"])
        trades.extend(result["trades"])
        page += 1
    # One economic trade is printed twice, once for the maker and once for the taker.
    dedup = {}
    for trade in trades:
        if not (start_ms <= int(trade["timestamp"]) <= now_ms):
            continue
        if not str(trade["instrument_name"]).endswith(("-C", "-P")):
            continue
        key = (trade["trade_id"], trade["liquidity_role"], trade.get("subaccount_id"))
        dedup[key] = trade
    clean = list(dedup.values())
    # Cache without treating wallets as a user census. Raw tape is what the API returned.
    save_json(
        "derive_option_trades_24h.json",
        {
            "from_timestamp": start_ms,
            "to_timestamp": now_ms,
            "n_raw_rows": len(trades),
            "n_dedup_rows": len(clean),
            "trades": clean,
        },
    )
    taker = [trade for trade in clean if trade.get("liquidity_role") == "taker"]

    def currency_of(name: str) -> str:
        head = name.split("-", 1)[0]
        if head in ("BTC", "ETH"):
            return head
        return "OTHER"

    def accumulate(subset: list[dict]) -> dict:
        out = {
            "matches": len(subset),
            "rfq_matches": 0,
            "notional": 0.0,
            "premium_px_times_amount": 0.0,
            "rfq_notional": 0.0,
            "rfq_premium": 0.0,
            "wallets": set(),
        }
        for trade in subset:
            amount = num(trade.get("trade_amount"))
            notional = amount * num(trade.get("index_price"))
            premium = amount * num(trade.get("trade_price"))
            is_rfq = bool(trade.get("rfq_id"))
            out["notional"] += notional
            out["premium_px_times_amount"] += premium
            if is_rfq:
                out["rfq_matches"] += 1
                out["rfq_notional"] += notional
                out["rfq_premium"] += premium
            if trade.get("wallet"):
                out["wallets"].add(trade["wallet"])
        return out

    grouped = {"ALL": taker, "BTC": [], "ETH": [], "OTHER": []}
    for trade in taker:
        grouped[currency_of(trade["instrument_name"])].append(trade)
    for label, subset in grouped.items():
        stats = accumulate(subset)
        notes = (
            "Taker rows only, so the maker copy of the same trade_id is not counted twice. "
            "RFQ means rfq_id is non-null. That is an execution channel, not an institutional share and not a customer type. "
            "Notional is trade_amount times index_price. Premium candidate is trade_amount times trade_price; compare with ticker stats.pr before treating the unit as settled. "
            "Distinct wallets are addresses that traded in this window, not registered users."
        )
        add("Derive", "taker_matches_24h", f"{label} options", stats["matches"], "taker_trades", asof=iso(), window="trailing 24h", endpoint=trade_url, notes=notes)
        add("Derive", "taker_rfq_matches_24h", f"{label} options", stats["rfq_matches"], "taker_trades", asof=iso(), window="trailing 24h", endpoint=trade_url, notes=notes)
        if stats["matches"]:
            add("Derive", "taker_rfq_match_share_24h", f"{label} options", stats["rfq_matches"] / stats["matches"], "share_of_taker_trades", asof=iso(), window="trailing 24h", endpoint=trade_url, notes=notes)
        add("Derive", "taker_notional_24h", f"{label} options", stats["notional"], "amount_times_index_price", asof=iso(), window="trailing 24h", endpoint=trade_url, notes=notes)
        add("Derive", "taker_premium_amount_times_price_24h", f"{label} options", stats["premium_px_times_amount"], "amount_times_trade_price", asof=iso(), window="trailing 24h", endpoint=trade_url, notes=notes)
        if stats["notional"]:
            add("Derive", "taker_rfq_notional_share_24h", f"{label} options", stats["rfq_notional"] / stats["notional"], "share_of_taker_notional", asof=iso(), window="trailing 24h", endpoint=trade_url, notes=notes)
        add("Derive", "distinct_taker_wallets_24h", f"{label} options", len(stats["wallets"]), "wallets_in_window", asof=iso(), window="trailing 24h", endpoint=trade_url, notes="Not a user census, not DAU, and not a professional-versus-retail split.")
        ticker_side = ticker_totals.get(label)
        if ticker_side and ticker_side["premium"]:
            add(
                "Derive",
                "tape_premium_over_ticker_premium",
                f"{label} options",
                stats["premium_px_times_amount"] / ticker_side["premium"],
                "ratio",
                asof=iso(),
                window="trade pull trailing 24h versus sum of ticker stats.pr",
                endpoint=trade_url,
                notes="Near 1 means trade_amount times trade_price is the same USD premium as stats.pr. The windows are not identical, so the ratio is a unit check, not a restatement of volume.",
            )
        if ticker_side and ticker_side["notional"]:
            add(
                "Derive",
                "tape_notional_over_ticker_notional",
                f"{label} options",
                stats["notional"] / ticker_side["notional"],
                "ratio",
                asof=iso(),
                window="trade pull trailing 24h versus sum of ticker stats.v",
                endpoint=trade_url,
                notes="Taker notional is trade_amount times index_price. A ratio near 1 supports that unit. It is not a second independent volume print.",
            )

    programs = derive_post("public/get_maker_programs", {})["result"]
    save_json("derive_maker_programs.json", programs)
    now_ms = int(time.time() * 1000)
    option_major = [item for item in programs if item.get("name") == "OPTIONS-MAJ"]
    open_epochs = [item for item in option_major if item["start_timestamp"] <= now_ms < item["end_timestamp"]]
    closed = [item for item in option_major if item["end_timestamp"] <= now_ms]
    closed.sort(key=lambda item: item["end_timestamp"])
    add(
        "Derive",
        "options_maj_epochs_returned",
        "OPTIONS-MAJ",
        len(option_major),
        "epochs",
        endpoint=program_url,
        notes="Every returned OPTIONS-MAJ epoch includes a DRV reward. The list does not contain a pre-incentive BTC/ETH options epoch, so before-versus-after incentive volume is not identified.",
    )
    if open_epochs:
        current = open_epochs[-1]
        add(
            "Derive",
            "options_maj_current_reward_drv",
            "OPTIONS-MAJ",
            num((current.get("rewards") or {}).get("DRV")),
            "DRV_tokens_allocated",
            asof=iso(),
            window=f"{ms_to_iso(current['start_timestamp'])} .. {ms_to_iso(current['end_timestamp'])}",
            endpoint=program_url,
            notes=f"Currencies={current.get('currencies')}. Reward allocation is not volume and is not a rebate already paid.",
        )
    if closed:
        previous = closed[-1]
        scores = derive_post(
            "public/get_maker_program_scores",
            {
                "program_name": previous["name"],
                "epoch_start_timestamp": previous["start_timestamp"],
            },
        )["result"]
        wallet_rows = scores.get("scores") or []
        nonzero = sum(1 for row in wallet_rows if num(row.get("volume")) > 0)
        save_json(
            "derive_options_maj_previous_epoch_score_totals.json",
            {
                "program_name": previous["name"],
                "start_timestamp": previous["start_timestamp"],
                "end_timestamp": previous["end_timestamp"],
                "currencies": previous.get("currencies"),
                "rewards": previous.get("rewards"),
                "total_volume": scores.get("total_volume"),
                "total_score": scores.get("total_score"),
                "n_wallets": len(wallet_rows),
                "n_wallets_with_positive_volume": nonzero,
            },
        )
        add(
            "Derive",
            "options_maj_scored_volume",
            "OPTIONS-MAJ previous closed epoch",
            num(scores.get("total_volume")),
            "program_total_volume_field",
            window=f"{ms_to_iso(previous['start_timestamp'])} .. {ms_to_iso(previous['end_timestamp'])}",
            endpoint=score_url,
            notes="Maker-program scored volume for wallets in that epoch. Not venue-wide option volume, not organic volume with incentives removed, and not a user census. Wallet rows were not written to the observation file.",
        )
        add(
            "Derive",
            "options_maj_wallets_with_positive_scored_volume",
            "OPTIONS-MAJ previous closed epoch",
            nonzero,
            "wallets",
            window=f"{ms_to_iso(previous['start_timestamp'])} .. {ms_to_iso(previous['end_timestamp'])}",
            endpoint=score_url,
            notes="Makers with positive program volume. Not the number of option users.",
        )


def fetch_defillama() -> None:
    specs = (
        (
            "daily_notional",
            "https://api.llama.fi/summary/options/derive-v3-options?dataType=dailyNotionalVolume",
            "derive_v3_notional.json",
        ),
        (
            "daily_premium",
            "https://api.llama.fi/summary/options/derive-v3-options?dataType=dailyPremiumVolume",
            "derive_v3_premium.json",
        ),
        (
            "open_interest",
            "https://api.llama.fi/summary/open-interest/derive-v3-options",
            "derive_v3_open_interest.json",
        ),
        (
            "v2_daily_notional",
            "https://api.llama.fi/summary/options/derive-options?dataType=dailyNotionalVolume",
            "derive_v2_notional.json",
        ),
    )
    for metric, url, filename in specs:
        payload = get(url).json()
        chart = payload.get("totalDataChart") or []
        # Keep the raw chart; it is the series.
        save_json(filename, payload)
        latest = chart[-1] if chart else None
        methodology = payload.get("methodology") or {}
        if isinstance(methodology, dict):
            method_text = json.dumps(methodology, ensure_ascii=False)
        else:
            method_text = str(methodology)
        add(
            "DefiLlama",
            metric + "_latest_total24h_field",
            payload.get("name") or metric,
            payload.get("total24h"),
            "usd_api_field_total24h",
            asof=ms_to_iso(latest[0] * 1000) if latest else "",
            window="latest chart day" if metric != "open_interest" else "latest open-interest point; field name is total24h",
            endpoint=url.split("?")[0],
            notes=f"dataType or summary kind is in the URL. Methodology={method_text[:500]}. Secondary aggregator, not the venue. V2 and V3 are separate slugs.",
        )
        if latest:
            add(
                "DefiLlama",
                metric + "_latest_chart_point",
                payload.get("name") or metric,
                latest[1],
                "usd",
                asof=ms_to_iso(latest[0] * 1000),
                window="one daily point",
                endpoint=url,
                notes="Chart timestamp is unix seconds. For open interest, DefiLlama's methodology string on this response says one side is counted.",
            )
        add(
            "DefiLlama",
            metric + "_chart_points",
            payload.get("name") or metric,
            len(chart),
            "days",
            endpoint=url,
            notes="Short V3 history should not be spliced onto the V2 chart without labeling the break.",
        )


def main() -> None:
    steps = (
        ("occ", fetch_occ),
        ("cftc", fetch_cftc),
        ("cftc_options_only_probe", fetch_cftc_options_only_probe),
        ("cme", fetch_cme),
        ("coinbase", fetch_coinbase_instruments),
        ("deribit", fetch_deribit),
        ("derive", fetch_derive),
        ("defillama", fetch_defillama),
    )
    failures = []
    for name, func in steps:
        print(f"== {name} ==")
        try:
            func()
        except Exception as exc:  # noqa: BLE001 - one source should not drop the others
            failures.append({"step": name, "error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc()})
            add("fetch", "step_failed", name, exc.__class__.__name__, "error", notes=str(exc)[:500])
            print(failures[-1]["trace"])
    frame = pd.DataFrame(OBSERVATIONS)
    columns = ["source", "metric", "entity", "asof", "window", "value", "unit", "endpoint", "notes"]
    frame = frame.reindex(columns=columns)
    out = ROOT / "observations.csv"
    frame.to_csv(out, index=False)
    save_json(
        "run_meta.json",
        {
            "retrieved_at_utc": iso(),
            "n_observations": int(len(frame)),
            "failures": failures,
        },
    )
    print(f"wrote {out} rows={len(frame)} failures={len(failures)}")


if __name__ == "__main__":
    main()
