"""T-399 — the defect-corrected re-run of T-315 (static un-gated leverage), ORIGINAL beside CORRECTED.

Pre-declared in amendment 1 of docs/Audit/static_leverage_t315_2026_07_27.md (commit ccd60c8), BEFORE the
fix. The July 2026 run charged the static arms' "annual rebalance" cost every DAY (a PeriodIndex.shift mask
true on every row; ~1.29 %/yr). scripts/offense_campaign_t312_t315.py now charges it once per year-change.

This runner imports the campaign's functions unchanged and reports, for every static arm, window and
haircut:
  ORIGINAL   the July result, reproduced by `static_arm_as_published` (cost every day — the defect, on
             purpose, labelled). FAIL-CLOSED acceptance: it must equal the published tables.
  CORRECTED  `offense_campaign_t312_t315.static_arm` after the fix. The frozen spec, nothing else changed.
  S1         SENSITIVITY — the blended-fee model for L < 2 (SPY + SSO; SSO's ER on the SSO slice only).
  S2         SENSITIVITY — financing from B-5's H.15 / SOFR snapshot instead of the T-306 cash leg,
             on D-B and D-A truncated to 2025-12-31.

N_trials consumed: 0 (director ruling 2026-11-14; the B-5 A2.2 precedent). Standalone; never
BacktestController. Reads data/research/substrate_multidecade/ and data/research/b5/inputs/ (md5-verified);
writes ONLY under --out (default data/t399_local/, worktree-local).

Usage:
  python scripts/t315_static_cost_rerun_t399.py --tag A
  python scripts/t315_static_cost_rerun_t399.py --tag B      # determinism twin; compare results.json md5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import b5_levered_diversified as b5                      # noqa: E402  (import only)
from scripts import offense_campaign_t312_t315 as oc                  # noqa: E402  (the fixed campaign)
from scripts.deep_reverify_sleeve_t311 import ER, TD, cagr, load_substrate, maxdd  # noqa: E402

DEFAULT_OUT = ROOT / "data" / "t399_local"
STATIC_L: Tuple[float, ...] = (1.25, 1.35, 1.5, 1.75, 2.0)
HAIRCUTS: Tuple[Tuple[float, str], ...] = ((0.0, "none"), (0.02, "-2%"), (0.03, "-3%"))
WINDOWS: Tuple[Tuple[str, str], ...] = (("D-B ~58yr (1968+)", "1968-01-01"), ("D-A ~64yr (1962+)", "1962-01-01"),
                                        ("~99yr (1926+)", "1900-01-01"))
S2_END = pd.Timestamp("2025-12-31")
CONTRIB = 7000.0

# ---- the PUBLISHED record the reproduced ORIGINAL must equal (fail-closed acceptance, amendment A1.4) ----
PUB_DB = {  # static_leverage_t315_2026_07_27.md:113-119 — wealth $, CAGR %, MaxDD %, CI (rounded)
    "bar": (3_363_893, 10.50, -55.2, None), 1.25: (1_740_848, 9.26, -68.7, (-371, -7)),
    1.35: (2_067_540, 9.58, -72.5, (-160, 1471)), 1.5: (2_593_908, 10.01, -77.7, (-96, 5417)),
    1.75: (3_482_188, 10.57, -84.5, (-74, 18744)), 2.0: (4_208_246, 10.93, -89.6, (-78, 47392)),
    "glide": (5_865_931, 11.57, -88.3, (-66, 55141)),
}
PUB_HAIRCUT = {  # :137-139 — terminal $10k, D-B
    "none": (3_363_893, {1.25: 1_740_848, 1.35: 2_067_540, 1.5: 2_593_908, 1.75: 3_482_188, 2.0: 4_208_246}),
    "-2%": (1_050_392, {1.25: 406_296, 1.35: 429_514, 1.5: 452_519, 1.75: 454_063, 2.0: 410_131}),
    "-3%": (586_937, {1.25: 196_273, 1.35: 195_755, 1.5: 188_992, 1.75: 163_946, 2.0: 128_018}),
}
PUB_1929 = {  # :149-154 — drawdown %, trough $, years to recover
    "bar": (-84.1, 1594, 12.5), "gated": (-21.6, 7874, 0.0), 1.25: (-91.3, 873, 18.1),
    1.5: (-95.0, 499, 18.4), 1.75: (-97.2, 278, 19.1), 2.0: (-98.5, 152, 20.6),
}
PUB_RACE_M = {"bar": 35.0, 1.25: 23.1, 1.5: 36.5, 2.0: 70.1, "glide": 86.5, "gated": 26.6}   # :175-176, $M
PUB_T312 = {  # deep_reverify_offense_t312_2026_07_27.md:93-95 — bar and gated terminal $
    "D-B ~58yr (1968+)": (3_363_893, 3_294_909), "D-A ~64yr (1962+)": (5_647_734, 7_988_176),
    "~99yr (1926+)": (145.8e6, 1960.9e6),
}


class T399Halt(RuntimeError):
    """A fail-closed halt in the measurement path. Never caught inside the runner."""


# ------------------------------------------------------------------ arms
def static_arm_as_published(eq_ret: pd.Series, cash: pd.Series, L: float) -> pd.Series:
    """THE DEFECT, REPRODUCED ON PURPOSE for the ORIGINAL column: the 0.51 bp cost on EVERY bar.

    Never use this for a measurement. It exists so the July 2026 numbers stay reproducible beside the
    corrected ones; `acceptance()` halts the run unless it equals the published tables."""
    r = oc.lev_daily(eq_ret, cash, L)
    if L > 1.0:
        r = r - pd.Series(oc.SLIP_EQ, index=r.index)
    return r.dropna()


def blend_arm(eq_ret: pd.Series, cash: pd.Series, L: float) -> pd.Series:
    """S1: hold (2-L) of the 1x fund and (L-1) of the 2x fund; SSO's ER on the SSO slice only.

    The expression the gated arm already uses (offense_campaign_t312_t315.gated_t298, the `hi` leg), with
    the corrected once-per-year-change cost."""
    if not 1.0 <= L <= 2.0:
        raise T399Halt(f"blend_arm is defined for 1 <= L <= 2, got {L}")
    r = (2.0 - L) * (eq_ret - ER["equity"] / TD) + (L - 1.0) * oc.lev_daily(eq_ret, cash, 2.0)
    if L > 1.0:
        cost = pd.Series(0.0, index=r.index)
        cost[oc.year_change_mask(r.index)] = oc.SLIP_EQ
        r = r - cost
    return r.dropna()


def b5_cash_argument(eq_px: pd.Series, window: pd.DatetimeIndex, base: pd.Series) -> pd.Series:
    """S2: the `cash` argument that makes lev_daily's `(cash + SPREAD/TD)` equal B-5's daily charge,
    `(base[t-1] + SPREAD) * calendar_days / 360` — B-5's financing_arrays, imported unchanged."""
    i0 = eq_px.index.get_loc(window[0])
    if i0 < 1:
        raise T399Halt("S2 window has no prior close")
    dates = eq_px.index[i0 - 1: i0 + len(window)]
    if not dates[1:].equals(window):
        raise T399Halt("S2 window is not contiguous on the equity calendar")
    b5.fin_gap_check(base, window[0], window[-1])
    r, dcal = b5.financing_arrays(dates, base)
    charge = (r + oc.SPREAD) * dcal / 360.0
    return pd.Series(charge - oc.SPREAD / TD, index=window)


# ------------------------------------------------------------------ statistics
def paired_boot(a: pd.Series, b: pd.Series, years: float, L: int = 21, n: int = 1000, seed: int = 0) -> Dict:
    """oc.paired_dw's draws EXACTLY (same generator, same order, same np.prod), returning the frozen
    paired dwealth CI plus two REPORTED, non-gating reads from the same draws: the CI of d(log growth)
    per year and the share of draws with the arm ahead."""
    j = pd.concat({"a": a, "b": b}, axis=1, sort=True).dropna()
    A, B_ = j["a"].values, j["b"].values
    N = len(A)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(N / L))
    dw, dl = [], []
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb)
        ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        pa, pb = np.prod(1 + A[ix]), np.prod(1 + B_[ix])
        dw.append(pa - pb)
        dl.append((np.log(pa) - np.log(pb)) / years)
    dw_a, dl_a = np.asarray(dw), np.asarray(dl)
    return {"dw_lo": float(np.percentile(dw_a, 2.5)), "dw_hi": float(np.percentile(dw_a, 97.5)),
            "dlog_lo": float(np.percentile(dl_a, 2.5)), "dlog_hi": float(np.percentile(dl_a, 97.5)),
            "p_ahead": float((dw_a > 0).mean())}


def span_years(r: pd.Series) -> float:
    """Calendar years from the first to the last bar (the convention of T-311's `cagr`)."""
    return float((r.index[-1] - r.index[0]).days / 365.25)


def arm_stats(r: pd.Series, bar: pd.Series, boot: bool = True) -> Dict:
    """Terminal wealth, CAGR, MaxDD, d(log growth)/yr vs the bar and (boot=True) the frozen paired CI.
    Halts on a non-finite or too-short series."""
    if not np.isfinite(r.values).all() or len(r) < 250:
        raise T399Halt("non-finite or too-short arm return series")
    e = oc.eqc(r)
    yrs = span_years(bar)
    out = {"wealth": oc.wealth(r), "cagr": cagr(e), "maxdd": maxdd(e), "n": int(len(r)),
           "dlog_per_yr": float((np.log1p(r).sum() - np.log1p(bar.reindex(r.index)).sum()) / yrs)}
    if boot:
        out.update(paired_boot(r, bar, yrs))
        out["verdict"] = ("SIGNIFICANT" if out["dw_lo"] > 0 else ("LOSES" if out["dw_hi"] < 0 else "straddles-0"))
    return out


def accumulate(r: pd.Series, contrib: float = CONTRIB) -> float:
    """The July race, verbatim (offense_campaign_t312_t315.main.accumulate is nested, so it is copied)."""
    bal = 0.0
    yr = None
    for t, x in r.items():
        if yr != t.year:
            bal += contrib
            yr = t.year
        bal *= (1 + x)
    return bal


def crisis_1929(r: pd.Series) -> Dict:
    """The July 1929 read: drawdown and trough from $10,000 over 1929-09..1932-07, years to recover."""
    s = r[(r.index >= "1929-09-01") & (r.index <= "1932-07-31")]
    if len(s) < 5:
        raise T399Halt("the 1929 window is not covered")
    e = oc.eqc(s)
    return {"dd": maxdd(e), "trough": float(10_000 * e.min()), "recover_yrs": oc.years_to_recover(r, "1932-07-31")}


# ------------------------------------------------------------------ the run
def _pair(fn_orig: Callable, fn_corr: Callable, er: pd.Series, cr: pd.Series, bar: pd.Series, L: float,
          boot: bool = True) -> Dict:
    return {"original": arm_stats(fn_orig(er, cr, L), bar, boot), "corrected": arm_stats(fn_corr(er, cr, L), bar, boot)}


def run() -> Dict:
    """Every table of amendment A1.4 and A1.5, then the fail-closed acceptance check."""
    man = b5.verify_snapshot()                       # B-5 inputs AND the T-306 substrate md5s; halts on drift
    legs, cash = load_substrate(["equity"])
    eq_px = legs["equity"]
    eq_ret = eq_px.pct_change().dropna()
    cash = cash.reindex(eq_ret.index).ffill().fillna(0.0)
    res: Dict = {"task": "T-399", "spec": "static_leverage_t315_2026_07_27.md amendment 1 (ccd60c8)",
                 "n_trials_consumed": 0, "span": [str(eq_ret.index[0].date()), str(eq_ret.index[-1].date())],
                 "b5_inputs": {k: v["md5"] for k, v in sorted(man["files"].items())
                               if k in (b5.H15_FILE, b5.SOFR_FILE)},
                 "substrate_md5": dict(sorted(b5.SUBSTRATE_MD5.items())),
                 "bootstrap": {"block": 21, "n": 1000, "seed": 0}, "windows": {}}

    win: Dict[str, Tuple[pd.Series, pd.Series, pd.Series]] = {}
    for wl, start in WINDOWS:
        m = eq_ret.index >= pd.Timestamp(start)
        er, cr = eq_ret[m], cash[m]
        bar = (er - ER["equity"] / TD).dropna()
        win[wl] = (er, cr, bar)
        g, viol, mexp = oc.gated_t298(eq_px, er, cr)
        w: Dict = {"bar": arm_stats(bar, bar, boot=False), "gated": arm_stats(g, bar),
                   "gated_invariant_violations": int(viol), "gated_mean_exposure": float(mexp),
                   "glide": arm_stats(oc.glide_arm(er, cr, 2.0), bar), "static": {}, "s1_blend": {}}
        for L in STATIC_L:
            w["static"][str(L)] = _pair(static_arm_as_published, oc.static_arm, er, cr, bar, L)
            w["s1_blend"][str(L)] = arm_stats(blend_arm(er, cr, L), bar)
        res["windows"][wl] = w
        print(f"  done: {wl}", flush=True)

    e58, c58, bar58 = win["D-B ~58yr (1968+)"]
    e64, c64, _ = win["D-A ~64yr (1962+)"]
    e99, c99, bar99 = win["~99yr (1926+)"]

    # ---- forward-ERP haircuts on D-B: wealth as in July, plus the per-scenario CI the gate text asks for
    res["haircuts"] = {}
    for hc, lab in HAIRCUTS:
        eh = oc.erp_haircut(e58, hc)
        bh = (eh - ER["equity"] / TD).dropna()
        h: Dict = {"bar_wealth": oc.wealth(bh), "static": {}, "s1_blend": {}}
        for L in STATIC_L:
            h["static"][str(L)] = _pair(static_arm_as_published, oc.static_arm, eh, c58, bh, L)
            h["s1_blend"][str(L)] = arm_stats(blend_arm(eh, c58, L), bh)
        res["haircuts"][lab] = h
        print(f"  done: haircut {lab}", flush=True)

    # ---- Kelly: the July reading (CAGR gap) and the erratum (arithmetic mean excess), D-B
    sig = float(e58.std() * np.sqrt(TD))
    erp_gap = float((1 + e58).prod() ** (252 / len(e58)) - 1 - ((1 + c58).prod() ** (252 / len(c58)) - 1))
    mu = float((e58 - c58).mean() * TD)
    res["kelly"] = {"sigma": sig, "cagr_gap": erp_gap, "arith_mean_excess": mu,
                    "rows": {lab: {"july_cagr_gap": (erp_gap - hc) / sig ** 2, "corrected_arithmetic": (mu - hc) / sig ** 2}
                             for hc, lab in HAIRCUTS}}

    # ---- the 1929 path (~99yr window)
    g99 = oc.gated_t298(eq_px, e99, c99)[0]
    res["crisis_1929"] = {"bar": crisis_1929(bar99), "gated": crisis_1929(g99), "static": {}, "s1_blend": {}}
    for L in (1.25, 1.5, 1.75, 2.0):
        res["crisis_1929"]["static"][str(L)] = {"original": crisis_1929(static_arm_as_published(e99, c99, L)),
                                                "corrected": crisis_1929(oc.static_arm(e99, c99, L))}
        res["crisis_1929"]["s1_blend"][str(L)] = crisis_1929(blend_arm(e99, c99, L))

    # ---- cash-rate regime split (D-A window, the July cut)
    res["regime_split"] = {}
    for lab, (a, b) in oc.REGIMES.items():
        m = (e64.index >= pd.Timestamp(a)) & (e64.index <= pd.Timestamp(b))
        er_, cr_ = e64[m], c64[m]
        if len(er_) < 500:
            raise T399Halt(f"regime {lab} too short")
        bar_ = (er_ - ER["equity"] / TD).dropna()
        row: Dict = {"avg_cash": float((1 + cr_).prod() ** (252 / len(cr_)) - 1), "bar_cagr": cagr(oc.eqc(bar_)),
                     "gated_cagr": cagr(oc.eqc(oc.gated_t298(eq_px, er_, cr_)[0])), "static": {}}
        for L in (1.5, 2.0):
            row["static"][str(L)] = {"original": cagr(oc.eqc(static_arm_as_published(er_, cr_, L))),
                                     "corrected": cagr(oc.eqc(oc.static_arm(er_, cr_, L)))}
        res["regime_split"][lab] = row

    # ---- lost-decades overlay (the July graft: -2 %/yr on the final 20 years of D-B)
    jp = e58.copy()
    n20 = int(20 * 252)
    jp.iloc[-n20:] = jp.iloc[-n20:] - (0.02 / TD)
    bj = (jp - ER["equity"] / TD).dropna()
    res["lost_decades"] = {"bar": {"wealth": oc.wealth(bj), "cagr": cagr(oc.eqc(bj))}, "static": {}}
    for L in (1.25, 1.5, 2.0):
        ro, rc = static_arm_as_published(jp, c58, L), oc.static_arm(jp, c58, L)
        res["lost_decades"]["static"][str(L)] = {
            "original": {"wealth": oc.wealth(ro), "cagr": cagr(oc.eqc(ro))},
            "corrected": {"wealth": oc.wealth(rc), "cagr": cagr(oc.eqc(rc))}}

    # ---- the $7k/yr accumulation race (D-B), the glide against the static arms
    res["accumulation_race"] = {"bar": accumulate(bar58), "glide": accumulate(oc.glide_arm(e58, c58, 2.0)),
                                "gated": accumulate(oc.gated_t298(eq_px, e58, c58)[0]), "static": {}, "s1_blend": {}}
    for L in STATIC_L:
        res["accumulation_race"]["static"][str(L)] = {"original": accumulate(static_arm_as_published(e58, c58, L)),
                                                      "corrected": accumulate(oc.static_arm(e58, c58, L))}
        res["accumulation_race"]["s1_blend"][str(L)] = accumulate(blend_arm(e58, c58, L))

    # ---- S2: B-5 H.15 / SOFR financing, D-B and D-A truncated to 2025-12-31
    base = b5.financing_base()
    res["s2_b5_financing"] = {}
    for wl in ("D-B ~58yr (1968+)", "D-A ~64yr (1962+)"):
        er_full, cr_full, _ = win[wl]
        m = er_full.index <= S2_END
        er, cr = er_full[m], cr_full[m]
        bar = (er - ER["equity"] / TD).dropna()
        c2 = b5_cash_argument(eq_px, er.index, base)
        yrs = span_years(er)
        s2: Dict = {"end": str(er.index[-1].date()), "bar": arm_stats(bar, bar, boot=False),
                    "financing_per_yr": {"t306_cash_plus_60bp": float((cr + oc.SPREAD / TD).sum() / yrs),
                                         "b5_base_plus_60bp": float((c2 + oc.SPREAD / TD).sum() / yrs)},
                    "static": {}, "glide": {"t306_cash": arm_stats(oc.glide_arm(er, cr, 2.0), bar),
                                            "b5_financing": arm_stats(oc.glide_arm(er, c2, 2.0), bar)}}
        for L in STATIC_L:
            s2["static"][str(L)] = {"t306_cash": arm_stats(oc.static_arm(er, cr, L), bar),
                                    "b5_financing": arm_stats(oc.static_arm(er, c2, L), bar)}
        res["s2_b5_financing"][wl] = s2
        print(f"  done: S2 {wl}", flush=True)

    acceptance(res)
    return res


# ------------------------------------------------------------------ fail-closed acceptance
def _eq_dollar(x: float, pub: float, what: str, errs: List[str]) -> None:
    if round(x) != pub:
        errs.append(f"{what}: reproduced {x:,.2f} != published {pub:,}")


def acceptance(res: Dict) -> None:
    """The reproduced ORIGINAL must equal the published record, and S1 at 2.0x must equal the corrected
    headline arm. Any miss halts: a reproduction that does not reproduce proves nothing about the defect."""
    errs: List[str] = []
    db = res["windows"]["D-B ~58yr (1968+)"]
    for key, (w, c, dd, ci) in PUB_DB.items():
        s = db["bar"] if key == "bar" else db["glide"] if key == "glide" else db["static"][str(key)]["original"]
        _eq_dollar(s["wealth"], w, f"D-B {key} wealth", errs)
        if round(s["cagr"] * 100, 2) != c:
            errs.append(f"D-B {key} CAGR {s['cagr']*100:.4f} != {c}")
        if round(s["maxdd"] * 100, 1) != dd:
            errs.append(f"D-B {key} MaxDD {s['maxdd']*100:.3f} != {dd}")
        if ci is not None and (round(s["dw_lo"]), round(s["dw_hi"])) != ci:
            errs.append(f"D-B {key} CI [{s['dw_lo']:.2f}, {s['dw_hi']:.2f}] != {ci}")
    for lab, (bw, arms) in PUB_HAIRCUT.items():
        _eq_dollar(res["haircuts"][lab]["bar_wealth"], bw, f"haircut {lab} bar", errs)
        for L, w in arms.items():
            _eq_dollar(res["haircuts"][lab]["static"][str(L)]["original"]["wealth"], w, f"haircut {lab} {L}x", errs)
    for key, (dd, tr, yr) in PUB_1929.items():
        c = res["crisis_1929"]
        s = c[key] if key in ("bar", "gated") else c["static"][str(key)]["original"]
        if (round(s["dd"] * 100, 1), round(s["trough"]), round(s["recover_yrs"], 1)) != (dd, tr, yr):
            errs.append(f"1929 {key}: ({s['dd']*100:.2f}, {s['trough']:.1f}, {s['recover_yrs']:.2f}) != {(dd, tr, yr)}")
    race = res["accumulation_race"]
    for key, pub in PUB_RACE_M.items():
        x = race[key] if key in ("bar", "glide", "gated") else race["static"][str(key)]["original"]
        if round(x / 1e6, 1) != pub:
            errs.append(f"race {key}: ${x/1e6:.3f}M != ${pub}M")
    for wl, (bw, gw) in PUB_T312.items():
        w = res["windows"][wl]
        if bw < 1e8:
            _eq_dollar(w["bar"]["wealth"], bw, f"{wl} bar (T-312)", errs)
            _eq_dollar(w["gated"]["wealth"], gw, f"{wl} gated (T-312)", errs)
        elif (round(w["bar"]["wealth"] / 1e6, 1), round(w["gated"]["wealth"] / 1e6, 1)) != (bw / 1e6, gw / 1e6):
            errs.append(f"{wl} bar/gated (T-312): {w['bar']['wealth']:,.0f} / {w['gated']['wealth']:,.0f}")
    for wl, w in res["windows"].items():           # S1 self-check: at 2.0x the blend IS the fund
        a, b = w["s1_blend"]["2.0"]["wealth"], w["static"]["2.0"]["corrected"]["wealth"]
        if abs(a / b - 1.0) > 1e-9:
            errs.append(f"S1 self-check {wl}: blend 2.0x {a:,.2f} != corrected static 2.0x {b:,.2f}")
    if errs:
        raise T399Halt("acceptance FAILED — nothing may be quoted:\n  " + "\n  ".join(errs))
    res["acceptance"] = "PASS: the reproduced ORIGINAL equals the published T-315 / T-312 record; S1(2.0x) = corrected 2.0x"


# ------------------------------------------------------------------ output
def _ci(s: Dict) -> str:
    return f"[{s['dw_lo']:+,.0f}, {s['dw_hi']:+,.0f}] {s['verdict']}"


def _dl(s: Dict) -> str:
    return f"{s['dlog_per_yr']*100:+.2f} [{s['dlog_lo']*100:+.2f}, {s['dlog_hi']*100:+.2f}]"


def tables_md(res: Dict) -> str:
    """The result dict as markdown tables (headline first, then S1 and S2, each labelled)."""
    o: List[str] = ["# T-399 tables — ORIGINAL (July 2026, cost charged daily) beside CORRECTED (cost once per year-change)",
                    "", f"Acceptance: {res['acceptance']}", ""]
    for wl, w in res["windows"].items():
        o += [f"## Frontier — {wl}", "",
              f"Bar (buy-hold 1x): ${w['bar']['wealth']:,.0f}, CAGR {w['bar']['cagr']*100:.2f}%, MaxDD {w['bar']['maxdd']*100:.1f}%. "
              "dlog = d(log growth) %/yr vs the bar with a 95% CI from the same blocks (reported, non-gating).", "",
              "| arm | ORIGINAL $10k-> | CAGR | dwealth 95% CI | CORRECTED $10k-> | CAGR | MaxDD | dlog %/yr | P(ahead) | dwealth 95% CI (the gate) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for L in STATIC_L:
            a, c = w["static"][str(L)]["original"], w["static"][str(L)]["corrected"]
            o.append(f"| static {L:.2f}x | {a['wealth']:,.0f} | {a['cagr']*100:.2f}% | {_ci(a)} | {c['wealth']:,.0f} | "
                     f"{c['cagr']*100:.2f}% | {c['maxdd']*100:.1f}% | {_dl(c)} | {c['p_ahead']*100:.0f}% | {_ci(c)} |")
        for nm in ("glide", "gated"):
            c = w[nm]
            o.append(f"| {nm} (unaffected) | {c['wealth']:,.0f} | {c['cagr']*100:.2f}% | {_ci(c)} | {c['wealth']:,.0f} | "
                     f"{c['cagr']*100:.2f}% | {c['maxdd']*100:.1f}% | {_dl(c)} | {c['p_ahead']*100:.0f}% | {_ci(c)} |")
        o.append("")
    o += ["## Forward-ERP haircuts — D-B", "",
          "| haircut | arm | bar $ | ORIGINAL $ (x bar) | ORIGINAL CI | CORRECTED $ (x bar) | dlog %/yr | P(ahead) | CORRECTED CI |",
          "|---|---|---|---|---|---|---|---|---|"]
    for lab, h in res["haircuts"].items():
        for L in STATIC_L:
            a, c = h["static"][str(L)]["original"], h["static"][str(L)]["corrected"]
            o.append(f"| {lab} | {L:.2f}x | {h['bar_wealth']:,.0f} | {a['wealth']:,.0f} ({a['wealth']/h['bar_wealth']:.2f}) | {_ci(a)} | "
                     f"{c['wealth']:,.0f} ({c['wealth']/h['bar_wealth']:.2f}) | {_dl(c)} | {c['p_ahead']*100:.0f}% | {_ci(c)} |")
    k = res["kelly"]
    o += ["", "## Kelly — D-B", "",
          f"sigma {k['sigma']*100:.2f}%; CAGR gap {k['cagr_gap']*100:.2f}%; arithmetic mean excess {k['arith_mean_excess']*100:.2f}%.", "",
          "| haircut | July (CAGR gap / sigma^2) | corrected (arithmetic mean excess / sigma^2) |", "|---|---|---|"]
    o += [f"| {lab} | {r['july_cagr_gap']:.2f} | {r['corrected_arithmetic']:.2f} |" for lab, r in k["rows"].items()]
    c29 = res["crisis_1929"]
    o += ["", "## The 1929 path (1929-09 -> 1932-07, from $10,000)", "",
          "| arm | ORIGINAL dd / trough / yrs to recover | CORRECTED dd / trough / yrs to recover |", "|---|---|---|"]
    for nm in ("bar", "gated"):
        s = c29[nm]
        o.append(f"| {nm} (unaffected) | {s['dd']*100:.1f}% / ${s['trough']:,.0f} / {s['recover_yrs']:.1f} | same |")
    for L, d in c29["static"].items():
        a, c = d["original"], d["corrected"]
        o.append(f"| static {float(L):.2f}x | {a['dd']*100:.1f}% / ${a['trough']:,.0f} / {a['recover_yrs']:.1f} | "
                 f"{c['dd']*100:.1f}% / ${c['trough']:,.0f} / {c['recover_yrs']:.1f} |")
    o += ["", "## Cash-rate regime split (CAGR)", "",
          "| era | avg cash | bar | 1.5x ORIGINAL | 1.5x CORRECTED | 2.0x ORIGINAL | 2.0x CORRECTED | gated |", "|---|---|---|---|---|---|---|---|"]
    for lab, r in res["regime_split"].items():
        o.append(f"| {lab} | {r['avg_cash']*100:.1f}% | {r['bar_cagr']*100:.2f}% | {r['static']['1.5']['original']*100:.2f}% | "
                 f"{r['static']['1.5']['corrected']*100:.2f}% | {r['static']['2.0']['original']*100:.2f}% | "
                 f"{r['static']['2.0']['corrected']*100:.2f}% | {r['gated_cagr']*100:.2f}% |")
    ld = res["lost_decades"]
    o += ["", "## Lost-decades overlay (final 20 years at -2%/yr)", "",
          f"Bar ${ld['bar']['wealth']:,.0f} ({ld['bar']['cagr']*100:.2f}%).", "",
          "| arm | ORIGINAL $ | CORRECTED $ (x bar) |", "|---|---|---|"]
    o += [f"| static {float(L):.2f}x | {d['original']['wealth']:,.0f} | {d['corrected']['wealth']:,.0f} ({d['corrected']['wealth']/ld['bar']['wealth']:.2f}) |"
          for L, d in ld["static"].items()]
    ar = res["accumulation_race"]
    o += ["", "## $7k/yr accumulation race — D-B, one cohort from 1968 (no CI; realized premium)", "",
          f"Bar ${ar['bar']:,.0f}; glide 2x->1x (unaffected) ${ar['glide']:,.0f}; gated (unaffected) ${ar['gated']:,.0f}.", "",
          "| arm | ORIGINAL final $ | CORRECTED final $ | S1 blend final $ |", "|---|---|---|---|"]
    o += [f"| static {float(L):.2f}x | {d['original']:,.0f} | {d['corrected']:,.0f} | {ar['s1_blend'][L]:,.0f} |"
          for L, d in ar["static"].items()]
    o += ["", "# SENSITIVITY S1 — blended fee for L < 2 (labelled; never the headline)", ""]
    for wl, w in res["windows"].items():
        o += [f"## S1 — {wl}", "", "| arm | CORRECTED headline $ | S1 blend $ | MaxDD | dlog %/yr | P(ahead) | S1 dwealth 95% CI |",
              "|---|---|---|---|---|---|---|"]
        for L in STATIC_L:
            c, s = w["static"][str(L)]["corrected"], w["s1_blend"][str(L)]
            o.append(f"| {L:.2f}x | {c['wealth']:,.0f} | {s['wealth']:,.0f} | {s['maxdd']*100:.1f}% | {_dl(s)} | {s['p_ahead']*100:.0f}% | {_ci(s)} |")
        o.append("")
    o += ["## S1 — haircuts, D-B", "", "| haircut | arm | bar $ | S1 blend $ (x bar) | dlog %/yr | P(ahead) | S1 CI |", "|---|---|---|---|---|---|---|"]
    for lab, h in res["haircuts"].items():
        for L in STATIC_L:
            s = h["s1_blend"][str(L)]
            o.append(f"| {lab} | {L:.2f}x | {h['bar_wealth']:,.0f} | {s['wealth']:,.0f} ({s['wealth']/h['bar_wealth']:.2f}) | {_dl(s)} | {s['p_ahead']*100:.0f}% | {_ci(s)} |")
    o += ["", "## S1 — the 1929 path", "", "| arm | dd / trough / yrs to recover |", "|---|---|"]
    o += [f"| blend {float(L):.2f}x | {s['dd']*100:.1f}% / ${s['trough']:,.0f} / {s['recover_yrs']:.1f} |" for L, s in c29["s1_blend"].items()]
    o += ["", "# SENSITIVITY S2 — B-5 H.15 / SOFR financing (labelled; never the headline)", ""]
    for wl, s2 in res["s2_b5_financing"].items():
        f = s2["financing_per_yr"]
        o += [f"## S2 — {wl}, truncated to {s2['end']}", "",
              f"Bar ${s2['bar']['wealth']:,.0f}. Financing charged per year on the borrowed fraction: T-306 cash + 60 bp "
              f"{f['t306_cash_plus_60bp']*100:.3f}%; B-5 base + 60 bp {f['b5_base_plus_60bp']*100:.3f}%.", "",
              "| arm | T-306 cash $ | T-306 dlog %/yr | T-306 CI | B-5 financing $ | B-5 dlog %/yr | B-5 CI |", "|---|---|---|---|---|---|---|"]
        for L in STATIC_L:
            a, b = s2["static"][str(L)]["t306_cash"], s2["static"][str(L)]["b5_financing"]
            o.append(f"| static {L:.2f}x | {a['wealth']:,.0f} | {_dl(a)} | {_ci(a)} | {b['wealth']:,.0f} | {_dl(b)} | {_ci(b)} |")
        a, b = s2["glide"]["t306_cash"], s2["glide"]["b5_financing"]
        o += [f"| glide 2x->1x | {a['wealth']:,.0f} | {_dl(a)} | {_ci(a)} | {b['wealth']:,.0f} | {_dl(b)} | {_ci(b)} |", ""]
    return "\n".join(o) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    """Run once and write results.json + tables.md under <out>/run_<tag>/; print the result md5."""
    p = argparse.ArgumentParser(description="T-399: the defect-corrected re-run of T-315.")
    p.add_argument("--tag", required=True, help="run tag, e.g. A or B (the determinism twin)")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="output root (worktree-local; never data/research)")
    a = p.parse_args(argv)
    out = Path(a.out).resolve() / f"run_{a.tag}"
    if (ROOT / "data" / "research").resolve() in [out, *out.parents]:
        raise T399Halt(f"refusing to write under data/research: {out}")
    out.mkdir(parents=True, exist_ok=True)
    res = run()
    blob = json.dumps(res, sort_keys=True, indent=1, allow_nan=False)
    (out / "results.json").write_text(blob)
    (out / "tables.md").write_text(tables_md(res))
    print(f"T-399 run {a.tag}: {res['acceptance']}")
    print(f"results.json md5 {hashlib.md5(blob.encode()).hexdigest()} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
