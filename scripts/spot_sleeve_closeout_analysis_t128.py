"""T-128 spot-sleeve close-out analysis — the definitive 16/26-yr integrated A/B.

Pulls the 6-cell campaign results (t128-spot-sleeve-closeout) from S3,
computes per-arm metrics and the pre-registered decision gate:

    recommend the sleeve iff
        (a) Sharpe-ci_low on the DIFFERENCE (ON - OFF daily returns)
            is NOT below 0 at depth, AND
        (b) 26-yr MDD reduction >= 15%, AND
        (c) the 2022-style crisis-year reversal does NOT reproduce at depth.

Metrics per arm x window:
    Sharpe, CAGR, MDD, crisis-year (2008/2020/2022) sub-returns,
    calm-stretch Sharpe (all days excluding the 3 crisis years).
Differences vs arm0 with block-bootstrap CI (block=7, n_iter=1000,
seed=42 — same parameters as T-115 for comparability).

Usage:
    python scripts/spot_sleeve_closeout_analysis_t128.py \
        --campaign-json data/cloud_runs/t128-spot-sleeve-closeout_<ts>.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
TRADING_DAYS = 252
CRISIS_YEARS = [2008, 2020, 2022]
BOOT_ITER = 1000
BOOT_BLOCK = 7
BOOT_SEED = 42


def fetch_snapshots(s3_prefix: str, dest: Path) -> pd.DataFrame:
    dest.mkdir(parents=True, exist_ok=True)
    local = dest / "portfolio_snapshots.csv"
    if not local.exists():
        subprocess.run(
            ["aws", "s3", "cp", f"{s3_prefix}/portfolio_snapshots.csv",
             str(local), "--profile", "archondex"],
            check=True, capture_output=True,
        )
    df = pd.read_csv(local)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def daily_returns(df: pd.DataFrame) -> pd.Series:
    eq = df.set_index("timestamp")["equity"].astype(float)
    rets = eq.pct_change().dropna()
    return rets


def sharpe(rets: pd.Series) -> float:
    if len(rets) < 2:
        return float("nan")
    sd = rets.std(ddof=1)
    if sd is None or sd < 1e-12 or not np.isfinite(sd):
        return 0.0
    return float(rets.mean() / sd * np.sqrt(TRADING_DAYS))


def cagr(df: pd.DataFrame) -> float:
    eq = df.set_index("timestamp")["equity"].astype(float)
    n_years = (eq.index[-1] - eq.index[0]).days / 365.25
    if n_years <= 0 or eq.iloc[0] <= 0:
        return float("nan")
    return float((eq.iloc[-1] / eq.iloc[0]) ** (1 / n_years) - 1)


def max_drawdown(df: pd.DataFrame) -> float:
    eq = df.set_index("timestamp")["equity"].astype(float)
    peak = eq.cummax()
    dd = (eq - peak) / peak
    return float(dd.min())


def year_return(df: pd.DataFrame, year: int) -> float:
    eq = df.set_index("timestamp")["equity"].astype(float)
    yr = eq[eq.index.year == year]
    if len(yr) < 2:
        return float("nan")
    return float(yr.iloc[-1] / yr.iloc[0] - 1)


def block_bootstrap_ci(diff: pd.Series, n_iter: int = BOOT_ITER,
                       block: int = BOOT_BLOCK, seed: int = BOOT_SEED):
    """Block bootstrap on the DIFFERENCE series; returns (ci_low, ci_high)
    of the annualized Sharpe of the difference. Same parameters as the
    T-115 sweep (block=7, n_iter=1000, seed=42) for comparability."""
    rng = np.random.default_rng(seed)
    vals = diff.values
    n = len(vals)
    if n < block * 2:
        return float("nan"), float("nan")
    n_blocks = int(np.ceil(n / block))
    stats: List[float] = []
    for _ in range(n_iter):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([vals[s:s + block] for s in starts])[:n]
        sd = sample.std(ddof=1)
        if sd < 1e-12 or not np.isfinite(sd):
            stats.append(0.0)
        else:
            stats.append(float(sample.mean() / sd * np.sqrt(TRADING_DAYS)))
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(lo), float(hi)


def analyze(campaign_json: Path) -> Dict:
    camp = json.loads(campaign_json.read_text())
    cells = {}
    cache = REPO / "data/cloud_runs/t128_cells"
    for c in camp["cells"]:
        if c["status"] != "SUCCEEDED":
            print(f"[warn] {c['cell_id']} status={c['status']} — skipped")
            continue
        run_prefix = c["manifest"]["s3_prefix"]
        key = (c["arm"], c["window_label"])
        cells[key] = {
            "df": fetch_snapshots(run_prefix, cache / c["arm"] / c["window_label"]),
            "canon": c["manifest"].get("canon_md5"),
            "sharpe_reported": c["manifest"].get("sharpe"),
        }

    out: Dict = {"task": "T-2026-06-10-128", "windows": {}}
    for window in ["2010-2025", "2000-2025"]:
        base = cells.get(("arm0_off", window))
        if base is None:
            continue
        base_rets = daily_returns(base["df"])
        wres = {"arm0_off": {
            "canon": base["canon"],
            "sharpe": sharpe(base_rets),
            "cagr": cagr(base["df"]),
            "mdd": max_drawdown(base["df"]),
            "crisis_years": {y: year_return(base["df"], y) for y in CRISIS_YEARS},
            "calm_sharpe": sharpe(base_rets[~base_rets.index.year.isin(CRISIS_YEARS)]),
        }}
        for arm in ["arm1_on_25pct", "arm2_on_30pct"]:
            cell = cells.get((arm, window))
            if cell is None:
                continue
            rets = daily_returns(cell["df"])
            # Align on common dates for the paired difference
            common = rets.index.intersection(base_rets.index)
            diff = (rets.loc[common] - base_rets.loc[common]).dropna()
            ci_lo, ci_hi = block_bootstrap_ci(diff)
            mdd_on, mdd_off = max_drawdown(cell["df"]), wres["arm0_off"]["mdd"]
            wres[arm] = {
                "canon": cell["canon"],
                "sharpe": sharpe(rets),
                "cagr": cagr(cell["df"]),
                "mdd": mdd_on,
                "mdd_reduction_rel": (abs(mdd_off) - abs(mdd_on)) / abs(mdd_off) if mdd_off else float("nan"),
                "mdd_reduction_abs_pp": (abs(mdd_off) - abs(mdd_on)) * 100,
                "sharpe_delta": sharpe(rets) - wres["arm0_off"]["sharpe"],
                "diff_sharpe_ci_low": ci_lo,
                "diff_sharpe_ci_high": ci_hi,
                "crisis_years": {y: year_return(cell["df"], y) for y in CRISIS_YEARS},
                "calm_sharpe": sharpe(rets[~rets.index.year.isin(CRISIS_YEARS)]),
                "calm_sharpe_delta": (sharpe(rets[~rets.index.year.isin(CRISIS_YEARS)])
                                      - wres["arm0_off"]["calm_sharpe"]),
            }
        out["windows"][window] = wres

    # ---- pre-registered decision gate (26-yr window, 25% arm primary) ----
    w26 = out["windows"].get("2000-2025", {})
    arm1 = w26.get("arm1_on_25pct")
    arm0 = w26.get("arm0_off")
    if arm1 and arm0:
        ci_ok = arm1["diff_sharpe_ci_low"] >= 0.0
        mdd_ok = arm1["mdd_reduction_rel"] >= 0.15
        # 2022-style reversal at depth: does ON underperform OFF in 2022
        # the way the single-year cells showed (0.464 -> 0.042)?
        rev_2022 = (arm1["crisis_years"].get(2022, float("nan"))
                    < arm0["crisis_years"].get(2022, float("nan")))
        gate = ci_ok and mdd_ok and not rev_2022
        out["decision_gate"] = {
            "ci_low_on_difference_not_down": ci_ok,
            "mdd_reduction_26yr_ge_15pct": mdd_ok,
            "no_2022_reversal_at_depth": not rev_2022,
            "verdict": "RECOMMEND" if gate else "CLOSE-OUT-NEGATIVE",
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign-json", required=True)
    args = ap.parse_args()
    res = analyze(Path(args.campaign_json))
    out = REPO / "docs/Measurements/2026-06/t128_spot_sleeve_closeout.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=2, default=str))
    print(f"\n[T-128] wrote {out}")


if __name__ == "__main__":
    main()
