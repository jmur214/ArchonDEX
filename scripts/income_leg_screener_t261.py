"""T-261 income-leg SCREENER ($0, screening only — NO gauntlet, NO N_trials consumed).

Screens income-leg candidates for the T-248 composer's 3rd sleeve on the SAME
yardstick, on the T-256 substrate (data/raw/cboe/ + data/processed/tr_reconciled/):
Sortino/Sharpe/MaxDD/CAGR/skew/Calmar + the two named crisis windows (COVID-2020,
2022) + correlation to the trend sleeve AND to its FAILURE MODES (fast gaps).

Candidates: CBOE PUT (put-write, 1986+ spliced by RETURNS), BXMD (30-delta buywrite),
PFF/PGX (preferreds), JEPI (covered-call, 2020+), PCEF (CEF income composite)/MUB
(muni), SCHD (dividend-growth), baseline AGG TR. Full-window AND a common-window
(JEPI-limited) pass — honest about the PUT-1986 vs JEPI-2020 mismatch.

KEY question: which income stream is LEAST correlated with the sleeve's fast-gap
failures while adding the most CAGR per unit MaxDD? Picks ONE for the pre-registered
50/50-with-sleeve gauntlet. Output is a ranked table + recommendation, nothing built.
"""
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME              # noqa: E402
from core.trend_overlay import sleeve_returns                    # noqa: E402

TD = 252
TR = os.path.join(ROOT, "data/processed/tr_reconciled")
CBOE = os.path.join(ROOT, "data/raw/cboe")
XLS = os.path.join(CBOE, "dailypricehistory_wayback_19862019.xls")

COVID = ("2020-02-19", "2020-04-30")   # fast crash + initial bounce (the sleeve's long/flat failure)
Y2022 = ("2022-01-03", "2022-12-30")   # slow bear (the sleeve's right-tail regime)


def tr_close(ticker):
    df = pd.read_csv(os.path.join(TR, f"{ticker}_1d.csv"), parse_dates=["Date"]).set_index("Date")
    return df["Close"].astype(float).sort_index()


def cboe_cdn(sym):
    df = pd.read_csv(os.path.join(CBOE, f"{sym}_cdn.csv"))
    df.columns = ["Date", "v"]
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
    return df.set_index("Date")["v"].astype(float).sort_index()


def cboe_xls(col_idx):
    raw = pd.read_excel(XLS, "Sheet1", header=None, skiprows=5, usecols=[0, col_idx])
    raw.columns = ["Date", "v"]
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    raw["v"] = pd.to_numeric(raw["v"], errors="coerce")
    return raw.dropna().set_index("Date")["v"].sort_index()


def splice_returns(deep, recent):
    """Chain two index levels by RETURNS, level-matched at the seam (NOT raw levels).

    The Wayback xls is DENSE 1986-2019; the CDN is dense only from ~2007 (sparse
    before — splicing into the sparse region manufactures spurious jumps, e.g. a
    fake +72% 'day' in 2001). So use the xls for its full dense range, scale the CDN
    to match the xls level at the seam (xls end), and append only the CDN tail."""
    seam = deep.index[-1]
    prior = recent.index[recent.index <= seam]
    if len(prior) == 0:
        return deep.pct_change().dropna()
    scale = deep.iloc[-1] / recent.loc[prior[-1]]      # level-match at the seam
    tail = recent[recent.index > seam] * scale
    full = pd.concat([deep, tail])
    return full.pct_change().dropna()


def put_returns():
    deep = cboe_xls(4)        # PUT column in the Wayback master (1986-2019)
    recent = cboe_cdn("PUT")  # CDN (1991+, dense late)
    return splice_returns(deep, recent)


def bxmd_returns():
    deep = cboe_xls(9)        # BXMD column (1986-2019)
    recent = cboe_cdn("BXMD")
    return splice_returns(deep, recent)


def maxdd(r):
    eq = (1 + r).cumprod()
    return (eq / eq.cummax() - 1).min()


def cagr(r):
    eq = (1 + r).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else float("nan")


def sortino_ci(r):
    s = ME.sortino_ratio(r, 0.0, TD)
    try:
        ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD),
                                       n_iterations=1000, seed=0).get("ci_low")
    except Exception:
        ci = float("nan")
    return s, ci


def win(r, a, b):
    return r[(r.index >= a) & (r.index <= b)]


def main():
    # --- trend sleeve on the TR-reconciled substrate ---
    closes = {t: tr_close(t) for t in ["SPY", "AGG", "GLD"]}
    sleeve = sleeve_returns(closes, 105)

    cand = {
        "CBOE PUT (put-write)": put_returns(),
        "CBOE BXMD (30d buywrite)": bxmd_returns(),
        "PFF (preferreds)": tr_close("PFF").pct_change().dropna(),
        "PGX (preferreds)": tr_close("PGX").pct_change().dropna(),
        "JEPI (cov-call 2020+)": tr_close("JEPI").pct_change().dropna(),
        "PCEF (CEF income)": tr_close("PCEF").pct_change().dropna(),
        "MUB (muni)": tr_close("MUB").pct_change().dropna(),
        "SCHD (div-growth)": tr_close("SCHD").pct_change().dropna(),
        "AGG TR (baseline)": tr_close("AGG").pct_change().dropna(),
    }

    # sleeve fast-gap failure mask: sleeve's worst 5% of days (the fast-gap regime)
    thr = sleeve.quantile(0.05)
    gap_days = sleeve[sleeve <= thr].index

    print(f"\n=== INCOME-LEG SCREENER (T-261, $0, screening only) — sleeve fast-gap thr={thr:.4f} ===")
    hdr = (f"{'candidate':<26}{'start':>8}{'Sortino':>8}{'so_ci':>7}{'Sharpe':>7}{'MaxDD':>7}"
           f"{'CAGR':>7}{'skew':>6}{'Calmar':>7}{'COVID':>7}{'2022':>7}{'rSlv':>6}{'gapRet':>7}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for nm, r in cand.items():
        r = r.dropna()
        so, soc = sortino_ci(r)
        sh = ME.sharpe_ratio(r, 0.0, TD)
        md, cg = maxdd(r), cagr(r)
        sk = float(pd.Series(r).skew())
        covid = (1 + win(r, *COVID)).prod() - 1
        y22 = (1 + win(r, *Y2022)).prod() - 1
        j = pd.concat({"c": r, "s": sleeve}, axis=1, sort=True).dropna()
        rslv = float(j["c"].corr(j["s"])) if len(j) > 30 else float("nan")
        # mean candidate return on the sleeve's fast-gap days (want >=0 → diversifies the failure)
        gapret = float(r.reindex(gap_days).dropna().mean())
        rows[nm] = dict(so=so, soc=soc, sh=sh, md=md, cg=cg, sk=sk, covid=covid,
                        y22=y22, rslv=rslv, gapret=gapret, start=r.index[0])
        print(f"{nm:<26}{str(r.index[0].year):>8}{so:>8.2f}{soc:>7.2f}{sh:>7.2f}{md:>7.1%}"
              f"{cg:>7.1%}{sk:>6.1f}{cg/abs(md):>7.2f}{covid:>7.1%}{y22:>7.1%}{rslv:>6.2f}{gapret*1e4:>7.0f}")

    # --- COMMON-WINDOW pass (all candidates present = JEPI-limited 2020-05+) ---
    common_start = max(v["start"] for v in rows.values())
    print(f"\n=== COMMON WINDOW {common_start.date()}+ (fair cross-comparison; JEPI-limited) ===")
    print(f"{'candidate':<26}{'Sortino':>8}{'Sharpe':>7}{'MaxDD':>7}{'CAGR':>7}{'Calmar':>7}{'rSlv':>6}{'gapRet_bps':>11}")
    cw = {}
    for nm, r in cand.items():
        rr = r[r.index >= common_start].dropna()
        if len(rr) < 60:
            continue
        so, _ = sortino_ci(rr)
        md, cg = maxdd(rr), cagr(rr)
        j = pd.concat({"c": rr, "s": sleeve}, axis=1, sort=True).dropna()
        rslv = float(j["c"].corr(j["s"]))
        gapret = float(rr.reindex(gap_days).dropna().mean())
        cw[nm] = dict(so=so, md=md, cg=cg, rslv=rslv, gapret=gapret)
        print(f"{nm:<26}{so:>8.2f}{ME.sharpe_ratio(rr,0.0,TD):>7.2f}{md:>7.1%}{cg:>7.1%}"
              f"{cg/abs(md):>7.2f}{rslv:>6.2f}{gapret*1e4:>11.0f}")

    # --- screening score: reward CAGR/MaxDD (Calmar) + LOW sleeve corr + POSITIVE gap-day return ---
    print("\n=== SCREEN RANK (full-window; score = Calmar - |rSlv| + 50*gapRet, higher=better diversifier) ===")
    score = {nm: v["cg"] / abs(v["md"]) - abs(v["rslv"]) + 50 * v["gapret"]
             for nm, v in rows.items() if nm != "AGG TR (baseline)"}
    for i, (nm, sc) in enumerate(sorted(score.items(), key=lambda x: -x[1]), 1):
        v = rows[nm]
        print(f"  {i}. {nm:<26} score={sc:+.3f}  (Calmar {v['cg']/abs(v['md']):.2f}, "
              f"rSlv {v['rslv']:+.2f}, gapRet {v['gapret']*1e4:+.0f}bps, COVID {v['covid']:+.1%})")


if __name__ == "__main__":
    main()
