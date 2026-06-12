"""T-157: re-price T-135's LPS overnight harvest under the SHIPPED
T-146 auction-fill model.

Pure analysis on the T-135 construction — imports build_panels /
build_strategy from scripts/analyze_overnight_intraday_t135 UNCHANGED.
The cost configuration, tax treatment, decision rule, and N-policy were
pre-registered and COMMITTED in
docs/Audit/lps_reprice_auction_t157_2026_06_11.md BEFORE this script
produced any net number.

FIDELITY GATE: the rebuilt overnight component must reproduce the
T-135 artifact's ann_return_pct / ann_vol_pct to >=6 significant
figures before any cost math runs; otherwise the script aborts.

Usage: PYTHONHASHSEED=0 python -m scripts.reprice_lps_auction_t157
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_overnight_intraday_t135 import (  # noqa: E402
    build_panels,
    build_strategy,
)

OUT_DIR = ROOT / "data" / "measurements" / "lps_reprice_t157"
OUT_JSON = OUT_DIR / "lps_reprice_auction_t157.json"

# ---- T-135 artifact fidelity targets (pre-registered) ----
ARTIFACT_ANN_RET = 13.60304523983977   # %
ARTIFACT_ANN_VOL = 18.009753538803963  # %

# ---- Pre-registered cost configuration (bp/day of capital) ----
AUCTION_SAFETY_BP_PER_SIDE = 1.0      # T-146 shipped default
FILLS_PER_DAY_X_CAPITAL = 4.0         # entry 2x + exit 2x
SELLS_PER_DAY_X_CAPITAL = 2.0         # short entry + long exit
SEC_FEE = 27.80 / 1_000_000.0         # AlpacaFeesConfig.sec_fee_per_dollar
TAF_PER_SHARE = 0.000166              # AlpacaFeesConfig.taf_per_share
ASSUMED_SHARE_PRICE = 60.0            # stated assumption
BORROW_PRIMARY_ANN = 0.0030           # 0.30%/yr on 1x short notional
BORROW_SENS_ANN = 0.0100              # 1.00%/yr sensitivity arm
LEGACY_BPS_PER_SIDE = 5.0             # the standing T-135 verdict model

# ---- Tax (pre-registered) ----
ST_TAXABLE_IL = 0.30 + 0.0495         # 34.95% combined
TRADING_DAYS = 252

# ---- Bootstrap (pre-registered) ----
BOOT_BLOCK = 7
BOOT_ITER = 1000
BOOT_SEED = 42


def cost_per_day_decimal(safety_bp_side: float, borrow_ann: float) -> dict:
    """All channels in decimal daily return units (of capital)."""
    safety = safety_bp_side * FILLS_PER_DAY_X_CAPITAL / 1e4
    sec = SEC_FEE * SELLS_PER_DAY_X_CAPITAL
    taf = (TAF_PER_SHARE / ASSUMED_SHARE_PRICE) * SELLS_PER_DAY_X_CAPITAL
    borrow = borrow_ann / TRADING_DAYS  # charged nightly on 1x short
    return {
        "safety": safety, "sec": sec, "taf": taf, "borrow": borrow,
        "total": safety + sec + taf + borrow,
    }


def ann_ret_pct(daily: pd.Series) -> float:
    return float(daily.mean() * TRADING_DAYS * 100)


def ann_vol_pct(daily: pd.Series) -> float:
    return float(daily.std(ddof=1) * np.sqrt(TRADING_DAYS) * 100)


def sharpe(daily: pd.Series) -> float:
    sd = daily.std(ddof=1)
    if sd is None or sd < 1e-12 or not np.isfinite(sd):
        return 0.0
    return float(daily.mean() / sd * np.sqrt(TRADING_DAYS))


def block_bootstrap_ann_ci(daily: pd.Series):
    rng = np.random.default_rng(BOOT_SEED)
    vals = daily.values
    n = len(vals)
    n_blocks = int(np.ceil(n / BOOT_BLOCK))
    stats = []
    for _ in range(BOOT_ITER):
        starts = rng.integers(0, n - BOOT_BLOCK + 1, size=n_blocks)
        sample = np.concatenate([vals[s:s + BOOT_BLOCK] for s in starts])[:n]
        stats.append(sample.mean() * TRADING_DAYS * 100)
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(lo), float(hi)


def account_views(net_daily: pd.Series, label: str) -> dict:
    """Roth (pre-tax) and taxable-IL (annual-netting approximation)."""
    pre = ann_ret_pct(net_daily)
    lo, hi = block_bootstrap_ann_ci(net_daily)
    roth = {
        "net_ann_pct": pre, "ci_low": lo, "ci_high": hi,
        "sharpe": sharpe(net_daily),
        "harvestable_ci_low_gt0": bool(lo > 0),
    }
    # Taxable: scale positive nets by (1 - rate). The CI is scaled the
    # same way when the bound is positive (tax only applies to gains;
    # negative outcomes keep their pre-tax value under full loss offset).
    def _tax(x: float) -> float:
        return x * (1 - ST_TAXABLE_IL) if x > 0 else x
    taxable = {
        "net_ann_pct": _tax(pre), "ci_low": _tax(lo), "ci_high": _tax(hi),
        "harvestable_ci_low_gt0": bool(_tax(lo) > 0),
    }
    return {"label": label, "roth": roth, "taxable_il": taxable}


def main() -> int:
    print("[T157] rebuilding T-135 panels + strategy (unchanged construction)...")
    tot, on, idy = build_panels()
    s_net, s_on, s_id, breadth = build_strategy(tot, on, idy)

    got_ret, got_vol = ann_ret_pct(s_on), ann_vol_pct(s_on)
    print(f"[T157] fidelity: ann_ret {got_ret!r} (target {ARTIFACT_ANN_RET!r})")
    print(f"[T157] fidelity: ann_vol {got_vol!r} (target {ARTIFACT_ANN_VOL!r})")
    if not (np.isclose(got_ret, ARTIFACT_ANN_RET, rtol=1e-6)
            and np.isclose(got_vol, ARTIFACT_ANN_VOL, rtol=1e-6)):
        print("[T157] FIDELITY GATE FAILED — aborting before any cost math.")
        return 1
    print("[T157] FIDELITY GATE PASS — proceeding to pre-registered re-price.")

    arms = {}
    # gross (no costs)
    arms["gross"] = account_views(s_on, "gross overnight component (no costs)")
    # legacy 5bp/side (the standing verdict)
    legacy = cost_per_day_decimal(LEGACY_BPS_PER_SIDE, 0.0)
    # legacy verdict in T-135 used flat per-side cost only (no fees/borrow)
    legacy_total = LEGACY_BPS_PER_SIDE * FILLS_PER_DAY_X_CAPITAL / 1e4
    arms["legacy_5bp"] = account_views(s_on - legacy_total, "legacy flat 5bp/side")
    arms["legacy_5bp"]["cost_per_day_bp"] = legacy_total * 1e4
    # auction primary (0.30%/yr borrow)
    c1 = cost_per_day_decimal(AUCTION_SAFETY_BP_PER_SIDE, BORROW_PRIMARY_ANN)
    arms["auction_primary"] = account_views(s_on - c1["total"],
                                            "auction fills + fees + 0.30%/yr borrow")
    arms["auction_primary"]["cost_channels_bp_per_day"] = {k: v * 1e4 for k, v in c1.items()}
    # auction sensitivity (1.00%/yr borrow)
    c2 = cost_per_day_decimal(AUCTION_SAFETY_BP_PER_SIDE, BORROW_SENS_ANN)
    arms["auction_borrow_sens"] = account_views(s_on - c2["total"],
                                                "auction fills + fees + 1.00%/yr borrow")
    arms["auction_borrow_sens"]["cost_channels_bp_per_day"] = {k: v * 1e4 for k, v in c2.items()}

    harvestable_any = any(
        arms[a][acct]["harvestable_ci_low_gt0"]
        for a in ("auction_primary", "auction_borrow_sens")
        for acct in ("roth", "taxable_il")
    )

    out = {
        "task": "T-2026-06-11-157",
        "n_trials_policy": "N += 0 (pre-registered re-accounting of closed T-135 measurement)",
        "fidelity": {"ann_ret": got_ret, "ann_vol": got_vol,
                     "targets": [ARTIFACT_ANN_RET, ARTIFACT_ANN_VOL], "pass": True},
        "n_obs": int(len(s_on)),
        "arms": arms,
        "binary_answer_harvestable_any_context": bool(harvestable_any),
        "verdict": ("FLIPPED — harvestable in at least one context"
                    if harvestable_any else
                    "UNHARVESTABLE VERDICT SURVIVES the shipped auction-fill model"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"\n[T157] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
