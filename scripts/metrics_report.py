"""scripts/metrics_report.py
====================================
T-2026-05-22-069: reusable CLI for the T-059..T-065 metrics suite.

Generalizes the T-066 hardcoded-T-035-runs report into a tool agents
(and the director) can run on any backtest output: per-run-id, by year,
or across a list. Generates the same audit JSON + Markdown.

Usage:
  # Single run by run_id:
  python -m scripts.metrics_report --run-id <uuid>

  # Multiple runs by run_id (comma-separated):
  python -m scripts.metrics_report --run-ids uuid1,uuid2,uuid3

  # All runs registered in the SQLite registry within a date window:
  python -m scripts.metrics_report --since 2026-05-01

  # Output paths:
  python -m scripts.metrics_report --run-id X --out-md /tmp/foo.md

By default outputs are written to docs/Audit/metrics_report_<timestamp>.{md,json}.

Source-data convention:
  - Each run_id has a directory under data/trade_logs/<run_id>/
  - portfolio_snapshots.csv (cockpit-fixed schema) → equity curve
  - PBO across multiple runs uses first-N-overlapping-bars as the
    trial-matrix dimension (similar to T-066's year-as-trial approach)

Metrics applied (per the 2026-05-16 metrics research dive's Layer 1-3):
  - T-059: Lo η(q) autocorrelation correction
  - T-060: PBO via CSCV (when N >= 2 runs)
  - T-062: Expected Shortfall_97.5, CDaR_95, max drawdown
  - T-063: rolling-PSR (60-bar window), CUSUM decay monitor

What this script does NOT do:
  - Run any backtest (read-only on existing trade logs)
  - Modify any production state
  - Lower any threshold or hardcode a deployment decision
"""
from __future__ import annotations

import argparse
import gzip
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np
import pandas as pd

from core.metrics_engine import MetricsEngine

log = logging.getLogger("metrics_report")


# =============================================================================
# Trade-log loader
# =============================================================================

def load_equity_curve(run_id: str) -> Optional[pd.Series]:
    """Load equity from a run's portfolio_snapshots.csv (cockpit-fixed schema).

    Returns None if the snapshots file is missing or unparseable. Supports
    both raw .csv and gzipped .csv.gz (T-040 retention-policy compression
    preserves readability for archived runs).
    """
    snap_path_csv = REPO / f"data/trade_logs/{run_id}/portfolio_snapshots.csv"
    snap_path_gz = REPO / f"data/trade_logs/{run_id}/portfolio_snapshots.csv.gz"

    if snap_path_csv.exists():
        df = pd.read_csv(snap_path_csv)
    elif snap_path_gz.exists():
        with gzip.open(snap_path_gz, "rt") as f:
            df = pd.read_csv(f)
    else:
        log.warning("No portfolio_snapshots found for run_id %s", run_id)
        return None

    if "timestamp" not in df.columns or "equity" not in df.columns:
        log.warning(
            "Snapshots for %s missing required columns "
            "(timestamp, equity). Got: %s", run_id, list(df.columns)
        )
        return None

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp")["equity"].astype(float)


# =============================================================================
# Per-run metrics
# =============================================================================

def compute_metrics_for_run(run_id: str, label: Optional[str] = None) -> Dict:
    """Apply T-059..T-065 metrics to a single run's equity curve.

    `label` is a human-readable identifier (e.g., "2024" for a year-run);
    falls back to the first 8 chars of run_id if not provided.
    """
    eq = load_equity_curve(run_id)
    if eq is None:
        return {"run_id": run_id, "label": label or run_id[:8], "error": "no_equity"}

    returns = eq.pct_change().dropna()
    if len(returns) < 30:
        return {
            "run_id": run_id, "label": label or run_id[:8],
            "error": f"insufficient_returns_n={len(returns)}",
        }

    # T-059: Lo-corrected Sharpe
    naive_sharpe = MetricsEngine.sharpe_ratio(returns)
    lo_corrected = MetricsEngine.sharpe_ratio_lo_corrected(returns, max_lag=30)
    lo_eta = MetricsEngine.lo_eta(returns, q=252, max_lag=30)

    # T-062: Layer 2 portfolio health
    es_975 = MetricsEngine.expected_shortfall(returns, confidence=0.975)
    cdar_95 = MetricsEngine.conditional_drawdown_at_risk(eq, alpha=0.95)
    mdd = MetricsEngine.max_drawdown(eq)

    # T-063: rolling-PSR + CUSUM
    psr_window = min(60, len(returns) // 2)
    rolling_psr = MetricsEngine.rolling_psr(returns, window=psr_window)
    psr_median = float(rolling_psr.dropna().median()) if not rolling_psr.empty else None

    # CUSUM uses self-reference (within-run self-check). For OOS-vs-IS
    # decay-detection, caller should run CUSUM separately with proper
    # pre-registered (ref_mean, ref_std) from in-sample.
    ref_mean = float(returns.mean())
    ref_std = float(returns.std())
    if ref_std < 1e-12 or not np.isfinite(ref_std):
        cusum = {"decay_alarm_fired": False, "max_cusum_minus": 0.0}
    else:
        cusum = MetricsEngine.cusum_decay_monitor(
            returns, reference_mean=ref_mean, reference_std=ref_std,
            k=0.5, h=10.0,
        )

    haircut_pct = (
        float((naive_sharpe - lo_corrected) / naive_sharpe * 100)
        if abs(naive_sharpe) > 1e-9 else 0.0
    )

    return {
        "run_id": run_id,
        "label": label or run_id[:8],
        "n_returns": len(returns),
        "sharpe_naive": float(naive_sharpe),
        "sharpe_lo_corrected": float(lo_corrected),
        "lo_eta": float(lo_eta),
        "lo_haircut_pct": haircut_pct,
        "expected_shortfall_975_pct": float(es_975 * 100),
        "max_drawdown_pct": float(mdd * 100),
        "cdar_95_pct": float(cdar_95 * 100),
        "rolling_psr_median": psr_median,
        "psr_window_used": psr_window,
        "cusum_alarm_fired": bool(cusum["decay_alarm_fired"]),
        "cusum_max_minus": float(cusum.get("max_cusum_minus", 0.0)),
    }


# =============================================================================
# Multi-run aggregation
# =============================================================================

def compute_aggregate(per_run: List[Dict]) -> Dict:
    """Cross-run summary stats."""
    valid = [c for c in per_run if "error" not in c]
    if not valid:
        return {"error": "no valid runs"}
    sharpes_naive = [c["sharpe_naive"] for c in valid]
    sharpes_lo = [c["sharpe_lo_corrected"] for c in valid]
    return {
        "n_valid_runs": len(valid),
        "mean_sharpe_naive": float(np.mean(sharpes_naive)),
        "mean_sharpe_lo_corrected": float(np.mean(sharpes_lo)),
        "min_sharpe_lo_corrected": float(min(sharpes_lo)),
        "max_sharpe_lo_corrected": float(max(sharpes_lo)),
        "n_alarms_fired": sum(1 for c in valid if c["cusum_alarm_fired"]),
    }


def compute_pbo_across_runs(
    run_ids: List[str],
    labels: List[str],
    n_partitions: Optional[int] = None,
) -> Dict:
    """Run PBO via CSCV using runs as trials, common-bar-count as time.

    Each run is one trial; bars within each run are the time dimension.
    Requires N >= 2 runs and T >= 2*n_partitions bars per run.

    n_partitions: override the auto-selection. Auto picks 16 if min_len>=64,
    else 8 if min_len>=32, else 4. T-066 baseline uses 8 explicitly; pass
    n_partitions=8 to reproduce that report's PBO exactly.
    """
    if len(run_ids) < 2:
        return {"error": "need >= 2 runs for PBO"}

    panel: Dict[str, pd.Series] = {}
    for run_id, label in zip(run_ids, labels):
        eq = load_equity_curve(run_id)
        if eq is None:
            continue
        rets = eq.pct_change().dropna().reset_index(drop=True)
        if len(rets) >= 32:  # min for n_partitions=8
            panel[label] = rets

    if len(panel) < 2:
        return {"error": f"only {len(panel)} runs have usable data"}

    min_len = min(len(s) for s in panel.values())
    if n_partitions is None:
        n_partitions = 16 if min_len >= 64 else (8 if min_len >= 32 else 4)
    if min_len < 2 * n_partitions:
        return {"error": f"min bars per run {min_len} < 2 * n_partitions {n_partitions}"}

    matrix = pd.DataFrame({
        label: panel[label].iloc[:min_len].values
        for label in sorted(panel.keys())
    })

    return MetricsEngine.probability_of_backtest_overfitting(
        matrix, n_partitions=n_partitions, rank_metric="sharpe",
    )


# =============================================================================
# Run-id resolution (CLI flags)
# =============================================================================

def resolve_run_ids(args: argparse.Namespace) -> List[Tuple[str, str]]:
    """Return list of (run_id, label) tuples per CLI args.

    Sources, in precedence order:
      1. --run-id (single)
      2. --run-ids (comma-separated)
      3. --since (date) — pull from run_registry.sqlite
    """
    if args.run_id:
        return [(args.run_id, args.label or args.run_id[:8])]
    if args.run_ids:
        ids = [x.strip() for x in args.run_ids.split(",") if x.strip()]
        return [(i, i[:8]) for i in ids]
    if args.since:
        return _query_run_registry_since(args.since)
    raise SystemExit("must specify --run-id, --run-ids, or --since")


def _query_run_registry_since(since_iso: str) -> List[Tuple[str, str]]:
    """Pull run_ids from the SQLite registry whose snapshot_at >= since."""
    import sqlite3
    db = REPO / "data/observability/run_registry.sqlite"
    if not db.exists():
        log.error("Run registry not found at %s", db)
        return []
    conn = sqlite3.connect(db)
    try:
        cursor = conn.execute(
            "SELECT run_id, snapshot_at FROM runs "
            "WHERE snapshot_at >= ? ORDER BY snapshot_at",
            (since_iso,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()
    return [(rid, rid[:8]) for (rid, _ts) in rows]


# =============================================================================
# Output formatting
# =============================================================================

def render_per_run_table(per_run: List[Dict]) -> str:
    """ASCII table of per-run metrics for terminal output."""
    header = (
        f"{'Label':<14} {'Sharpe_naive':>13} {'Sharpe_Lo':>11} "
        f"{'Lo_η':>7} {'haircut%':>10} {'ES_97.5%':>10} {'MDD%':>7} "
        f"{'CDaR%':>8} {'PSR':>6} {'CUSUM':>7}"
    )
    sep = "-" * len(header)
    lines = [header, sep]
    for c in per_run:
        if "error" in c:
            lines.append(f"{c['label']:<14} ERROR: {c['error']}")
            continue
        alarm = "FIRED" if c["cusum_alarm_fired"] else "ok"
        psr = f"{c['rolling_psr_median']:.3f}" if c["rolling_psr_median"] is not None else "n/a"
        lines.append(
            f"{c['label']:<14} {c['sharpe_naive']:>13.3f} {c['sharpe_lo_corrected']:>11.3f} "
            f"{c['lo_eta']:>7.2f} {c['lo_haircut_pct']:>9.1f}% "
            f"{c['expected_shortfall_975_pct']:>9.2f}% {c['max_drawdown_pct']:>6.2f}% "
            f"{c['cdar_95_pct']:>7.2f}% {psr:>6} {alarm:>7}"
        )
    return "\n".join(lines)


def render_markdown(per_run: List[Dict], aggregate: Dict, pbo: Dict, args: argparse.Namespace) -> str:
    """Generate the audit-doc Markdown."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "---",
        f"title: Metrics report — {len(per_run)} run(s) under T-059..T-065 suite",
        f"date: {ts}",
        "author: scripts/metrics_report.py (T-2026-05-22-069)",
        "---",
        "",
        f"# Metrics report — {len(per_run)} run(s) under T-059..T-065 suite",
        "",
        "## Per-run breakdown",
        "",
        "| Label | Sharpe_naive | Sharpe_Lo | Lo_η | Lo_haircut | ES_97.5% | MDD% | CDaR_95% | Rolling-PSR | CUSUM alarm |",
        "|-------|--------------|-----------|------|------------|----------|------|----------|-------------|-------------|",
    ]
    for c in per_run:
        if "error" in c:
            lines.append(f"| {c['label']} | ERROR: {c['error']} | | | | | | | | |")
            continue
        alarm = "FIRED" if c["cusum_alarm_fired"] else "—"
        psr = f"{c['rolling_psr_median']:.3f}" if c["rolling_psr_median"] is not None else "n/a"
        lines.append(
            f"| {c['label']} | {c['sharpe_naive']:+.3f} | {c['sharpe_lo_corrected']:+.3f} | "
            f"{c['lo_eta']:.2f} | {c['lo_haircut_pct']:+.1f}% | "
            f"{c['expected_shortfall_975_pct']:+.2f}% | {c['max_drawdown_pct']:+.2f}% | "
            f"{c['cdar_95_pct']:+.2f}% | {psr} | {alarm} |"
        )
    lines.extend([
        "",
        "## Aggregate",
        "",
    ])
    if "error" in aggregate:
        lines.append(f"- ERROR: {aggregate['error']}")
    else:
        lines.extend([
            f"- **n_valid_runs**: {aggregate['n_valid_runs']}",
            f"- **Mean Sharpe (naive)**: `{aggregate['mean_sharpe_naive']:.3f}`",
            f"- **Mean Sharpe (Lo corrected)**: `{aggregate['mean_sharpe_lo_corrected']:.3f}`",
            f"- **Worst Sharpe (Lo)**: `{aggregate['min_sharpe_lo_corrected']:.3f}`",
            f"- **Best Sharpe (Lo)**: `{aggregate['max_sharpe_lo_corrected']:.3f}`",
            f"- **Runs with CUSUM alarm**: {aggregate['n_alarms_fired']} / {aggregate['n_valid_runs']}",
        ])
    lines.extend([
        "",
        "## PBO via CSCV",
        "",
    ])
    if "error" in pbo:
        lines.append(f"- ERROR: {pbo['error']}")
    else:
        verdict = (
            "edge present (PBO < 0.5)" if pbo["pbo"] < 0.5
            else "overfit-pattern (PBO ≥ 0.5)"
        )
        lines.extend([
            f"- **PBO**: `{pbo['pbo']:.3f}` → **{verdict}**",
            f"- **n_combinations**: {pbo['n_combinations']}",
            f"- **n_partitions**: {pbo.get('n_partitions', 'n/a')}",
            f"- **n_trials (runs)**: {pbo['n_trials']}",
            f"- **logit_mean**: {pbo['logit_mean']:.3f}",
        ])
    lines.extend([
        "",
        "## Metric definitions",
        "",
        "- **Sharpe_naive**: standard `mean/std × √252` annualization",
        "- **Sharpe_Lo**: T-059 Lo η(q) autocorrelation correction; deflates "
        "naive Sharpe under positive autocorrelation, amplifies under negative",
        "- **ES_97.5%**: T-062 Expected Shortfall (mean of worst 2.5% of returns); "
        "Basel III FRTB standard, coherent unlike VaR",
        "- **CDaR_95%**: T-062 Conditional Drawdown at Risk (mean of worst 5% of "
        "drawdowns); LP-tractable + convex (unlike raw MDD)",
        "- **Rolling-PSR**: T-063 Probability that true Sharpe > 0 over a "
        "60-bar trailing window; live-monitoring signal for decay",
        "- **CUSUM alarm**: T-063 sequential analysis detector; fires when "
        "within-run drift exceeds k=0.5σ tolerance for sustained periods",
        "- **PBO via CSCV**: T-060 Probability of Backtest Overfitting; "
        "Bailey-Borwein-López de Prado-Zhu (2017). PBO < 0.5 = edge; > 0.5 = overfit.",
        "",
    ])
    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="single run_id to report on")
    parser.add_argument("--run-ids", help="comma-separated list of run_ids")
    parser.add_argument("--since", help="ISO date — pull runs from registry on/after this date")
    parser.add_argument("--label", help="label for single --run-id (default: first 8 chars)")
    parser.add_argument("--out-md", help="output Markdown path (default: docs/Audit/...)")
    parser.add_argument("--out-json", help="output JSON path (default: docs/Audit/...)")
    parser.add_argument("--no-pbo", action="store_true", help="skip PBO computation (faster)")
    parser.add_argument(
        "--pbo-partitions", type=int, default=None,
        help="CSCV partition count (default auto: 16/8/4 by data length; "
             "pass 8 to match T-066 baseline)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    runs = resolve_run_ids(args)
    print(f"[metrics_report] Processing {len(runs)} run(s)")

    per_run: List[Dict] = []
    for run_id, label in runs:
        result = compute_metrics_for_run(run_id, label=label)
        per_run.append(result)
        if "error" in result:
            print(f"  {label}: ERROR — {result['error']}")
        else:
            print(f"  {label}: n_returns={result['n_returns']}, "
                  f"Sharpe={result['sharpe_lo_corrected']:.3f} (Lo), "
                  f"alarm={'FIRED' if result['cusum_alarm_fired'] else 'ok'}")

    aggregate = compute_aggregate(per_run)
    pbo: Dict = {"error": "skipped"} if args.no_pbo or len(runs) < 2 else compute_pbo_across_runs(
        [r[0] for r in runs], [r[1] for r in runs],
        n_partitions=args.pbo_partitions,
    )

    print()
    print(render_per_run_table(per_run))
    print()
    if "error" not in aggregate:
        print(f"Aggregate Mean Sharpe (Lo): {aggregate['mean_sharpe_lo_corrected']:.3f}")
        print(f"Worst:                       {aggregate['min_sharpe_lo_corrected']:.3f}")
        print(f"Alarms fired:                {aggregate['n_alarms_fired']}/{aggregate['n_valid_runs']}")
    if "error" not in pbo:
        print(f"PBO via CSCV: {pbo['pbo']:.3f}")

    # Write outputs
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_md = Path(args.out_md) if args.out_md else REPO / f"docs/Audit/metrics_report_{timestamp}.md"
    out_json = Path(args.out_json) if args.out_json else REPO / f"docs/Audit/metrics_report_{timestamp}.json"

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    md = render_markdown(per_run, aggregate, pbo, args)
    out_md.write_text(md)

    out = {
        "task_id": "T-2026-05-22-069",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_runs": len(runs),
        "per_run": per_run,
        "aggregate": aggregate,
        "pbo_cscv": pbo,
    }
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, default=str)

    print()
    print(f"Markdown: {out_md.relative_to(REPO)}")
    print(f"JSON:     {out_json.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
