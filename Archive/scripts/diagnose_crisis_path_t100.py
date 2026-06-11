"""T-2026-06-04-100 — diagnose the existing HMM crisis-de-gross path.

Phase 0 of the kill-switch proposal. **DIAGNOSTIC ONLY — no engine code
edits on disk.** Instruments a 26-yr arm0_off backtest via monkey-
patches that wrap `AdvisoryEngine.generate` and capture per-bar
advisory state. Also computes the filtered/causal HMM `p_crisis`
posterior offline (using the same `HMMRegimeClassifier.predict_proba_at`
method T-089 validated) so we can answer "what would HMM have said?"
even though the live config has it disabled.

Four questions:
  Q1. Is hmm_proba passed into advisory.generate() on the live backtest?
  Q2. Did regime_summary flip to "crisis" in 2008 / 2020 / 2000-02?
  Q3. When crisis fired, did realized gross actually fall?
  Q4. Classify finding as (a) HMM not wired, (b) wired but never crisis,
      or (c) fired but de-gross too weak.

The dispatch allows monkey-patches (throwaway instrumentation that lives
only in this script). It does NOT edit any file under engines/.

Usage:
  PYTHONHASHSEED=0 python -m scripts.diagnose_crisis_path_t100 \\
      --start 2000-01-01 --end 2025-12-31 \\
      --output docs/Audit/crisis_path_diagnostic_t100_2026_06_04.json

Smoke (1 year):
  PYTHONHASHSEED=0 python -m scripts.diagnose_crisis_path_t100 \\
      --start 2008-01-01 --end 2008-12-31 --output /tmp/t100_smoke.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_isolated import (  # noqa: E402
    ISOLATED_ANCHOR,
    TRADES_DIR,
    isolated,
    _find_run_id,
)


# ---------------------------------------------------------------------- #
# Per-bar advisory log (populated by monkey-patched AdvisoryEngine.generate)
# ---------------------------------------------------------------------- #

ADVISORY_LOG: List[dict] = []


def install_advisory_monkeypatch() -> None:
    """Wrap AdvisoryEngine.generate so every per-bar call records its
    inputs + outputs. Throwaway instrumentation; not committed to engine
    code on disk."""
    import engines.engine_e_regime.advisory as adv_mod

    orig_generate = adv_mod.AdvisoryEngine.generate

    def wrapped_generate(
        self,
        axis_states,
        axis_confidences,
        axis_durations,
        flip_counts,
        corr_details=None,
        hmm_proba=None,
    ):
        macro_regime, advisory = orig_generate(
            self,
            axis_states,
            axis_confidences,
            axis_durations,
            flip_counts,
            corr_details=corr_details,
            hmm_proba=hmm_proba,
        )
        ADVISORY_LOG.append({
            "regime_summary": advisory.get("regime_summary"),
            "suggested_exposure_cap": advisory.get("suggested_exposure_cap"),
            "suggested_max_positions": advisory.get("suggested_max_positions"),
            "risk_scalar": advisory.get("risk_scalar"),
            "edge_affinity": advisory.get("edge_affinity"),
            "hmm_proba_was_passed": hmm_proba is not None,
            "hmm_p_benign": (hmm_proba or {}).get("benign"),
            "hmm_p_stressed": (hmm_proba or {}).get("stressed"),
            "hmm_p_crisis": (hmm_proba or {}).get("crisis"),
            "axis_state_correlation": axis_states.get("correlation"),
            "axis_state_volatility": axis_states.get("volatility"),
            "axis_state_trend": axis_states.get("trend"),
            "axis_state_breadth": axis_states.get("breadth"),
            "axis_state_forward_stress": axis_states.get("forward_stress"),
        })
        return macro_regime, advisory

    adv_mod.AdvisoryEngine.generate = wrapped_generate


def install_detect_regime_monkeypatch() -> None:
    """Wrap RegimeDetector.detect_regime so it stamps the timestamp onto
    the most-recent advisory log entry."""
    import engines.engine_e_regime.regime_detector as rd_mod

    orig_detect = rd_mod.RegimeDetector.detect_regime

    def wrapped_detect(self, *args, **kwargs):
        prelog_count = len(ADVISORY_LOG)
        out = orig_detect(self, *args, **kwargs)
        # advisory.generate is called inside detect_regime; if it was
        # called at all, the most recent entry corresponds to this bar.
        if len(ADVISORY_LOG) > prelog_count:
            ts = out.get("timestamp") if isinstance(out, dict) else None
            ADVISORY_LOG[-1]["timestamp"] = str(ts) if ts else None
            # Also surface the macro_regime + hmm_regime block.
            if isinstance(out, dict):
                macro = out.get("macro_regime")
                if isinstance(macro, dict):
                    ADVISORY_LOG[-1]["macro_regime_label"] = macro.get("label")
                elif isinstance(macro, str):
                    ADVISORY_LOG[-1]["macro_regime_label"] = macro
                hmm_regime = out.get("hmm_regime")
                if isinstance(hmm_regime, dict):
                    ADVISORY_LOG[-1]["hmm_regime_argmax"] = hmm_regime.get("argmax")
                    ADVISORY_LOG[-1]["hmm_regime_confidence"] = hmm_regime.get("confidence")
        return out

    rd_mod.RegimeDetector.detect_regime = wrapped_detect


# ---------------------------------------------------------------------- #
# Run the 26-yr arm0_off backtest under isolated()
# ---------------------------------------------------------------------- #

def run_backtest(start: str, end: str) -> Optional[str]:
    """Run a 26-yr arm0_off backtest. Returns the run_id."""
    from orchestration.mode_controller import ModeController

    before = {p.name for p in TRADES_DIR.iterdir() if p.is_dir() and p.name != "backup"}
    with isolated():
        mc = ModeController(ROOT, env="prod")
        mc.run_backtest(
            mode="prod",
            fresh=False,
            no_governor=False,
            reset_governor=True,
            alpha_debug=False,
            override_start=start,
            override_end=end,
        )
    return _find_run_id(before)


def read_snapshot_gross(run_id: str) -> pd.DataFrame:
    """Load portfolio_snapshots.csv → DataFrame with per-bar
    timestamp, cash, market_value, equity, gross_frac = market_value/equity."""
    p = TRADES_DIR / run_id / "portfolio_snapshots.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    if "timestamp" not in df.columns:
        return pd.DataFrame()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in ("cash", "market_value", "equity"):
        if col not in df.columns:
            df[col] = float("nan")
        df[col] = df[col].astype(float)
    df["gross_frac"] = df["market_value"] / df["equity"].replace(0, np.nan)
    return df[["timestamp", "cash", "market_value", "equity", "gross_frac"]]


# ---------------------------------------------------------------------- #
# Side-channel: offline filtered HMM p_crisis per date
# ---------------------------------------------------------------------- #

def compute_offline_hmm_p_crisis(
    start: str, end: str,
) -> pd.DataFrame:
    """Build the HMM feature panel + drive HMMRegimeClassifier.predict_proba_at
    (filtered/causal — the T-089 path) on every date in [start, end].

    This shows what hmm_proba['crisis'] WOULD HAVE BEEN if the live
    config had `hmm_enabled=True`. Independent of whether HMM was enabled
    in the backtest run.
    """
    try:
        from engines.engine_e_regime.hmm_classifier import HMMRegimeClassifier
        from engines.engine_e_regime import macro_features as mf
    except Exception as exc:
        print(f"[T-100] could not import HMM modules: {exc}", file=sys.stderr)
        return pd.DataFrame()

    # Load the same model the live config would have used.
    model_path = ROOT / "engines" / "engine_e_regime" / "models" / "hmm_3state_v1.pkl"
    if not model_path.exists():
        print(f"[T-100] HMM model missing at {model_path}", file=sys.stderr)
        return pd.DataFrame()

    try:
        clf = HMMRegimeClassifier.load(str(model_path))
    except Exception as exc:
        print(f"[T-100] HMM load failed: {exc}", file=sys.stderr)
        return pd.DataFrame()

    # Build the feature panel for [start, end] — same path the live
    # detector uses internally.
    try:
        panel = mf.build_feature_panel(
            start=start, end=end,
        )
    except Exception as exc:
        print(f"[T-100] feature panel build failed: {exc}", file=sys.stderr)
        return pd.DataFrame()

    if panel is None or panel.empty:
        return pd.DataFrame()

    out_rows = []
    for ts in panel.index:
        try:
            row = mf.latest_feature_row(panel, pd.Timestamp(ts))
        except Exception:
            continue
        if row is None:
            continue
        try:
            proba = clf.predict_proba_at(row, history_panel=panel)
        except Exception:
            continue
        if not proba:
            continue
        out_rows.append({
            "timestamp": pd.Timestamp(ts),
            "hmm_p_benign_offline": proba.get("benign"),
            "hmm_p_stressed_offline": proba.get("stressed"),
            "hmm_p_crisis_offline": proba.get("crisis"),
        })
    return pd.DataFrame(out_rows)


# ---------------------------------------------------------------------- #
# Analysis
# ---------------------------------------------------------------------- #

def analyze(
    df_adv: pd.DataFrame,
    df_snap: pd.DataFrame,
    df_hmm: pd.DataFrame,
) -> dict:
    """Cross-join + summary stats per year + crisis-bar / benign-bar
    comparison. Returns the analysis dict."""
    # Normalize timestamps to dates so the join is exact.
    if not df_adv.empty:
        df_adv = df_adv.copy()
        df_adv["timestamp"] = pd.to_datetime(df_adv["timestamp"])
        df_adv["date"] = df_adv["timestamp"].dt.date
    if not df_snap.empty:
        df_snap = df_snap.copy()
        df_snap["date"] = df_snap["timestamp"].dt.date
    if not df_hmm.empty:
        df_hmm = df_hmm.copy()
        df_hmm["date"] = df_hmm["timestamp"].dt.date

    # Build a unified daily frame.
    joined = pd.DataFrame()
    if not df_adv.empty:
        joined = df_adv.groupby("date").last().reset_index()
    if not df_snap.empty:
        joined = joined.merge(
            df_snap.groupby("date").last().reset_index()[
                ["date", "cash", "market_value", "equity", "gross_frac"]
            ],
            on="date", how="left",
        ) if not joined.empty else df_snap.groupby("date").last().reset_index()
    if not df_hmm.empty:
        joined = joined.merge(
            df_hmm.groupby("date").last().reset_index()[
                ["date", "hmm_p_benign_offline", "hmm_p_stressed_offline", "hmm_p_crisis_offline"]
            ],
            on="date", how="left",
        ) if not joined.empty else df_hmm.groupby("date").last().reset_index()

    if joined.empty:
        return {"error": "no joinable per-bar data captured"}

    joined["year"] = pd.to_datetime(joined["date"]).dt.year

    # Did hmm_proba EVER get passed to advisory.generate in the live run?
    hmm_proba_was_passed_any = (
        bool(joined.get("hmm_proba_was_passed", pd.Series([False])).any())
        if "hmm_proba_was_passed" in joined.columns else False
    )

    # Per-year crisis-bar counts (live regime_summary == "crisis")
    per_year = []
    crisis_years = {2000, 2001, 2002, 2008, 2009, 2020}
    for year, sub in joined.groupby("year"):
        n_bars = len(sub)
        n_live_crisis = int((sub.get("regime_summary") == "crisis").sum()) if "regime_summary" in sub else 0
        n_live_stressed = int((sub.get("regime_summary") == "stressed").sum()) if "regime_summary" in sub else 0
        # Offline HMM p_crisis high (>= 0.50 nominal, also report 0.70)
        n_hmm_p050 = int((sub.get("hmm_p_crisis_offline", pd.Series(dtype=float)) >= 0.50).sum()) if "hmm_p_crisis_offline" in sub else 0
        n_hmm_p070 = int((sub.get("hmm_p_crisis_offline", pd.Series(dtype=float)) >= 0.70).sum()) if "hmm_p_crisis_offline" in sub else 0
        # Gross in crisis vs benign bars (live regime_summary)
        crisis_mask = sub.get("regime_summary") == "crisis" if "regime_summary" in sub else None
        if crisis_mask is not None and "gross_frac" in sub.columns:
            gross_crisis = float(sub.loc[crisis_mask, "gross_frac"].mean()) if crisis_mask.any() else float("nan")
            gross_benign = float(sub.loc[~crisis_mask, "gross_frac"].mean()) if (~crisis_mask).any() else float("nan")
        else:
            gross_crisis, gross_benign = float("nan"), float("nan")

        per_year.append({
            "year": int(year),
            "n_bars": n_bars,
            "n_live_crisis": n_live_crisis,
            "n_live_stressed": n_live_stressed,
            "n_hmm_p_crisis_ge_050": n_hmm_p050,
            "n_hmm_p_crisis_ge_070": n_hmm_p070,
            "mean_gross_crisis": gross_crisis,
            "mean_gross_benign": gross_benign,
            "mean_exposure_cap": float(sub.get("suggested_exposure_cap", pd.Series(dtype=float)).mean()) if "suggested_exposure_cap" in sub else float("nan"),
            "min_exposure_cap": float(sub.get("suggested_exposure_cap", pd.Series(dtype=float)).min()) if "suggested_exposure_cap" in sub else float("nan"),
            "mean_risk_scalar": float(sub.get("risk_scalar", pd.Series(dtype=float)).mean()) if "risk_scalar" in sub else float("nan"),
            "min_risk_scalar": float(sub.get("risk_scalar", pd.Series(dtype=float)).min()) if "risk_scalar" in sub else float("nan"),
            "mean_max_positions": float(sub.get("suggested_max_positions", pd.Series(dtype=float)).mean()) if "suggested_max_positions" in sub else float("nan"),
            "min_max_positions": float(sub.get("suggested_max_positions", pd.Series(dtype=float)).min()) if "suggested_max_positions" in sub else float("nan"),
            "is_known_crisis_year": int(year) in crisis_years,
        })

    # Aggregate: live crisis bars vs benign bars (whole span)
    if "regime_summary" in joined and "gross_frac" in joined:
        crisis_mask = joined["regime_summary"] == "crisis"
        agg = {
            "total_bars": int(len(joined)),
            "total_live_crisis_bars": int(crisis_mask.sum()),
            "total_live_stressed_bars": int((joined["regime_summary"] == "stressed").sum()),
            "total_live_benign_bars": int((joined["regime_summary"] == "benign").sum()),
            "total_live_cautious_bars": int((joined["regime_summary"] == "cautious").sum()),
            "mean_gross_crisis": float(joined.loc[crisis_mask, "gross_frac"].mean()) if crisis_mask.any() else float("nan"),
            "mean_gross_benign": float(joined.loc[~crisis_mask, "gross_frac"].mean()) if (~crisis_mask).any() else float("nan"),
            "delta_gross_crisis_vs_benign": (
                float(joined.loc[crisis_mask, "gross_frac"].mean()) - float(joined.loc[~crisis_mask, "gross_frac"].mean())
            ) if (crisis_mask.any() and (~crisis_mask).any()) else float("nan"),
            "mean_exposure_cap_crisis": float(joined.loc[crisis_mask, "suggested_exposure_cap"].mean()) if (crisis_mask.any() and "suggested_exposure_cap" in joined) else float("nan"),
            "mean_exposure_cap_benign": float(joined.loc[~crisis_mask, "suggested_exposure_cap"].mean()) if ((~crisis_mask).any() and "suggested_exposure_cap" in joined) else float("nan"),
            "mean_risk_scalar_crisis": float(joined.loc[crisis_mask, "risk_scalar"].mean()) if (crisis_mask.any() and "risk_scalar" in joined) else float("nan"),
            "mean_risk_scalar_benign": float(joined.loc[~crisis_mask, "risk_scalar"].mean()) if ((~crisis_mask).any() and "risk_scalar" in joined) else float("nan"),
        }
    else:
        agg = {"error": "no regime_summary or gross_frac in joined frame"}

    # HMM offline aggregate
    if "hmm_p_crisis_offline" in joined and joined["hmm_p_crisis_offline"].notna().any():
        agg["hmm_offline_max_p_crisis"] = float(joined["hmm_p_crisis_offline"].max())
        agg["hmm_offline_mean_p_crisis"] = float(joined["hmm_p_crisis_offline"].mean())
        agg["hmm_offline_bars_p_ge_050"] = int((joined["hmm_p_crisis_offline"] >= 0.50).sum())
        agg["hmm_offline_bars_p_ge_070"] = int((joined["hmm_p_crisis_offline"] >= 0.70).sum())

    return {
        "hmm_proba_was_passed_in_live_run_any_bar": hmm_proba_was_passed_any,
        "aggregate": agg,
        "per_year": per_year,
    }


# ---------------------------------------------------------------------- #
# Driver
# ---------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=str, default="2000-01-01",
                        help="Start date for the 26-yr arm0_off backtest.")
    parser.add_argument("--end", type=str, default="2025-12-31",
                        help="End date.")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs" / "Audit" / "crisis_path_diagnostic_t100_2026_06_04.json",
                        help="JSON output path for the analysis.")
    parser.add_argument("--per-bar-csv", type=Path,
                        default=ROOT / "docs" / "Audit" / "crisis_path_diagnostic_t100_per_bar.csv",
                        help="CSV output path for the per-bar joined frame.")
    parser.add_argument("--skip-backtest", action="store_true",
                        help="Skip the backtest run (re-use the most recent in TRADES_DIR + offline HMM).")
    parser.add_argument("--skip-hmm", action="store_true",
                        help="Skip offline HMM side-channel.")
    args = parser.parse_args()

    if os.environ.get("PYTHONHASHSEED") != "0":
        print("[T-100][WARN] PYTHONHASHSEED is not 0; determinism not guaranteed.",
              file=sys.stderr)

    if not ISOLATED_ANCHOR.exists():
        print(f"[T-100] ERROR: anchor missing at {ISOLATED_ANCHOR}. "
              "Run `python -m scripts.run_isolated --save-anchor` first.",
              file=sys.stderr)
        return 2

    t_start = time.time()

    # Phase A: instrumented backtest
    if args.skip_backtest:
        print("[T-100] --skip-backtest: trying to re-use the most recent run_id "
              "from TRADES_DIR (advisory log will be EMPTY without a fresh run).",
              flush=True)
        cands = [p for p in TRADES_DIR.iterdir() if p.is_dir() and p.name != "backup"]
        cands.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        run_id = cands[0].name if cands else None
        if run_id is None:
            print("[T-100] ERROR: no run dirs in TRADES_DIR", file=sys.stderr)
            return 2
        print(f"[T-100] reusing run_id={run_id}", flush=True)
    else:
        print(f"[T-100] installing AdvisoryEngine + RegimeDetector monkey-patches", flush=True)
        install_advisory_monkeypatch()
        install_detect_regime_monkeypatch()
        print(f"[T-100] running 26-yr arm0_off: {args.start} → {args.end}", flush=True)
        run_id = run_backtest(args.start, args.end)
        print(f"[T-100] backtest done: run_id={run_id} "
              f"(advisory log rows={len(ADVISORY_LOG)})", flush=True)

    df_adv = pd.DataFrame(ADVISORY_LOG)
    df_snap = read_snapshot_gross(run_id) if run_id else pd.DataFrame()
    print(f"[T-100] snapshot rows={len(df_snap)}", flush=True)

    # Phase B: offline HMM side-channel
    df_hmm = pd.DataFrame()
    if not args.skip_hmm:
        print(f"[T-100] computing offline HMM p_crisis over {args.start} → {args.end}",
              flush=True)
        t_hmm = time.time()
        df_hmm = compute_offline_hmm_p_crisis(args.start, args.end)
        print(f"[T-100] offline HMM done: {len(df_hmm)} dates in "
              f"{time.time() - t_hmm:.1f}s", flush=True)

    # Phase C: analysis
    print(f"[T-100] running analysis", flush=True)
    result = analyze(df_adv, df_snap, df_hmm)
    result["run_id"] = run_id
    result["start"] = args.start
    result["end"] = args.end
    result["wall_time_seconds"] = round(time.time() - t_start, 1)
    result["advisory_log_rows"] = int(len(df_adv))
    result["snapshot_rows"] = int(len(df_snap))
    result["hmm_offline_rows"] = int(len(df_hmm))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=str))
    print(f"[T-100] wrote {args.output}", flush=True)

    # Save the per-bar joined frame as CSV for downstream analysis.
    if not df_adv.empty or not df_snap.empty:
        df_adv2 = df_adv.copy()
        if "timestamp" in df_adv2.columns:
            df_adv2["timestamp"] = pd.to_datetime(df_adv2["timestamp"])
            df_adv2["date"] = df_adv2["timestamp"].dt.date
            df_adv2 = df_adv2.groupby("date").last().reset_index()
        df_snap2 = df_snap.copy()
        if not df_snap2.empty:
            df_snap2["date"] = df_snap2["timestamp"].dt.date
            df_snap2 = df_snap2.groupby("date").last().reset_index()
            df_adv2 = df_adv2.merge(df_snap2, on="date", how="outer")
        if not df_hmm.empty:
            df_hmm2 = df_hmm.copy()
            df_hmm2["date"] = df_hmm2["timestamp"].dt.date
            df_hmm2 = df_hmm2.groupby("date").last().reset_index()
            df_adv2 = df_adv2.merge(df_hmm2, on="date", how="outer")
        args.per_bar_csv.parent.mkdir(parents=True, exist_ok=True)
        df_adv2.to_csv(args.per_bar_csv, index=False)
        print(f"[T-100] wrote {args.per_bar_csv} ({len(df_adv2)} rows)", flush=True)

    print(f"[T-100] total wall {time.time() - t_start:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
