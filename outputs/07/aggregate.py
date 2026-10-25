"""Offline tie-out for Derive subsidy budgets and DefiLlama parent fees.

Reads committed snapshots only. Does not call APIs.
"""

from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
PRIOR = ROOT.parent / "06" / "raw"
OUT = ROOT / "clean" / "figures.json"

UTC = dt.timezone.utc


def day_range(start: str, end: str) -> list[str]:
    cur = dt.datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=UTC)
    last = dt.datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=UTC)
    days = []
    while cur <= last:
        days.append(cur.strftime("%Y-%m-%d"))
        cur += dt.timedelta(days=1)
    return days


def chart(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text())
    series = {}
    for ts, value in payload["totalDataChart"]:
        day = dt.datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
        series[day] = float(value)
    return series


def combine_positive(left: dict[str, float], right: dict[str, float], days: list[str]) -> dict:
    total = 0.0
    missing = []
    both_positive = []
    for day in days:
        a = left.get(day)
        b = right.get(day)
        if a is not None and b is not None and a > 0 and b > 0:
            both_positive.append(day)
        if b is not None and b > 0:
            total += b
        elif a is not None and a > 0:
            total += a
        elif a == 0 or b == 0:
            continue
        else:
            missing.append(day)
    return {"total": total, "missing": missing, "both_positive": both_positive}


def prorate_programs(window_start: dt.datetime, window_end: dt.datetime, programs: list[dict]) -> dict:
    by_name = defaultdict(lambda: {"DRV": 0.0, "OP": 0.0})
    for program in programs:
        start = dt.datetime.fromtimestamp(program["start_timestamp"] / 1000, UTC)
        end = dt.datetime.fromtimestamp(program["end_timestamp"] / 1000, UTC)
        overlap_start = max(start, window_start)
        overlap_end = min(end, window_end)
        if overlap_end <= overlap_start:
            continue
        fraction = (overlap_end - overlap_start).total_seconds() / (end - start).total_seconds()
        bucket = by_name[program["name"]]
        bucket["DRV"] += float(program["rewards"]["DRV"]) * fraction
        bucket["OP"] += float(program["rewards"]["OP"]) * fraction
    return {
        "by_program": {name: values for name, values in sorted(by_name.items())},
        "DRV": sum(v["DRV"] for v in by_name.values()),
        "OP": sum(v["OP"] for v in by_name.values()),
    }


def main() -> None:
    parent = {
        "fees": chart(RAW / "parent_dailyFees.json"),
        "revenue": chart(RAW / "parent_dailyRevenue.json"),
        "supply_side": chart(RAW / "parent_dailySupplySideRevenue.json"),
        "protocol": chart(RAW / "parent_dailyProtocolRevenue.json"),
        "holders": chart(RAW / "parent_dailyHoldersRevenue.json"),
    }
    options = {
        "notional_v2": chart(PRIOR / "llama_summary_options_derive-options_dataType=dailyNotionalVolume.json"),
        "notional_v3": chart(PRIOR / "llama_summary_options_derive-v3-options_dataType=dailyNotionalVolume.json"),
        "fees_v2": chart(PRIOR / "llama_summary_fees_derive-options_dataType=dailyFees.json"),
        "fees_v3": chart(PRIOR / "llama_summary_fees_derive-v3-options_dataType=dailyFees.json"),
        "revenue_v2": chart(PRIOR / "llama_summary_fees_derive-options_dataType=dailyRevenue.json"),
        "revenue_v3": chart(PRIOR / "llama_summary_fees_derive-v3-options_dataType=dailyRevenue.json"),
    }
    programs = json.loads((PRIOR / "derive_maker_programs.json").read_text())
    windows = {
        "2026Q2": ("2026-04-01", "2026-06-30"),
        "2026Q3": ("2026-07-01", "2026-09-30"),
        "2026-10-01_to_10-25": ("2026-10-01", "2026-10-25"),
        "2026-10-01_to_10-05": ("2026-10-01", "2026-10-05"),
        "2026-10-06_to_10-25": ("2026-10-06", "2026-10-25"),
        "2026-10-01_to_10-24": ("2026-10-01", "2026-10-24"),
    }
    rows = {}
    for name, (start, end) in windows.items():
        days = day_range(start, end)
        sums = {}
        missing = {}
        for key, series in parent.items():
            missing[key] = [day for day in days if day not in series]
            sums[key] = sum(series.get(day, 0.0) for day in days)
        window_start = dt.datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=UTC)
        window_end = dt.datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=UTC) + dt.timedelta(days=1)
        budget = prorate_programs(window_start, window_end, programs)
        length = len(days)
        usdc_cap = 500_000 * length / 28
        drv_doc_cap = 1_000_000 * length / 28
        rebate_proxy = sums["fees"] - sums["revenue"]
        rows[name] = {
            "days": length,
            "parent": sums,
            "parent_missing_days": {k: v for k, v in missing.items() if v},
            "fees_minus_revenue": rebate_proxy,
            "fees_minus_supply_side_minus_revenue": sums["fees"] - sums["supply_side"] - sums["revenue"],
            "protocol_plus_holders_minus_revenue": sums["protocol"] + sums["holders"] - sums["revenue"],
            "api_budget": budget,
            "doc_cap_prorated": {"USDC": usdc_cap, "DRV": drv_doc_cap},
            "observed_usdc_per_28d": rebate_proxy / length * 28,
            "observed_usdc_cap_utilization": (rebate_proxy / length * 28) / 500_000,
            "full_cap_revenue_if_fees_unchanged": sums["fees"] - usdc_cap,
            "options_notional": combine_positive(options["notional_v2"], options["notional_v3"], days),
            "options_fees": combine_positive(options["fees_v2"], options["fees_v3"], days),
            "options_revenue": combine_positive(options["revenue_v2"], options["revenue_v3"], days),
        }
    OUT.write_text(json.dumps(rows, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
