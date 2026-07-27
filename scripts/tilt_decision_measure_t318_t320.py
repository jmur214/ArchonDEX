"""T-318 + T-320 — the tilt DECISION measurements (frozen pre-regs; N += 2, one per family).

Decision-support, NOT alpha claims. Runs both frozen families on one engine so the value
half (T-318) and the aggressive half (T-320) are directly comparable — the director's
benchmark ruling: FF market PRIMARY + the T-306 deep-SPY CROSS-CHECK, applied to BOTH.

Report order is frozen: THE REGRET METRIC LEADS (worst rolling 15yr RELATIVE drawdown vs
the benchmark, in $ per $10k, + time-to-recover the relative high — "never" where true),
then the rolling-40yr win fraction, then the log-wealth-ratio 95% CI (excluding zero = the
"real edge" bar).

Momentum is reported BOTH ways: the long-only deployable portfolio (what you can hold) and
the long-short academic factor (the upper bound) — never the factor alone as if investable.

Usage: python -m scripts.tilt_decision_measure_t318_t320
"""
import io
import os
import sys
import urllib.request as u
import warnings
import zipfile

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
ER = {"SV": 0.0025, "MOM": 0.0025, "GROWTH": 0.0020, "QUAL": 0.0015, "MKT": 0.000945}
ROLL_YEARS = 40          # the decision window (frozen)
REGRET_YEARS = 15        # the regret window (frozen)


def _ff_raw(fn):
    import pandas as pd
    b = u.urlopen(u.Request(FF + fn, headers={"User-Agent": "Mozilla/5.0"}), timeout=45).read()
    z = zipfile.ZipFile(io.BytesIO(b))
    txt = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    hdr_i = next(i for i, l in enumerate(txt)
                 if l.count(",") >= 3 and not l[:6].strip().isdigit() and l.strip().startswith(","))
    cols = [c.strip() for c in txt[hdr_i].split(",")][1:]
    rows = [l.split(",") for l in txt[hdr_i:] if l[:6].strip().isdigit() and len(l[:6].strip()) == 6]
    df = pd.DataFrame([r[1:len(cols) + 1] for r in rows],
                      index=pd.to_datetime([r[0].strip() for r in rows], format="%Y%m"),
                      columns=cols).apply(pd.to_numeric, errors="coerce") / 100.0
    return df[~df.index.duplicated()]


def ff_factor(fn, col):
    """A single FF factor/portfolio column, monthly decimal returns."""
    import pandas as pd
    b = u.urlopen(u.Request(FF + fn, headers={"User-Agent": "Mozilla/5.0"}), timeout=45).read()
    z = zipfile.ZipFile(io.BytesIO(b))
    txt = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    rows = [l.split(",") for l in txt if l[:6].strip().isdigit() and len(l[:6].strip()) == 6]
    df = pd.DataFrame(rows).apply(pd.to_numeric, errors="coerce")
    df.index = pd.to_datetime(df[0].astype(int).astype(str), format="%Y%m")
    return (df[col] / 100.0).rename("r")


def load_legs():
    """All legs, monthly, TOTAL return (market = MktRF + RF)."""
    import pandas as pd
    f3 = _ff_raw("F-F_Research_Data_Factors_CSV.zip")
    mkt = (f3["Mkt-RF"] + f3["RF"]).rename("MKT")           # FF market TR — the PRIMARY benchmark
    rf = f3["RF"].rename("RF")
    six = _ff_raw("6_Portfolios_2x3_CSV.zip")
    sv = six["SMALL HiBM"].rename("SV")                      # small-value (T-318)
    # GROWTH, total-return, same library/construction as the benchmark. REQUIRED because
    # ^IXIC is a PRICE index: comparing it to a TR benchmark silently biases AGAINST growth
    # by its dividend yield (~1%/yr compounds to ~+48% over 40yr). "BIG LoBM" is the factor-
    # history growth leg (the value premium's mirror) — the apples-to-apples measurement.
    # ^IXIC/QQQ are still reported as the POPULAR tech-concentration version, caveat named.
    growth_ff = ((six["BIG LoBM"] + six["SMALL LoBM"]) / 2.0).rename("GROWTH_FF")
    mom6 = _ff_raw("6_Portfolios_ME_Prior_12_2_CSV.zip")
    mom_lo = ((mom6["SMALL HiPRIOR"] + mom6["BIG HiPRIOR"]) / 2.0).rename("MOM")  # long-only winners
    mom_ls = ff_factor("F-F_Momentum_Factor_CSV.zip", 1).rename("MOM_LS")         # academic L/S
    opd = _ff_raw("Portfolios_Formed_on_OP_CSV.zip")
    qcol = next((c for c in opd.columns if c.strip() in ("Hi 20", "Hi 30", "HiOP")), None)
    qual = opd[qcol].rename("QUAL") if qcol else None        # high operating profitability
    return dict(MKT=mkt, RF=rf, SV=sv, MOM=mom_lo, MOM_LS=mom_ls, QUAL=qual,
                GROWTH_FF=growth_ff)


def nasdaq_monthly():
    """^IXIC monthly TR proxy (price index — dividends light for a growth index; named caveat)."""
    import pandas as pd
    import yfinance as yf
    h = yf.Ticker("^IXIC").history(period="max", auto_adjust=True)["Close"]
    h.index = pd.to_datetime(h.index).tz_localize(None)
    return h.resample("ME").last().pct_change().dropna().rename("GROWTH")


def _mnorm(s):
    """Normalize a monthly series to a MONTH-END stamp.

    FAIL-LOUD GUARD: FF stamps month-START and yfinance month-END, so joining them raw
    silently yields ZERO overlap — which would print a blank arm that reads like 'measured
    and found nothing' (silent-wrongness). Every leg is normalized here, and `blend` asserts
    a non-empty overlap so a mis-join HALTS instead of reporting an empty result."""
    if s is None:
        return None
    out = s.copy()
    out.index = out.index.to_period("M").to_timestamp("M")
    return out[~out.index.duplicated()]


def blend(bench, tilt, w, er_tilt, er_bench=ER["MKT"]):
    """Monthly-rebalanced (1-w) benchmark + w tilt, each net of its annual ER."""
    import pandas as pd
    j = pd.concat({"b": _mnorm(bench), "t": _mnorm(tilt)}, axis=1).dropna()
    if j.empty:
        raise RuntimeError("blend(): ZERO overlap between benchmark and tilt — "
                           "refusing to report an empty arm as a measurement")
    return ((1 - w) * (j["b"] - er_bench / 12) + w * (j["t"] - er_tilt / 12)).rename("blend")


def regret(blend_r, bench_r):
    """THE REGRET METRIC: worst rolling-15yr RELATIVE drawdown + time to recover."""
    import numpy as np
    import pandas as pd
    j = pd.concat({"a": blend_r, "b": bench_r}, axis=1).dropna()
    rel = (1 + j["a"]).cumprod() / (1 + j["b"]).cumprod()
    win = REGRET_YEARS * 12
    worst, worst_end = 0.0, None
    for i in range(len(rel)):
        lo = max(0, i - win)
        seg = rel.iloc[lo:i + 1]
        dd = float(seg.iloc[-1] / seg.max() - 1.0)
        if dd < worst:
            worst, worst_end = dd, rel.index[i]
    # time to recover the relative high (from the pre-drawdown peak)
    rec_yrs, recovered = float("nan"), False
    if worst_end is not None:
        pk_val = rel.loc[:worst_end].max()
        pk_dt = rel.loc[:worst_end].idxmax()
        after = rel[(rel.index > worst_end) & (rel >= pk_val)]
        if len(after):
            rec_yrs, recovered = (after.index[0] - pk_dt).days / 365.25, True
        else:
            rec_yrs = (rel.index[-1] - pk_dt).days / 365.25
    return worst, rec_yrs, recovered


def rolling_win_and_ci(blend_r, bench_r, n_boot=1000):
    """Fraction of rolling-40yr windows the blend wins + block-bootstrap log-wealth CI."""
    import numpy as np
    import pandas as pd
    j = pd.concat({"a": blend_r, "b": bench_r}, axis=1).dropna()
    win = ROLL_YEARS * 12
    if len(j) <= win:
        return float("nan"), 0, (float("nan"), float("nan")), float("nan")
    la = np.log1p(j["a"].values)
    lb = np.log1p(j["b"].values)
    diffs = []
    for s in range(len(j) - win + 1):
        diffs.append(la[s:s + win].sum() - lb[s:s + win].sum())
    diffs = np.array(diffs)
    frac = float((diffs > 0).mean())
    # block-bootstrap the per-month log difference (block = 60mo, serial correlation)
    d = la - lb
    n, L = len(d), 60
    rng = np.random.default_rng(0)
    nb = int(np.ceil(win / L))
    boots = []
    for _ in range(n_boot):
        st = rng.integers(0, n - L + 1, size=nb)
        ix = np.concatenate([np.arange(t, t + L) for t in st])[:win]
        boots.append(d[ix].sum())
    return frac, len(diffs), (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))), float(np.median(diffs))


def report_arm(name, tilt, bench, w, er_tilt, note=""):
    import numpy as np
    b = blend(bench, tilt, w, er_tilt)
    bm = _mnorm(bench).reindex(b.index).dropna()   # SAME normalization as blend() — see _mnorm
    b = b.reindex(bm.index)
    if b.empty:
        raise RuntimeError(f"report_arm({name}): empty overlap after alignment")
    worst, rec, recovered = regret(b, bm)
    frac, nwin, (lo, hi), med = rolling_win_and_ci(b, bm)
    sig = "CI EXCLUDES 0" if lo > 0 else ("CI excl 0 (NEG)" if hi < 0 else "straddles 0")
    rec_s = (f"{rec:.1f}y" if recovered else f"NEVER (≥{rec:.1f}y)") if rec == rec else "—"
    print(f"  {name:34}{worst*100:>8.1f}%  ${10000*abs(worst):>7,.0f}  {rec_s:>12}"
          f"{(frac*100 if frac==frac else float('nan')):>8.0f}%{nwin:>5}"
          f"  [{lo:+.3f},{hi:+.3f}] {sig}{note}")
    return dict(name=name, regret=worst, rec=rec, recovered=recovered, frac=frac,
                nwin=nwin, ci=(lo, hi), med=med)


HDR = (f"  {'arm':34}{'regretDD':>9}{'$/10k':>9}{'recover':>12}"
       f"{'win40y':>8}{'N':>5}  log-wealth 95% CI")


def main():
    import pandas as pd
    legs = load_legs()
    mkt, rf = legs["MKT"], legs["RF"]
    print(f"benchmark PRIMARY = FF market TR ({mkt.index[0].date()}→{mkt.index[-1].date()}), "
          f"net {ER['MKT']*100:.3f}% ER. Regret = worst rolling {REGRET_YEARS}yr RELATIVE DD; "
          f"win40y = fraction of rolling {ROLL_YEARS}yr windows the blend beats the benchmark.")

    # ---------------- T-318: the VALUE half ----------------
    print("\n" + "=" * 118)
    print("T-318 — SMALL-VALUE TILT (frozen). REGRET LEADS.")
    print("=" * 118)
    print(HDR)
    sv = legs["SV"]
    r318 = [report_arm("80/20 SPY/small-value", sv, mkt, 0.20, ER["SV"]),
            report_arm("70/30 SPY/small-value", sv, mkt, 0.30, ER["SV"])]
    # post-1993 (publication) decay variant: haircut = MEASURED post-pub realized premium
    pre = (sv - mkt).loc[:"1992-12"].mean() * 12
    post = (sv - mkt).loc["1993-01":].mean() * 12
    hair = post - pre                      # measured, not chosen (negative => decayed)
    sv_dec = sv + hair / 12
    print(f"  [decay variant: measured SV premium pre-1993 {pre*100:+.2f}%/yr → "
          f"post-1993 {post*100:+.2f}%/yr; haircut {hair*100:+.2f}%/yr applied full-sample]")
    r318.append(report_arm("80/20 decayed (post-1993 prem)", sv_dec, mkt, 0.20, ER["SV"]))

    # ---------------- T-320: the AGGRESSIVE half ----------------
    print("\n" + "=" * 118)
    print("T-320 — AGGRESSIVE TILTS (frozen, one family). REGRET LEADS.")
    print("=" * 118)
    print(HDR)
    r320 = []
    mom, mom_ls, qual = legs["MOM"], legs["MOM_LS"], legs["QUAL"]
    r320 += [report_arm("80/20 SPY/momentum (long-only)", mom, mkt, 0.20, ER["MOM"]),
             report_arm("70/30 SPY/momentum (long-only)", mom, mkt, 0.30, ER["MOM"])]
    # the academic long-short upper bound — reported BESIDE, never as the deployable arm
    mom_ls_tot = (mom_ls + rf).dropna()
    r320.append(report_arm("  [MOM long-SHORT factor+rf]", mom_ls_tot, mkt, 0.20, ER["MOM"],
                           note="  ← academic upper bound, NOT investable"))
    # GROWTH — reported TWO ways (see load_legs): the FF total-return growth leg is the
    # apples-to-apples measurement; ^IXIC is the popular tech-concentration version, whose
    # PRICE-index basis biases it DOWN by its dividend yield (bound printed below).
    gff = legs["GROWTH_FF"]
    r320 += [report_arm("80/20 SPY/growth (FF, TR)", gff, mkt, 0.20, ER["GROWTH"]),
             report_arm("70/30 SPY/growth (FF, TR)", gff, mkt, 0.30, ER["GROWTH"])]
    growth = nasdaq_monthly()
    r320 += [report_arm("80/20 SPY/Nasdaq (price idx)", growth, mkt, 0.20, ER["GROWTH"],
                        note="  ← price index: biased DOWN ~1%/yr div"),
             report_arm("70/30 SPY/Nasdaq (price idx)", growth, mkt, 0.30, ER["GROWTH"],
                        note="  ← same caveat")]
    if qual is not None:
        r320 += [report_arm("80/20 SPY/quality (high-OP)", qual, mkt, 0.20, ER["QUAL"]),
                 report_arm("70/30 SPY/quality (high-OP)", qual, mkt, 0.30, ER["QUAL"])]
    # decay variants (measured post-publication haircuts)
    for lbl, leg, cut, key in [("momentum", mom, "1993-01", "MOM"), ("quality", qual, "2013-01", "QUAL")]:
        if leg is None:
            continue
        pre = (leg - mkt).loc[:cut].mean() * 12
        post = (leg - mkt).loc[cut:].mean() * 12
        h = post - pre
        print(f"  [decay {lbl}: pre {pre*100:+.2f}%/yr → post {post*100:+.2f}%/yr; haircut {h*100:+.2f}%/yr]")
        r320.append(report_arm(f"80/20 {lbl} DECAYED", leg + h / 12, mkt, 0.20, ER[key]))

    # ---------------- the T-306 deep-SPY CROSS-CHECK ----------------
    print("\n=== CROSS-CHECK on the deployable substrate (T-306 deep SPY, director's ruling) ===")
    try:
        import csv
        from datetime import datetime
        rows = list(csv.DictReader(open(os.path.join(ROOT, "data/processed/SPY_1d.csv"))))
        spx = pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in rows}).sort_index()
        spy_m = spx.resample("ME").last().pct_change().dropna()
        spy_m.index = spy_m.index.to_period("M").to_timestamp("M")
        for nm, leg, w, k in [("small-value 80/20", sv, 0.20, "SV"), ("momentum 80/20", mom, 0.20, "MOM"),
                              ("growth 80/20", growth, 0.20, "GROWTH"), ("quality 80/20", qual, 0.20, "QUAL")]:
            if leg is None:
                continue
            lg = leg.copy()
            lg.index = lg.index.to_period("M").to_timestamp("M")
            b = blend(spy_m, lg, w, ER[k])
            bm = spy_m.reindex(b.index).dropna()
            b = b.reindex(bm.index)
            wst, rc, rcv = regret(b, bm)
            fr, nw, (lo, hi), _ = rolling_win_and_ci(b, bm)
            print(f"  {nm:26} {b.index[0].date()}→{b.index[-1].date()}  regret {wst*100:+.1f}% "
                  f"(${10000*abs(wst):,.0f})  win40y={'n/a' if fr!=fr else f'{fr*100:.0f}%'} "
                  f"CI[{lo:+.3f},{hi:+.3f}]")
    except Exception as exc:
        print(f"  cross-check unavailable: {type(exc).__name__}: {exc}")

    print("\n*** DECISION-SUPPORT, not alpha claims. The deploying sleeve is untouched by every "
          "outcome. No timing/sizing rule, no stacking arms. ***")


if __name__ == "__main__":
    main()
