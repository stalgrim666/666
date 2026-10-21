#!/usr/bin/env python3
"""One-off supplement. Does not write into outputs/05/raw or observations.csv.

Reads the frozen 24h trade snapshot and maker-program cache. Re-counts that
same window, then pulls the 7d option tape ending at the snapshot's end time.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
SNAP_TRADES = ROOT / "raw" / "derive_option_trades_24h.json"
SNAP_PROGRAMS = ROOT / "raw" / "derive_maker_programs.json"
OUT = ROOT / "supplement"
OUT.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "research-bot/1.0 (derive-supplement; public market data)", "Accept": "application/json"}
)


def iso(ms: int | float) -> str:
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def num(value) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def derive_post(method: str, params: dict) -> dict:
    response = SESSION.post(f"https://api.derive.xyz/v3/{method}", json=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    return payload


def is_option(name: str) -> bool:
    return name.endswith("-C") or name.endswith("-P")


def fetch_window(start_ms: int, end_ms: int, page_size: int = 1000) -> dict:
    trades = []
    page = 1
    declared_pages = None
    declared_count = None
    while True:
        payload = derive_post(
            "public/get_trade_history",
            {
                "instrument_type": "option",
                "from_timestamp": start_ms,
                "to_timestamp": end_ms,
                "page": page,
                "page_size": page_size,
            },
        )
        result = payload["result"]
        declared_pages = int(result["pagination"]["num_pages"])
        declared_count = int(result["pagination"]["count"])
        batch = result["trades"]
        trades.extend(batch)
        if page >= declared_pages or not batch or page >= 40:
            break
        page += 1
    dedup = {}
    for trade in trades:
        if not (start_ms <= int(trade["timestamp"]) <= end_ms):
            continue
        if not is_option(str(trade["instrument_name"])):
            continue
        key = (trade["trade_id"], trade["liquidity_role"], trade.get("subaccount_id"))
        dedup[key] = trade
    clean = list(dedup.values())
    stamps = [int(trade["timestamp"]) for trade in clean]
    return {
        "from_timestamp": start_ms,
        "to_timestamp": end_ms,
        "page_size": page_size,
        "api_num_pages": declared_pages,
        "api_count": declared_count,
        "pages_fetched": page,
        "raw_rows": len(trades),
        "dedup_rows": len(clean),
        "earliest_trade": min(stamps) if stamps else None,
        "latest_trade": max(stamps) if stamps else None,
        "trades": clean,
    }


def channel_stats(trades: list[dict]) -> dict:
    taker = [trade for trade in trades if trade.get("liquidity_role") == "taker"]
    out = {}
    for label, subset in (
        ("RFQ", [trade for trade in taker if trade.get("rfq_id")]),
        ("CLOB", [trade for trade in taker if not trade.get("rfq_id")]),
        ("ALL", taker),
    ):
        notional = 0.0
        premium = 0.0
        by_wallet = defaultdict(float)
        rfq_ids = set()
        for trade in subset:
            amount = num(trade.get("trade_amount"))
            notion = amount * num(trade.get("index_price"))
            notional += notion
            premium += amount * num(trade.get("trade_price"))
            by_wallet[trade.get("wallet") or ""] += notion
            if trade.get("rfq_id"):
                rfq_ids.add(trade["rfq_id"])
        ranked = sorted((value for value in by_wallet.values() if value > 0), reverse=True)
        def share(n: int) -> float | None:
            if notional <= 0:
                return None
            return sum(ranked[:n]) / notional
        out[label] = {
            "taker_legs": len(subset),
            "unique_rfq": len(rfq_ids) if label != "CLOB" else 0,
            "notional": notional,
            "premium": premium,
            "wallets": len(ranked),
            "top5_notional_share": share(5),
            "top10_notional_share": share(10),
        }
    return out


def load_snapshot_trades() -> tuple[dict, list[dict]]:
    payload = json.loads(SNAP_TRADES.read_text())
    trades = [
        trade
        for trade in payload["trades"]
        if is_option(str(trade["instrument_name"]))
        and payload["from_timestamp"] <= int(trade["timestamp"]) <= payload["to_timestamp"]
    ]
    return payload, trades


def options_maj_rows() -> list[dict]:
    programs = json.loads(SNAP_PROGRAMS.read_text())
    epochs = [item for item in programs if item.get("name") == "OPTIONS-MAJ"]
    epochs.sort(key=lambda item: item["start_timestamp"])
    rows = []
    previous = None
    for index, item in enumerate(epochs, start=1):
        drv = num((item.get("rewards") or {}).get("DRV"))
        op = num((item.get("rewards") or {}).get("OP"))
        start = int(item["start_timestamp"])
        end = int(item["end_timestamp"])
        change = None if previous is None else drv - previous
        change_pct = None if not previous else (drv - previous) / previous
        rows.append(
            {
                "epoch": index,
                "start": iso(start),
                "end": iso(end),
                "days": round((end - start) / 86400000, 4),
                "currencies": ",".join(item.get("currencies") or []),
                "drv": drv,
                "op": op,
                "drv_change": change,
                "drv_change_pct": change_pct,
                "min_notional": item.get("min_notional"),
            }
        )
        previous = drv
    return rows


def main() -> None:
    snap, snap_trades = load_snapshot_trades()
    start_ms = int(snap["from_timestamp"])
    end_ms = int(snap["to_timestamp"])
    recount = derive_post(
        "public/get_trade_history",
        {
            "instrument_type": "option",
            "from_timestamp": start_ms,
            "to_timestamp": end_ms,
            "page": 1,
            "page_size": 1000,
        },
    )["result"]["pagination"]
    seven_start = end_ms - 7 * 86400 * 1000
    thirty_start = end_ms - 30 * 86400 * 1000
    thirty = derive_post(
        "public/get_trade_history",
        {
            "instrument_type": "option",
            "from_timestamp": thirty_start,
            "to_timestamp": end_ms,
            "page": 1,
            "page_size": 1,
        },
    )["result"]["pagination"]
    pulled = fetch_window(seven_start, end_ms, page_size=1000)
    cache = dict(pulled)
    (OUT / "derive_option_trades_7d.json").write_text(json.dumps(cache))
    stats_24h = channel_stats(snap_trades)
    stats_7d = channel_stats(pulled["trades"])
    nested = [trade for trade in pulled["trades"] if int(trade["timestamp"]) >= start_ms]
    epochs = options_maj_rows()
    summary = {
        "snapshot_file": str(SNAP_TRADES.relative_to(ROOT)),
        "window_24h": {"from": iso(start_ms), "to": iso(end_ms), "from_ms": start_ms, "to_ms": end_ms},
        "completeness_24h": {
            "api_count_rechecked": recount["count"],
            "api_num_pages_at_page_size_1000": recount["num_pages"],
            "snapshot_raw_rows": snap["n_raw_rows"],
            "snapshot_dedup_rows": snap["n_dedup_rows"],
            "snapshot_rows_in_file": len(snap["trades"]),
            "snapshot_earliest": iso(min(int(t["timestamp"]) for t in snap_trades)),
            "snapshot_latest": iso(max(int(t["timestamp"]) for t in snap_trades)),
            "inferred_pages_fetched": 3,
            "note": "The frozen file did not store page count. Same-window recount count equals the frozen row count, and 2636 rows at page_size 1000 is 3 pages. The original loop cap was 20.",
        },
        "window_7d": {
            "from": iso(seven_start),
            "to": iso(end_ms),
            "api_count": pulled["api_count"],
            "api_num_pages": pulled["api_num_pages"],
            "pages_fetched": pulled["pages_fetched"],
            "raw_rows": pulled["raw_rows"],
            "dedup_rows": pulled["dedup_rows"],
            "earliest": iso(pulled["earliest_trade"]),
            "latest": iso(pulled["latest_trade"]),
            "rows_inside_frozen_24h": len(nested),
        },
        "window_30d_count_only": {
            "from": iso(thirty_start),
            "to": iso(end_ms),
            "api_count_at_page_size_1": thirty["count"],
            "api_num_pages_at_page_size_1": thirty["num_pages"],
            "fetched": False,
        },
        "channels_24h_snapshot": stats_24h,
        "channels_7d": stats_7d,
        "options_maj_epochs": epochs,
        "program_names_in_cache": sorted({item["name"] for item in json.loads(SNAP_PROGRAMS.read_text())}),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in summary if k != "options_maj_epochs"}, indent=2)[:4000])
    print("epochs", len(epochs), "first", epochs[0]["start"], epochs[0]["drv"], "last", epochs[-1])


if __name__ == "__main__":
    main()
