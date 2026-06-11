#!/usr/bin/env python
# scripts/crisis_replay_t118b.py
"""T-143 — Crisis-replay harness implementing the LOCKED T-118b
pre-registration (docs/Audit/t118b_preregistration_2026_06_10.md,
v1 + ADDENDUM v2) as tested code.

THE REGISTRATION GOVERNS. Every criterion, threshold, episode and split
below is transcribed from the locked doc; deviations are forbidden.
Where the prose leaves an operationalization choice, the §6 integrity
rule applies — resolve LESS favorable to the overlay — and the choice is
documented inline AND in the T-143 audit doc. This harness contains the
analysis only; it has never touched a real campaign artifact (T-143
hard constraint — the first real-data run is director-executed
post-relaunch).

Inputs (per arm): a per-bar artifact frame with columns
``equity`` (portfolio NAV — capital accounting in NAV terms ONLY),
``gross_notional`` (T-124 column; mechanism check), indexed by trading
date. Daily returns derive from equity.

The locked criteria (gate = PRIMARY CONFIG ONLY; all others sensitivity):
  (i)    median ΔMaxDD over the 5 actionable episodes ≥ +3pp
  (ii)   sign test ≥ 4/5 (success = episode ΔMaxDD > +0.5pp)
  (iii)  calm-drag: CAGR(on)−CAGR(off) on non-episode days ≥ −40 bps,
         stationary-bootstrap 90% CI excluding −80 bps
  (iv)   no single episode > 50% of aggregate equal-weighted benefit
  (v2-a) OOS both improve: COVID and 2022 each ΔMaxDD > +0.5pp
  (v2-b) terminal wealth: full-window cumulative return on ≥ off
  (v2-c) episode-frequency-annualized crisis benefit ≥ 3× realized calm drag
  (v2-d) GFC floor: ΔMaxDD(GFC) ≥ +5pp
PASS iff ALL; PARTIAL iff (i)+(iii) hold but not all; FAIL otherwise.
Dotcom is REPORTED blind (HMM data floor 2006-04), never gated.

CLI (the director's one command post-relaunch, real artifacts):
  python -m scripts.crisis_replay_t118b \
      --on <on_artifacts.csv> --off <off_artifacts.csv> \
      --spx <spx_tr.csv> --primary-config --config-label "0.5x_k5_h(0.4/0.3/10)"
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

TRADING_DAYS = 252.0

# ----------------------------------------------------------------------
# Locked thresholds (registration §4, §5, addendum v2) — DO NOT EDIT
# ----------------------------------------------------------------------
DD_THRESHOLD = 0.15              # episode rule: TR peak-to-trough ≥ 15%
EXTENSION_TD = 20                # window = peak → trough + 20 trading days
MEDIAN_DMAXDD_PP = 3.0           # (i)
SIGN_SUCCESS_PP = 0.5            # success = ΔMaxDD > +0.5pp
SIGN_REQUIRED = 4                # (ii) ≥ 4/5 (addendum supersedes 5/6)
SIGN_N = 5
CALM_DRAG_FLOOR_BPS = -40.0      # (iii) point
CALM_DRAG_CI_BOUND_BPS = -80.0   # (iii) 90% CI must exclude
SINGLE_EPISODE_MAX_SHARE = 0.50  # (iv)
OOS_IMPROVE_PP = 0.5             # (v2-a)
RATIO_REQUIRED = 3.0             # (v2-c)
GFC_FLOOR_PP = 5.0               # (v2-d)

# Locked episode set (addendum v2 §1). Peak/trough months anchor the
# mechanical date-fixing; exact trading dates are fixed from the TR
# series at analysis time (no discretion).
LOCKED_EPISODES: List[Dict] = [
    {"id": "dotcom", "label": "Dotcom 2000-03→2002-10",
     "peak_month": "2000-03", "trough_month": "2002-10",
     "actionable": False, "oos": False, "blind": True},
    {"id": "gfc", "label": "GFC 2007-10→2009-03",
     "peak_month": "2007-10", "trough_month": "2009-03",
     "actionable": True, "oos": False, "blind": False},
    {"id": "us2011", "label": "US downgrade 2011-04→2011-10",
     "peak_month": "2011-04", "trough_month": "2011-10",
     "actionable": True, "oos": False, "blind": False},
    {"id": "q42018", "label": "Q4-2018 2018-09→2018-12",
     "peak_month": "2018-09", "trough_month": "2018-12",
     "actionable": True, "oos": False, "blind": False},
    {"id": "covid", "label": "COVID 2020-02→2020-03 (fast)",
     "peak_month": "2020-02", "trough_month": "2020-03",
     "actionable": True, "oos": True, "blind": False},
    {"id": "y2022", "label": "2022 grind 2022-01→2022-10 (slow)",
     "peak_month": "2022-01", "trough_month": "2022-10",
     "actionable": True, "oos": True, "blind": False},
]
ACTIONABLE_IDS = [e["id"] for e in LOCKED_EPISODES if e["actionable"]]
OOS_IDS = [e["id"] for e in LOCKED_EPISODES if e["oos"]]


@dataclass
class Episode:
    episode_id: str
    label: str
    peak: pd.Timestamp
    trough: pd.Timestamp
    end: pd.Timestamp            # trough + EXTENSION_TD trading days
    actionable: bool
    oos: bool
    blind: bool
    max_dd: float                # the TR drawdown that qualified it


@dataclass
class EpisodeResult:
    episode_id: str
    label: str
    actionable: bool
    oos: bool
    blind: bool
    d_maxdd_pp: float
    d_total_return_pp: float
    d_realized_vol_pp: float
    days_to_degross: Optional[int]
    boot_ci_l5: Tuple[float, float]    # ΔMaxDD 90% CI, 5d blocks (descriptive)
    boot_ci_l10: Tuple[float, float]   # ΔMaxDD 90% CI, 10d blocks (descriptive)


# ----------------------------------------------------------------------
# Mechanical episode derivation (registration §1; addendum v2 §1)
#
# T-143 FINDING (reported, not patched): the locked prose rule
# "S&P 500 TR peak-to-trough DD ≥ 15%" is UNDERSPECIFIED. Under the
# strict all-time-high reading, the 2011 episode does NOT exist on a TR
# basis — the market had not regained its 2007-10 TR peak until ~2012,
# so 2011's decline nests inside the unrecovered GFC spell. Only the
# local-peak ("zigzag") reading — peak = running max since the last
# trough confirmed by a ≥15% reversal — reproduces the locked set. Both
# readings are implemented; locked-set date-fixing uses "local_peak"
# (the registration's evident intent, since its own re-derivation lists
# 2011), and the divergence is escalated to the director pre-unblinding.
# ----------------------------------------------------------------------
def derive_episodes_mechanical(
    tr: pd.Series,
    dd_threshold: float = DD_THRESHOLD,
    extension_td: int = EXTENSION_TD,
    rule: str = "local_peak",
) -> List[Dict]:
    """Mechanically derive ≥threshold peak-to-trough drawdown episodes.

    rule="alltime_high": a spell runs from the last all-time high until
        the series regains it; qualifies if min drawdown ≤ −threshold.
    rule="local_peak": alternating-swing (zigzag) segmentation — a peak
        confirms when the series falls ≥threshold from the running max;
        the trough confirms when it rallies ≥threshold from the running
        min. Each confirmed (peak, trough) pair is an episode.

    Returns dicts with peak/trough/end/max_dd — NO discretion. An
    in-progress ≥threshold drawdown at end-of-data is emitted open.
    """
    tr = tr.dropna().sort_index()
    if len(tr) < 2:
        return []
    if rule == "alltime_high":
        return _derive_alltime_high(tr, dd_threshold, extension_td)
    if rule == "local_peak":
        return _derive_local_peak(tr, dd_threshold, extension_td)
    raise ValueError(f"unknown rule '{rule}'")


def _derive_alltime_high(tr: pd.Series, dd_threshold: float, extension_td: int) -> List[Dict]:
    cummax = tr.cummax()
    dd = tr / cummax - 1.0
    at_high = tr >= cummax - 1e-12

    episodes: List[Dict] = []
    spell_peak_pos: Optional[int] = None
    for pos in range(len(tr)):
        if at_high.iloc[pos]:
            if spell_peak_pos is not None:
                spell = dd.iloc[spell_peak_pos:pos]
                if spell.min() <= -dd_threshold:
                    episodes.append(_emit(tr, spell, spell_peak_pos, extension_td))
                spell_peak_pos = None
            spell_peak_pos = pos  # a high starts (or restarts) a potential spell
    # Open spell at end of data (e.g. an in-progress drawdown)
    if spell_peak_pos is not None and spell_peak_pos < len(tr) - 1:
        spell = dd.iloc[spell_peak_pos:]
        if spell.min() <= -dd_threshold:
            episodes.append(_emit(tr, spell, spell_peak_pos, extension_td))
    return episodes


def _derive_local_peak(tr: pd.Series, dd_threshold: float, extension_td: int) -> List[Dict]:
    vals = tr.values
    episodes: List[Dict] = []
    phase_up = True
    run_max_pos = 0
    run_min_pos = 0
    pending_peak_pos: Optional[int] = None
    for pos in range(len(vals)):
        v = vals[pos]
        if phase_up:
            if v >= vals[run_max_pos]:
                run_max_pos = pos
            elif v <= vals[run_max_pos] * (1.0 - dd_threshold):
                pending_peak_pos = run_max_pos
                run_min_pos = pos
                phase_up = False
        else:
            if v <= vals[run_min_pos]:
                run_min_pos = pos
            elif v >= vals[run_min_pos] * (1.0 + dd_threshold):
                episodes.append(_emit_pair(tr, pending_peak_pos, run_min_pos, extension_td))
                run_max_pos = pos
                phase_up = True
                pending_peak_pos = None
    if not phase_up and pending_peak_pos is not None:
        # in-progress drawdown at end-of-data
        episodes.append(_emit_pair(tr, pending_peak_pos, run_min_pos, extension_td))
    return episodes


def _emit_pair(tr: pd.Series, peak_pos: int, trough_pos: int, extension_td: int) -> Dict:
    idx = tr.index
    end_pos = min(trough_pos + extension_td, len(idx) - 1)
    return {
        "peak": idx[peak_pos],
        "trough": idx[trough_pos],
        "end": idx[end_pos],
        "max_dd": float(tr.iloc[trough_pos] / tr.iloc[peak_pos] - 1.0),
    }


def _emit(tr: pd.Series, spell: pd.Series, peak_pos: int, extension_td: int) -> Dict:
    idx = tr.index
    trough_ts = spell.idxmin()
    trough_pos = idx.get_loc(trough_ts)
    end_pos = min(trough_pos + extension_td, len(idx) - 1)
    return {
        "peak": idx[peak_pos],
        "trough": trough_ts,
        "end": idx[end_pos],
        "max_dd": float(spell.min()),
    }


def pin_locked_episodes(tr: pd.Series) -> Tuple[List[Episode], List[str]]:
    """Pin the LOCKED episode set's exact trading dates from the TR
    series — registration §1: "Exact peak/trough trading dates are fixed
    mechanically from the S&P 500 TR series at analysis time (no
    discretion); the episode SET above is locked."

    Mechanical day-fixing given the locked months: peak = date of the TR
    maximum within the locked peak month; trough = date of the TR
    minimum within the locked trough month; end = trough + 20 trading
    days. This is rule-ambiguity-free (see check_mechanical_derivation
    for why the derivation RULE cannot pin the set — a reported T-143
    finding). Locked episodes without data coverage are returned in the
    second element (e.g. dotcom on a series starting 2005).
    """
    tr = tr.dropna().sort_index()
    episodes: List[Episode] = []
    uncoverable: List[str] = []
    for spec in LOCKED_EPISODES:
        peak_month = tr.loc[tr.index.strftime("%Y-%m") == spec["peak_month"]]
        trough_month = tr.loc[tr.index.strftime("%Y-%m") == spec["trough_month"]]
        if peak_month.empty or trough_month.empty:
            uncoverable.append(spec["id"])
            continue
        peak_ts = peak_month.idxmax()
        trough_ts = trough_month.idxmin()
        trough_pos = tr.index.get_loc(trough_ts)
        end_pos = min(trough_pos + EXTENSION_TD, len(tr.index) - 1)
        episodes.append(Episode(
            episode_id=spec["id"], label=spec["label"],
            peak=peak_ts, trough=trough_ts, end=tr.index[end_pos],
            actionable=spec["actionable"], oos=spec["oos"],
            blind=spec["blind"],
            max_dd=float(tr.loc[trough_ts] / tr.loc[peak_ts] - 1.0),
        ))
    return episodes, uncoverable


def check_mechanical_derivation(tr: pd.Series, rule: str = "alltime_high") -> Dict:
    """The honest-derivation check the T-143 brief requires: does the
    locked mechanical rule actually reproduce the locked episode SET on
    real TR data? Returns matched/missing/extra — divergence is a
    FINDING about the registration, reported, never patched.
    """
    derived = derive_episodes_mechanical(tr, rule=rule)
    matched: List[str] = []
    extras: List[Dict] = []
    remaining = {s["id"]: s for s in LOCKED_EPISODES}
    for d in derived:
        hit = next(
            (sid for sid, s in remaining.items()
             if str(d["peak"])[:7] == s["peak_month"]),
            None,
        )
        if hit is not None:
            matched.append(hit)
            del remaining[hit]
        else:
            extras.append(d)
    return {
        "rule": rule,
        "matched": matched,
        "missing": sorted(remaining.keys()),
        "extras": extras,
    }


# ----------------------------------------------------------------------
# Metric helpers
# ----------------------------------------------------------------------
def _window(df: pd.DataFrame, ep: Episode) -> pd.DataFrame:
    return df.loc[(df.index >= ep.peak) & (df.index <= ep.end)]


def _max_drawdown(equity: pd.Series) -> float:
    """Max drawdown within a window, relative to the running max that
    starts at the window's first bar (peak-to-trough inside the window)."""
    if len(equity) < 2:
        return 0.0
    dd = equity / equity.cummax() - 1.0
    return float(dd.min())


def _total_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1.0)


def _realized_vol(returns: pd.Series) -> float:
    if len(returns) < 2:
        return 0.0
    sd = returns.std()
    if sd is None or not np.isfinite(sd) or sd < 1e-12:
        return 0.0
    return float(sd * np.sqrt(TRADING_DAYS))


def _annualized_from_daily(returns: pd.Series) -> float:
    """CAGR from a set of daily returns (calm-day aggregation)."""
    n = len(returns)
    if n == 0:
        return 0.0
    growth = float(np.prod(1.0 + returns.values))
    if growth <= 0:
        return -1.0
    return growth ** (TRADING_DAYS / n) - 1.0


def _days_to_degross(
    on_w: pd.DataFrame, off_w: pd.DataFrame, ratio_trigger: float = 0.75
) -> Optional[int]:
    """Mechanism check (NON-GATING): trading days from the episode peak
    until gross_notional(on)/gross_notional(off) first drops below
    `ratio_trigger` (halfway to the 0.5× primary de-gross level). The
    registration measures from the regime-transition signal; the
    artifact schema carries no signal column, so window-start is the
    documented approximation — commentary only, never the gate."""
    if "gross_notional" not in on_w.columns or "gross_notional" not in off_w.columns:
        return None
    joined = pd.DataFrame({
        "on": on_w["gross_notional"], "off": off_w["gross_notional"]
    }).dropna()
    if joined.empty:
        return None
    off_safe = joined["off"].where(joined["off"].abs() > 1e-9)
    ratio = (joined["on"] / off_safe).dropna()
    hit = ratio[ratio < ratio_trigger]
    if hit.empty:
        return None
    return int(joined.index.get_loc(hit.index[0]))


def _circular_block_bootstrap_dmaxdd(
    on_rets: pd.Series, off_rets: pd.Series, block: int,
    n_iter: int = 1000, seed: int = 0,
) -> Tuple[float, float]:
    """Within-episode 90% CI on ΔMaxDD via circular block bootstrap of
    PAIRED daily returns (blocks never cross the episode boundary —
    registration §3). Descriptive only."""
    pair = pd.DataFrame({"on": on_rets, "off": off_rets}).dropna()
    n = len(pair)
    if n < block + 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    arr_on = pair["on"].values
    arr_off = pair["off"].values
    stats = np.empty(n_iter)
    n_blocks = int(np.ceil(n / block))
    for i in range(n_iter):
        starts = rng.integers(0, n, size=n_blocks)
        pos = (starts[:, None] + np.arange(block)[None, :]).ravel() % n
        pos = pos[:n]
        eq_on = np.cumprod(1.0 + arr_on[pos])
        eq_off = np.cumprod(1.0 + arr_off[pos])
        dd_on = float((eq_on / np.maximum.accumulate(eq_on) - 1.0).min())
        dd_off = float((eq_off / np.maximum.accumulate(eq_off) - 1.0).min())
        stats[i] = (dd_on - dd_off) * 100.0
    return (float(np.percentile(stats, 5)), float(np.percentile(stats, 95)))


def _stationary_bootstrap_calm_diff_ci(
    on_rets: pd.Series, off_rets: pd.Series,
    mean_block: int = 10, n_iter: int = 1000, seed: int = 0,
) -> Tuple[float, float]:
    """90% CI on the annualized calm-day CAGR difference via stationary
    bootstrap (Politis-Romano, geometric block lengths, paired days)."""
    pair = pd.DataFrame({"on": on_rets, "off": off_rets}).dropna()
    n = len(pair)
    if n < mean_block + 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    p = 1.0 / float(mean_block)
    arr_on = pair["on"].values
    arr_off = pair["off"].values
    stats = np.empty(n_iter)
    for i in range(n_iter):
        pos = np.empty(n, dtype=np.int64)
        t = rng.integers(0, n)
        for j in range(n):
            if j > 0 and rng.random() >= p:
                t = (t + 1) % n
            else:
                t = rng.integers(0, n) if j > 0 else t
            pos[j] = t
        cagr_on = _annualized_from_daily(pd.Series(arr_on[pos]))
        cagr_off = _annualized_from_daily(pd.Series(arr_off[pos]))
        stats[i] = (cagr_on - cagr_off) * 1e4  # bps
    return (float(np.percentile(stats, 5)), float(np.percentile(stats, 95)))


def _bayesian_credible_interval(
    values: np.ndarray, level: float = 0.90
) -> Tuple[float, float]:
    """Descriptive 90% credible interval on the mean per-episode ΔMaxDD.
    Conjugate Normal–Inverse-Gamma with weakly-informative prior
    (μ0=0, κ0=1, α0=1, β0=1) → Student-t posterior for μ. Reported
    descriptively per registration §3; never gates."""
    from scipy import stats as sps

    x = np.asarray(values, dtype=float)
    n = len(x)
    if n == 0:
        return (float("nan"), float("nan"))
    mu0, k0, a0, b0 = 0.0, 1.0, 1.0, 1.0
    xbar = x.mean()
    ssd = float(((x - xbar) ** 2).sum())
    kn = k0 + n
    mun = (k0 * mu0 + n * xbar) / kn
    an = a0 + n / 2.0
    bn = b0 + 0.5 * ssd + (k0 * n * (xbar - mu0) ** 2) / (2.0 * kn)
    scale = np.sqrt(bn / (an * kn))
    t = sps.t(df=2 * an, loc=mun, scale=scale)
    lo = (1.0 - level) / 2.0
    return (float(t.ppf(lo)), float(t.ppf(1.0 - lo)))


# ----------------------------------------------------------------------
# Evaluation (the locked gate)
# ----------------------------------------------------------------------
@dataclass
class Criterion:
    key: str
    description: str
    value: object
    threshold: str
    passed: bool
    gating: bool = True


@dataclass
class CrisisReplayResult:
    config_label: str
    is_primary_config: bool
    episode_results: List[EpisodeResult]
    criteria: List[Criterion]
    verdict: str                    # PASS | PARTIAL | FAIL | SENSITIVITY
    splits: Dict[str, Dict[str, float]]
    calm: Dict[str, float]
    bayes_cri_90: Tuple[float, float]
    sign_test_p: float
    notes: List[str] = field(default_factory=list)

    def verdict_line(self) -> str:
        parts = [
            f"{c.key}={c.value if not isinstance(c.value, float) else round(c.value, 3)}"
            f"({'PASS' if c.passed else 'fail'})"
            for c in self.criteria if c.gating
        ]
        return f"T-118b crisis-replay [{self.config_label}] VERDICT: " \
               f"{self.verdict} | " + " | ".join(parts)


def evaluate_crisis_replay(
    on: pd.DataFrame,
    off: pd.DataFrame,
    episodes: List[Episode],
    config_label: str = "primary",
    is_primary_config: bool = True,
    seed: int = 0,
) -> CrisisReplayResult:
    """Run the locked T-118b evaluation on one config's artifact pair.

    `on`/`off`: per-bar frames indexed by trading date with columns
    ``equity`` (+ optional ``gross_notional``). Identical base, same
    cells (registration §2). Returns derive from equity.
    """
    on = on.sort_index()
    off = off.sort_index()
    notes: List[str] = []

    on_ret = on["equity"].pct_change().dropna()
    off_ret = off["equity"].pct_change().dropna()

    # ---- per-episode metrics (§2) ------------------------------------
    ep_results: List[EpisodeResult] = []
    for ep in episodes:
        on_w, off_w = _window(on, ep), _window(off, ep)
        if len(on_w) < 2 or len(off_w) < 2:
            notes.append(f"episode {ep.episode_id}: no artifact coverage — skipped")
            continue
        dd_on, dd_off = _max_drawdown(on_w["equity"]), _max_drawdown(off_w["equity"])
        r_on, r_off = _total_return(on_w["equity"]), _total_return(off_w["equity"])
        on_wr = on_w["equity"].pct_change().dropna()
        off_wr = off_w["equity"].pct_change().dropna()
        ep_results.append(EpisodeResult(
            episode_id=ep.episode_id, label=ep.label,
            actionable=ep.actionable, oos=ep.oos, blind=ep.blind,
            d_maxdd_pp=(dd_on - dd_off) * 100.0,
            d_total_return_pp=(r_on - r_off) * 100.0,
            d_realized_vol_pp=(_realized_vol(on_wr) - _realized_vol(off_wr)) * 100.0,
            days_to_degross=_days_to_degross(on_w, off_w),
            boot_ci_l5=_circular_block_bootstrap_dmaxdd(on_wr, off_wr, 5, seed=seed),
            boot_ci_l10=_circular_block_bootstrap_dmaxdd(on_wr, off_wr, 10, seed=seed),
        ))

    actionable = [r for r in ep_results if r.actionable]
    dmaxdd = np.array([r.d_maxdd_pp for r in actionable])

    # ---- splits (addendum v2 §2: always reported) ----------------------
    ins = [r.d_maxdd_pp for r in actionable if not r.oos]
    oos = [r.d_maxdd_pp for r in actionable if r.oos]
    splits = {
        "in_sample": {"n": len(ins), "median_d_maxdd_pp": float(np.median(ins)) if ins else float("nan")},
        "oos": {"n": len(oos), "median_d_maxdd_pp": float(np.median(oos)) if oos else float("nan")},
    }

    # ---- calm-drag (§4) -----------------------------------------------
    in_episode = pd.Series(False, index=on.index)
    for ep in episodes:  # ALL reported episodes excluded from calm —
        # the union (incl. blind/appended) is the less-favorable choice:
        # crisis residue may not contaminate the calm-drag estimate.
        in_episode.loc[(on.index >= ep.peak) & (on.index <= ep.end)] = True
    calm_idx = in_episode[~in_episode].index
    calm_on = on_ret.reindex(calm_idx).dropna()
    calm_off = off_ret.reindex(calm_idx).dropna()
    calm_diff_bps = (
        _annualized_from_daily(calm_on) - _annualized_from_daily(calm_off)
    ) * 1e4
    calm_ci = _stationary_bootstrap_calm_diff_ci(calm_on, calm_off, seed=seed)
    calm = {
        "n_calm_days": int(len(calm_idx)),
        "cagr_diff_bps": float(calm_diff_bps),
        "ci90_low_bps": calm_ci[0],
        "ci90_high_bps": calm_ci[1],
    }

    # ---- aggregate criteria --------------------------------------------
    median_dmaxdd = float(np.median(dmaxdd)) if len(dmaxdd) else float("nan")
    n_success = int((dmaxdd > SIGN_SUCCESS_PP).sum()) if len(dmaxdd) else 0
    from scipy import stats as sps
    sign_p = float(sps.binomtest(n_success, len(dmaxdd), 0.5,
                                 alternative="greater").pvalue) if len(dmaxdd) else float("nan")

    # (iv) single-episode dependence — operationalized per §6
    # less-favorable rule: if the NET aggregate benefit is ≤ 0 the
    # criterion FAILS outright (there is no benefit to distribute);
    # otherwise share = largest single positive ΔMaxDD over the NET sum
    # (the smaller net denominator is harsher than positives-only).
    net_benefit = float(dmaxdd.sum()) if len(dmaxdd) else 0.0
    if net_benefit <= 0.0:
        single_share = float("inf")
    else:
        single_share = float(dmaxdd.max() / net_benefit) if dmaxdd.max() > 0 else 0.0

    # (v2-a) OOS both improve
    oos_results = [r for r in actionable if r.oos]
    oos_both = (len(oos_results) == 2
                and all(r.d_maxdd_pp > OOS_IMPROVE_PP for r in oos_results))

    # (v2-b) terminal wealth
    tw_on, tw_off = _total_return(on["equity"]), _total_return(off["equity"])

    # (v2-c) ratio — operationalized (documented; less-favorable when
    # ambiguous): annualized crisis benefit = Σ actionable-episode
    # Δtotal-return-pp ÷ full-window years (return units per the
    # addendum's "return-units benefit floor"); calm drag = max(0,
    # −calm CAGR diff). drag = 0 ⇒ criterion requires benefit ≥ 0.
    window_years = max((on.index[-1] - on.index[0]).days / 365.25, 1e-9)
    annualized_benefit_pp = float(
        sum(r.d_total_return_pp for r in actionable) / window_years
    )
    calm_drag_pp = max(0.0, -calm_diff_bps / 100.0)  # bps → pp
    ratio_pass = annualized_benefit_pp >= RATIO_REQUIRED * calm_drag_pp

    # (v2-d) GFC floor
    gfc = next((r for r in actionable if r.episode_id == "gfc"), None)
    gfc_dmaxdd = gfc.d_maxdd_pp if gfc else float("nan")

    bayes_cri = _bayesian_credible_interval(dmaxdd) if len(dmaxdd) else (float("nan"),) * 2

    criteria = [
        Criterion("median_dmaxdd_pp", "(i) median ΔMaxDD over 5 actionable",
                  median_dmaxdd, f">= +{MEDIAN_DMAXDD_PP}pp",
                  bool(len(dmaxdd)) and median_dmaxdd >= MEDIAN_DMAXDD_PP),
        Criterion("sign_test", f"(ii) episodes with ΔMaxDD > +{SIGN_SUCCESS_PP}pp",
                  f"{n_success}/{len(dmaxdd)}", f">= {SIGN_REQUIRED}/{SIGN_N}",
                  len(dmaxdd) == SIGN_N and n_success >= SIGN_REQUIRED),
        Criterion("calm_drag_bps", "(iii) calm-day CAGR(on)−CAGR(off)",
                  round(calm_diff_bps, 2), f">= {CALM_DRAG_FLOOR_BPS} bps",
                  calm_diff_bps >= CALM_DRAG_FLOOR_BPS),
        Criterion("calm_drag_ci90_low_bps", "(iii) stationary-bootstrap 90% CI low",
                  round(calm_ci[0], 2) if np.isfinite(calm_ci[0]) else calm_ci[0],
                  f"> {CALM_DRAG_CI_BOUND_BPS} bps (CI excludes)",
                  np.isfinite(calm_ci[0]) and calm_ci[0] > CALM_DRAG_CI_BOUND_BPS),
        Criterion("single_episode_share", "(iv) max single-episode share of net benefit",
                  round(single_share, 3) if np.isfinite(single_share) else "inf(net<=0)",
                  f"<= {SINGLE_EPISODE_MAX_SHARE}",
                  single_share <= SINGLE_EPISODE_MAX_SHARE),
        Criterion("oos_both_improve", "(v2-a) COVID and 2022 each > +0.5pp",
                  {r.episode_id: round(r.d_maxdd_pp, 2) for r in oos_results},
                  "both > +0.5pp", oos_both),
        Criterion("terminal_wealth", "(v2-b) full-window return on ≥ off",
                  f"on={tw_on:.4f} off={tw_off:.4f}", "on >= off",
                  tw_on >= tw_off),
        Criterion("benefit_drag_ratio", "(v2-c) annualized crisis benefit vs calm drag",
                  f"benefit={annualized_benefit_pp:.3f}pp/yr drag={calm_drag_pp:.3f}pp/yr",
                  f"benefit >= {RATIO_REQUIRED}x drag", ratio_pass),
        Criterion("gfc_floor_pp", "(v2-d) GFC ΔMaxDD",
                  round(gfc_dmaxdd, 2) if np.isfinite(gfc_dmaxdd) else gfc_dmaxdd,
                  f">= +{GFC_FLOOR_PP}pp",
                  np.isfinite(gfc_dmaxdd) and gfc_dmaxdd >= GFC_FLOOR_PP),
    ]

    if is_primary_config:
        all_pass = all(c.passed for c in criteria)
        # PARTIAL operationalization (documented; §6 less-favorable rule +
        # the T-143 brief's explicit adjudication that the v1-hole case
        # must FAIL): PARTIAL = (i) median and (iii) calm-drag hold AND
        # every v2 co-equal return-units criterion holds — i.e. only the
        # trigger-TUNABLE shape criteria (ii)/(iv) failed, which is what
        # "iterate trigger parameters" can address. A failed v2 criterion
        # (terminal wealth, ratio, OOS, GFC floor) is structural → FAIL.
        by_key = {c.key: c.passed for c in criteria}
        v2_ok = all(by_key[k] for k in (
            "oos_both_improve", "terminal_wealth",
            "benefit_drag_ratio", "gfc_floor_pp",
        ))
        calm_ok = by_key["calm_drag_bps"] and by_key["calm_drag_ci90_low_bps"]
        partial = by_key["median_dmaxdd_pp"] and calm_ok and v2_ok
        verdict = "PASS" if all_pass else ("PARTIAL" if partial else "FAIL")
    else:
        verdict = "SENSITIVITY"
        notes.append("non-primary config — metrics reported, gate NOT evaluated "
                     "(addendum v2 §4 multiplicity rule)")

    return CrisisReplayResult(
        config_label=config_label,
        is_primary_config=is_primary_config,
        episode_results=ep_results,
        criteria=criteria,
        verdict=verdict,
        splits=splits,
        calm=calm,
        bayes_cri_90=bayes_cri,
        sign_test_p=sign_p,
        notes=notes,
    )


def format_report(result: CrisisReplayResult) -> str:
    lines = [result.verdict_line(), ""]
    lines.append(f"{'episode':28} {'ΔMaxDD pp':>10} {'ΔTotRet pp':>11} "
                 f"{'ΔVol pp':>8} {'d2degross':>9} {'split':>9} "
                 f"{'boot90 L5':>18} {'boot90 L10':>18}")
    for r in result.episode_results:
        split = "BLIND" if r.blind else ("OOS" if r.oos else "in-sample")
        d2g = "-" if r.days_to_degross is None else str(r.days_to_degross)
        ci5 = f"[{r.boot_ci_l5[0]:+.1f},{r.boot_ci_l5[1]:+.1f}]"
        ci10 = f"[{r.boot_ci_l10[0]:+.1f},{r.boot_ci_l10[1]:+.1f}]"
        lines.append(f"{r.label:28} {r.d_maxdd_pp:>+10.2f} "
                     f"{r.d_total_return_pp:>+11.2f} {r.d_realized_vol_pp:>+8.2f} "
                     f"{d2g:>9} {split:>9} {ci5:>18} {ci10:>18}")
    lines.append("")
    lines.append(f"splits: in-sample median ΔMaxDD "
                 f"{result.splits['in_sample']['median_d_maxdd_pp']:+.2f}pp (n={result.splits['in_sample']['n']}), "
                 f"OOS {result.splits['oos']['median_d_maxdd_pp']:+.2f}pp (n={result.splits['oos']['n']})")
    lines.append(f"calm: {result.calm['n_calm_days']} days, "
                 f"CAGR diff {result.calm['cagr_diff_bps']:+.1f} bps, "
                 f"90% CI [{result.calm['ci90_low_bps']:+.1f}, {result.calm['ci90_high_bps']:+.1f}] bps")
    lines.append(f"bayes 90% CrI on mean ΔMaxDD (descriptive): "
                 f"[{result.bayes_cri_90[0]:+.2f}, {result.bayes_cri_90[1]:+.2f}] pp; "
                 f"exact binomial sign-test p={result.sign_test_p:.4f} (descriptive)")
    lines.append("")
    lines.append(f"{'criterion':26} {'value':>34} {'threshold':>26} {'verdict':>8}")
    for c in result.criteria:
        lines.append(f"{c.key:26} {str(c.value):>34} {c.threshold:>26} "
                     f"{'PASS' if c.passed else 'FAIL':>8}")
    for n in result.notes:
        lines.append(f"note: {n}")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# CLI (the director's post-relaunch command — real artifacts)
# ----------------------------------------------------------------------
def _load_artifacts(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    date_col = "date" if "date" in df.columns else "timestamp"
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col).sort_index()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--on", required=True, help="overlay-ON artifacts CSV (date,equity[,gross_notional])")
    ap.add_argument("--off", required=True, help="overlay-OFF artifacts CSV")
    ap.add_argument("--spx", required=True, help="S&P 500 TR series CSV (date,close)")
    ap.add_argument("--config-label", default="0.5x_k5_h(0.4/0.3/10)")
    ap.add_argument("--primary-config", action="store_true",
                    help="evaluate the gate (addendum v2 §4: ONE designated config only)")
    args = ap.parse_args()

    spx = pd.read_csv(args.spx)
    date_col = "date" if "date" in spx.columns else spx.columns[0]
    close_col = "close" if "close" in spx.columns else spx.columns[-1]
    tr = pd.Series(
        pd.to_numeric(spx[close_col], errors="coerce").values,
        index=pd.to_datetime(spx[date_col]),
    ).dropna()

    episodes, uncoverable = pin_locked_episodes(tr)
    if uncoverable:
        print(f"!! locked episodes WITHOUT data coverage on this series: {uncoverable}")
    for rule in ("alltime_high", "local_peak"):
        chk = check_mechanical_derivation(tr, rule=rule)
        if chk["missing"] or chk["extras"]:
            print(f"!! HONEST-DERIVATION DIVERGENCE vs the LOCKED list "
                  f"(rule={rule}) — a finding, not patched:")
            for m in chk["missing"]:
                print(f"   locked episode NOT produced by this rule/series: {m}")
            for u in chk["extras"]:
                print(f"   mechanical episode NOT in locked list: "
                      f"peak {u['peak'].date()} trough {u['trough'].date()} dd {u['max_dd']:.1%}")
    print("   (gate evaluates the LOCKED set only, dates month-pinned per §1; "
          "extras reported, never gated)")

    result = evaluate_crisis_replay(
        _load_artifacts(args.on), _load_artifacts(args.off), episodes,
        config_label=args.config_label, is_primary_config=args.primary_config,
    )
    print(format_report(result))


if __name__ == "__main__":
    main()
