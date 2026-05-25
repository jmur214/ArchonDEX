"""T-2026-05-23-057b aggregation — bootstrap CI on the 2-arm × 5-yr ×
5-rep verification campaign for confidence-gated execution on the
extended Stooq+Alpaca substrate (post-T-082b swap).

Reads:
  data/measurements/confidence_gated_t057b_2026_05_23/results.json

Writes:
  docs/Audit/confidence_gated_flag_flip_t057b_2026_05_23.json

Verdict gate (per CLAUDE.md non-negotiable #6):
  * FLIP if ci_low(Δ Sharpe arm2_n3 vs arm0_off) > 0
  * DEFER if ci_low(Δ Sharpe) ≤ 0
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULTS_PATH = ROOT / "data" / "measurements" / "confidence_gated_t057b_2026_05_23" / "results.json"
AUDIT_JSON = ROOT / "docs" / "Audit" / "confidence_gated_flag_flip_t057b_2026_05_23.json"


def _bootstrap_ci(values: list[float], n_iter: int = 1000,
                  ci_low: float = 0.025, ci_high: float = 0.975,
                  seed: int = 0) -> dict:
    if not values:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    rng = np.random.default_rng(seed)
    means = np.empty(n_iter)
    for i in range(n_iter):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means[i] = float(np.mean(sample))
    return {
        "mean": float(np.mean(arr)),
        "ci_low": float(np.quantile(means, ci_low)),
        "ci_high": float(np.quantile(means, ci_high)),
        "n": int(len(arr)),
    }


def _load() -> list:
    if not RESULTS_PATH.exists():
        return []
    return json.loads(RESULTS_PATH.read_text())


def _filter(rows: list, arm: str) -> list:
    return [r for r in rows if r.get("ok") and r.get("arm") == arm]


def _collect(rows: list, key: str) -> list[float]:
    out = []
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _per_year(rows: list, key: str) -> dict:
    by_year: dict[int, list[float]] = {}
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        try:
            by_year.setdefault(int(r["year"]), []).append(float(v))
        except (TypeError, ValueError, KeyError):
            continue
    return {
        str(y): {
            "mean": float(np.mean(vs)) if vs else None,
            "values": vs,
        }
        for y, vs in sorted(by_year.items())
    }


def _per_year_canon(rows: list) -> dict:
    by_year: dict[int, list[str]] = {}
    for r in rows:
        md5 = r.get("trades_canon_md5")
        if md5:
            by_year.setdefault(int(r["year"]), []).append(md5)
    return {
        str(y): {"canon_set_size": len(set(md5s)), "md5s": md5s}
        for y, md5s in sorted(by_year.items())
    }


def main() -> int:
    rows = _load()
    arm0 = _filter(rows, "arm0_off")
    arm1 = _filter(rows, "arm2_n3")

    metrics_keys = [
        ("sharpe", "Sharpe"),
        ("sortino", "Sortino"),
        ("cagr_pct", "CAGR_pct"),
        ("max_drawdown_pct", "MDD_pct"),
        ("win_rate_pct", "WinRate_pct"),
        ("total_trades", "TotalTrades"),
    ]

    headline = {}
    for key, label in metrics_keys:
        a0 = _collect(arm0, key)
        a1 = _collect(arm1, key)
        ci0 = _bootstrap_ci(a0)
        ci1 = _bootstrap_ci(a1)
        delta = None
        delta_ci = None
        if ci0["mean"] is not None and ci1["mean"] is not None:
            delta = round(ci1["mean"] - ci0["mean"], 4)
            if len(a0) == len(a1) and len(a0) > 0:
                paired = [a1[i] - a0[i] for i in range(len(a0))]
                delta_ci = _bootstrap_ci(paired)
        headline[label] = {
            "arm0_off": ci0,
            "arm2_n3": ci1,
            "delta_point": delta,
            "delta_ci": delta_ci,
        }

    per_year = {
        label: {
            "arm0_off": _per_year(arm0, key),
            "arm2_n3": _per_year(arm1, key),
        }
        for key, label in metrics_keys
    }

    canon = {
        "arm0_off_per_year": _per_year_canon(arm0),
        "arm2_n3_per_year": _per_year_canon(arm1),
    }

    # Verdict
    sharpe = headline.get("Sharpe", {})
    delta_ci = sharpe.get("delta_ci") or {}
    ci_low_delta = delta_ci.get("ci_low")
    delta_point = sharpe.get("delta_point")
    if ci_low_delta is not None and ci_low_delta > 0:
        verdict = "FLIP"
        verdict_reason = (
            f"ci_low(Δ Sharpe) = {ci_low_delta:.4f} > 0 — clears CLAUDE.md #6 strict gate"
        )
    elif delta_point is not None:
        verdict = "DEFER"
        verdict_reason = (
            f"ci_low(Δ Sharpe) = {ci_low_delta} ≤ 0 — does not clear CLAUDE.md #6"
        )
    else:
        verdict = "INCOMPLETE"
        verdict_reason = "Insufficient data — campaign not complete"

    payload = {
        "task_id": "T-2026-05-23-057b",
        "description": "Confidence-gated execution flag-flip verification on extended substrate",
        "substrate": "Stooq+Alpaca merged (post-T-082b), 1962-2026 depth",
        "n_backtests": {
            "arm0_off": sum(1 for r in arm0),
            "arm2_n3": sum(1 for r in arm1),
            "total": len(arm0) + len(arm1),
        },
        "headline": headline,
        "per_year": per_year,
        "canon_md5_stability": canon,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }

    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(payload, indent=2, default=str))
    print(f"[T-057b] aggregation written → {AUDIT_JSON}")

    print("\n=== HEADLINE ===")
    for label in ("Sharpe", "Sortino", "CAGR_pct", "MDD_pct"):
        h = headline.get(label, {})
        a0 = h.get("arm0_off", {})
        a1 = h.get("arm2_n3", {})
        print(f"\n{label}:")
        print(f"  Arm 0 (OFF):    mean={a0.get('mean')} ci=[{a0.get('ci_low')}, {a0.get('ci_high')}] n={a0.get('n')}")
        print(f"  Arm 2 (n=3):    mean={a1.get('mean')} ci=[{a1.get('ci_low')}, {a1.get('ci_high')}] n={a1.get('n')}")
        if h.get("delta_point") is not None:
            d = h.get("delta_ci") or {}
            print(f"  Δ (n=3 - OFF):  point={h.get('delta_point')} ci=[{d.get('ci_low')}, {d.get('ci_high')}]")

    print(f"\n=== VERDICT: {verdict} ===")
    print(f"  {verdict_reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
