"""T-301b — the CONSUME-POLICY: measured operational rates → harness assumptions, bounded + frozen.

Implements the FROZEN rule of `docs/Audit/exec_refresh_consume_policy_t301b_2026_07_10.md` (director-frozen
2026-07-10). The machine's OWN measured execution costs + operational rates (from the T-301 ExecCostLedger
and the pulse order/gate/reconcile logs) update the harness's cost/operational assumptions — quarterly,
min-n-gated, shrunk toward the current assumption, hard-capped per refresh, and NEVER touching a decision
threshold, a strategy parameter, or the measurement apparatus. A refresh that would FLIP a standing deploy
decision HALTS to a human. Operational-cost learning, not alpha learning.

This is the concrete B/T-305 form of "the machine improves from what works": bounded, pre-registered, frozen,
OOS. `refresh_harness_assumptions` REPORTS a diff + writes a versioned, revertible history; it never mutates
in place, and it fails closed to the hardcoded defaults.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSUMPTIONS_PATH = ROOT / "config" / "harness_assumptions.json"
HISTORY_PATH = ROOT / "data" / "state" / "harness_assumptions_history.jsonl"

# ---- FROZEN constants (do not change without a new pre-registration) ----------------
K_SLIPPAGE = 50          # prior pseudo-observations for the continuous (slippage) shrinkage
K_RATE = 100             # prior pseudo-counts for the binomial (fill/gate/reconcile) shrinkage
N_MIN = {"slippage_bps": 30, "fill_rate": 60, "gate_pass_rate": 60,
         "defer_rate": 60, "reconcile_clean_rate": 60}
REL_CAP = 0.25           # ≤25% relative move per refresh (continuous metrics)
ABS_CAP_RATE = 0.10      # ≤0.10 absolute move per refresh (rate metrics)
RATE_METRICS = {"fill_rate", "gate_pass_rate", "defer_rate", "reconcile_clean_rate"}

# Standing DECISION-FLIP breakevens: if applying the refresh would move a metric across one of these, the
# update HALTS to a human (the number is recorded, the flip is never auto-applied). Named example: the
# T-294/298 offense-config breakeven — SSO-leg slippage 1.55 bps is where gated-2x = buy-hold SPY.
DECISION_FLIP_BREAKEVENS: List[Dict[str, Any]] = [
    {"metric": "slippage_bps", "instrument": "SSO", "breakeven": 1.55,
     "note": "T-294/298: SSO-leg slippage where the offense config crosses buy-hold SPY"},
]


def _default_assumptions() -> Dict[str, Any]:
    """Today's hardcoded harness defaults — the fail-closed seed. Generic per-instrument overrides live
    under 'instruments'; global operational-rate assumptions default optimistic (what the harness implies)."""
    return {
        "version": "seed-t301b",
        "global": {"fill_rate": 1.0, "gate_pass_rate": 1.0, "defer_rate": 0.0,
                   "reconcile_clean_rate": 1.0, "liquid_etf_slippage_bps": 1.5},
        # per (account, instrument) overrides accrue here as refreshes apply:
        "instruments": {},
    }


def load_assumptions(path: pathlib.Path = ASSUMPTIONS_PATH) -> Dict[str, Any]:
    """Fail-closed read: a missing/empty/unparseable file → the hardcoded defaults (never a fabricated one)."""
    try:
        d = json.loads(pathlib.Path(path).read_text())
        if isinstance(d, dict) and d.get("global"):
            return d
    except Exception:
        pass
    return _default_assumptions()


# ---- the frozen shrinkage forms ------------------------------------------------------
def shrink_continuous(measured: float, current: float, n: int, k: int = K_SLIPPAGE) -> float:
    """Normal-normal shrinkage toward the current assumption: (n·measured + k·current)/(n+k)."""
    return (n * measured + k * current) / (n + k) if (n + k) > 0 else current


def shrink_rate(successes: int, n: int, p0: float, k: int = K_RATE) -> float:
    """Beta-binomial posterior mean toward the current rate p0: (k·p0 + successes)/(k+n)."""
    return (k * p0 + successes) / (k + n) if (k + n) > 0 else p0


def apply_cap(current: float, proposed: float, is_rate: bool) -> Tuple[float, bool]:
    """Clamp the per-refresh move. Returns (capped_value, was_capped)."""
    if is_rate:
        lo, hi = current - ABS_CAP_RATE, current + ABS_CAP_RATE
    else:
        lo, hi = current * (1 - REL_CAP), current * (1 + REL_CAP)
        lo, hi = min(lo, hi), max(lo, hi)          # current could be 0
    capped = min(hi, max(lo, proposed))
    return capped, (abs(capped - proposed) > 1e-12)


def _crosses_breakeven(metric: str, instrument: Optional[str], current: float, proposed: float) -> Optional[dict]:
    """Return the breakeven spec if applying `proposed` would move the metric across it (a decision flip)."""
    for b in DECISION_FLIP_BREAKEVENS:
        if b["metric"] != metric:
            continue
        if b.get("instrument") and instrument and b["instrument"] != instrument:
            continue
        be = b["breakeven"]
        if (current - be) * (proposed - be) < 0:   # opposite sides ⇒ a flip
            return b
    return None


@dataclass
class RefreshEntry:
    account: Optional[str]
    instrument: Optional[str]
    metric: str
    old: float
    measured: float
    n: int
    proposed: float
    new: float
    applied: bool
    reason: str = ""            # "" | "below_n_min" | "capped" | "tripwire_halt:<breakeven>"
    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("account", "instrument", "metric", "old", "measured",
                                              "n", "proposed", "new", "applied", "reason")}


@dataclass
class RefreshResult:
    quarter: str
    entries: List[RefreshEntry] = field(default_factory=list)
    new_assumptions: Dict[str, Any] = field(default_factory=dict)
    halts: List[dict] = field(default_factory=list)     # decision-flip escalations for the human


def refresh_harness_assumptions(quarter: str, *, slippage_agg: Dict[Tuple[str, str], Dict[str, float]],
                                rate_counts: Dict[Tuple[str, str, str], Tuple[int, int]],
                                current: Optional[Dict[str, Any]] = None) -> RefreshResult:
    """One quarterly refresh (report + versioned diff; NEVER auto-applies a decision-flip).

    slippage_agg: {(account, instrument): {"n": int, "median_slippage_bps": float}} (from ExecCostLedger.aggregate).
    rate_counts:  {(account, instrument, metric): (successes, n)} for the rate metrics.
    Returns the diff + the new assumptions (in memory); the caller writes them via `write_refresh`.
    """
    cur = json.loads(json.dumps(current or load_assumptions()))   # deep copy
    inst = cur.setdefault("instruments", {})
    res = RefreshResult(quarter=quarter, new_assumptions=cur)

    def _cur_slip(acct: str, ins: str) -> float:
        return inst.get(f"{acct}:{ins}", {}).get("slippage_bps",
                                                 cur["global"].get("liquid_etf_slippage_bps", 1.5))

    # --- slippage (continuous) ---
    for (acct, ins), agg in sorted(slippage_agg.items()):
        n = int(agg.get("n", 0)); measured = float(agg.get("median_slippage_bps", 0.0))
        old = _cur_slip(acct, ins)
        if n < N_MIN["slippage_bps"]:
            res.entries.append(RefreshEntry(acct, ins, "slippage_bps", old, measured, n, old, old, False, "below_n_min"))
            continue
        proposed_raw = shrink_continuous(measured, old, n)
        proposed, capped = apply_cap(old, proposed_raw, is_rate=False)
        flip = _crosses_breakeven("slippage_bps", ins, old, proposed)
        if flip:
            res.halts.append({"account": acct, "instrument": ins, "metric": "slippage_bps",
                              "old": old, "proposed": proposed, "breakeven": flip["breakeven"], "note": flip["note"]})
            res.entries.append(RefreshEntry(acct, ins, "slippage_bps", old, measured, n, proposed, old, False,
                                            f"tripwire_halt:be={flip['breakeven']}"))
            continue                                   # HALT: recorded, NOT applied
        inst.setdefault(f"{acct}:{ins}", {})["slippage_bps"] = proposed
        res.entries.append(RefreshEntry(acct, ins, "slippage_bps", old, measured, n, proposed_raw, proposed, True,
                                        "capped" if capped else ""))

    # --- rates (binomial) ---
    for (acct, ins, metric), (succ, n) in sorted(rate_counts.items()):
        if metric not in RATE_METRICS:
            continue
        key = f"{acct}:{ins}"
        old = inst.get(key, {}).get(metric, cur["global"].get(metric, 1.0))
        if n < N_MIN.get(metric, 60):
            res.entries.append(RefreshEntry(acct, ins, metric, old, (succ / n if n else old), n, old, old, False, "below_n_min"))
            continue
        proposed_raw = shrink_rate(succ, n, old)
        proposed, capped = apply_cap(old, proposed_raw, is_rate=True)
        proposed = min(1.0, max(0.0, proposed))
        inst.setdefault(key, {})[metric] = proposed
        res.entries.append(RefreshEntry(acct, ins, metric, old, succ / n if n else old, n, proposed_raw, proposed, True,
                                        "capped" if capped else ""))
    cur["version"] = f"refresh-{quarter}"
    return res


def write_refresh(res: RefreshResult, *, config_path: pathlib.Path = ASSUMPTIONS_PATH,
                  history_path: pathlib.Path = HISTORY_PATH, now_iso: str = "1970-01-01T00:00:00") -> None:
    """Versioned, append-only, revertible write: the diff to history, then the new current config."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a") as fh:
        for e in res.entries:
            fh.write(json.dumps({"ts": now_iso, "quarter": res.quarter, **e.to_dict()}) + "\n")
        for h in res.halts:
            fh.write(json.dumps({"ts": now_iso, "quarter": res.quarter, "TRIPWIRE_HALT": True, **h}) + "\n")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(res.new_assumptions, indent=2, sort_keys=True))
