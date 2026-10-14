"""core/measurement/mbl_gate.py
==============================
T-083: MBL Gate-0 — Minimum Backtest Length check.
RR-3 (2026-09-30, PROPOSAL): fail-closed honest-N, exact E[max], correlation-aware N_eff.

Per CLAUDE.md non-negotiable `[NN-MBL]` and Bailey-Borwein-López de Prado-Zhu (Notices
AMS 2014), the Minimum Backtest Length is

    MinBTL = E[max_N]^2 / SR_target^2

where E[max_N] is the expected maximum of N independent standard normals. The familiar
`2 * ln(N) / SR^2` is the UPPER BOUND that paper quotes for intuition (E[max_N] <=
sqrt(2 ln N)); used as the gate itself it overstates required years by ~39% at N=260
(`scripts/probe_mbl_n_effective.py`). The exact form is the default; the bound stays
behind `upper_bound=True` for comparison only.

THE THREE DEFECTS RR-3 REPAIRS (each verified on main before changing it):
  1. FAIL-OPEN N. `compute_n_effective` returned 1 when the registry was absent, and 1
     gives MinBTL = 0, so Gate 0 PASSED. The registry is `.dockerignore`d and never
     pulled from S3, so this was not a latent risk: every cloud Discovery cell ran Gate 0
     at N=1. An EMPTY registry did the same via `max(1, 0)`. Both now raise
     `HonestNUnavailableError`. **A trial count that cannot be established is never a
     licence to proceed at N=1.**
  2. THE UPPER BOUND USED AS THE GATE. Now exact E[max]^2 (Euler-γ approximation, the
     same constant `MetricsEngine.deflated_sharpe_ratio` uses — one definition).
  3. EVERY RUN COUNTED AS AN INDEPENDENT TRIAL. `compute_n_effective_correlated` adjusts
     the count for the measured correlation between trials, read from the empirical
     artifact `data/observability/n_effective_<date>.json` (`scripts/rr3_empirical_rho.py`).
     It fails closed if the artifact is missing — the adjustment is never assumed.

A correlation estimate is NEVER allowed to collapse the multiple-testing correction to
none: N_eff is floored at `N_EFF_FLOOR` (2). With N_eff = 1 the gate is vacuous (MinBTL
= 0) — the same door defect 1 left open, reached by a different route.

Public API
----------
- `compute_n_effective(db_path)`                  raw registry count; FAILS CLOSED
- `compute_n_effective_correlated(db_path, ...)`  correlation-aware N_eff; FAILS CLOSED
- `expected_max_normal(n)`                        E[max of n iid N(0,1)] (Euler-γ)
- `n_eff_equicorrelated(n, rho_bar)`              the equicorrelated-trials identity
- `compute_mbl_min(n_effective, sr_target)`       exact MinBTL (or the bound, on request)
- `check_mbl_gate(t_years, n_effective=None, ...)` the full Gate-0 check
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, Optional

from scipy import stats as _stats

from core.metrics_engine import _EULER_GAMMA

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data/observability/run_registry.sqlite"
DEFAULT_ARTIFACT_DIR = DEFAULT_DB_PATH.parent
# RR-3 §9.3 (2026-10-13): BOTH honest-N inputs — the ρ̄ artifact and the run registry — are
# PINNED by one committed pointer carrying each file's sha256.
DEFAULT_PIN_PATH = Path(__file__).resolve().parents[2] / "config/honest_n_pin.json"

# A correlation estimate may shrink N, never erase the correction (see module docstring).
N_EFF_FLOOR = 2.0

METHODS = ("conservative", "onc", "equicorr")


class HonestNUnavailableError(FileNotFoundError):
    """The honest trial count cannot be established (registry or ρ̄ artifact absent,
    empty, or unreadable). A HARNESS failure, never a candidate failure: callers must
    let it propagate rather than convert it into a per-candidate verdict, or a missing
    registry reads as "nothing passed" — a plausible, wrong number (`[NN-FAIL-CLOSED]`)."""


# ----------------------------------------------------------------------------- math
def expected_max_normal(n: float) -> float:
    """E[max of n iid standard normals], Bailey-López de Prado (2014) approximation:

        E[max_n] ≈ (1 - γ)·Φ⁻¹(1 - 1/n) + γ·Φ⁻¹(1 - 1/(n·e))

    The identical expression `MetricsEngine.deflated_sharpe_ratio` inlines, with the same
    γ, so Gate 0 and Gate 8 cannot drift apart. Within ~1.3% of exact numerical
    integration at n=260 (the probe reports both). n <= 1 → 0.0 (no selection)."""
    if n <= 1:
        return 0.0
    a = float(_stats.norm.ppf(1.0 - 1.0 / n))
    b = float(_stats.norm.ppf(1.0 - 1.0 / (n * math.e)))
    return (1.0 - _EULER_GAMMA) * a + _EULER_GAMMA * b


def n_eff_equicorrelated(n: float, rho_bar: float) -> float:
    """The equicorrelated-trials identity. If N trials have pairwise correlation ρ̄,

        X_i = sqrt(ρ̄)·Z₀ + sqrt(1-ρ̄)·Z_i   ⇒   E[max_i X_i] = sqrt(1-ρ̄)·E[max_N]

    so the selection benchmark shrinks by sqrt(1-ρ̄). Returns the N_eff of INDEPENDENT
    trials with that same expected maximum (solved by bisection), floored at N_EFF_FLOOR.
    ρ̄ <= 0 returns n unchanged: negative average correlation does not license more
    trials than were run."""
    if n <= N_EFF_FLOOR:
        return float(max(n, 1.0))
    if not (rho_bar == rho_bar) or rho_bar <= 0.0:
        return float(n)
    if rho_bar >= 1.0:
        return N_EFF_FLOOR
    target = math.sqrt(1.0 - rho_bar) * expected_max_normal(n)
    lo, hi = N_EFF_FLOOR, float(n)
    if expected_max_normal(lo) >= target:
        return N_EFF_FLOOR
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if expected_max_normal(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)


def compute_mbl_min(n_effective: float, sr_target: float = 1.0, *, upper_bound: bool = False) -> float:
    """Minimum Backtest Length in years.

    Exact (default):  E[max_N]^2 / SR_target^2
    Upper bound:      2·ln(N) / SR_target^2   (`upper_bound=True`; comparison only)

    At N=1 there is no selection, so MinBTL = 0 in both forms. That is correct maths and
    the reason N must never DEFAULT to 1 — see `compute_n_effective`.

    Raises ValueError if n_effective < 1 or sr_target <= 0."""
    if n_effective < 1:
        raise ValueError(f"n_effective must be >= 1, got {n_effective}")
    if sr_target <= 0:
        raise ValueError(f"sr_target must be > 0, got {sr_target}")
    if n_effective == 1:
        return 0.0
    if upper_bound:
        return 2.0 * math.log(n_effective) / (sr_target ** 2)
    return expected_max_normal(n_effective) ** 2 / (sr_target ** 2)


# ----------------------------------------------------------------------------- N sources
def compute_n_effective(
    db_path: Optional[Path] = None,
    since_iso: Optional[str] = None,
) -> int:
    """Raw honest-N: the run registry's row count. FAILS CLOSED.

    Raises `HonestNUnavailableError` when the registry is absent OR holds zero rows.
    Both used to return 1, and N=1 makes Gate 0 vacuous; since the registry is excluded
    from the Docker image, "absent" was the normal state of every cloud container.

    This is a RAW count — every row one trial, including determinism reps and near-
    identical A/B arms. Prefer `compute_n_effective_correlated` for gating."""
    db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    if not db_path.exists():
        raise HonestNUnavailableError(
            f"run registry absent at {db_path} — honest N cannot be established. "
            f"Pass an explicit trial count or supply the registry; never proceed at N=1.")
    import sqlite3
    # Read-only (RR-3 §9.3): the registry's bytes are pinned, so the gate must never be
    # able to change them — not even a journal side effect of a read-write connection.
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        try:
            if since_iso:
                cur = conn.execute("SELECT COUNT(*) FROM runs WHERE snapshot_at >= ?", (since_iso,))
            else:
                cur = conn.execute("SELECT COUNT(*) FROM runs")
        except sqlite3.DatabaseError as exc:          # e.g. a 0-byte file or no `runs` table
            raise HonestNUnavailableError(f"run registry at {db_path} unreadable: {exc}") from exc
        n = int(cur.fetchone()[0])
    finally:
        conn.close()
    if n < 1:
        raise HonestNUnavailableError(
            f"run registry at {db_path} holds 0 rows — an empty registry is not evidence of "
            f"zero prior trials.")
    return n


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pin(pin_path: Optional[Path] = None) -> Dict:
    """Read and validate the committed honest-N pin. FAILS CLOSED on absence or malformation."""
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    try:
        pin = json.loads(pin_path.read_text())
        for key in ("artifact", "registry"):
            entry = pin[key]
            if not (isinstance(entry, dict) and isinstance(entry["file"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", str(entry["sha256"]).lower())):
                raise ValueError(f"{key!r} needs a file name and a 64-hex sha256")
            if "/" in entry["file"] or "\\" in entry["file"]:
                raise HonestNUnavailableError(
                    f"honest-N pin {pin_path} names a path for {key!r}, not a file name: {entry['file']!r}")
    except HonestNUnavailableError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HonestNUnavailableError(
            f"honest-N pin {pin_path} absent or malformed ({exc}) — the gate will not guess which "
            f"inputs to trust") from exc
    return pin


def _verify_pinned(path: Path, entry: Dict, what: str, pin_path: Path) -> Path:
    if path.name != entry["file"]:
        raise HonestNUnavailableError(
            f"the gate was given {what} {path.name!r} but the pin names {entry['file']!r} ({pin_path})")
    if not path.exists():
        raise HonestNUnavailableError(f"pinned {what} {path} is absent (pin: {pin_path}). Ship it, or re-pin by commit.")
    got, want = sha256_file(path), str(entry["sha256"]).lower()
    if got != want:
        raise HonestNUnavailableError(
            f"pinned {what} {path} does not match its pin: sha256 {got[:12]}… ≠ pinned {want[:12]}…. "
            f"It changed after it was pinned; re-pin by commit, after review.")
    return path


def pinned_n_effective_artifact(
    pin_path: Optional[Path] = None,
    artifact_dir: Optional[Path] = None,
) -> Path:
    """The ρ̄ artifact the gate is PINNED to, hash-verified. FAILS CLOSED.

    RR-3 §9.3. This replaced `latest_n_effective_artifact()`, which took the NEWEST
    `n_effective_*.json` by filename — so any re-run of `scripts/rr3_empirical_rho.py`, by anyone,
    silently replaced the live gate's input with no review. The 2026-10-13 Option B pass avoided
    that only by choosing a different output name; a filename convention is not a control."""
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    artifact_dir = Path(artifact_dir) if artifact_dir is not None else DEFAULT_ARTIFACT_DIR
    entry = load_pin(pin_path)["artifact"]
    return _verify_pinned(artifact_dir / entry["file"], entry, "n_effective artifact", pin_path)


def verify_pinned_registry(db_path: Optional[Path] = None, pin_path: Optional[Path] = None) -> Path:
    """The run registry the gate is PINNED to, hash-verified. FAILS CLOSED.

    R's addition to §9.3: pinning the registry as well closes T-356b's rebuild-after-loss case.
    `rebuild()` upserts from whatever sits in local `data/trade_logs/` on the day, and the 125 run
    rows' directories exist nowhere, so a registry rebuilt after loss would hand the gate a SMALLER
    N without complaint. With the registry pinned, any rebuild, backfill or recreation changes its
    bytes and the gate refuses until someone re-pins by a reviewed commit."""
    pin_path = Path(pin_path) if pin_path is not None else DEFAULT_PIN_PATH
    db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    return _verify_pinned(db_path, load_pin(pin_path)["registry"], "run registry", pin_path)


def load_n_effective_artifact(
    path: Optional[Path] = None,
    artifact_dir: Optional[Path] = None,
    pin_path: Optional[Path] = None,
) -> Dict:
    """Load and validate a ρ̄ artifact. With no explicit `path` — every production call — it is
    the PINNED artifact, hash-verified. An explicit `path` is a deliberate choice by the caller
    (tools, tests), the way an explicit `n_trials_for_dsr` is."""
    p = Path(path) if path else pinned_n_effective_artifact(pin_path, artifact_dir)
    try:
        art = json.loads(p.read_text())
    except (OSError, ValueError) as exc:
        raise HonestNUnavailableError(f"n_effective artifact {p} unreadable: {exc}") from exc
    gi = art.get("gate_inputs")
    if not isinstance(gi, dict):
        raise HonestNUnavailableError(f"n_effective artifact {p} lacks a `gate_inputs` block")
    for key in ("rho_bar", "onc_compression"):
        v = gi.get(key)
        if not isinstance(v, (int, float)) or v != v:
            raise HonestNUnavailableError(f"n_effective artifact {p} gate_inputs lacks a numeric {key!r}")
    return art


def compute_n_effective_correlated(
    db_path: Optional[Path] = None,
    method: str = "conservative",
    artifact_path: Optional[Path] = None,
    artifact_dir: Optional[Path] = None,
    pin_path: Optional[Path] = None,
) -> float:
    """Correlation-aware N_eff. FAILS CLOSED (registry, pin, or pinned artifact missing or
    mismatched → raise).

    method="conservative" (default): the LARGER of the two below. On the 2026-09-30
                       measurement the estimators disagree (equicorrelated ~33, ONC ~21
                       at the registry's 231) and nothing in the data says which is right,
                       so the referee takes the one that makes the gate stricter.
    method="onc":      N_raw × (ONC clusters / runs), the compression López de Prado's
                       Optimal Number of Clusters measured on the executed runs. Its
                       silhouette criterion favours coarse splits when clusters overlap, so
                       it is the LESS conservative estimator on our data.
    method="equicorr": the equicorrelated identity at the measured ρ̄.

    The artifact's `gate_inputs` are the CONSERVATIVE CI bounds, not the point estimates
    (`[NN-SHARPE-CI]`'s logic applied to the trial count): ρ̄'s ci_LOW and the ONC
    compression's ci_HIGH, both of which make N_eff LARGER and the gate STRICTER. N_eff
    moves from 231 to ~61 to ~10 as ρ̄ goes 0 → 0.3 → 0.68, so gating on a noisy point
    would let estimation error loosen the bar.

    N_raw is the registry count (per the RR-3 brief). The proposal documents that the
    registry is a stale manual snapshot DISJOINT from the surviving run evidence — the
    choice of N_raw's population is flagged there for the user, not settled here."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    if artifact_path is None:
        # Production path: BOTH inputs must match the committed pin, the registry checked before
        # it is read. An explicit artifact_path (tools, tests) is a deliberate caller choice and
        # bypasses the pin entirely, the way an explicit n_trials_for_dsr does.
        verify_pinned_registry(db_path, pin_path)
    n_raw = compute_n_effective(db_path)
    gi = load_n_effective_artifact(artifact_path, artifact_dir, pin_path)["gate_inputs"]
    eq = n_eff_equicorrelated(n_raw, float(gi["rho_bar"]))
    onc = max(N_EFF_FLOOR, min(float(n_raw), n_raw * float(gi["onc_compression"])))
    if method == "equicorr":
        return eq
    if method == "onc":
        return onc
    return max(eq, onc)


def resolve_cycle_n_trials(
    batch_len: int,
    db_path: Optional[Path] = None,
    artifact_dir: Optional[Path] = None,
    pin_path: Optional[Path] = None,
) -> Dict:
    """The trial count a Discovery cycle gates Gate 0 and Gate 8 on. FAILS CLOSED.

    Replaces production's `max(1, len(batch))`. The batch is one cycle's candidates;
    [NN-MBL]'s honest N counts every configuration ever run on the substrate, so the
    batch size under-counted by every prior cycle — and when the batch held one
    candidate, it disabled Gate 8 outright. `batch_len` is carried for the log only,
    so the pre-RR-3 figure stays visible beside the one now used."""
    n = compute_n_effective_correlated(db_path, artifact_dir=artifact_dir, pin_path=pin_path)
    return {"n_trials": n, "source": "registry_correlated", "batch_len": int(batch_len)}


# ----------------------------------------------------------------------------- gate
def check_mbl_gate(
    t_years: float,
    n_effective: Optional[float] = None,
    sr_target: float = 1.0,
    db_path: Optional[Path] = None,
    *,
    upper_bound: bool = False,
) -> Dict:
    """Run the MBL Gate-0 check and return a verdict dict.

    n_effective None → `compute_n_effective_correlated(db_path)`, which FAILS CLOSED.
    Keys: passed, t_years, mbl_min, n_effective, n_effective_source, sr_target,
    margin_years, formula, reason."""
    source = "explicit"
    if n_effective is None:
        n_effective = compute_n_effective_correlated(db_path)
        source = "registry_correlated"
    mbl_min = compute_mbl_min(n_effective, sr_target, upper_bound=upper_bound)
    margin = t_years - mbl_min
    passed = margin >= 0.0
    formula = "2ln(N)/SR^2 (upper bound)" if upper_bound else "E[max_N]^2/SR^2 (exact)"
    if passed:
        reason = (
            f"PASS: T_years={t_years:.2f} >= MBL_min={mbl_min:.2f} "
            f"(N_effective={n_effective:.2f} [{source}], SR_target={sr_target}, "
            f"margin={margin:+.2f}yr, {formula})")
    else:
        reason = (
            f"FAIL: T_years={t_years:.2f} < MBL_min={mbl_min:.2f} "
            f"(N_effective={n_effective:.2f} [{source}], SR_target={sr_target}, "
            f"short by {-margin:.2f}yr, {formula}). "
            f"Backtest is statistically under-powered to clear DSR — "
            f"per CLAUDE.md `[NN-MBL]`, no deployment decision is valid until the "
            f"window extends or N_effective decreases.")
    return {
        "passed": passed,
        "t_years": float(t_years),
        "mbl_min": float(mbl_min),
        "n_effective": round(float(n_effective), 4),
        "n_effective_source": source,
        "sr_target": float(sr_target),
        "margin_years": float(margin),
        "formula": formula,
        "reason": reason,
    }


def years_from_window(start_date: str, end_date: str) -> float:
    """Convert ISO date strings (YYYY-MM-DD) to a year-fraction window length."""
    from datetime import datetime
    s = datetime.fromisoformat(start_date)
    e = datetime.fromisoformat(end_date)
    return (e - s).days / 365.25
