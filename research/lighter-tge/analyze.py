#!/usr/bin/env python3
"""Lighter TGE daily operating-stabilization study.

Rules in PRIMARY are fixed in this file and are not chosen by proximity to the
LIT price low. Price enters only the ex-post block. Each signal on day t uses
rows dated <= t.

State variable: S_t = trailing 7-day median of the raw series (inclusive).
Weekly rate: OLS slope of log S on a window of w days, multiplied by 7,
then r = exp(beta_w) - 1.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
OUT = ROOT / "output"
FIG = ROOT / "figures"
XLSX = CACHE / "Lighter_Core_ALL_2026-11-16.xlsx"

TGE = pd.Timestamp("2025-12-30")
CORE_END = pd.Timestamp("2026-03-29")
VALID_END = pd.Timestamp("2026-06-30")
PRICE_REF = pd.Timestamp("2026-03-31")  # ex-post label only
PEAK_START = pd.Timestamp("2025-10-01")

# Primary deceleration rule. Middle of the sensitivity grid, not a fitted cell.
PRIMARY = dict(pi_prior=-0.12, delta_pp=0.08, pi_floor=-0.08, k=5, require_28=True)
# Primary base rule.
BASE = dict(w=28, L=14, omega=0.50, drift_min=-0.10, frac_min=0.70, max_breaks=2, eps=0.05, k=5)
Q_PARAMS = dict(g_active_max=-0.08, gap_min=0.08, g_oi_min=-0.05, k=5)

CORE_METRICS = [
    "volume",
    "oi",
    "revenue",
    "active",
    "new",
    "trade_fee",
    "withdraw",
    "transfer",
    "nontrade",
    "v_per_a",
    "r_per_a",
    "tf_per_a",
    "w_per_a",
    "x_per_a",
    "oi_per_a",
    "take_bps",
    "tf_bps",
    "v_over_oi",
    "maker_share",
    "nt_share",
    "new_over_active",
    "active_over_cum",
    "net_flow",
    "liq_fee",
    "trade_count",
    "v_per_trade",
    "buyback_usdc",
]

LEVEL_FOR_SIGNALS = ["volume", "oi", "revenue", "active", "new", "oi_per_a", "v_per_a", "v_over_oi", "withdraw"]

LABELS = {
    "volume": "Volume",
    "oi": "OI",
    "revenue": "Revenue",
    "active": "活跃账户",
    "new": "新增账户",
    "trade_fee": "Maker+Taker",
    "withdraw": "提现费",
    "transfer": "转账费",
    "nontrade": "非交易费",
    "v_per_a": "Volume/活跃账户",
    "r_per_a": "Revenue/活跃账户",
    "tf_per_a": "交易费/活跃账户",
    "w_per_a": "提现费/活跃账户",
    "x_per_a": "转账费/活跃账户",
    "oi_per_a": "OI/活跃账户",
    "take_bps": "Revenue/Volume（bps）",
    "tf_bps": "交易费/Volume（bps）",
    "v_over_oi": "Volume/OI",
    "maker_share": "Maker/(Maker+Taker)",
    "nt_share": "非交易收入占比",
    "new_over_active": "新增/活跃",
    "active_over_cum": "活跃/累计",
    "net_flow": "净流入（API）",
    "liq_fee": "清算费（API，不计入 Revenue）",
    "trade_count": "成交笔数（API）",
    "v_per_trade": "Volume/成交笔数",
    "buyback_usdc": "回购 USDC（API）",
}


def weekly_rate(y: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(y) & (y > 0)
    # Windows of 7 days or less use every point. Longer windows may drop a few nonpositive days.
    need = len(y) if len(y) <= 7 else max(5, int(math.ceil(0.8 * len(y))))
    if int(mask.sum()) < need:
        return np.nan
    yy = np.log(y[mask])
    x = np.flatnonzero(mask).astype(float)
    x = x - x.mean()
    var = float(np.dot(x, x))
    if var <= 0:
        return np.nan
    beta_d = float(np.dot(x, yy - yy.mean()) / var)
    return float(np.expm1(beta_d * 7.0))


def rolling_weekly_rate(state: pd.Series, w: int) -> pd.Series:
    vals = state.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    for i in range(w - 1, len(vals)):
        out[i] = weekly_rate(vals[i - w + 1 : i + 1])
    return pd.Series(out, index=state.index)


def persist(cond: pd.Series, k: int) -> pd.Series:
    c = cond.fillna(False).astype(int)
    return c.rolling(k, min_periods=k).sum().ge(k)


def trailing_median(s: pd.Series, w: int = 7) -> pd.Series:
    return s.rolling(w, min_periods=w).median()


def load_api_series(kind: str) -> pd.Series:
    data = json.loads((CACHE / f"{kind}.json").read_text())
    rows = data["metrics"]
    idx = pd.to_datetime([r["timestamp"] for r in rows], unit="s", utc=True).tz_localize(None)
    s = pd.Series([float(r["data"]) for r in rows], index=idx, name=kind)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def load_panel() -> tuple[pd.DataFrame, dict]:
    raw = pd.read_excel(XLSX, sheet_name="Core日度数据")
    df = pd.DataFrame(
        {
            "maker": raw["Maker Fee USD"].to_numpy(dtype=float),
            "taker": raw["Taker Fee USD"].to_numpy(dtype=float),
            "withdraw": raw["Withdraw Fee USD"].to_numpy(dtype=float),
            "transfer": raw["Transfer Fee USD"].to_numpy(dtype=float),
            "volume": raw["Volume（官网）USD"].to_numpy(dtype=float),
            "active": raw["活跃账户（日）"].to_numpy(dtype=float),
            "revenue": raw["Revenue（官网）USD"].to_numpy(dtype=float),
            "oi": raw["OI（官网原值）USD"].to_numpy(dtype=float),
            "new": raw["新增账户（日）"].to_numpy(dtype=float),
            "cum": raw["累计创建账户"].to_numpy(dtype=float),
            "trade_fee_col": raw["交易费用分项合计"].to_numpy(dtype=float),
            "nontrade_col": raw["非交易费用合计"].to_numpy(dtype=float),
        },
        index=pd.to_datetime(raw["日期 UTC"]),
    ).sort_index()
    df.index.name = "date"
    audit = {
        "n": int(len(df)),
        "start": str(df.index.min().date()),
        "end": str(df.index.max().date()),
        "dup_dates": int(df.index.duplicated().sum()),
        "missing_days": int(len(pd.date_range(df.index.min(), df.index.max(), freq="D").difference(df.index))),
        "nulls": int(df.isna().sum().sum()),
        "maker_taker_vs_trade_fee_col_max_abs": float((df.maker + df.taker - df.trade_fee_col).abs().max()),
        "withdraw_transfer_vs_nontrade_col_max_abs": float((df.withdraw + df.transfer - df.nontrade_col).abs().max()),
        "cum_equals_cumsum_new": bool(np.allclose(df.cum.diff().fillna(df.cum.iloc[0]), df.new)),
    }
    vol_api = load_api_series("volume")
    oi_api = load_api_series("open_interest")
    maker_api = load_api_series("maker_fee")
    active_api = load_api_series("active_account_count")
    aligned = pd.DataFrame(
        {
            "volume_api": vol_api,
            "oi_api": oi_api,
            "maker_api": maker_api,
            "active_api": active_api,
            "inflow": load_api_series("inflow"),
            "outflow": load_api_series("outflow"),
            "liq_fee": load_api_series("liquidation_fee"),
            "trade_count": load_api_series("trade_count"),
            "attr_maker": load_api_series("attribution_maker_fee"),
            "attr_taker": load_api_series("attribution_taker_fee"),
            "buyback": load_api_series("buyback"),
            "buyback_usdc": load_api_series("buyback_usdc"),
        }
    )
    both = df.join(aligned, how="left")
    audit["volume_vs_api_max_abs"] = float((both.volume - both.volume_api).abs().max())
    audit["oi_vs_api_max_abs"] = float((both.oi - both.oi_api).abs().max())
    audit["maker_vs_api_max_abs"] = float((both.maker - both.maker_api).abs().max())
    audit["active_vs_api_max_abs"] = float((both.active - both.active_api).abs().max())
    audit["api_rows"] = {c: int(aligned[c].notna().sum()) for c in aligned.columns}
    both["attr"] = both["attr_maker"].fillna(0) + both["attr_taker"].fillna(0)
    both["revenue_residual_vs_four"] = both.revenue - both.maker - both.taker - both.withdraw - both.transfer
    audit["residual_vs_four_abs_max"] = float(both.revenue_residual_vs_four.abs().max())
    audit["attr_sum_by_month"] = {
        str(k.date()): float(v)
        for k, v in both["attr"].resample("MS").sum().round(2).items()
        if abs(v) > 1
    }
    audit["residual_abs_gt_1_days"] = int((both.revenue_residual_vs_four.abs() > 1).sum())
    both["trade_fee"] = both.maker + both.taker
    both["nontrade"] = both.withdraw + both.transfer
    both["net_flow"] = both.inflow - both.outflow
    both["v_per_a"] = both.volume / both.active
    both["r_per_a"] = both.revenue / both.active
    both["tf_per_a"] = both.trade_fee / both.active
    both["w_per_a"] = both.withdraw / both.active
    both["x_per_a"] = both.transfer / both.active
    both["oi_per_a"] = both.oi / both.active
    both["take_bps"] = both.revenue / both.volume * 1e4
    both["tf_bps"] = both.trade_fee / both.volume * 1e4
    both["v_over_oi"] = both.volume / both.oi
    both["maker_share"] = np.where(both.trade_fee > 0, both.maker / both.trade_fee, np.nan)
    both["nt_share"] = np.where(both.revenue > 0, both.nontrade / both.revenue, np.nan)
    both["new_over_active"] = both.new / both.active
    both["active_over_cum"] = both.active / both.cum
    both["v_per_trade"] = both.volume / both.trade_count.replace(0, np.nan)
    both["liq_over_revenue"] = np.where(both.revenue > 0, both.liq_fee / both.revenue, np.nan)
    both["buyback_over_revenue"] = np.where(both.revenue > 0, both.buyback_usdc / both.revenue, np.nan)
    return both, audit


def add_states(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for m in CORE_METRICS:
        out[f"{m}_s"] = trailing_median(out[m], 7)
    # Causal spike flags, using only the prior 14 days.
    prior_active = out["active"].rolling(14, min_periods=14).median().shift(1)
    prior_new = out["new"].rolling(14, min_periods=14).median().shift(1)
    out["active_spike"] = out["active"] > 3.0 * prior_active
    out["new_spike"] = out["new"] > 5.0 * prior_new
    prior_w = out["withdraw"].rolling(28, min_periods=21).median().shift(7)
    out["withdraw_shock"] = (out["withdraw_s"] > 2.0 * prior_w) & (prior_w > 0)
    return out


def add_rates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    for m in CORE_METRICS:
        state = df[f"{m}_s"]
        raw = df[m]
        for w in (3, 7, 14, 21, 28):
            r = rolling_weekly_rate(state, w)
            frames.append(r.rename(f"{m}_r{w}"))
            frames.append((r - r.shift(w)).rename(f"{m}_d{w}"))
        raw_pos = raw.where(raw > 0)
        for w in (3, 7, 21):
            frames.append(rolling_weekly_rate(raw_pos, w).rename(f"{m}_r{w}_raw"))
        dlog = np.log(state.where(state > 0)).diff()
        for w in (14, 21, 28):
            frames.append(dlog.rolling(w, min_periods=w).std().rename(f"{m}_vol{w}"))
            roll_min = state.rolling(w, min_periods=w).min()
            frames.append(state.le(roll_min * 1.001).rename(f"{m}_atlow{w}"))
    rates = pd.concat(frames, axis=1)
    # Simple growth of the 7d median, as a cross-check of the OLS rate.
    for m in LEVEL_FOR_SIGNALS:
        s = df[f"{m}_s"]
        for w in (7, 14, 21, 28):
            rates[f"{m}_g{w}"] = s / s.shift(w) - 1.0
    rates["div_oi_active_21"] = rates["oi_r21"] - rates["active_r21"]
    rates["div_vol_active_21"] = rates["volume_r21"] - rates["active_r21"]
    rates["div_rev_vol_21"] = rates["revenue_r21"] - rates["volume_r21"]
    rates["div_new_active_21"] = rates["new_r21"] - rates["active_r21"]
    return df, rates


def decel_flag(rates: pd.DataFrame, metric: str, p: dict) -> pd.Series:
    r14 = rates[f"{metric}_r14"]
    r21 = rates[f"{metric}_r21"]
    r28 = rates[f"{metric}_r28"]
    c14 = (r14.shift(14) <= p["pi_prior"]) & ((r14 - r14.shift(14)) >= p["delta_pp"]) & (r14 >= p["pi_floor"])
    c21 = (r21.shift(21) <= p["pi_prior"]) & ((r21 - r21.shift(21)) >= p["delta_pp"]) & (r21 >= p["pi_floor"])
    flag = persist(c14, p["k"]) & persist(c21, p["k"])
    if p["require_28"]:
        ok28 = (r28 > p["pi_prior"]) & ((r28 - r28.shift(28)) > 0)
        flag = flag & ok28.fillna(False)
    return flag.fillna(False)


def base_diagnostics(state: pd.Series, rates_28: pd.Series, spec: dict) -> pd.DataFrame:
    vals = state.to_numpy(dtype=float)
    n = len(vals)
    w, L, eps = spec["w"], spec["L"], spec["eps"]
    p10 = np.full(n, np.nan)
    p50 = np.full(n, np.nan)
    p90 = np.full(n, np.nan)
    frac = np.full(n, np.nan)
    breaks = np.full(n, np.nan)
    drift = np.full(n, np.nan)
    width = np.full(n, np.nan)
    for i in range(L + w - 1, n):
        frozen = vals[i - L - w + 1 : i - L + 1]
        recent = vals[i - L + 1 : i + 1]
        if not (np.isfinite(frozen).sum() >= int(0.8 * w) and np.isfinite(recent).sum() >= int(0.8 * L)):
            continue
        a, b, c = np.nanpercentile(frozen, [10, 50, 90])
        if not np.isfinite(b) or b <= 0:
            continue
        p10[i], p50[i], p90[i] = a, b, c
        lo, hi = a * (1 - eps), c * (1 + eps)
        frac[i] = float(np.mean((recent >= lo) & (recent <= hi)))
        breaks[i] = float(np.sum(recent < a * (1 - eps)))
        drift[i] = float(np.nanmedian(recent) / b - 1.0)
        width[i] = float((c - a) / b)
    peak = state.copy()
    peak_vals = np.full(n, np.nan)
    run = np.nan
    for i, (dt, v) in enumerate(state.items()):
        if dt >= PEAK_START and np.isfinite(v):
            run = v if not np.isfinite(run) else max(run, v)
        peak_vals[i] = run
    deep = pd.Series(peak_vals, index=state.index)
    came_down = (state <= 0.75 * deep) | (rates_28.shift(28) <= -0.08)
    raw = (
        (pd.Series(width, index=state.index) <= spec["omega"])
        & (pd.Series(frac, index=state.index) >= spec["frac_min"])
        & (pd.Series(breaks, index=state.index) <= spec["max_breaks"])
        & (pd.Series(drift, index=state.index) >= spec["drift_min"])
        & came_down.fillna(False)
    )
    out = pd.DataFrame(
        {
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "width": width,
            "frac": frac,
            "breaks": breaks,
            "drift": drift,
            "deep_drawdown": (state <= 0.75 * deep).fillna(False),
            "raw": raw.fillna(False),
            "flag": persist(raw, spec["k"]).fillna(False),
        },
        index=state.index,
    )
    return out


def fee_and_quality(df: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    bps = df["tf_bps_s"]
    bps_now = bps.rolling(21, min_periods=21).median()
    bps_prev = bps.shift(21).rolling(21, min_periods=21).median()
    fee_shift = ((bps_now / bps_prev - 1).abs() > 0.30) & bps_prev.notna() & (bps_prev > 0)
    # Known, already-public regime changes. Block confidence upgrades for 21 days.
    fee_event = pd.Series(False, index=df.index)
    fee_event.loc["2026-02-08":"2026-02-28"] = True
    fee_event.loc["2026-04-15":"2026-05-05"] = True
    incentive = pd.Series(False, index=df.index)
    incentive.loc["2026-03-20":"2026-04-02"] = True
    g_oi = rates["oi_r21"]
    g_a = rates["active_r21"]
    g_v = rates["volume_r21"]
    g_voi = rates["v_over_oi_r21"]
    q_raw = (g_a <= Q_PARAMS["g_active_max"]) & ((g_oi - g_a) >= Q_PARAMS["gap_min"]) & (g_oi >= Q_PARAMS["g_oi_min"])
    q = persist(q_raw, Q_PARAMS["k"]).fillna(False)
    turnover_collapse = (g_voi <= -0.10) & (g_v <= -0.10) & (g_oi >= -0.03)
    # Denominator artifact: per-account level up mostly because active is down.
    denom = (rates["oi_per_a_r21"] > 0.10) & (g_a < -0.08) & (g_oi < -0.05)
    flow_14 = df["net_flow"].rolling(14, min_periods=14).sum()
    flow_stress = flow_14 < -0.10 * df["oi"]
    out = pd.DataFrame(
        {
            "fee_shift": fee_shift.fillna(False),
            "fee_event": fee_event,
            "incentive_event": incentive,
            "tf_bps_21": bps_now,
            "tf_bps_prior21": bps_prev,
            "q_raw": q_raw.fillna(False),
            "q": q,
            "turnover_collapse": turnover_collapse.fillna(False),
            "denominator_artifact": denom.fillna(False),
            "flow_stress": flow_stress.fillna(False),
            "withdraw_shock": df["withdraw_shock"].fillna(False),
        },
        index=df.index,
    )
    out["q_clean"] = out["q"] & ~out["fee_shift"] & ~out["turnover_collapse"] & ~out["withdraw_shock"] & ~out["fee_event"]
    return out


def episode_starts(flag: pd.Series, min_gap: int = 14) -> list[pd.Timestamp]:
    f = flag.fillna(False).astype(bool)
    starts = list(f.index[f & ~f.shift(1, fill_value=False)])
    kept: list[pd.Timestamp] = []
    for dt in starts:
        if not kept or (dt - kept[-1]).days >= min_gap:
            kept.append(pd.Timestamp(dt))
    return kept


def run_length(flag: pd.Series, dt: pd.Timestamp) -> int:
    """Consecutive true days starting at dt, inclusive."""
    if dt not in flag.index or not bool(flag.loc[dt]):
        return 0
    loc = flag.index.get_loc(dt)
    n = 0
    while loc + n < len(flag) and bool(flag.iloc[loc + n]):
        n += 1
    return int(n)


def streak_on(flag: pd.Series, dt: pd.Timestamp) -> int:
    if dt not in flag.index or not bool(flag.loc[dt]):
        return 0
    n = 0
    loc = flag.index.get_loc(dt)
    while loc - n >= 0 and bool(flag.iloc[loc - n]):
        n += 1
    return n


def fwd(state: pd.Series, dt: pd.Timestamp, h: int) -> float:
    t1 = dt + pd.Timedelta(days=h)
    if dt not in state.index or t1 not in state.index:
        return np.nan
    a, b = state.loc[dt], state.loc[t1]
    if not (np.isfinite(a) and np.isfinite(b) and a != 0):
        return np.nan
    return float(b / a - 1.0)


def max_dd(state: pd.Series, dt: pd.Timestamp, h: int = 56) -> float:
    t1 = dt + pd.Timedelta(days=h)
    seg = state.loc[dt + pd.Timedelta(days=1) : t1]
    if seg.dropna().empty or dt not in state.index or not np.isfinite(state.loc[dt]) or state.loc[dt] == 0:
        return np.nan
    return float(seg.min() / state.loc[dt] - 1.0)


def reaccelerated(rate14: pd.Series, dt: pd.Timestamp, horizon: int = 56, thresh: float = -0.15) -> bool:
    seg = rate14.loc[dt + pd.Timedelta(days=1) : dt + pd.Timedelta(days=horizon)]
    bad = seg.le(thresh)
    return bool(persist(bad, 5).fillna(False).any())


def build_flags(df: pd.DataFrame, rates: pd.DataFrame, bases: dict[str, pd.DataFrame], qual: pd.DataFrame) -> pd.DataFrame:
    flags = pd.DataFrame(index=df.index)
    for m in LEVEL_FOR_SIGNALS:
        flags[f"decel_{m}"] = decel_flag(rates, m, PRIMARY)
        flags[f"base_{m}"] = bases[m]["flag"] if m in bases else False
    # Joints. Excel-only. Fee-event and incentive windows cannot upgrade confidence.
    block = qual["fee_event"] | qual["incentive_event"] | qual["fee_shift"]
    oi_d, vol_d, rev_d = flags["decel_oi"], flags["decel_volume"], flags["decel_revenue"]
    act_d = flags["decel_active"]
    oi_b, vol_b, rev_b, act_b = flags["base_oi"], flags["base_volume"], flags["base_revenue"], flags["base_active"]
    flags["J1_oi_decel"] = oi_d & ~qual["withdraw_shock"]
    flags["J2_active_decel"] = act_d & ~qual["withdraw_shock"]
    flags["J3_oi_base"] = oi_b
    flags["J4_volume_decel"] = vol_d
    flags["J5_revenue_decel"] = rev_d
    flags["J6_oi_and_volume_decel"] = oi_d & vol_d & ~block
    flags["J7_oi_base_and_flow_decel"] = oi_b & (vol_d | rev_d | vol_b | rev_b) & ~block
    flags["J8_three_family"] = oi_b & act_b & (vol_d | rev_d | vol_b | rev_b) & ~block
    flags["J9_quality_and_volume"] = qual["q_clean"] & vol_d & ~block
    flags["watch"] = (oi_d | act_d | oi_b) & ~qual["withdraw_shock"]
    still_crashing = (rates["volume_r14"] <= -0.12) & (rates["revenue_r14"] <= -0.12)
    flags["confirm"] = (
        (oi_b | persist(oi_d, 7))
        & (vol_d | rev_d | vol_b | rev_b)
        & ~block
        & ~still_crashing.fillna(False)
        & ~qual["withdraw_shock"]
    )
    # Augmented confirm also requires the public flow series not to be in stress.
    flags["confirm_flow"] = flags["confirm"] & ~qual["flow_stress"]
    flags["watch_only"] = flags["watch"] & ~flags["confirm"]
    return flags


def evaluate_rule(
    name: str,
    flag: pd.Series,
    anchor: str,
    df: pd.DataFrame,
    rates: pd.DataFrame,
    qual: pd.DataFrame,
) -> list[dict]:
    rows = []
    state = df[f"{anchor}_s"] if f"{anchor}_s" in df.columns else df[anchor]
    for dt in episode_starts(flag):
        if dt < TGE or dt > VALID_END:
            continue
        window = "core" if dt <= CORE_END else "validation"
        inputs = {}
        for m in ("oi", "volume", "revenue", "active", "new"):
            inputs[f"{m}_r14"] = _num(rates.loc[dt, f"{m}_r14"])
            inputs[f"{m}_r21"] = _num(rates.loc[dt, f"{m}_r21"])
            inputs[f"{m}_d21"] = _num(rates.loc[dt, f"{m}_d21"])
            inputs[f"{m}_r28"] = _num(rates.loc[dt, f"{m}_r28"])
            inputs[f"{m}_s"] = _num(df.loc[dt, f"{m}_s"])
        rec = {
            "rule": name,
            "anchor": anchor,
            "date": str(dt.date()),
            "window": window,
            "streak_into_trigger": streak_on(flag, dt),
            "run_days": run_length(flag, dt),
            "self_fwd7": fwd(state, dt, 7),
            "self_fwd14": fwd(state, dt, 14),
            "self_fwd28": fwd(state, dt, 28),
            "self_fwd56": fwd(state, dt, 56),
            "self_dd56": max_dd(state, dt, 56),
            "reaccel_14": reaccelerated(rates[f"{anchor}_r14"], dt) if f"{anchor}_r14" in rates else False,
        }
        for m in ("volume", "oi", "revenue", "active"):
            sm = df[f"{m}_s"]
            rec[f"{m}_fwd7"] = fwd(sm, dt, 7)
            rec[f"{m}_fwd14"] = fwd(sm, dt, 14)
            rec[f"{m}_fwd28"] = fwd(sm, dt, 28)
            rec[f"{m}_fwd56"] = fwd(sm, dt, 56)
            rec[f"{m}_dd56"] = max_dd(sm, dt, 56)
        rec["self_fp15"] = bool(rec["self_fwd28"] <= -0.15) if np.isfinite(rec["self_fwd28"]) else False
        rec["self_fp25"] = bool(rec["self_fwd28"] <= -0.25) if np.isfinite(rec["self_fwd28"]) else False
        rec["self_fp35"] = bool(rec["self_fwd28"] <= -0.35) if np.isfinite(rec["self_fwd28"]) else False
        rec["outcome_fail_28"] = bool(
            np.isfinite(rec["revenue_fwd28"])
            and np.isfinite(rec["volume_fwd28"])
            and rec["revenue_fwd28"] <= -0.20
            and rec["volume_fwd28"] <= -0.20
        )
        rec["fee_shift"] = bool(qual.loc[dt, "fee_shift"])
        rec["fee_event"] = bool(qual.loc[dt, "fee_event"])
        rec["incentive_event"] = bool(qual.loc[dt, "incentive_event"])
        rec["flow_stress"] = bool(qual.loc[dt, "flow_stress"])
        rec["inputs"] = inputs
        # Ex-post price annotation. Not an input.
        rec["days_before_price_ref"] = int((PRICE_REF - dt).days)
        rows.append(rec)
    return rows


def _num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def sensitivity(df: pd.DataFrame, rates: pd.DataFrame, bases_cache_builder) -> pd.DataFrame:
    rows = []
    grid_pi = (-0.08, -0.12, -0.20)
    grid_delta = (0.05, 0.08, 0.12)
    grid_floor = (-0.03, -0.08, -0.15)
    grid_k = (3, 5, 7)
    for metric in ("oi", "active", "volume", "revenue", "new", "oi_per_a"):
        for pi in grid_pi:
            for delta in grid_delta:
                for floor in grid_floor:
                    for k in grid_k:
                        for req in (True, False):
                            # Full factorial on require_28 only at the primary other values,
                            # plus the full grid with require_28 True. Keeps the null honest
                            # without treating every loose cell as a candidate model.
                            if (not req) and not (pi == -0.12 and delta == 0.08 and floor == -0.08):
                                continue
                            p = dict(pi_prior=pi, delta_pp=delta, pi_floor=floor, k=k, require_28=req)
                            flag = decel_flag(rates, metric, p)
                            starts = [d for d in episode_starts(flag) if TGE <= d <= VALID_END]
                            core = [d for d in starts if d <= CORE_END]
                            valid = [d for d in starts if d > CORE_END]
                            first = core[0] if core else (starts[0] if starts else None)
                            self28 = fwd(df[f"{metric}_s"], first, 28) if first is not None else np.nan
                            rev56 = fwd(df["revenue_s"], first, 56) if first is not None else np.nan
                            fp = 0
                            for d in core:
                                ch = fwd(df[f"{metric}_s"], d, 28)
                                if np.isfinite(ch) and ch <= -0.25:
                                    fp += 1
                            rows.append(
                                {
                                    "family": "decel",
                                    "metric": metric,
                                    "pi_prior": pi,
                                    "delta_pp": delta,
                                    "pi_floor": floor,
                                    "k": k,
                                    "require_28": req,
                                    "first_date": None if first is None else str(first.date()),
                                    "first_in_core": bool(core),
                                    "n_core": len(core),
                                    "n_valid": len(valid),
                                    "n_core_self_fp25": fp,
                                    "first_self_fwd28": self28,
                                    "first_revenue_fwd56": rev56,
                                }
                            )
    # Base grid on the same state series. Recompute because thresholds change.
    for metric in ("oi", "active", "volume", "revenue", "new"):
        state = df[f"{metric}_s"]
        r28 = rates[f"{metric}_r28"]
        for omega in (0.35, 0.50, 0.70):
            for drift_min in (-0.05, -0.10, -0.15):
                for k in (3, 5, 7):
                    for w in (21, 28):
                        spec = dict(BASE)
                        spec.update(omega=omega, drift_min=drift_min, k=k, w=w)
                        diag = base_diagnostics(state, r28, spec)
                        flag = diag["flag"]
                        starts = [d for d in episode_starts(flag) if TGE <= d <= VALID_END]
                        core = [d for d in starts if d <= CORE_END]
                        valid = [d for d in starts if d > CORE_END]
                        first = core[0] if core else (starts[0] if starts else None)
                        fp = 0
                        for d in core:
                            ch = fwd(state, d, 28)
                            if np.isfinite(ch) and ch <= -0.25:
                                fp += 1
                        rows.append(
                            {
                                "family": "base",
                                "metric": metric,
                                "pi_prior": np.nan,
                                "delta_pp": np.nan,
                                "pi_floor": np.nan,
                                "k": k,
                                "require_28": np.nan,
                                "omega": omega,
                                "drift_min": drift_min,
                                "w": w,
                                "first_date": None if first is None else str(first.date()),
                                "first_in_core": bool(core),
                                "n_core": len(core),
                                "n_valid": len(valid),
                                "n_core_self_fp25": fp,
                                "first_self_fwd28": fwd(state, first, 28) if first is not None else np.nan,
                                "first_revenue_fwd56": fwd(df["revenue_s"], first, 56) if first is not None else np.nan,
                            }
                        )
    return pd.DataFrame(rows)


def grid_stability(sens: pd.DataFrame) -> list[dict]:
    out = []
    for (family, metric), g in sens.groupby(["family", "metric"]):
        # Stability is measured on the require_28=True decel grid, and on w=28 base grid.
        if family == "decel":
            g = g[g["require_28"] == True]  # noqa: E712
        else:
            g = g[g["w"] == 28]
        dates = pd.to_datetime(g["first_date"])
        core_dates = dates[g["first_in_core"].to_numpy()]
        if core_dates.empty:
            modal = None
            share = float((~g["first_in_core"]).mean()) if len(g) else 0.0
            note = "no_core_trigger"
        else:
            # 14-day buckets from TGE.
            bucket = ((core_dates - TGE).dt.days // 14) * 14
            mode = int(bucket.mode().iloc[0])
            share = float((bucket == mode).mean())
            # share of ALL cells, not only cells that fired in-core
            share = float((bucket == mode).sum() / len(g))
            modal = str((TGE + pd.Timedelta(days=mode)).date())
            note = "modal_14d_bucket_start"
        # Overfit illustration: cell whose first date is closest to the price ref.
        # Reported so it can be rejected, not used.
        dist = (dates - PRICE_REF).abs().dt.days
        if dist.notna().any():
            i = dist.idxmin()
            near = g.loc[i]
            overfit = {
                "date": near["first_date"],
                "days_from_price_ref": int(dist.loc[i]) if np.isfinite(dist.loc[i]) else None,
                "k": int(near["k"]) if pd.notna(near["k"]) else None,
                "pi_prior": None if pd.isna(near.get("pi_prior", np.nan)) else float(near["pi_prior"]),
                "delta_pp": None if pd.isna(near.get("delta_pp", np.nan)) else float(near["delta_pp"]),
                "pi_floor": None if pd.isna(near.get("pi_floor", np.nan)) else float(near["pi_floor"]),
                "omega": None if "omega" not in near or pd.isna(near["omega"]) else float(near["omega"]),
                "w": None if "w" not in near or pd.isna(near["w"]) else int(near["w"]),
            }
        else:
            overfit = None
        out.append(
            {
                "family": family,
                "metric": metric,
                "n_cells": int(len(g)),
                "share_in_modal_core_bucket": share,
                "modal_bucket_start": modal,
                "share_never_in_core": float((~g["first_in_core"]).mean()),
                "rejected_overfit_cell": overfit,
                "note": note,
            }
        )
    return out


def first_episode(episodes: list[dict], rule: str, window: str | None = None) -> dict | None:
    hits = [e for e in episodes if e["rule"] == rule and (window is None or e["window"] == window)]
    return hits[0] if hits else None


def placebo(rates: pd.DataFrame) -> dict:
    out = {}
    for metric in ("oi", "active", "volume", "revenue"):
        flag = decel_flag(rates, metric, PRIMARY)
        pre = [d for d in episode_starts(flag) if pd.Timestamp("2025-10-15") <= d < TGE]
        out[metric] = [str(d.date()) for d in pre]
    return out


def regime_table(df: pd.DataFrame) -> list[dict]:
    periods = [
        ("TGE前8周", "2025-11-04", "2025-12-26"),
        ("TGE当周", "2025-12-27", "2026-01-05"),
        ("出清前段", "2026-01-06", "2026-02-14"),
        ("观察窗后段", "2026-02-15", "2026-03-29"),
        ("验证窗", "2026-03-30", "2026-06-30"),
        ("积分重启前", "2026-07-01", "2026-08-09"),
        ("RH积分后", "2026-08-10", "2026-11-16"),
    ]
    cols = [
        "volume",
        "oi",
        "revenue",
        "active",
        "new",
        "tf_bps",
        "take_bps",
        "v_over_oi",
        "v_per_a",
        "oi_per_a",
        "nt_share",
        "maker_share",
        "net_flow",
        "liq_fee",
        "trade_count",
    ]
    rows = []
    for name, a, b in periods:
        sl = df.loc[a:b, cols]
        rec = {"regime": name, "start": a, "end": b, "days": int(len(sl))}
        for c in cols:
            rec[c] = float(sl[c].median())
        rec["net_flow_sum"] = float(df.loc[a:b, "net_flow"].sum())
        rec["revenue_sum"] = float(df.loc[a:b, "revenue"].sum())
        rec["buyback_usdc_sum"] = float(df.loc[a:b, "buyback_usdc"].sum(min_count=1))
        rows.append(rec)
    return rows


def event_study_bps(df: pd.DataFrame) -> list[dict]:
    events = [
        ("premium_fee_tiers", "2026-02-08"),
        ("rwa_premium_fees_on", "2026-04-15"),
        ("fee_credits", "2026-02-26"),
        ("commodities_challenge", "2026-03-20"),
    ]
    rows = []
    for name, day in events:
        dt = pd.Timestamp(day)
        pre = df.loc[dt - pd.Timedelta(days=14) : dt - pd.Timedelta(days=1)]
        post = df.loc[dt : dt + pd.Timedelta(days=13)]
        def med(sl, col):
            return float(sl[col].median()) if len(sl) else np.nan
        rec = {"event": name, "date": day, "pre_days": int(len(pre)), "post_days": int(len(post))}
        for col in ("tf_bps", "take_bps", "volume", "revenue", "oi", "active", "maker_share"):
            rec[f"{col}_pre"] = med(pre, col)
            rec[f"{col}_post"] = med(post, col)
            if rec[f"{col}_pre"]:
                rec[f"{col}_chg"] = rec[f"{col}_post"] / rec[f"{col}_pre"] - 1.0
        rows.append(rec)
    return rows


def operating_troughs(df: pd.DataFrame) -> dict:
    out = {}
    sl = df.loc[TGE:VALID_END]
    for m in ("volume", "oi", "revenue", "active", "new", "trade_fee"):
        s = sl[f"{m}_s"].dropna()
        out[m] = {"date": str(s.idxmin().date()), "median7": float(s.min()), "raw_on_that_day": float(df.loc[s.idxmin(), m])}
    return out


def dow_table(df: pd.DataFrame) -> dict:
    sl = df.loc[TGE:VALID_END].copy()
    sl["dow"] = sl.index.day_name()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    tab = {}
    for col in ("volume", "revenue", "active", "oi"):
        med = sl.groupby("dow")[col].median()
        base = float(med.mean())
        tab[col] = {d: float(med.get(d, np.nan) / base - 1.0) for d in order}
    return tab


def oi_jumps(df: pd.DataFrame) -> list[dict]:
    r = np.log(df["oi"]).diff()
    hits = r[r.abs() > math.log(1.30)]
    return [{"date": str(i.date()), "log_change": float(v), "oi": float(df.loc[i, "oi"])} for i, v in hits.items()]


def checkpoints(df, rates, bases, qual, flags) -> list[dict]:
    days = ["2026-02-15", "2026-02-28", "2026-03-07", "2026-03-15", "2026-03-29"]
    metrics = ["oi", "active", "new", "volume", "revenue", "oi_per_a", "v_over_oi", "tf_bps"]
    out = []
    for day in days:
        dt = pd.Timestamp(day)
        levels = {}
        slope = {}
        for m in metrics:
            levels[m] = {
                "raw": _num(df.loc[dt, m]),
                "median7": _num(df.loc[dt, f"{m}_s"]),
            }
            slope[m] = {
                f"r{w}": _num(rates.loc[dt, f"{m}_r{w}"]) for w in (3, 7, 14, 21, 28)
            }
            slope[m].update({f"d{w}": _num(rates.loc[dt, f"{m}_d{w}"]) for w in (7, 14, 21, 28)})
            for w in (3, 7, 21):
                col = f"{m}_r{w}_raw"
                slope[m][f"r{w}_raw"] = _num(rates.loc[dt, col]) if col in rates.columns else None
        base_now = {}
        for m in ("oi", "active", "volume", "revenue", "new"):
            row = bases[m].loc[dt]
            base_now[m] = {
                "width": _num(row["width"]),
                "frac": _num(row["frac"]),
                "breaks": _num(row["breaks"]),
                "drift": _num(row["drift"]),
                "p10": _num(row["p10"]),
                "p50": _num(row["p50"]),
                "p90": _num(row["p90"]),
                "raw": bool(row["raw"]),
                "flag": bool(row["flag"]),
            }
        on = sorted(c for c in flags.columns if bool(flags.loc[dt, c]))
        judgment = mechanical_judgment(dt, slope, base_now, qual.loc[dt], on)
        subsequent = {}
        for m in ("oi", "volume", "revenue", "active"):
            subsequent[m] = {f"fwd{h}": fwd(df[f"{m}_s"], dt, h) for h in (7, 14, 28, 56)}
        out.append(
            {
                "date": day,
                "levels": levels,
                "slopes": slope,
                "base": base_now,
                "quality": {
                    "div_oi_active_21": _num(rates.loc[dt, "div_oi_active_21"]),
                    "div_vol_active_21": _num(rates.loc[dt, "div_vol_active_21"]),
                    "div_rev_vol_21": _num(rates.loc[dt, "div_rev_vol_21"]),
                    "fee_shift": bool(qual.loc[dt, "fee_shift"]),
                    "fee_event": bool(qual.loc[dt, "fee_event"]),
                    "incentive_event": bool(qual.loc[dt, "incentive_event"]),
                    "q": bool(qual.loc[dt, "q"]),
                    "q_clean": bool(qual.loc[dt, "q_clean"]),
                    "turnover_collapse": bool(qual.loc[dt, "turnover_collapse"]),
                    "denominator_artifact": bool(qual.loc[dt, "denominator_artifact"]),
                    "flow_stress": bool(qual.loc[dt, "flow_stress"]),
                    "withdraw_shock": bool(qual.loc[dt, "withdraw_shock"]),
                    "tf_bps_21": _num(qual.loc[dt, "tf_bps_21"]),
                    "net_flow_14_over_oi": _num(df["net_flow"].rolling(14).sum().loc[dt] / df.loc[dt, "oi"]),
                },
                "flags_on": on,
                "judgment_then": judgment,
                "subsequent_not_known_on_that_day": subsequent,
            }
        )
    return out


def mechanical_judgment(dt, slope, base_now, qrow, flags_on: list[str]) -> list[str]:
    lines = []
    fast, slow, flat = [], [], []
    for m in ("oi", "active", "new", "volume", "revenue"):
        r = slope[m]["r21"]
        if r is None:
            continue
        name = LABELS[m]
        if r <= -0.12:
            fast.append(f"{name} 21日周率 {r:+.1%}")
        elif r <= -0.03:
            slow.append(f"{name} 21日周率 {r:+.1%}")
        else:
            flat.append(f"{name} 21日周率 {r:+.1%}")
    if fast:
        lines.append("仍在快速恶化（21日周率≤-12%）：" + "；".join(fast) + "。")
    else:
        lines.append("五个核心水平指标当日都没有 21日周率低于 -12% 的快速恶化。")
    if slow:
        lines.append("仍在下行但速度已不是快崩（-12%到-3%）：" + "；".join(slow) + "。")
    if flat:
        lines.append("21日周率已不差于 -3%：" + "；".join(flat) + "。")
    decel_on = [LABELS[m] for m in ("oi", "active", "new", "volume", "revenue") if f"decel_{m}" in flags_on]
    base_on = [LABELS[m] for m in ("oi", "active", "new", "volume", "revenue") if f"base_{m}" in flags_on]
    lines.append(
        "主规则下降减速已持续满足：" + ("、".join(decel_on) if decel_on else "无") + "。"
    )
    lines.append(
        "主规则底部区间已持续满足：" + ("、".join(base_on) if base_on else "无") + "。"
    )
    if "confirm" in flags_on:
        lines.append("联合确认规则当日为真：OI 已经减速或进入区间，且 Volume 或 Revenue 也满足减速或区间，费率事件窗、激励窗和费率漂移都不成立。这只提高研究关注，不是交易指令。")
    elif "watch" in flags_on:
        lines.append("当日只有观察级信号（OI 或活跃账户减速，或 OI 进入区间）。流量指标尚未共同确认，不能提高投资信心。")
    else:
        lines.append("当日观察级和确认级联合规则都未触发。")
    if bool(qrow["fee_event"]):
        lines.append("当日处于已知费率事件后的 21 日封锁窗，收入变化不能直接读成需求变化。")
    if bool(qrow["incentive_event"]):
        lines.append("当日处于商品挑战赛激励窗，Volume 和活跃账户的改善不能直接读成自然需求。")
    if bool(qrow["fee_shift"]):
        lines.append("交易费/Volume 的 21 日中位数相对前 21 日变动超过 30%，费率结构本身在变。")
    if bool(qrow["q"]) and not bool(qrow["q_clean"]):
        lines.append("OI 相对活跃账户的背离条件成立，但费率、换手塌陷或提现费冲击使之不能当成用户质量改善。")
    elif bool(qrow["q_clean"]):
        lines.append("OI 相对活跃账户的背离通过了费率、换手和提现费过滤。账户分布仍然缺失，这只是可检验推断，不是集中度证明。")
    if bool(qrow["flow_stress"]):
        lines.append("过去 14 日 API 净流入低于 -10% 的 OI。即使 OI 横盘，保证金流向也不支持需求企稳。流入流出口径本身尚未审计。")
    lines.append("当日不能使用 3 月 31 日价格、其后的低点，或此后才实现的经营数字。")
    return lines


def announcements() -> list[dict]:
    data = json.loads((CACHE / "announcements.json").read_text())
    keep_words = (
        "fee",
        "premium",
        "lit",
        "attribution",
        "competition",
        "rebate",
        "credit",
        "liquidity partner",
        "collateral",
        "delist",
    )
    rows = []
    for a in data["announcements"]:
        created = pd.Timestamp(a["created_at"], unit="s")
        if created < pd.Timestamp("2025-12-01") or created > pd.Timestamp("2026-06-30"):
            continue
        title = a["title"].strip()
        content = " ".join(a["content"].split())
        blob = f"{title} {content}".lower()
        if not any(w in blob for w in keep_words):
            continue
        rows.append({"date": str(created.date()), "title": title, "content": content[:400]})
    rows.sort(key=lambda r: r["date"])
    return rows


def load_price() -> pd.Series:
    data = json.loads((CACHE / "lit_price_cg.json").read_text())
    idx = pd.to_datetime([p[0] for p in data["prices"]], unit="ms")
    s = pd.Series([p[1] for p in data["prices"]], index=idx, name="price")
    s.index = s.index.tz_localize(None) if getattr(s.index, "tz", None) is not None else s.index
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s.index = s.index.normalize()
    return s


def price_block(price: pd.Series) -> dict:
    sl = price.loc[:VALID_END]
    windows = {
        "cg_min_through_2026_06_30": (TGE, VALID_END),
        "late_march": ("2026-03-25", "2026-04-05"),
        "late_april": ("2026-04-20", "2026-05-02"),
        "mid_may": ("2026-05-10", "2026-05-22"),
    }
    out = {"source": "CoinGecko market_chart daily USD snapshots, coins/lighter. Annotation only."}
    for name, (a, b) in windows.items():
        seg = price.loc[a:b]
        out[name] = {
            "min_date": str(seg.idxmin().date()),
            "min": float(seg.min()),
            "start": float(seg.iloc[0]),
            "end": float(seg.iloc[-1]),
        }
    for d in ("2026-03-30", "2026-03-31", "2026-04-28", "2026-05-15", "2026-05-16"):
        if pd.Timestamp(d) in price.index:
            out[d] = float(price.loc[pd.Timestamp(d)])
    return out


def correlations(rates: pd.DataFrame) -> dict:
    cols = ["oi_r21", "active_r21", "volume_r21", "revenue_r21", "new_r21", "trade_fee_r21", "v_per_a_r21", "r_per_a_r21", "oi_per_a_r21", "tf_bps_r21"]
    sl = rates.loc["2026-01-15":"2026-03-29", cols]
    c = sl.corr()
    return {
        "window": "2026-01-15 to 2026-03-29",
        "pairs": {
            "revenue_volume": float(c.loc["revenue_r21", "volume_r21"]),
            "trade_fee_revenue": float(c.loc["trade_fee_r21", "revenue_r21"]),
            "r_per_a_revenue": float(c.loc["r_per_a_r21", "revenue_r21"]),
            "v_per_a_volume": float(c.loc["v_per_a_r21", "volume_r21"]),
            "oi_active": float(c.loc["oi_r21", "active_r21"]),
            "oi_volume": float(c.loc["oi_r21", "volume_r21"]),
            "active_volume": float(c.loc["active_r21", "volume_r21"]),
            "tf_bps_revenue": float(c.loc["tf_bps_r21", "revenue_r21"]),
        },
    }


def screening(episodes, sens_summary, df) -> list[dict]:
    """One row per candidate. Credibility uses operating follow-through, not price."""
    specs = [
        ("OI", "7日中位数的 14日与21日对数斜率减速，主参数", "存量保证金/未平仓是否停止快崩", "decel_oi", "oi", "lead"),
        ("OI 区间", "冻结28日 P10-P90，近14日落入比例与中枢漂移", "存量是否进入可识别震荡", "base_oi", "oi", "lead"),
        ("活跃账户", "同 OI 的减速规则", "激励流量是否停止离开", "decel_active", "active", "lead"),
        ("活跃账户区间", "同 OI 的区间规则", "活跃计数是否不再创新低", "base_active", "active", "lead"),
        ("新增账户", "同减速规则", "拉新是否停止塌缩", "decel_new", "new", "lead"),
        ("新增账户区间", "同区间规则", "拉新是否落入低位区间", "base_new", "new", "lead"),
        ("Volume", "同减速规则", "真实成交需求的流量确认", "decel_volume", "volume", "confirm"),
        ("Volume 区间", "同区间规则", "成交额是否进入震荡", "base_volume", "volume", "confirm"),
        ("Revenue", "同减速规则", "费用现金流确认", "decel_revenue", "revenue", "confirm"),
        ("Revenue 区间", "同区间规则", "费用现金流是否进入震荡", "base_revenue", "revenue", "confirm"),
        ("OI/活跃账户", "同减速规则", "可能只是分母下降，默认低可信", "decel_oi_per_a", "oi_per_a", "reject"),
        ("Volume/活跃账户", "同减速规则", "可能只是分母下降，默认低可信", "decel_v_per_a", "v_per_a", "reject"),
        ("Volume/OI", "同减速规则", "周转变化，不是需求水平", "decel_v_over_oi", "v_over_oi", "context"),
        ("提现费", "同减速规则", "收费不是净提款", "decel_withdraw", "withdraw", "reject"),
        ("OI减速且Volume减速", "两个独立对象同时满足减速，并避开费率/激励窗", "存量与流量共同放缓", "J6_oi_and_volume_decel", "revenue", "joint"),
        ("OI区间且流量减速或区间", "确认规则的主体", "研究信心上调的最低组合", "J7_oi_base_and_flow_decel", "revenue", "joint"),
        ("OI区间、活跃区间、流量", "三类同时满足", "更严的联合确认", "J8_three_family", "revenue", "joint"),
        ("质量背离且Volume减速", "OI斜率显著好于活跃账户，且通过反方过滤", "低质量账户离场的可检验版本", "J9_quality_and_volume", "revenue", "joint"),
        ("观察", "OI或活跃减速，或OI区间", "只触发跟踪", "watch", "revenue", "joint"),
        ("确认", "OI减速持续7日或OI区间，且流量减速或区间，费率与激励窗关闭", "研究信心", "confirm", "revenue", "joint"),
        ("确认加净流入过滤", "确认，且14日净流入不低于 -10% OI", "把未审计的资金流当作额外否决", "confirm_flow", "revenue", "joint"),
    ]
    stab = {(s["family"], s["metric"]): s for s in sens_summary}
    rows = []
    rev_decel = first_episode(episodes, "decel_revenue", "core") or first_episode(episodes, "decel_revenue")
    vol_decel = first_episode(episodes, "decel_volume", "core") or first_episode(episodes, "decel_volume")
    for name, formula, meaning, rule, anchor, role in specs:
        ep = first_episode(episodes, rule, "core") or first_episode(episodes, rule)
        all_eps = [e for e in episodes if e["rule"] == rule]
        core_eps = [e for e in all_eps if e["window"] == "core"]
        valid_eps = [e for e in all_eps if e["window"] == "validation"]
        if ep is None:
            first = None
            lead_vs_rev = None
            persistent = None
            fp = f"核心窗与验证窗均未触发（验证窗启动 {len(valid_eps)} 次）"
            trust = "无信号"
        else:
            first = ep["date"]
            persistent = ep["run_days"]
            fp_n = sum(1 for e in core_eps if e["self_fp25"])
            out_n = sum(1 for e in core_eps if e["outcome_fail_28"])
            fp = f"核心窗 {len(core_eps)} 次，其中自身28日再跌超25%的 {fp_n} 次；Revenue与Volume 28日同跌超20%的 {out_n} 次。验证窗另有 {len(valid_eps)} 次。"
            if rev_decel and rule not in ("decel_revenue", "base_revenue"):
                lead_vs_rev = int((pd.Timestamp(rev_decel["date"]) - pd.Timestamp(first)).days)
            elif rev_decel and rule in ("decel_revenue", "base_revenue"):
                lead_vs_rev = 0
            else:
                lead_vs_rev = None
            trust = credibility(ep, core_eps, role)
        family = "decel" if rule.startswith("decel_") else ("base" if rule.startswith("base_") else None)
        metric = rule.split("_", 1)[1] if family else None
        if rule.startswith("decel_"):
            metric = rule[len("decel_") :]
        elif rule.startswith("base_"):
            metric = rule[len("base_") :]
        stab_row = stab.get((family, metric)) if family else None
        rows.append(
            {
                "指标": name,
                "计算公式": formula,
                "经济意义": meaning,
                "角色": role,
                "是否领先": lead_label(lead_vs_rev, role, ep),
                "首次触发日期": first,
                "相对Revenue减速的天数": lead_vs_rev,
                "事后距价格参照日天数": None if ep is None else ep["days_before_price_ref"],
                "启动后连续为真天数": persistent,
                "误报情况": fp,
                "可信度": trust,
                "参数稳定性": None
                if stab_row is None
                else {
                    "modal_bucket_start": stab_row["modal_bucket_start"],
                    "share_in_modal_core_bucket": stab_row["share_in_modal_core_bucket"],
                    "share_never_in_core": stab_row["share_never_in_core"],
                },
                "episode": ep,
            }
        )
    return rows


def lead_label(lead_vs_rev, role, ep) -> str:
    if ep is None:
        return "窗口内未触发"
    if role == "reject":
        return "不作为企稳信号"
    if role == "confirm":
        return "验证指标"
    if lead_vs_rev is None:
        return "Revenue减速未出现，领先无法定义"
    if lead_vs_rev >= 14:
        return "领先于Revenue减速"
    if lead_vs_rev >= 0:
        return "与Revenue减速同步"
    return "滞后于Revenue减速"


def credibility(ep: dict, core_eps: list[dict], role: str) -> str:
    if role == "reject":
        return "低"
    fp = np.mean([e["self_fp25"] for e in core_eps]) if core_eps else 1
    outcome = np.mean([e["outcome_fail_28"] for e in core_eps]) if core_eps else 1
    self28 = ep["self_fwd28"]
    rev56 = ep["revenue_fwd56"]
    if role in ("joint", "confirm") and ep["rule"] in ("confirm", "J7_oi_base_and_flow_decel", "J8_three_family", "confirm_flow"):
        if ep["outcome_fail_28"] or (rev56 is not None and rev56 <= -0.25):
            return "低"
        if rev56 is not None and rev56 > -0.10 and not ep["self_fp25"]:
            return "中"
        return "低"
    if self28 is not None and self28 <= -0.25:
        return "低"
    if fp > 0.5 or outcome > 0.5:
        return "低"
    if self28 is not None and self28 > -0.15 and rev56 is not None and rev56 > -0.15:
        return "中"
    if self28 is not None and self28 > -0.20:
        return "中"
    return "低"


def style_plots() -> None:
    font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    if Path(font_path).exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = "WenQuanYi Micro Hei"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25


def mark_dates(ax, extra: list[tuple[pd.Timestamp, str]] | None = None) -> None:
    ax.axvline(TGE, color="#444444", lw=1.0, ls="--")
    ax.axvline(PRICE_REF, color="#888888", lw=0.8, ls=":")
    ax.axvline(pd.Timestamp("2026-04-28"), color="#888888", lw=0.8, ls=":")
    ax.axvline(pd.Timestamp("2026-05-16"), color="#888888", lw=0.8, ls=":")
    if extra:
        for dt, _ in extra:
            ax.axvline(dt, color="#9a3412", lw=0.7, ls="-")


def save_plots(df, rates, flags, episodes, price) -> None:
    style_plots()
    FIG.mkdir(parents=True, exist_ok=True)
    sl = df.loc["2025-12-01":"2026-06-30"]
    # Levels
    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    series = [
        ("volume_s", "Volume 7日中位数（USD）"),
        ("oi_s", "OI 7日中位数（USD，官网原值）"),
        ("revenue_s", "Revenue 7日中位数（USD）"),
        ("active_s", "活跃账户 7日中位数（账户数）"),
    ]
    for ax, (col, title) in zip(axes, series):
        ax.plot(sl.index, sl[col], color="#1f3a5f", lw=1.4)
        ax.set_ylabel(title)
        mark_dates(ax)
        ax.axvspan(pd.Timestamp("2026-02-08"), pd.Timestamp("2026-02-28"), color="#d97706", alpha=0.08)
        ax.axvspan(pd.Timestamp("2026-03-20"), pd.Timestamp("2026-04-02"), color="#7c3aed", alpha=0.08)
    axes[0].set_title("Lighter Core 日度经营水平（7日中位数）\n虚线为 TGE；点线为事后价格参照，不参与信号")
    axes[-1].set_xlabel("UTC 日期")
    fig.tight_layout()
    fig.savefig(FIG / "levels_median7.png", dpi=140)
    plt.close()

    fig, ax = plt.subplots(figsize=(12, 5.5))
    for col, label, color in (
        ("oi_r21", "OI", "#9a3412"),
        ("active_r21", "活跃账户", "#6d28d9"),
        ("volume_r21", "Volume", "#1d4ed8"),
        ("revenue_r21", "Revenue", "#047857"),
    ):
        ax.plot(rates.loc[sl.index].index, rates.loc[sl.index, col] * 100, label=label, lw=1.3, color=color)
    ax.axhline(0, color="black", lw=0.6)
    ax.axhline(-12, color="#666666", lw=0.6, ls="--")
    ax.axhline(-8, color="#666666", lw=0.6, ls=":")
    mark_dates(ax)
    ax.set_ylabel("21日窗口周变化率（%）")
    ax.set_xlabel("UTC 日期")
    ax.set_title("滚动对数斜率换算的周变化率（7日中位数上的 OLS）")
    ax.legend(ncol=4, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "slopes_21d.png", dpi=140)
    plt.close()

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    axes[0].plot(sl.index, sl["tf_bps"], color="#1f3a5f", lw=1.0, label="日度")
    axes[0].plot(sl.index, sl["tf_bps_s"], color="#9a3412", lw=1.4, label="7日中位数")
    axes[0].set_ylabel("交易费 / Volume（bps）")
    axes[0].legend(frameon=False)
    axes[0].set_title("实现费率与周转。2月8日费率升级、4月15日 RWA Premium 收费为公开事件")
    axes[1].plot(sl.index, sl["v_over_oi_s"], color="#1f3a5f", lw=1.4)
    axes[1].set_ylabel("Volume / OI（7日中位数）")
    axes[1].set_xlabel("UTC 日期")
    for ax in axes:
        mark_dates(ax)
        ax.axvline(pd.Timestamp("2026-02-08"), color="#d97706", lw=0.8)
        ax.axvline(pd.Timestamp("2026-04-15"), color="#d97706", lw=0.8)
    fig.tight_layout()
    fig.savefig(FIG / "fee_and_turnover.png", dpi=140)
    plt.close()

    # OI base band
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(sl.index, sl["oi_s"] / 1e9, color="#1f3a5f", lw=1.4, label="OI 7日中位数")
    # band is stored only inside bases; recompute lightly by reading output later if needed
    ax.set_ylabel("OI（十亿美元）")
    ax.set_xlabel("UTC 日期")
    ax.set_title("OI 7日中位数。信号标记在时间轴图中，避免把价格低点画成答案")
    mark_dates(ax)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "oi_level.png", dpi=140)
    plt.close()

    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(sl.index, sl["oi"] / 1e9, color="#1f3a5f", lw=1.2, label="OI（十亿美元，左轴）")
    ax2 = ax.twinx()
    ax2.plot(sl.index, sl["net_flow"].rolling(7).sum() / 1e6, color="#9a3412", lw=1.1, label="7日净流入合计（百万USD）")
    ax.set_ylabel("OI（十亿美元）")
    ax2.set_ylabel("API 净流入 7日合计（百万 USD）")
    ax.set_title("OI 与官方 inflow−outflow。净流入不是已审计的保证金净额")
    ax.set_xlabel("UTC 日期")
    mark_dates(ax)
    fig.tight_layout()
    fig.savefig(FIG / "oi_vs_net_flow.png", dpi=140)
    plt.close()

    # Timeline of primary flags
    lanes = [
        ("decel_active", "活跃减速"),
        ("base_active", "活跃区间"),
        ("decel_oi", "OI减速"),
        ("base_oi", "OI区间"),
        ("decel_new", "新增减速"),
        ("decel_volume", "Volume减速"),
        ("base_volume", "Volume区间"),
        ("decel_revenue", "Revenue减速"),
        ("base_revenue", "Revenue区间"),
        ("watch", "观察"),
        ("confirm", "确认"),
        ("confirm_flow", "确认+资金流"),
    ]
    fig, ax = plt.subplots(figsize=(12, 6.2))
    for i, (col, label) in enumerate(lanes):
        f = flags.loc[sl.index, col].astype(bool)
        ax.fill_between(sl.index, i - 0.35, i + 0.35, where=f, color="#1f3a5f", step="mid")
    fp_dates = sorted({pd.Timestamp(e["date"]) for e in episodes if e["self_fp25"] and e["rule"] in dict(lanes)})
    for d in fp_dates:
        ax.axvline(d, color="#c2410c", lw=0.6, alpha=0.7)
    mark_dates(ax)
    ax.set_yticks(range(len(lanes)))
    ax.set_yticklabels([x[1] for x in lanes])
    ax.set_xlabel("UTC 日期")
    ax.set_title("主规则逐日开关。橙色竖线是该规则自身28日后再跌超25%的启动日")
    fig.tight_layout()
    fig.savefig(FIG / "signal_timeline.png", dpi=140)
    plt.close()

    fig, ax = plt.subplots(figsize=(12, 4.8))
    ps = price.loc["2025-12-30":"2026-06-30"]
    ax.plot(ps.index, ps.values, color="#1f3a5f", lw=1.3)
    ax.scatter([ps.idxmin()], [ps.min()], color="#9a3412", zorder=3)
    ax.set_ylabel("LIT 美元快照")
    ax.set_xlabel("UTC 日期")
    ax.set_title("事后对照：CoinGecko 日度快照。此曲线没有进入任何经营信号")
    for d, lab in (("2026-03-31", "快照低点附近"), ("2026-04-28", "4月28日"), ("2026-05-16", "5月16日")):
        if pd.Timestamp(d) in ps.index:
            ax.axvline(pd.Timestamp(d), color="#888888", lw=0.8, ls=":")
    fig.tight_layout()
    fig.savefig(FIG / "price_expost.png", dpi=140)
    plt.close()

    # per account caution
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(sl.index, sl["active_s"] / sl["active_s"].iloc[20], label="活跃账户（指数，20日后为1）", color="#6d28d9")
    ax.plot(sl.index, sl["oi_s"] / sl.loc[sl.index[20], "oi_s"], label="OI", color="#9a3412")
    ax.plot(sl.index, sl["volume_s"] / sl.loc[sl.index[20], "volume_s"], label="Volume", color="#1d4ed8")
    ax.plot(sl.index, sl["revenue_s"] / sl.loc[sl.index[20], "revenue_s"], label="Revenue", color="#047857")
    ax.set_ylabel("相对 2025-12-21 附近的7日中位数")
    ax.set_xlabel("UTC 日期")
    ax.set_title("同一张图上看存量、流量和活跃计数。指数化只用于比较降幅")
    # fix reference to TGE median
    plt.close()
    fig, ax = plt.subplots(figsize=(12, 5))
    ref = sl.loc[TGE]
    for col, label, color in (
        ("active_s", "活跃账户", "#6d28d9"),
        ("oi_s", "OI", "#9a3412"),
        ("volume_s", "Volume", "#1d4ed8"),
        ("revenue_s", "Revenue", "#047857"),
    ):
        ax.plot(sl.index, sl[col] / ref[col], label=label, color=color, lw=1.3)
    ax.axhline(1, color="black", lw=0.5)
    ax.set_ylabel("相对 TGE 当日 7日中位数")
    ax.set_xlabel("UTC 日期")
    ax.set_title("TGE 日起的相对路径。活跃账户的分母效应会抬高一切“每账户”指标")
    ax.legend(ncol=4, frameon=False)
    mark_dates(ax)
    fig.tight_layout()
    fig.savefig(FIG / "indexed_paths.png", dpi=140)
    plt.close()


def self_tests() -> None:
    f = np.exp(np.log(0.8) / 7.0)
    y = 100 * f ** np.arange(40)
    r = weekly_rate(y[-21:])
    assert abs(r + 0.20) < 1e-9, r
    # Two clean regimes of 40 days.
    y2 = np.concatenate([100 * f ** np.arange(40), (100 * f ** 39) * np.exp(np.log(0.95) / 7.0) ** np.arange(1, 41)])
    idx = pd.date_range("2025-01-01", periods=len(y2), freq="D")
    state = pd.Series(y2, index=idx)
    r21 = rolling_weekly_rate(state, 21)
    r14 = rolling_weekly_rate(state, 14)
    r28 = rolling_weekly_rate(state, 28)
    rates = pd.DataFrame({"m_r14": r14, "m_r21": r21, "m_r28": r28})
    # Only t where both the 21d window and its non-overlapping prior sit in a single regime.
    dt = idx[60]
    assert abs(rates.loc[dt, "m_r21"] + 0.05) < 1e-8, rates.loc[dt, "m_r21"]
    assert abs(rates.loc[dt - pd.Timedelta(days=21), "m_r21"] + 0.20) < 1e-8
    c21 = (rates["m_r21"].shift(21) <= -0.12) & ((rates["m_r21"] - rates["m_r21"].shift(21)) >= 0.08) & (rates["m_r21"] >= -0.08)
    assert bool(c21.loc[dt])
    assert not bool(c21.fillna(False).loc[idx[30]])
    # 14d prior still overlaps the regime break at this boundary, so the joint rule must not be forced true here.
    # Base: decline then tight oscillation, and a flat series that must not fire.
    decline = 100 * (0.97 ** np.arange(50))
    low = decline[-1]
    osc = low * (1 + 0.01 * np.sin(np.arange(80)))
    series = pd.Series(np.concatenate([decline, osc]), index=pd.date_range("2025-10-01", periods=130, freq="D"))
    # Use the series itself as state.
    dummy_r = rolling_weekly_rate(series, 28)
    diag = base_diagnostics(series, dummy_r, dict(w=28, L=14, omega=0.50, drift_min=-0.10, frac_min=0.70, max_breaks=2, eps=0.05, k=5))
    assert not bool(diag["flag"].iloc[40])
    assert bool(diag["flag"].iloc[-1]), "expected a base after a held oscillation"
    flat = pd.Series(100.0, index=pd.date_range("2025-10-01", periods=130, freq="D"))
    diag_flat = base_diagnostics(flat, rolling_weekly_rate(flat, 28), BASE)
    assert not bool(diag_flat["flag"].any())
    print("self tests passed")


def main() -> None:
    self_tests()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    df, audit = load_panel()
    df = add_states(df)
    df, rates = add_rates(df)
    base_metrics = ["oi", "active", "volume", "revenue", "new", "oi_per_a", "v_over_oi"]
    bases = {m: base_diagnostics(df[f"{m}_s"], rates[f"{m}_r28"], BASE) for m in base_metrics}
    qual = fee_and_quality(df, rates)
    flags = build_flags(df, rates, bases, qual)
    # Raw-vs-median robustness at primary parameters, using a temporary rate frame.
    raw_first = {}
    for m in ("oi", "active", "volume", "revenue"):
        tmp = pd.DataFrame(
            {
                f"{m}_r14": rolling_weekly_rate(df[m].where(df[m] > 0), 14),
                f"{m}_r21": rolling_weekly_rate(df[m].where(df[m] > 0), 21),
                f"{m}_r28": rolling_weekly_rate(df[m].where(df[m] > 0), 28),
            },
            index=df.index,
        )
        # decel_flag expects columns on `rates` named metric_r*. Build a view by concatenation.
        merged = pd.concat([rates[[c for c in rates.columns if c.startswith(f"{m}_")]].iloc[:, :0], tmp], axis=1)
        # The function reads rates[f"{metric}_r14"] so merged must contain them. tmp does.
        flag_raw = decel_flag(tmp, m, PRIMARY)
        starts = [d for d in episode_starts(flag_raw) if TGE <= d <= CORE_END]
        raw_first[m] = None if not starts else str(starts[0].date())

    rules = {
        "decel_oi": ("oi", flags["decel_oi"]),
        "base_oi": ("oi", flags["base_oi"]),
        "decel_active": ("active", flags["decel_active"]),
        "base_active": ("active", flags["base_active"]),
        "decel_new": ("new", flags["decel_new"]),
        "base_new": ("new", flags["base_new"]),
        "decel_volume": ("volume", flags["decel_volume"]),
        "base_volume": ("volume", flags["base_volume"]),
        "decel_revenue": ("revenue", flags["decel_revenue"]),
        "base_revenue": ("revenue", flags["base_revenue"]),
        "decel_oi_per_a": ("oi_per_a", flags["decel_oi_per_a"]),
        "decel_v_per_a": ("v_per_a", flags["decel_v_per_a"]),
        "decel_v_over_oi": ("v_over_oi", flags["decel_v_over_oi"]),
        "decel_withdraw": ("withdraw", flags["decel_withdraw"]),
        "J6_oi_and_volume_decel": ("revenue", flags["J6_oi_and_volume_decel"]),
        "J7_oi_base_and_flow_decel": ("revenue", flags["J7_oi_base_and_flow_decel"]),
        "J8_three_family": ("revenue", flags["J8_three_family"]),
        "J9_quality_and_volume": ("revenue", flags["J9_quality_and_volume"]),
        "watch": ("revenue", flags["watch"]),
        "confirm": ("revenue", flags["confirm"]),
        "confirm_flow": ("revenue", flags["confirm_flow"]),
    }
    episodes = []
    for name, (anchor, flag) in rules.items():
        episodes.extend(evaluate_rule(name, flag, anchor, df, rates, qual))

    print("running sensitivity grid...")
    sens = sensitivity(df, rates, None)
    stab = grid_stability(sens)
    screen = screening(episodes, stab, df)
    price = load_price()
    checks = checkpoints(df, rates, bases, qual, flags)

    # Daily exports. Full sample, not a monthly reduction.
    panel_cols = [
        "maker",
        "taker",
        "withdraw",
        "transfer",
        "volume",
        "active",
        "revenue",
        "oi",
        "new",
        "cum",
        "trade_fee",
        "nontrade",
        "attr",
        "net_flow",
        "inflow",
        "outflow",
        "liq_fee",
        "trade_count",
        "buyback_usdc",
        "v_per_a",
        "r_per_a",
        "tf_per_a",
        "w_per_a",
        "x_per_a",
        "oi_per_a",
        "take_bps",
        "tf_bps",
        "v_over_oi",
        "maker_share",
        "nt_share",
        "new_over_active",
        "active_over_cum",
        "v_per_trade",
        "liq_over_revenue",
        "buyback_over_revenue",
        "active_spike",
        "new_spike",
        "withdraw_shock",
    ]
    df[panel_cols].to_csv(OUT / "daily_panel.csv", float_format="%.8g")
    slope_cols = [c for c in rates.columns if any(c.startswith(f"{m}_") for m in ("volume", "oi", "revenue", "active", "new", "trade_fee", "oi_per_a", "v_per_a", "v_over_oi", "tf_bps", "withdraw"))]
    slope_cols += ["div_oi_active_21", "div_vol_active_21", "div_rev_vol_21", "div_new_active_21"]
    rates[slope_cols].to_csv(OUT / "daily_slopes.csv", float_format="%.8g")
    base_frames = []
    for m, b in bases.items():
        t = b.add_prefix(f"{m}_")
        base_frames.append(t)
    pd.concat(base_frames, axis=1).to_csv(OUT / "daily_base.csv", float_format="%.8g")
    pd.concat([flags, qual], axis=1).to_csv(OUT / "daily_signals.csv")
    ep_df = pd.DataFrame(episodes)
    ep_df.to_csv(OUT / "episodes.csv", index=False)
    sens.to_csv(OUT / "sensitivity.csv", index=False)
    pd.DataFrame([{k: v for k, v in r.items() if k != "episode"} for r in screen]).to_csv(OUT / "screening.csv", index=False)

    spikes = {
        "active": [str(i.date()) for i in df.index[df["active_spike"].fillna(False)]],
        "new": [str(i.date()) for i in df.index[df["new_spike"].fillna(False)]],
    }
    summary = {
        "audit": audit,
        "primary_decel": PRIMARY,
        "primary_base": BASE,
        "quality_rule": Q_PARAMS,
        "placebo_pre_tge": placebo(rates),
        "raw_slope_first_core_date": raw_first,
        "regimes": regime_table(df),
        "event_study_bps": event_study_bps(df),
        "troughs_expost_operating": operating_troughs(df),
        "dow_deviation_from_mean": dow_table(df),
        "oi_jumps_gt_30pct": oi_jumps(df),
        "correlations_r21": correlations(rates),
        "stability": stab,
        "checkpoints": checks,
        "announcements_kept": announcements(),
        "price_expost": price_block(price),
        "screening": [{k: v for k, v in r.items() if k != "episode"} | {"first_episode": r["episode"]} for r in screen],
        "spike_days": spikes,
        "definitions": {
            "state": "S_t = median(Y_{t-6}..Y_t)",
            "weekly_rate": "OLS slope of log S on the window, times 7, then expm1",
            "decel": "prior non-overlapping window rate <= -12%, improvement >= 8pp, current rate >= -8%, on both 14d and 21d for 5 days, and 28d rate > -12% and improved",
            "base": "frozen prior 28d P10/P90, last 14d frac inside expanded band >= 0.70, breaks <= 2, width/median <= 0.50, center drift >= -10%, persisted 5 days, and series is already down 25% from its expanding peak since 2025-10-01 or was falling at least 8%/week",
            "false_self": "7d median 28 days later is at least 25% below the signal day",
            "false_outcome": "both revenue and volume 7d medians are at least 20% lower 28 days later",
            "price": "not an input",
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    save_plots(df, rates, flags, episodes, price)
    print("episodes", len(episodes))
    for rule in ("decel_oi", "base_oi", "decel_active", "base_active", "decel_volume", "decel_revenue", "confirm", "watch", "J7_oi_base_and_flow_decel"):
        hits = [e for e in episodes if e["rule"] == rule]
        print(rule, [(e["date"], e["window"], round(e["self_fwd28"] or 0, 3), round(e["revenue_fwd56"] or 0, 3)) for e in hits])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
