"""T-260-deep — DEEP re-verify of the multi-speed ensemble selection (T-306 substrate).

Pre-registration (director-FROZEN 2026-07-27, no amendment):
docs/Sources/prereg_deep_reverify_speeds_t260.md. N_trials += 1 (one family).

Re-verifies T-260's three shallow-window claims on 58-64yr:
 (1) spec-selection risk is material (Sortino range 0.401 across 4-10mo singles),
 (2) ensemble {2,5,10} vs single 5mo: ΔSortino CI [-0.023,+0.207] — DIRECTIONAL,
     NOT significant  ← the deep window RESOLVES this,
 (3) the ensemble is a ROBUSTNESS choice, not a significant-lift claim.

*** THE HARD PRE-COMMITMENT (frozen, quoted in the freeze block) ***
NO RE-SELECTION. The deployed {42,105,210} is FROZEN and does not change whatever
this run shows. The speed grid is CHARACTERIZATION ONLY — it quantifies spec-luck;
it is NOT a menu. A higher-scoring triple is REPORTED AS SPEC-SELECTION RISK, never
adopted: re-selecting on now-seen data would be the free-parameter fit that killed
MetaLearner/HRP/concentration, and it would contaminate T-314's baseline (this exact
spec). This script therefore contains NO selection step, by construction.

Reuses the T-311 code path verbatim (substrate loader, fair conventions, paired
block-bootstrap) so the two re-verifications cannot drift apart.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.deep_reverify_sleeve_t311 import (                          # noqa: E402
    load_substrate, maxdd, cagr, sortino, sharpe,
    ci_low_sortino, paired, ER, TXN, TD,
)

OUT = ROOT / "data/research/t260_deep_reverify.json"
DEPLOYED = [42, 105, 210]          # THE FROZEN SPEC — never re-selected here
COMPARATOR = 105                   # the single 5mo the shallow-window CI used
GRID = [21, 42, 63, 84, 105, 126, 147, 168, 189, 210, 252]   # pre-registered
N_TRIALS = 77                      # honest-N after this trial


def _pos(px: pd.Series, speeds) -> pd.Series:
    """Mean of binary long/flat signals across `speeds`, lagged 1d (causal, T-273)."""
    sig = [(px > px.rolling(s).mean()).astype(float) for s in speeds]
    return pd.concat(sig, axis=1).mean(axis=1).shift(1)


def sleeve(legs: dict, cash: pd.Series, speeds) -> pd.Series:
    """EW long/flat sleeve at the given speed set — T-255 fair conventions."""
    n = len(legs)
    tot = None
    for name, px in legs.items():
        pos = _pos(px, speeds)
        r = pos * (px.pct_change() - ER[name] / TD) + (1 - pos) * cash
        r = r - pos.diff().abs().fillna(0) * (1.0 / n) * TXN
        tot = r / n if tot is None else tot + r / n
    return tot.dropna()


def run(label: str, assets: list) -> dict:
    legs, cash = load_substrate(assets)
    ens = sleeve(legs, cash, DEPLOYED)
    singles = {s: sleeve(legs, cash, [s]) for s in GRID}
    start = max([ens.index.min()] + [v.index.min() for v in singles.values()])
    end = min([ens.index.max()] + [v.index.max() for v in singles.values()])
    cut = lambda x: x[(x.index >= start) & (x.index <= end)].dropna()      # noqa: E731
    ens, singles = cut(ens), {s: cut(v) for s, v in singles.items()}
    yrs = (end - start).days / 365.25

    def row(r):
        eq = (1 + r).cumprod()
        return {"sortino": sortino(r), "sortino_ci_low": ci_low_sortino(r),
                "sharpe": sharpe(r), "cagr": cagr(eq), "maxdd": maxdd(eq),
                "terminal_10k": float(10000 * eq.iloc[-1] / eq.iloc[0])}

    print(f"\n=== {label}: {start.date()} .. {end.date()} ({yrs:.1f} yr) ===")
    e_row = row(ens)
    print(f'{"spec":22}{"Sortino":>9}{"ci_low":>8}{"CAGR":>7}{"MaxDD":>8}{"$10k→":>13}')
    print(f'{"ENSEMBLE {2,5,10} *":22}{e_row["sortino"]:>9.3f}{e_row["sortino_ci_low"]:>8.3f}'
          f'{e_row["cagr"]*100:>6.1f}%{e_row["maxdd"]*100:>7.1f}%{e_row["terminal_10k"]:>13,.0f}')
    s_rows = {}
    for s in GRID:
        s_rows[s] = row(singles[s])
        print(f'{"single " + str(s) + "d":22}{s_rows[s]["sortino"]:>9.3f}'
              f'{s_rows[s]["sortino_ci_low"]:>8.3f}{s_rows[s]["cagr"]*100:>6.1f}%'
              f'{s_rows[s]["maxdd"]*100:>7.1f}%{s_rows[s]["terminal_10k"]:>13,.0f}')

    # --- PRIMARY GATE: ensemble − single 5mo (the shallow window's near-miss) --- #
    p_main = paired(ens, singles[COMPARATOR])
    lo, hi = p_main["dSortino_ci"]
    verdict = ("UPGRADE — significant lift" if lo > 0 else
               ("REFUTED — ensemble is a DRAG (escalate)" if hi < 0 else
                "CONFIRMED AS-IS — robustness choice, now SETTLED (not pending)"))
    print(f'\n--- PRIMARY GATE: ensemble − single {COMPARATOR}d ---')
    print(f'  ΔSortino 95% CI [{lo:+.3f}, {hi:+.3f}]   (shallow window was [-0.023,+0.207])')
    print(f'  Δcompound %/yr  [{p_main["dLogWealthAnn_ci"][0]*100:+.2f}, {p_main["dLogWealthAnn_ci"][1]*100:+.2f}]'
          f'   ΔMaxDD [{p_main["dMaxDD_ci"][0]*100:+.1f}%, {p_main["dMaxDD_ci"][1]*100:+.1f}%]')
    print(f'  ⇒ CLAIM 2: {verdict}')

    # --- secondary: vs each deployed constituent --- #
    print(f'\n--- vs each constituent leg ---')
    p_const = {}
    for s in DEPLOYED:
        p = paired(ens, singles[s])
        p_const[s] = p
        print(f'  ensemble − single {s:>3}d: ΔSortino [{p["dSortino_ci"][0]:+.3f},{p["dSortino_ci"][1]:+.3f}]'
              f'  ΔMaxDD [{p["dMaxDD_ci"][0]*100:+.1f}%,{p["dMaxDD_ci"][1]*100:+.1f}%]')

    # --- CLAIM 1: dispersion (CHARACTERIZATION ONLY — no selection) --- #
    so = {s: s_rows[s]["sortino"] for s in GRID}
    rng_all = max(so.values()) - min(so.values())
    core = [s for s in GRID if 84 <= s <= 210]            # the shallow 4-10mo band
    rng_core = max(so[s] for s in core) - min(so[s] for s in core)
    better = [s for s in GRID if so[s] > e_row["sortino"]]
    pct = 100.0 * sum(1 for s in GRID if e_row["sortino"] >= so[s]) / len(GRID)
    cagrs = [s_rows[s]["cagr"] for s in GRID]
    print(f'\n--- CLAIM 1: spec-selection dispersion (CHARACTERIZATION ONLY, no re-selection) ---')
    print(f'  Sortino range across grid {rng_all:.3f}  |  4-10mo band {rng_core:.3f}  '
          f'(shallow window: 0.401)')
    print(f'  CAGR spread across grid {(max(cagrs)-min(cagrs))*1e4:.0f} bps/yr '
          f'(shallow claim: 100-350 bps/yr is spec-selection)')
    print(f'  deployed ensemble percentile vs singles: {pct:.0f}th  |  '
          f'singles beating it on Sortino: {better if better else "NONE"}')
    print(f'  >>> PRE-COMMITMENT HONORED: spec stays {DEPLOYED} regardless. '
          f'The above is risk quantification, NOT a menu.')

    mbl = math.sqrt(2 * math.log(N_TRIALS) / yrs)
    print(f'\nMBL/DSR: N={N_TRIALS}, {yrs:.0f}yr → required Sharpe {mbl:.3f}; '
          f'ensemble Sharpe {e_row["sharpe"]:.3f} '
          f'({"CLEARS" if e_row["sharpe"] > mbl else "FAILS"})')
    return {"label": label, "window": [str(start.date()), str(end.date())], "years": yrs,
            "ensemble": e_row, "singles": {str(k): v for k, v in s_rows.items()},
            "primary_gate": p_main, "claim2_verdict": verdict,
            "constituents": {str(k): v for k, v in p_const.items()},
            "dispersion": {"sortino_range_grid": rng_all, "sortino_range_4_10mo": rng_core,
                           "cagr_spread_bps": (max(cagrs) - min(cagrs)) * 1e4,
                           "deployed_percentile": pct, "singles_beating_deployed": better},
            "mbl_required_sharpe": mbl, "n_trials": N_TRIALS,
            "reselection_performed": False}


def main() -> int:
    out = {"primary_2asset": run("PRIMARY — D-A 2-asset (equity+bond)", ["equity", "bond"]),
           "secondary_3asset": run("SECONDARY — D-B 3-asset", ["equity", "bond", "gold"])}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
