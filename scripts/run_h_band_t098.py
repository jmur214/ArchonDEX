"""T-2026-05-31-098 H-Band A/B harness — no-trade band sweep on the 12-yr window.

Three arms, all on canonical substrate (T-082b extended Stooq + Alpaca):

  arm0_off  : no_trade_band_enabled=False (current behavior; baseline)
  arm1_b20  : no_trade_band_enabled=True,  no_trade_band_pct=0.20
  arm2_b25  : no_trade_band_enabled=True,  no_trade_band_pct=0.25

Per year × per arm, we:
  1. restore the governor anchor via run_isolated.isolated()
  2. patch config/portfolio_settings.json for the arm (idempotent; restored on exit)
  3. run ModeController.run_backtest for the calendar year
  4. collect Sharpe (point), Sortino (point), CAGR%, MaxDD%, total trades,
     PSR (via summary), turnover (sum of trade notional / starting equity),
     return-skew (from the portfolio's daily return series, where available),
     trades_canon_md5.

Aggregation:
  - Per-arm 12-yr mean Sharpe + block-bootstrap CI (Künsch 1989; auto block
    length via Politis-White) over yearly Sharpes.
  - Per-arm Δ vs arm0_off (mean Δ Sharpe with block-bootstrap CI on the
    paired-year delta), Δ turnover, Δ skew, Δ MaxDD, Δ CAGR.

Output:
  - JSON aggregation at the --output path (default
    docs/Audit/no_trade_band_h_band_t098_2026_05_31.json).
  - Markdown report alongside (default
    docs/Audit/no_trade_band_h_band_t098_2026_05_31.md).

Usage:
  PYTHONHASHSEED=0 python -m scripts.run_h_band_t098 \\
      --years 2013,2014,...,2024 --runs 1

  Smoke (single year):
  PYTHONHASHSEED=0 python -m scripts.run_h_band_t098 --years 2022 --runs 1

  Canon-md5 verification (no aggregation, just per-cell canon):
  PYTHONHASHSEED=0 python -m scripts.run_h_band_t098 --years 2022 --canon-only
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_isolated import (  # noqa: E402
    ISOLATED_ANCHOR,
    TRADES_DIR,
    isolated,
    _find_run_id,
    _trades_canon_md5,
)

PORTFOLIO_CFG_PATH = ROOT / "config" / "portfolio_settings.json"


# Arm definitions — exposed at module level so the audit + report can cite them.
ARMS: List[dict] = [
    {"name": "arm0_off", "no_trade_band_enabled": False, "no_trade_band_pct": 0.0},
    {"name": "arm1_b20", "no_trade_band_enabled": True,  "no_trade_band_pct": 0.20},
    {"name": "arm2_b25", "no_trade_band_enabled": True,  "no_trade_band_pct": 0.25},
]


# ---------------------------------------------------------------------- #
# Config patching — atomic write + restore on exit. Sibling of T-055
# pattern; ensures canon-md5 OFF arm is byte-identical to the unpatched
# baseline, and ON arms differ.
# ---------------------------------------------------------------------- #

@contextlib.contextmanager
def patched_portfolio_cfg(arm: dict):
    """Apply an arm to portfolio_settings.json; restore on exit.

    The arm is OFF-equivalent to the original file IF AND ONLY IF the
    original already has no_trade_band_enabled=False (or absent — same
    default). We assert that pre-condition so an accidentally-flipped
    JSON doesn't silently corrupt the OFF arm's canon-md5 baseline.
    """
    original_text = PORTFOLIO_CFG_PATH.read_text()
    original_cfg = json.loads(original_text)
    # Sanity: original file must NOT have band ON (else OFF arm wouldn't be
    # the true baseline). T-093 + T-088 lessons: verify env-suffixed config
    # patches actually propagate / silently-mismatch family.
    if original_cfg.get("no_trade_band_enabled", False):
        raise RuntimeError(
            "config/portfolio_settings.json already has no_trade_band_enabled "
            "set; A/B baseline OFF arm cannot be the true pre-T-098 baseline. "
            "Reset to default OFF before running the harness."
        )
    try:
        patched = dict(original_cfg)
        patched["no_trade_band_enabled"] = bool(arm["no_trade_band_enabled"])
        patched["no_trade_band_pct"] = float(arm["no_trade_band_pct"])
        # Atomic-ish: write to temp + replace, so a Ctrl-C mid-write doesn't
        # leave a corrupt JSON behind.
        with tempfile.NamedTemporaryFile(
            "w", delete=False, dir=str(PORTFOLIO_CFG_PATH.parent), suffix=".json.tmp",
        ) as tf:
            json.dump(patched, tf, indent=4)
            tmp = tf.name
        shutil.move(tmp, PORTFOLIO_CFG_PATH)
        yield
    finally:
        PORTFOLIO_CFG_PATH.write_text(original_text)


# ---------------------------------------------------------------------- #
# Backtest + metrics
# ---------------------------------------------------------------------- #

def _run_year(year: int) -> dict:
    """Run a single calendar-year backtest under prod config."""
    from orchestration.mode_controller import ModeController
    mc = ModeController(ROOT, env="prod")
    return mc.run_backtest(
        mode="prod",
        fresh=False,
        no_governor=False,
        reset_governor=True,
        alpha_debug=False,
        override_start=f"{year}-01-01",
        override_end=f"{year}-12-31",
    )


def _trades_turnover(run_id: str, starting_equity: float) -> float:
    """Sum of absolute trade notional divided by starting equity.

    Per the 2026-05-31 research turnover convention; matches the
    "fraction-of-equity rebalanced" intuition the band targets.
    """
    if not run_id or run_id == "?" or starting_equity <= 0:
        return float("nan")
    run_dir = TRADES_DIR / run_id
    p = next(
        (run_dir / x for x in ("trades.csv", f"trades_{run_id}.csv") if (run_dir / x).exists()),
        None,
    )
    if p is None:
        return float("nan")
    try:
        import pandas as pd
        df = pd.read_csv(p)
        if df.empty:
            return 0.0
        qty_col = next((c for c in ("qty", "filled_qty") if c in df.columns), None)
        px_col = next((c for c in ("fill_price", "price", "avg_price") if c in df.columns), None)
        if qty_col is None or px_col is None:
            return float("nan")
        notional = (df[qty_col].abs() * df[px_col].abs()).sum()
        return float(notional / starting_equity)
    except Exception:
        return float("nan")


def _equity_skew(run_id: str) -> float:
    """Compute the skew of daily returns from the portfolio snapshots CSV."""
    if not run_id or run_id == "?":
        return float("nan")
    run_dir = TRADES_DIR / run_id
    p = run_dir / "portfolio_snapshots.csv"
    if not p.exists():
        return float("nan")
    try:
        import pandas as pd
        from scipy import stats as _stats
        df = pd.read_csv(p)
        if "equity" not in df.columns or len(df) < 4:
            return float("nan")
        eq = df["equity"].astype(float).values
        if (eq <= 0).any():
            return float("nan")
        rets = np.diff(eq) / eq[:-1]
        rets = rets[np.isfinite(rets)]
        if len(rets) < 4:
            return float("nan")
        return float(_stats.skew(rets, bias=False))
    except Exception:
        return float("nan")


def _summary_field(summary: Optional[dict], key: str) -> Optional[float]:
    if not summary:
        return None
    v = summary.get(key)
    if v is None:
        return None
    try:
        out = float(v)
        return out if np.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def _run_cell(year: int, arm: dict, do_canon: bool = True) -> dict:
    """Run one (arm, year) cell. Returns a dict with metrics + canon md5."""
    t0 = time.time()
    before = {p.name for p in TRADES_DIR.iterdir() if p.is_dir() and p.name != "backup"}
    summary = _run_year(year)
    run_id = _find_run_id(before) or "?"
    starting_equity = _summary_field(summary, "Starting Equity") or 0.0
    record = {
        "year": year,
        "arm": arm["name"],
        "no_trade_band_enabled": bool(arm["no_trade_band_enabled"]),
        "no_trade_band_pct": float(arm["no_trade_band_pct"]),
        "run_id": run_id,
        "sharpe": _summary_field(summary, "Sharpe Ratio"),
        "sortino": _summary_field(summary, "Sortino"),
        "psr": _summary_field(summary, "PSR"),
        "cagr_pct": _summary_field(summary, "CAGR (%)"),
        "max_drawdown_pct": _summary_field(summary, "Max Drawdown (%)"),
        "win_rate_pct": _summary_field(summary, "Win Rate (%)"),
        "total_trades": _summary_field(summary, "Total Trades"),
        "starting_equity": starting_equity,
        "trades_canon_md5": _trades_canon_md5(run_id) if do_canon and run_id != "?" else "(skipped)",
        "turnover_frac_equity": _trades_turnover(run_id, starting_equity),
        "return_skew": _equity_skew(run_id),
        "wall_time_seconds": round(time.time() - t0, 1),
        "ok": True,
    }
    return record


# ---------------------------------------------------------------------- #
# Block bootstrap CI — Künsch (1989) circular block bootstrap with auto
# block length per Politis-White (2004). Reuses the project standard.
# Local implementation: small, dependency-light, identical math to
# core/metrics_engine.bootstrap_distribution.
# ---------------------------------------------------------------------- #

def _politis_white_block_length(x: np.ndarray) -> int:
    """Politis-White (2004) automatic block length. Cheap heuristic for
    a 12-element series — clamp to [2, n//2]."""
    n = len(x)
    if n < 4:
        return max(1, n // 2)
    # Empirical autocorrelation at lag 1 — a 2-step proxy for the full
    # P-W spectral estimate when n is tiny.
    if x.std(ddof=1) < 1e-12:
        return 2
    centered = x - x.mean()
    denom = float((centered ** 2).sum())
    if denom <= 0:
        return 2
    rho1 = float((centered[:-1] * centered[1:]).sum() / denom)
    rho1 = max(min(rho1, 0.99), -0.99)
    # b* ~ (2 * rho1^2 / (1 - rho1^2))^(1/3) * n^(1/3); clamp.
    if abs(rho1) < 1e-6:
        b = 1
    else:
        b = int(np.ceil((2.0 * rho1 ** 2 / (1.0 - rho1 ** 2)) ** (1.0 / 3.0) * n ** (1.0 / 3.0)))
    return int(max(2, min(b, max(2, n // 2))))


def _block_bootstrap_ci(values: np.ndarray, n_iter: int = 1000, alpha: float = 0.05, seed: int = 42) -> dict:
    """Circular block bootstrap mean + (1-alpha) CI on a 1-D series.
    Returns a dict with mean, ci_low, ci_high, block_length, n.
    """
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    n = len(arr)
    if n == 0:
        return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"),
                "block_length": 0, "n": 0}
    b = _politis_white_block_length(arr)
    rng = np.random.default_rng(seed)
    means = np.empty(n_iter, dtype=float)
    for i in range(n_iter):
        # circular block bootstrap: sample n//b blocks of length b
        n_blocks = int(np.ceil(n / b))
        starts = rng.integers(0, n, size=n_blocks)
        idx = np.concatenate([(s + np.arange(b)) % n for s in starts])[:n]
        means[i] = arr[idx].mean()
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {
        "mean": float(arr.mean()),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "block_length": int(b),
        "n": int(n),
    }


# ---------------------------------------------------------------------- #
# Driver
# ---------------------------------------------------------------------- #

def _aggregate(results: List[dict]) -> dict:
    """Group cell records into per-arm summaries with block-bootstrap CIs.
    Also computes per-arm Δ vs arm0_off on the paired-year delta.
    """
    by_arm: Dict[str, List[dict]] = {}
    for r in results:
        if not r.get("ok", True):
            continue
        by_arm.setdefault(r["arm"], []).append(r)

    arm_summaries: Dict[str, dict] = {}
    for arm_name, cells in by_arm.items():
        sharpes = np.array([c.get("sharpe") if c.get("sharpe") is not None else np.nan for c in cells], dtype=float)
        cagrs = np.array([c.get("cagr_pct") if c.get("cagr_pct") is not None else np.nan for c in cells], dtype=float)
        mdds = np.array([c.get("max_drawdown_pct") if c.get("max_drawdown_pct") is not None else np.nan for c in cells], dtype=float)
        turnovers = np.array([c.get("turnover_frac_equity") if c.get("turnover_frac_equity") is not None else np.nan for c in cells], dtype=float)
        skews = np.array([c.get("return_skew") if c.get("return_skew") is not None else np.nan for c in cells], dtype=float)
        trades = np.array([c.get("total_trades") if c.get("total_trades") is not None else np.nan for c in cells], dtype=float)
        arm_summaries[arm_name] = {
            "n_cells": len(cells),
            "years": sorted({c["year"] for c in cells}),
            "sharpe_bootstrap": _block_bootstrap_ci(sharpes),
            "cagr_pct_mean": float(np.nanmean(cagrs)) if np.any(np.isfinite(cagrs)) else float("nan"),
            "max_drawdown_pct_mean": float(np.nanmean(mdds)) if np.any(np.isfinite(mdds)) else float("nan"),
            "turnover_frac_equity_mean": float(np.nanmean(turnovers)) if np.any(np.isfinite(turnovers)) else float("nan"),
            "return_skew_mean": float(np.nanmean(skews)) if np.any(np.isfinite(skews)) else float("nan"),
            "total_trades_mean": float(np.nanmean(trades)) if np.any(np.isfinite(trades)) else float("nan"),
        }

    # Δ vs arm0_off on paired-year deltas (within-year subtraction reduces
    # year-volatility noise that hits both arms equally).
    if "arm0_off" in by_arm:
        off_by_year = {c["year"]: c for c in by_arm["arm0_off"]}
        for arm_name, cells in by_arm.items():
            if arm_name == "arm0_off":
                continue
            delta_sharpe = []
            delta_turnover = []
            delta_skew = []
            delta_cagr = []
            delta_mdd = []
            for c in cells:
                off = off_by_year.get(c["year"])
                if not off:
                    continue
                def _d(a, b):
                    if a is None or b is None:
                        return None
                    if not (np.isfinite(a) and np.isfinite(b)):
                        return None
                    return a - b
                delta_sharpe.append(_d(c.get("sharpe"), off.get("sharpe")))
                delta_turnover.append(_d(c.get("turnover_frac_equity"), off.get("turnover_frac_equity")))
                delta_skew.append(_d(c.get("return_skew"), off.get("return_skew")))
                delta_cagr.append(_d(c.get("cagr_pct"), off.get("cagr_pct")))
                delta_mdd.append(_d(c.get("max_drawdown_pct"), off.get("max_drawdown_pct")))
            arm_summaries[arm_name]["delta_vs_arm0_off"] = {
                "sharpe_bootstrap": _block_bootstrap_ci(np.array([d for d in delta_sharpe if d is not None], dtype=float)),
                "turnover_frac_equity_mean": float(np.nanmean([d for d in delta_turnover if d is not None])) if any(d is not None for d in delta_turnover) else float("nan"),
                "return_skew_mean": float(np.nanmean([d for d in delta_skew if d is not None])) if any(d is not None for d in delta_skew) else float("nan"),
                "cagr_pct_mean": float(np.nanmean([d for d in delta_cagr if d is not None])) if any(d is not None for d in delta_cagr) else float("nan"),
                "max_drawdown_pct_mean": float(np.nanmean([d for d in delta_mdd if d is not None])) if any(d is not None for d in delta_mdd) else float("nan"),
            }

    return arm_summaries


def _write_markdown(results: List[dict], summaries: dict, output_md: Path) -> None:
    lines = [
        "# T-2026-05-31-098 H-Band 12-yr A/B — report",
        "",
        f"Generated: cells = {len(results)}; arms = {sorted({r['arm'] for r in results})}.",
        "",
        "## Per-arm aggregate",
        "",
        "| Arm | n | Sharpe mean | ci_low | ci_high | block | CAGR%% mean | MaxDD%% mean | Turnover | Skew | Trades |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for arm in sorted(summaries.keys()):
        s = summaries[arm]
        boot = s["sharpe_bootstrap"]
        lines.append(
            f"| {arm} | {s['n_cells']} | {boot['mean']:.4f} | {boot['ci_low']:.4f} | {boot['ci_high']:.4f} | {boot['block_length']} | "
            f"{s.get('cagr_pct_mean', float('nan')):.3f} | {s.get('max_drawdown_pct_mean', float('nan')):.3f} | "
            f"{s.get('turnover_frac_equity_mean', float('nan')):.4f} | {s.get('return_skew_mean', float('nan')):.3f} | "
            f"{s.get('total_trades_mean', float('nan')):.1f} |"
        )
    lines.append("")
    lines.append("## Δ vs arm0_off (paired-year)")
    lines.append("")
    lines.append("| Arm | Δ Sharpe mean | ci_low | ci_high | Δ Turnover | Δ Skew | Δ CAGR%% | Δ MaxDD%% |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for arm in sorted(summaries.keys()):
        if arm == "arm0_off":
            continue
        d = summaries[arm].get("delta_vs_arm0_off")
        if not d:
            continue
        b = d["sharpe_bootstrap"]
        lines.append(
            f"| {arm} | {b['mean']:.4f} | {b['ci_low']:.4f} | {b['ci_high']:.4f} | "
            f"{d['turnover_frac_equity_mean']:.4f} | {d['return_skew_mean']:.3f} | "
            f"{d['cagr_pct_mean']:.3f} | {d['max_drawdown_pct_mean']:.3f} |"
        )
    lines.append("")
    lines.append("## Per-cell detail")
    lines.append("")
    lines.append("| Year | Arm | Sharpe | CAGR%% | MDD%% | Turnover | Skew | Trades | canon_md5 | wall (s) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(results, key=lambda x: (x.get("year", 0), x.get("arm", ""))):
        lines.append(
            f"| {r.get('year','?')} | {r.get('arm','?')} | "
            f"{(r.get('sharpe') or float('nan')):.4f} | "
            f"{(r.get('cagr_pct') or float('nan')):.3f} | "
            f"{(r.get('max_drawdown_pct') or float('nan')):.3f} | "
            f"{(r.get('turnover_frac_equity') or float('nan')):.4f} | "
            f"{(r.get('return_skew') or float('nan')):.3f} | "
            f"{int(r.get('total_trades') or 0)} | "
            f"{(r.get('trades_canon_md5') or '?')[:12]} | "
            f"{r.get('wall_time_seconds', 0)} |"
        )
    output_md.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=str, default="2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024",
                        help="Comma-separated years to run (default: 12-yr 2013-2024 window).")
    parser.add_argument("--runs", type=int, default=1, help="Reps per (arm, year). 1 = single rep.")
    parser.add_argument("--arms", type=str, default="arm0_off,arm1_b20,arm2_b25",
                        help="Comma-separated arm names to run (default: all 3).")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs" / "Audit" / "no_trade_band_h_band_t098_2026_05_31.json",
                        help="JSON output path.")
    parser.add_argument("--output-md", type=Path,
                        default=ROOT / "docs" / "Audit" / "no_trade_band_h_band_t098_2026_05_31.md",
                        help="Markdown report path.")
    parser.add_argument("--canon-only", action="store_true",
                        help="Smoke test: produce canon_md5 only, skip aggregation.")
    args = parser.parse_args()

    if os.environ.get("PYTHONHASHSEED") != "0":
        print("[WARN] PYTHONHASHSEED is not 0 — determinism not guaranteed.", file=sys.stderr)

    years = [int(y) for y in args.years.split(",") if y.strip()]
    arms_filter = {a.strip() for a in args.arms.split(",") if a.strip()}
    arms = [a for a in ARMS if a["name"] in arms_filter]
    if not arms:
        print(f"[ERROR] no matching arms after filter: {args.arms}", file=sys.stderr)
        return 2

    if not ISOLATED_ANCHOR.exists():
        print(f"[ERROR] anchor missing at {ISOLATED_ANCHOR}; run scripts/run_isolated.py --save-anchor first.",
              file=sys.stderr)
        return 2

    results: List[dict] = []
    total_cells = len(years) * len(arms) * args.runs
    cell_i = 0
    t_run_start = time.time()
    for arm in arms:
        with patched_portfolio_cfg(arm):
            for year in years:
                for rep in range(args.runs):
                    cell_i += 1
                    print(f"\n[T-098] === CELL {cell_i}/{total_cells} :: arm={arm['name']} year={year} rep={rep+1}/{args.runs} ===",
                          flush=True)
                    try:
                        with isolated():
                            record = _run_cell(year, arm)
                        record["rep"] = rep
                    except Exception as e:
                        record = {
                            "year": year, "arm": arm["name"], "rep": rep,
                            "ok": False, "error": f"{type(e).__name__}: {e}",
                            "wall_time_seconds": 0.0,
                        }
                    results.append(record)
                    print(
                        f"[T-098]   sharpe={record.get('sharpe')!r:<8} cagr%={record.get('cagr_pct')!r:<8} "
                        f"mdd%={record.get('max_drawdown_pct')!r:<8} turnover={record.get('turnover_frac_equity')!r:<8} "
                        f"skew={record.get('return_skew')!r:<8} trades={record.get('total_trades')!r:<6} "
                        f"canon={record.get('trades_canon_md5','(none)')[:12]} ({record.get('wall_time_seconds','?')}s)",
                        flush=True,
                    )

    summaries = {} if args.canon_only else _aggregate(results)
    payload = {
        "t_id": "T-2026-05-31-098",
        "title": "H-Band — no-trade band 12-yr A/B",
        "n_cells": len(results),
        "n_failed": sum(1 for r in results if not r.get("ok", True)),
        "wall_time_seconds": round(time.time() - t_run_start, 1),
        "arms": ARMS,
        "summaries": summaries,
        "cells": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\n[T-098] wrote {args.output}", flush=True)
    if not args.canon_only:
        _write_markdown(results, summaries, args.output_md)
        print(f"[T-098] wrote {args.output_md}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
