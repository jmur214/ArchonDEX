"""T-385 (B-10) — a permanent 10% gold leg: 90% equity / 10% gold, monthly rebalance, vs 1x SPY.

Pre-registration FROZEN at 0cc3f56; amendment 1 (director rulings + pre-data operational decisions)
at f702523: docs/Sources/prereg_b10_gold_leg_2026-11-11.md. N_trials += 1.

Standalone harness (T-311 pattern). Never touches BacktestController. Substrate = T-306
(`data/research/substrate_multidecade/`, read-only) through T-311's `load_substrate` (imported,
never edited). The T-306 cash leg is NOT used (prereg §3.4): no number here depends on it.

Gating (prereg §6 + amendment 1): Δ log TW = Σ [log(1+r_T) − log(1+r_B)], ci_low from
`MetricsEngine.bootstrap_distribution` (auto block, 1000 iter, seed 0) on W-71 (1971–2025) and
W-00 (2000–2025); MDD reduction on W-71's realized path. The refutation takes precedence.

Fail-closed ([NN-FAIL-CLOSED]): every guard G1–G11 of prereg §8 raises B10Halt (exit 2).

Usage:
  python -m scripts.b10_gold_leg --smoke                 # first 12 months of each window
  python -m scripts.b10_gold_leg --out data/b10_local/b10_results.json
Outputs are worktree-LOCAL under data/b10_local/ (never through the data/research symlink).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from core.measurement.mbl_gate import expected_max_normal  # noqa: E402  (read-only)
from scripts import deep_reverify_sleeve_t311 as t311  # noqa: E402  (import only — never edited)

# --------------------------------------------------------------------------- frozen inputs (§3.5)
SUB = ROOT / "data/research/substrate_multidecade"
GLD_PATH = ROOT / "data/processed/GLD_1d.csv"
T311_PATH = ROOT / "scripts/deep_reverify_sleeve_t311.py"
PINNED_MD5: Dict[Path, str] = {
    SUB / "equity_tr_daily.csv": "c2030019b8846792b5f8e3d18421c905",
    SUB / "gold_tr_daily.csv": "30c9d15d18ce2a0c511a0e2398c55a26",
    GLD_PATH: "8088c96fb0630fe9843d4c1c8d911609",
    T311_PATH: "a7f77d5f28fdfb889c1cd3add83befbb",
}
OUT_DIR = ROOT / "data/b10_local"
DEFAULT_OUT = OUT_DIR / "b10_results.json"

# --------------------------------------------------------------------------- frozen construction (§4/§5)
TD = 252
WEIGHTS = {"equity": 0.90, "gold": 0.10}
ER_PRIMARY = {"equity": 0.0009, "gold": 0.0009}           # IAUM-class gold (ruling 3)
ER_SENS_GOLD = 0.0040                                       # GLD-class = T-311 ER["gold"]
N_ITER = 1000
SEED = 0
SENS_BLOCK = 252
PARITY_TOL = 1e-12
IDENTITY_TOL = 1e-9
MIN_BOOT_LEN = 2 * TD                                       # G8
MAX_NATIVE_GAP_DAYS = 10                                    # G3
MAX_STALENESS_DAYS = 7                                      # G4 / G6
MDD_CLAUSE_PP = 3.0
GLD_GAP_BOUNDS = (-0.0100, 0.0020)                          # G11, annualized log gap GLD − substrate
GLD_MIN_CORR21 = 0.95
GLD_START, GLD_END = "2020-04-09", "2025-12-31"

# (label, base close, last return date) — §3.1, ruling 5
WINDOWS: Dict[str, Tuple[str, str]] = {
    "W-71 (1971-2025)": ("1970-12-31", "2025-12-31"),
    "W-00 (2000-2025)": ("1999-12-31", "2025-12-31"),
}
W22 = ("W-22 (calendar 2022)", "2021-12-31", "2022-12-30")
SMOKE_WINDOWS: Dict[str, Tuple[str, str]] = {
    "W-71 first 12m": ("1970-12-31", "1971-12-31"),
    "W-00 first 12m": ("1999-12-31", "2000-12-29"),
}
# MBL lines (§10): gate N_eff at +1, and the hand count lower bound / upper sensitivity.
MBL_N = {"gate_N_eff_37.08": 37.084, "hand_N_281": 281.0, "hand_N_288": 288.0}


class B10Halt(RuntimeError):
    """A fail-closed guard fired. Never converted into a number."""


# --------------------------------------------------------------------------- G1: pins
def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pins(pins: Dict[Path, str]) -> Dict[str, str]:
    seen = {}
    for p, want in pins.items():
        if not p.exists():
            raise B10Halt(f"G1: pinned input missing: {p}")
        got = md5_file(p)
        if got != want:
            raise B10Halt(f"G1: md5 mismatch for {p.name}: got {got}, pinned {want}")
        seen[p.name] = got
    if t311.TD != TD or abs(t311.TXN - 0.00015) > 1e-15 or t311.ER.get("gold") != ER_SENS_GOLD \
            or t311.ER.get("equity") != ER_PRIMARY["equity"]:
        raise B10Halt("G1: T-311 constants differ from the prereg (TD/TXN/ER)")
    return seen


# --------------------------------------------------------------------------- G2–G6: native-calendar guards
def read_native(leg: str) -> pd.Series:
    s = pd.read_csv(SUB / f"{leg}_tr_daily.csv", parse_dates=[0], index_col=0).iloc[:, 0]
    return s


def assert_native_integrity(s: pd.Series, name: str) -> None:
    """G2 — on the NATIVE series, before any reindex/ffill."""
    if not s.index.is_monotonic_increasing:
        raise B10Halt(f"G2: {name} native index not monotonic increasing")
    if s.index.has_duplicates:
        raise B10Halt(f"G2: {name} native index has duplicate dates")
    v = s.to_numpy(dtype=float)
    if not np.all(np.isfinite(v)):
        raise B10Halt(f"G2: {name} has NaN/inf values")
    if np.any(v <= 0):
        raise B10Halt(f"G2: {name} has non-positive levels")


def native_span(idx: pd.DatetimeIndex, base: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """Native prints covering [base, end]: the last print at/before base through end."""
    pos = idx.searchsorted(base, side="right") - 1
    if pos < 0:
        raise B10Halt(f"G6: no native print at or before base {base.date()}")
    return idx[pos:][idx[pos:] <= end]


def max_native_gap(idx: pd.DatetimeIndex, base: pd.Timestamp, end: pd.Timestamp) -> int:
    span = native_span(idx, base, end)
    if len(span) < 2:
        raise B10Halt("G3: fewer than two native prints in the window")
    # unit-safe: TimedeltaIndex.days (pandas may parse to datetime64[us], so asi8 is NOT ns —
    # a hard-coded ns divisor silently shrinks every gap 1000x; caught by the planted-hole lock)
    return int((span[1:] - span[:-1]).days.max())


def assert_native_gaps(idx: pd.DatetimeIndex, base: pd.Timestamp, end: pd.Timestamp, name: str,
                       max_days: int = MAX_NATIVE_GAP_DAYS) -> int:
    """G3 — a data outage hidden by a later ffill shows here as a long native gap."""
    g = max_native_gap(idx, base, end)
    if g > max_days:
        raise B10Halt(f"G3: {name} native gap {g}d > {max_days}d inside [{base.date()}, {end.date()}]")
    return g


def asof_staleness(cal: pd.DatetimeIndex, native: pd.DatetimeIndex) -> np.ndarray:
    pos = native.searchsorted(cal, side="right") - 1
    if np.any(pos < 0):
        raise B10Halt("G4: a calendar date precedes the leg's first native print")
    return np.asarray((cal - native[pos]).days)


def assert_staleness(cal: pd.DatetimeIndex, native: pd.DatetimeIndex, name: str,
                     max_days: int = MAX_STALENESS_DAYS) -> int:
    """G4 — the price carried onto each equity date is at most `max_days` old."""
    st = asof_staleness(cal, native)
    m = int(st.max()) if len(st) else 0
    if m > max_days:
        raise B10Halt(f"G4: {name} as-of staleness {m}d > {max_days}d")
    return m


def assert_end_within_native(end: pd.Timestamp, natives: Dict[str, pd.DatetimeIndex]) -> None:
    """G5 — no window may end after a leg's last NATIVE print (T-311's loader ffills past it)."""
    last = min(ix.max() for ix in natives.values())
    if end > last:
        raise B10Halt(f"G5: window end {end.date()} is after min(native ends) {last.date()} — "
                      f"would use a forward-filled tail")


def assert_base_print(base: pd.Timestamp, natives: Dict[str, pd.DatetimeIndex],
                      max_days: int = MAX_STALENESS_DAYS) -> None:
    """G6 — each leg has a native print within `max_days` at/before the base close."""
    for name, ix in natives.items():
        pos = ix.searchsorted(base, side="right") - 1
        if pos < 0 or (base - ix[pos]).days > max_days:
            raise B10Halt(f"G6: {name} has no native print within {max_days}d of base {base.date()}")


# --------------------------------------------------------------------------- arms
def rebal_returns(px: pd.DataFrame, weights: Dict[str, float], er: Dict[str, float],
                  txn: float = t311.TXN) -> Tuple[pd.Series, Dict[str, float]]:
    """Vectorized monthly-rebalanced constant-mix book (the T-311 `robo_returns` convention, no cash).

    Holdings reset to target weights at the first trading day of each new month, BEFORE that day's
    return; cost = Σ|Δw| × txn charged that day; within a month the book drifts. Row 0 of `px` is
    the base close (no return). Returns (daily returns, census)."""
    cols = list(weights)
    if abs(sum(weights.values()) - 1.0) > 1e-12:
        raise B10Halt("weights must sum to 1 (no cash leg in B-10)")
    rets = px[cols].pct_change().iloc[1:]
    rets = rets - pd.Series({k: er[k] / TD for k in cols})
    if not np.all(np.isfinite(rets.to_numpy())):
        raise B10Halt("G7: non-finite leg return inside the window")
    month = rets.index.year * 12 + rets.index.month
    seg = pd.Series((month != np.roll(month, 1)).astype(int), index=rets.index)
    seg.iloc[0] = 0
    seg = seg.cumsum()
    w = pd.Series(weights)[cols]
    growth = (1.0 + rets).groupby(seg.values).cumprod()
    value = (growth * w).sum(axis=1)
    prev = value.groupby(seg.values).shift(1).fillna(1.0)
    out = value / prev - 1.0
    # turnover at each rebalance: drifted weights at the prior month's last close vs target
    last_rows = growth.groupby(seg.values).tail(1)
    drift_val = (last_rows * w).sum(axis=1)
    drifted_w = (last_rows * w).div(drift_val, axis=0)
    turnover = (drifted_w - w).abs().sum(axis=1).to_numpy()[:-1]   # the final segment never rebalances
    first_rows = rets.index[(seg.diff().fillna(0) > 0).to_numpy()]
    if len(first_rows) != len(turnover):
        raise B10Halt("G10: rebalance rows and turnover rows disagree")
    cost = pd.Series(0.0, index=rets.index)
    cost.loc[first_rows] = turnover * txn
    out = out - cost
    census = {"n_rebalances": int(len(first_rows)),
              "n_month_boundaries": int(seg.iloc[-1]),
              "turnover_sum": float(turnover.sum()),
              "turnover_mean": float(turnover.mean()) if len(turnover) else 0.0,
              "cost_sum": float(cost.sum())}
    if census["n_rebalances"] != census["n_month_boundaries"]:
        raise B10Halt("G10: rebalance count != month boundaries")
    return out, census


def t311_rebal(legs_w: Dict[str, pd.Series]) -> pd.Series:
    """The sensitivity arm, literally T-311's function (gold ER 0.40%); zero cash, no `_cash` weight."""
    zero = pd.Series(0.0, index=legs_w["equity"].index)
    r = t311.robo_returns(legs_w, dict(WEIGHTS), zero)
    r.index = pd.DatetimeIndex(r.index)
    return r


def assert_parity(px: pd.DataFrame, legs_w: Dict[str, pd.Series]) -> float:
    """G9 parity lock: own vectorized function at T-311's ER == t311.robo_returns to 1e-12."""
    mine, _ = rebal_returns(px, WEIGHTS, {"equity": t311.ER["equity"], "gold": t311.ER["gold"]})
    ref = t311_rebal(legs_w)
    if not mine.index.equals(ref.index):
        raise B10Halt("G9: parity index mismatch vs t311.robo_returns")
    d = float(np.max(np.abs(mine.to_numpy() - ref.to_numpy())))
    if not d <= PARITY_TOL:
        raise B10Halt(f"G9: parity vs t311.robo_returns failed, max |Δ| = {d:.3e}")
    return d


def slice_legs(legs: Dict[str, pd.Series], base: str, end: str) -> Dict[str, pd.Series]:
    b, e = pd.Timestamp(base), pd.Timestamp(end)
    out = {k: v[(v.index >= b) & (v.index <= e)] for k, v in legs.items()}
    if out["equity"].index[0] != b:
        raise B10Halt(f"G6: base {base} is not an equity trading day")
    if out["equity"].index[-1] != e:
        raise B10Halt(f"G5: window end {end} is not the last equity row in the slice")
    return out


def paired_diff(t_r: pd.Series, b_r: pd.Series) -> pd.Series:
    """G7 — identical dates, finite."""
    if not t_r.index.equals(b_r.index):
        raise B10Halt("G7: treatment and baseline date indexes differ")
    d = np.log1p(t_r) - np.log1p(b_r)
    if not np.all(np.isfinite(d.to_numpy())):
        raise B10Halt("G7: non-finite paired differential")
    return d


def boot(d: pd.Series, block: Optional[int]) -> Dict[str, float]:
    """G8 then the project-standard block bootstrap of Σd."""
    if len(d) < MIN_BOOT_LEN:
        raise B10Halt(f"G8: bootstrap input length {len(d)} < {MIN_BOOT_LEN}")
    res = ME.bootstrap_distribution(d, lambda x: float(np.sum(x)), n_iterations=N_ITER,
                                    block_length=block, seed=SEED, confidence=0.95)
    if res.get("n_iterations") != N_ITER:
        raise B10Halt("G8: bootstrap off-spec")
    return {k: float(v) for k, v in res.items()}


# --------------------------------------------------------------------------- metrics
def curve(r: pd.Series, base: pd.Timestamp) -> pd.Series:
    """Equity curve INCLUDING the base value 1.0 (a first-day loss counts — §5)."""
    return pd.concat([pd.Series([1.0], index=[base]), (1.0 + r).cumprod()])


def drawdown(eq: pd.Series) -> Dict[str, Optional[str]]:
    run_max = eq.cummax()
    dd = eq / run_max - 1.0
    trough = dd.idxmin()
    mdd = float(dd.min())
    peak = eq.loc[:trough].idxmax()
    after = eq.loc[trough:]
    rec = after.index[after >= eq.loc[peak]]
    return {"mdd": mdd, "peak": str(peak.date()), "trough": str(trough.date()),
            "recovery": str(rec[0].date()) if len(rec) else None}


def ann_ir(d: pd.Series) -> float:
    return float(ME.sharpe_ratio(d, 0.0, TD))


def window_arms(legs: Dict[str, pd.Series], base: str, end: str) -> Dict:
    lw = slice_legs(legs, base, end)
    px = pd.DataFrame(lw)
    t_r, cen = rebal_returns(px, WEIGHTS, ER_PRIMARY)
    b_r = t311.buyhold_equity(lw)
    b_r.index = pd.DatetimeIndex(b_r.index)
    parity = assert_parity(px, lw)
    s_r = t311_rebal(lw)                         # GLD-fee sensitivity arm
    return {"legs": lw, "T": t_r, "B": b_r, "S": s_r, "census": cen, "parity_max_abs": parity}


def run_window(label: str, legs: Dict[str, pd.Series], natives: Dict[str, pd.DatetimeIndex],
               base: str, end: str, full: bool = True) -> Dict:
    b_ts, e_ts = pd.Timestamp(base), pd.Timestamp(end)
    assert_end_within_native(e_ts, natives)                                   # G5
    assert_base_print(b_ts, natives)                                          # G6
    gaps = {k: assert_native_gaps(ix, b_ts, e_ts, k) for k, ix in natives.items()}   # G3
    arms = window_arms(legs, base, end)
    cal = arms["legs"]["equity"].index
    stale = {k: assert_staleness(cal, ix, k) for k, ix in natives.items()}   # G4
    d = paired_diff(arms["T"], arms["B"])
    eqT, eqB = curve(arms["T"], b_ts), curve(arms["B"], b_ts)
    ident = float(abs(d.sum() - (math.log(eqT.iloc[-1]) - math.log(eqB.iloc[-1]))))
    if not ident <= IDENTITY_TOL:
        raise B10Halt(f"G9: Σd identity failed by {ident:.3e}")
    years = (e_ts - b_ts).days / 365.25
    out = {"label": label, "base": base, "end": end, "first_return": str(cal[1].date()),
           "n_returns": int(len(d)), "years": years,
           "guards": {"native_max_gap_days": gaps, "asof_max_staleness_days": stale,
                      "parity_max_abs": arms["parity_max_abs"], "sum_identity_abs": ident,
                      "rebalance_census": arms["census"]}}
    if not full:
        return out
    dT, dB = drawdown(eqT), drawdown(eqB)
    out["arms"] = {
        "T_90_10_iaum": {"terminal_mult": float(eqT.iloc[-1]), "cagr": float(eqT.iloc[-1] ** (1 / years) - 1),
                         **{f"dd_{k}": v for k, v in dT.items()}},
        "B_1x_spy": {"terminal_mult": float(eqB.iloc[-1]), "cagr": float(eqB.iloc[-1] ** (1 / years) - 1),
                     **{f"dd_{k}": v for k, v in dB.items()}},
    }
    out["mdd_reduction_pp"] = (abs(dB["mdd"]) - abs(dT["mdd"])) * 100.0
    bs = boot(d, None)
    bs252 = boot(d, SENS_BLOCK)
    out["delta_log_tw"] = {"point": float(d.sum()), "ann_point": float(d.sum()) / years,
                           "auto_block": bs, "block_252": bs252,
                           "ann_ci_auto": [bs["ci_low"] / years, bs["ci_high"] / years],
                           "ann_ci_252": [bs252["ci_low"] / years, bs252["ci_high"] / years]}
    out["ir_diff"] = ann_ir(d)
    out["te_ann"] = float(d.std() * math.sqrt(TD))
    out["mbl_ir_needed"] = {k: expected_max_normal(n) / math.sqrt(years) for k, n in MBL_N.items()}
    # ER sensitivity (GLD 0.40% via t311.robo_returns)
    dS = paired_diff(arms["S"], arms["B"])
    bsS = boot(dS, None)
    out["sens_gld_fee"] = {"point": float(dS.sum()), "ann_point": float(dS.sum()) / years,
                           "auto_block": bsS,
                           "mdd": drawdown(curve(arms["S"], b_ts))["mdd"]}
    # independent cross-check (T-311 paired, L=21) — includes the ΔMDD CI
    p = t311.paired(arms["T"], arms["B"])
    out["t311_paired"] = {k: p[k] for k in ("dLogWealthAnn_ci", "dLogWealthAnn_mean", "dMaxDD_ci",
                                             "dMaxDD_mean", "p_compound_win")}
    out["_series"] = {"T": arms["T"], "B": arms["B"], "d": d, "legs": arms["legs"]}
    return out


# --------------------------------------------------------------------------- descriptive (§7)
def segment_mdd(r: pd.Series, a: str, b: str) -> Optional[Dict]:
    seg = r[(r.index >= a) & (r.index <= b)]
    if len(seg) < 20:
        return None
    base = r.index[r.index.get_loc(seg.index[0]) - 1] if r.index.get_loc(seg.index[0]) > 0 else seg.index[0]
    eq = curve(seg, base)
    return {"mdd": drawdown(eq)["mdd"], "ret": float(eq.iloc[-1] - 1.0)}


def crisis_table(T: pd.Series, B: pd.Series) -> Dict:
    out = {}
    for name, (a, b) in t311.CRISES.items():
        mt, mb = segment_mdd(T, a, b), segment_mdd(B, a, b)
        if mt is None or mb is None or pd.Timestamp(a) < T.index[0]:
            continue
        out[name] = {"T_mdd": mt["mdd"], "B_mdd": mb["mdd"], "T_ret": mt["ret"], "B_ret": mb["ret"],
                     "mdd_reduction_pp": (abs(mb["mdd"]) - abs(mt["mdd"])) * 100.0}
    return out


def decade_table(d: pd.Series, legs: Dict[str, pd.Series]) -> Dict:
    eq_net = legs["equity"].pct_change().iloc[1:] - ER_PRIMARY["equity"] / TD
    au_net = legs["gold"].pct_change().iloc[1:] - ER_PRIMARY["gold"] / TD
    key = eq_net.index.year * 100 + eq_net.index.month
    m_eq = (1 + eq_net).groupby(key).prod() - 1
    m_au = (1 + au_net).groupby(key).prod() - 1
    out = {}
    for dec in sorted(set((d.index.year // 10) * 10)):
        sel = (d.index.year // 10) * 10 == dec
        msel = (m_eq.index // 100 // 10) * 10 == dec
        out[f"{dec}s"] = {"sum_d": float(d[sel].sum()), "n_days": int(sel.sum()),
                          "corr_monthly_eq_gold": float(np.corrcoef(m_eq[msel], m_au[msel])[0, 1]),
                          "n_months": int(msel.sum())}
    return out


def w22(legs: Dict[str, pd.Series], natives: Dict[str, pd.DatetimeIndex]) -> Dict:
    label, base, end = W22
    r = run_window(label, legs, natives, base, end, full=False)
    arms = window_arms(legs, base, end)
    b_ts = pd.Timestamp(base)
    eqT, eqB = curve(arms["T"], b_ts), curve(arms["B"], b_ts)
    dT, dB = drawdown(eqT), drawdown(eqB)
    r.update({"T_ret": float(eqT.iloc[-1] - 1), "B_ret": float(eqB.iloc[-1] - 1),
              "T_mdd": dT["mdd"], "B_mdd": dB["mdd"], "T_trough": dT["trough"], "B_trough": dB["trough"],
              "mdd_reduction_pp": (abs(dB["mdd"]) - abs(dT["mdd"])) * 100.0,
              "delta_log_tw": float(paired_diff(arms["T"], arms["B"]).sum())})
    return r


def gld_validation(gold_native: pd.Series) -> Dict:
    """G11 — the local GLD file vs the substrate gold leg, 2020-04-09 → 2025-12-31."""
    g = pd.read_csv(GLD_PATH, parse_dates=["Date"], index_col="Date")["Close"].sort_index()
    assert_native_integrity(g, "GLD")
    a, b = pd.Timestamp(GLD_START), pd.Timestamp(GLD_END)
    g = g[(g.index >= a) & (g.index <= b)]
    s = gold_native[(gold_native.index >= a) & (gold_native.index <= b)]
    common = g.index.intersection(s.index)
    if len(common) < 1000 or (common[0] - a).days > MAX_STALENESS_DAYS \
            or (b - common[-1]).days > MAX_STALENESS_DAYS:
        raise B10Halt(f"G11: GLD/substrate common span too short or misaligned ({len(common)} days)")
    g, s = g.loc[common], s.loc[common]
    years = (common[-1] - common[0]).days / 365.25
    gap = (math.log(g.iloc[-1] / g.iloc[0]) - math.log(s.iloc[-1] / s.iloc[0])) / years
    pos = np.arange(0, len(common), 21)
    lg, ls = np.diff(np.log(g.to_numpy()[pos])), np.diff(np.log(s.to_numpy()[pos]))
    corr = float(np.corrcoef(lg, ls)[0, 1])
    ok = GLD_GAP_BOUNDS[0] <= gap <= GLD_GAP_BOUNDS[1] and corr >= GLD_MIN_CORR21
    res = {"span": [str(common[0].date()), str(common[-1].date())], "n_common_days": int(len(common)),
           "years": years, "ann_log_gap_gld_minus_substrate": gap, "corr_21d": corr,
           "n_21d_blocks": int(len(lg)), "bounds": list(GLD_GAP_BOUNDS), "min_corr": GLD_MIN_CORR21,
           "pass": bool(ok)}
    if not ok:
        raise B10Halt(f"G11: GLD splice validation failed: {res}")
    return res


# --------------------------------------------------------------------------- outcome (§6 + amendment 1)
def outcome(ci71: float, ci00: float, mdd_pp: float) -> str:
    if ci71 < 0 or ci00 < 0:
        return "REFUTED"
    if ci71 > 0 and mdd_pp >= MDD_CLAUSE_PP and ci00 >= 0:
        return "H1 MET"
    return "NOT MET, not refuted"


def labels(res: Dict) -> List[str]:
    out = []
    for w in WINDOWS:
        r = res["windows"][w]
        std, a252 = r["delta_log_tw"]["auto_block"]["ci_low"], r["delta_log_tw"]["block_252"]["ci_low"]
        gld = r["sens_gld_fee"]["auto_block"]["ci_low"]
        if np.sign(std) != np.sign(a252):
            out.append(f"not robust to annual blocks ({w})")
        if np.sign(std) != np.sign(gld):
            out.append(f"not robust to GLD-era cost ({w})")
    return out


# --------------------------------------------------------------------------- driver
def load_all() -> Tuple[Dict[str, pd.Series], Dict[str, pd.DatetimeIndex], pd.Series, Dict[str, str]]:
    pins = check_pins(PINNED_MD5)                                             # G1
    nat = {k: read_native(k) for k in ("equity", "gold")}
    for k, s in nat.items():
        assert_native_integrity(s, k)                                         # G2
    legs, _cash_discarded = t311.load_substrate(["equity", "gold"])           # cash NOT used (§3.4)
    del _cash_discarded
    return legs, {k: s.index for k, s in nat.items()}, nat["gold"], pins


def _out_dir_ok(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rp = path.resolve()
    if not str(rp).startswith(str(ROOT.resolve()) + "/data/b10_local"):
        raise B10Halt(f"outputs must be worktree-local under data/b10_local/, got {rp}")
    if path.parent.is_symlink():
        raise B10Halt("data/b10_local must be a real directory, not a symlink")
    return path


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [_strip(v) for v in obj]
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj


def write_json(path: Path, obj: Dict) -> str:
    _out_dir_ok(path)
    path.write_text(json.dumps(_strip(obj), indent=2, sort_keys=True, default=str) + "\n")
    return md5_file(path)


def smoke() -> int:
    legs, natives, _, pins = load_all()
    for label, (base, end) in SMOKE_WINDOWS.items():
        r = run_window(label, legs, natives, base, end, full=False)
        c = r["guards"]["rebalance_census"]
        if c["n_rebalances"] != 11 or not c["turnover_sum"] > 0:
            raise B10Halt(f"smoke census failed for {label}: {c}")
        r["pins"] = pins
        tag = "W71" if label.startswith("W-71") else "W00"
        m = write_json(OUT_DIR / f"b10_smoke_{tag}.json", r)
        print(f"SMOKE {label}: {r['n_returns']} returns, rebalances {c['n_rebalances']}, "
              f"parity {r['guards']['parity_max_abs']:.1e}, identity {r['guards']['sum_identity_abs']:.1e}, "
              f"gaps {r['guards']['native_max_gap_days']}, stale {r['guards']['asof_max_staleness_days']} "
              f"-> md5 {m}")
    return 0


def main(out: Path) -> int:
    legs, natives, gold_native, pins = load_all()
    res: Dict = {"task": "T-385 (B-10)", "prereg": "0cc3f56 + amendment f702523", "pins": pins,
                 "construction": {"weights": WEIGHTS, "er_primary": ER_PRIMARY, "er_sens_gold": ER_SENS_GOLD,
                                  "txn": t311.TXN, "n_iter": N_ITER, "seed": SEED, "sens_block": SENS_BLOCK},
                 "gld_validation": gld_validation(gold_native), "windows": {}}
    for label, (base, end) in WINDOWS.items():
        res["windows"][label] = run_window(label, legs, natives, base, end)
    w71 = res["windows"]["W-71 (1971-2025)"]
    w00 = res["windows"]["W-00 (2000-2025)"]
    res["crisis_mdd_w71"] = crisis_table(w71["_series"]["T"], w71["_series"]["B"])
    res["decades_w71"] = decade_table(w71["_series"]["d"], w71["_series"]["legs"])
    res["w22"] = w22(legs, natives)
    seg22 = t311.CRISES["2022"]
    res["w71_segment_2022_t311"] = {"T": segment_mdd(w71["_series"]["T"], *seg22),
                                    "B": segment_mdd(w71["_series"]["B"], *seg22)}
    res["outcome"] = outcome(w71["delta_log_tw"]["auto_block"]["ci_low"],
                             w00["delta_log_tw"]["auto_block"]["ci_low"], w71["mdd_reduction_pp"])
    res["labels"] = labels(res)
    m = write_json(out, res)
    for label in WINDOWS:
        r = res["windows"][label]
        dl = r["delta_log_tw"]
        print(f"{label}: ΔlogTW {dl['point']:+.4f} ({dl['ann_point']*100:+.3f}%/yr) "
              f"CI[{dl['auto_block']['ci_low']:+.4f},{dl['auto_block']['ci_high']:+.4f}] blk {dl['auto_block']['block_length']:.0f} | "
              f"252: [{dl['block_252']['ci_low']:+.4f},{dl['block_252']['ci_high']:+.4f}] | "
              f"MDD B {r['arms']['B_1x_spy']['dd_mdd']*100:.2f}% T {r['arms']['T_90_10_iaum']['dd_mdd']*100:.2f}% "
              f"(red {r['mdd_reduction_pp']:+.2f}pp)")
    print(f"OUTCOME: {res['outcome']}  labels: {res['labels']}")
    print(f"wrote {out} md5 {m}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--smoke", action="store_true", help="first 12 months of each window only")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()
    try:
        sys.exit(smoke() if a.smoke else main(a.out if a.out.is_absolute() else ROOT / a.out))
    except B10Halt as exc:
        print(f"B10 HALT: {exc}", file=sys.stderr)
        sys.exit(2)
