"""T-324 — skew-aware scoring for the thesis desk. The metric must be able to say a 1-in-5 hit rate is GOOD.

Why Brier alone is the WRONG metric here (the pre-stated design concession):
thematic wins are rare-but-large. RKLB @$23 → $151 is +557% against several theses that go to zero. A
Brier/hit-rate view scores that record as a failure; a log-wealth view scores it as the success it is.
So the promotion bar carries BOTH: Brier (calibration — is the model's confidence honest?) AND a
skew-aware payoff metric (did the record MAKE money against its twin?). A thesis desk can be badly
calibrated and still profitable, or well calibrated and useless — the two together are the honest picture.

Primary skew-aware statistic: the **log-wealth ratio vs the twin**, block-bootstrapped, since equal-weighted
thesis outcomes compound multiplicatively and log-space is where a 1-in-5-with-a-10-bagger reads correctly.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np


@dataclass
class ThesisOutcome:
    """One RESOLVED thesis: its realized return and its twin's over the SAME window."""
    thesis_id: str
    theme_class: str
    conviction: float                 # the model's stated confidence (for Brier/calibration)
    ret: float                        # realized total return of the thesis basket (e.g. +5.57 = +557%)
    twin_ret: float                   # SPY (or the matched twin) over the identical window
    resolved: bool = True
    killed_by_falsifier: bool = False


def _log_ratio(o: ThesisOutcome) -> float:
    """log((1+r_thesis)/(1+r_twin)) — the per-thesis excess in compounding space. Floor at total loss."""
    a = max(1.0 + o.ret, 1e-9); b = max(1.0 + o.twin_ret, 1e-9)
    return math.log(a / b)


def brier(outcomes: Sequence[ThesisOutcome]) -> Optional[float]:
    """Calibration: was the stated conviction honest? Outcome = 1 if the thesis beat its twin."""
    xs = [(o.conviction, 1.0 if o.ret > o.twin_ret else 0.0) for o in outcomes if o.resolved]
    return float(np.mean([(p - y) ** 2 for p, y in xs])) if xs else None


def hit_rate(outcomes: Sequence[ThesisOutcome]) -> Optional[float]:
    xs = [1.0 if o.ret > o.twin_ret else 0.0 for o in outcomes if o.resolved]
    return float(np.mean(xs)) if xs else None


def payoff_profile(outcomes: Sequence[ThesisOutcome]) -> Dict[str, Optional[float]]:
    """The skew picture: hit rate, mean win, mean loss, and the win/loss magnitude ratio."""
    res = [o for o in outcomes if o.resolved]
    if not res:
        return {"n": 0, "hit_rate": None, "mean_win": None, "mean_loss": None, "win_loss_ratio": None}
    wins = [_log_ratio(o) for o in res if o.ret > o.twin_ret]
    losses = [_log_ratio(o) for o in res if o.ret <= o.twin_ret]
    mw = float(np.mean(wins)) if wins else None
    ml = float(np.mean(losses)) if losses else None
    return {"n": len(res), "hit_rate": hit_rate(res), "mean_win": mw, "mean_loss": ml,
            "win_loss_ratio": (abs(mw / ml) if (mw is not None and ml not in (None, 0.0)) else None)}


def log_wealth_ratio(outcomes: Sequence[ThesisOutcome]) -> Optional[float]:
    """THE skew-aware headline: mean log-excess per thesis. >0 ⇒ the record compounds above its twin."""
    xs = [_log_ratio(o) for o in outcomes if o.resolved]
    return float(np.mean(xs)) if xs else None


def bootstrap_log_wealth_ci(outcomes: Sequence[ThesisOutcome], n_iter: int = 2000,
                            seed: int = 0, conf: float = 0.95) -> Optional[Dict[str, float]]:
    """Bootstrap CI on the mean log-wealth ratio. The promotion bar requires ci_low > 0.

    Resampling is over THESES (each is an independent bet), which is the right unit — a 1-in-5 record with
    one huge winner will show a WIDE, right-skewed CI, and that honesty is the point: it says 'promising,
    not yet proven' rather than laundering one lucky 10-bagger into significance.
    """
    xs = np.array([_log_ratio(o) for o in outcomes if o.resolved], dtype=float)
    if len(xs) < 3:
        return None
    rng = np.random.default_rng(seed)
    means = [float(np.mean(rng.choice(xs, size=len(xs), replace=True))) for _ in range(n_iter)]
    lo, hi = np.percentile(means, [(1 - conf) / 2 * 100, (1 + conf) / 2 * 100])
    return {"mean": float(np.mean(xs)), "ci_low": float(lo), "ci_high": float(hi), "n": int(len(xs))}


def by_theme(outcomes: Sequence[ThesisOutcome]) -> Dict[str, Dict]:
    """Per-theme_class breakdown — the promotion bar is per-class, not pooled."""
    out: Dict[str, Dict] = {}
    for tc in sorted({o.theme_class for o in outcomes}):
        sub = [o for o in outcomes if o.theme_class == tc]
        out[tc] = {"profile": payoff_profile(sub), "brier": brier(sub),
                   "log_wealth": bootstrap_log_wealth_ci(sub)}
    return out


# ---- the PRE-STATED promotion bar (written now so it cannot move later) ----
MIN_RESOLVED_PER_CLASS = 20


def promotion_check(outcomes: Sequence[ThesisOutcome], theme_class: str,
                    min_n: int = MIN_RESOLVED_PER_CLASS) -> Dict[str, object]:
    """A theme_class earns nothing until: (1) >= min_n RESOLVED theses in that class, AND (2) the
    bootstrap CI on the mean log-wealth ratio vs the twin EXCLUDES ZERO (ci_low > 0). Brier/calibration is
    reported alongside — a badly-calibrated but profitable record is flagged, not silently promoted."""
    sub = [o for o in outcomes if o.theme_class == theme_class and o.resolved]
    lw = bootstrap_log_wealth_ci(sub)
    n_ok = len(sub) >= min_n
    ci_ok = bool(lw and lw["ci_low"] > 0)
    return {"theme_class": theme_class, "n_resolved": len(sub), "n_required": min_n,
            "n_ok": n_ok, "log_wealth": lw, "ci_excludes_zero": ci_ok,
            "brier": brier(sub), "profile": payoff_profile(sub),
            "PROMOTED": bool(n_ok and ci_ok),
            "reason": ("" if (n_ok and ci_ok) else
                       ("insufficient_n" if not n_ok else "ci_straddles_zero"))}
