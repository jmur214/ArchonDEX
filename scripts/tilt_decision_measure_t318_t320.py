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

B-9 / T-380 (multi-factor combination tilts at deployable weights) extends this harness —
frozen pre-registration docs/Sources/prereg_b9_combo_tilts_2026-11-11.md (16432da + amendment 1):
  python -m scripts.tilt_decision_measure_t318_t320 --b9-snapshot   # ONE-TIME input snapshot
  python -m scripts.tilt_decision_measure_t318_t320 --b9-smoke      # first 12 months, by eye
  python -m scripts.tilt_decision_measure_t318_t320 --b9            # the frozen measurement
The B-9 path reads ONLY the md5-manifested snapshot under data/research/b9/inputs/.
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


def _ff_bytes(fn):
    """The raw zip bytes of one Ken French library file (B-9 snapshots these verbatim)."""
    return u.urlopen(u.Request(FF + fn, headers={"User-Agent": "Mozilla/5.0"}), timeout=45).read()


def _ff_raw(fn):
    return _ff_parse(_ff_bytes(fn))


def _ff_parse(b):
    """Parse the FIRST table of a French zip (the value-weighted monthly returns for the
    portfolio files; the factor table for F-F_Research_Data_Factors), monthly decimals."""
    import pandas as pd
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


# =====================================================================================
# B-9 / T-380 — multi-factor combination tilts at deployable weights (VOO / MTUM / AVUV).
# Frozen pre-registration: docs/Sources/prereg_b9_combo_tilts_2026-11-11.md (16432da, frozen by
# the director 2026-11-11 with Option A; amendment 1 = 60e51a5, input check (d)). Every constant
# below is quoted from that document; NOTHING here is tuned. Section numbers (§) refer to it.
# =====================================================================================
B9_DIR = os.path.join(ROOT, "data", "research", "b9")
B9_INPUTS = os.path.join(B9_DIR, "inputs")
B9_MANIFEST = os.path.join(B9_INPUTS, "manifest.json")
B9_RESULTS = os.path.join(B9_DIR, "b9_results.json")
B9_WINDOW = ("2000-01", "2026-06")            # §4, 318 monthly returns
B9_N_MONTHS = 318
B9_FR_WINDOW = ("1963-07", "2026-06")         # §4 secondary French-only window, 756 months
B9_FR_N_MONTHS = 756
B9_ER = {"VOO": 0.0003, "MTUM": 0.0015, "AVUV": 0.0025, "SPY": ER["MKT"]}   # §5, per year
B9_SPLICE = {"VOO": "2010-10", "MTUM": "2013-05", "AVUV": "2019-10"}         # §4, first ETF month
B9_COST = 0.0005                              # §5: 5 bp per rebalanced dollar
B9_HAIRCUT = 0.5                              # §5: half the French-era alpha, constant shift
B9_ARMS = {                                   # §6 (VOO, MTUM, AVUV) — FROZEN
    "(i) 60/20/20": (0.60, 0.20, 0.20),
    "(ii) 70/15/15": (0.70, 0.15, 0.15),
    "(iii) 80/20/0": (0.80, 0.20, 0.00),
    "(iv) 80/0/20": (0.80, 0.00, 0.20),
    "REF 85/15/0 deployed": (0.85, 0.15, 0.00),
}
B9_DECISION_ARM = "(i) 60/20/20"
B9_REF_ARM = "REF 85/15/0 deployed"
B9_PREDICTED_T = 2.2                          # §7, the brief's prior for arm (i)
B9_SENS_BLOCK = 60                            # §3.4 sensitivity block (months)
B9_N_BOOT, B9_SEED = 1000, 0
B9_BRIEF_N = 264                              # §7 the brief's N, a labelled third DSR line
B9_FF_FILES = {
    "factors": "F-F_Research_Data_Factors_CSV.zip",
    "mom6": "6_Portfolios_ME_Prior_12_2_CSV.zip",
    "bmop32": "32_Portfolios_ME_BEME_OP_2x4x4_CSV.zip",
}
B9_MOM_COL, B9_SVP_COL = "BIG HiPRIOR", "SMALL HiBM HiOP"                     # §3.3
B9_YF_TICKERS = ("SPY", "VOO", "MTUM", "AVUV")
B9_YF_START = {"SPY": "1999-11-01", "VOO": "2010-08-01", "MTUM": "2013-03-01", "AVUV": "2019-08-01"}
B9_YF_ASOF = "2026-07-01"                     # yfinance `end` is exclusive -> through 2026-06-30
B9_STOOQ = {                                  # check (a): the split-jump cross-reference
    "SPY": "data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt",
    "VOO": "data/raw/stooq/daily/us/nyse etfs/2/voo.us.txt",
    "MTUM": "data/raw/stooq/daily/us/nyse etfs/1/mtum.us.txt",
    "AVUV": "data/raw/stooq/daily/us/nyse etfs/1/avuv.us.txt",
}
B9_LOCAL_SPY = {                              # check (b): SPY-vs-SPY class references (fixed names)
    "tr_reconciled": ("data/processed/tr_reconciled/SPY_1d.csv", 2005, 2025),
    "processed": ("data/processed/SPY_1d.csv", 2000, 2025),
}
B9_SPLIT_JUMP_TOL = 0.20                      # check (a), T-256's SPLIT_JUMP_TOL
B9_YE_RATIO_TOL = 0.005                       # check (b): year-end level ratio constant ±0.5%
B9_MAX_ABS_MONTHLY = 0.50                     # check (c)
B9_DIV_GAP = (0.003, 0.040)                   # check (d), amendment 1


class B9Halt(RuntimeError):
    """A fail-closed census/validation failure: no results file is written ([NN-FAIL-CLOSED])."""


def _md5_bytes(b):
    import hashlib
    return hashlib.md5(b).hexdigest()


def _md5_file(path):
    with open(path, "rb") as fh:
        return _md5_bytes(fh.read())


def b9_snapshot():
    """ONE-TIME input snapshot (prereg §3.2 Option A, §16). Refuses to overwrite an existing one."""
    import datetime as _dt
    import json
    import pandas as pd
    import yfinance as yf
    from scripts.reconcile_stooq_tr_t256 import fetch_yf_tr   # the FETCH only — never its writer
    if os.path.exists(B9_MANIFEST):
        raise B9Halt(f"snapshot already exists ({B9_MANIFEST}) — the prereg allows ONE snapshot; "
                     f"refusing to re-fetch")
    os.makedirs(os.path.join(B9_INPUTS, "ff"), exist_ok=True)
    os.makedirs(os.path.join(B9_INPUTS, "yf"), exist_ok=True)
    files = {}
    for fn in B9_FF_FILES.values():
        b = _ff_bytes(fn)
        rel = f"ff/{fn}"
        with open(os.path.join(B9_INPUTS, rel), "wb") as fh:
            fh.write(b)
        files[rel] = _md5_bytes(b)
    for t in B9_YF_TICKERS:
        tr, close = fetch_yf_tr(t, B9_YF_START[t], B9_YF_ASOF)
        if tr is None or close is None or not len(tr):
            raise B9Halt(f"yfinance returned nothing for {t} — HALT (a partial snapshot is unusable)")
        df = pd.DataFrame({"AdjClose": tr["Close"].astype(float), "Close": close.astype(float)})
        idx = pd.to_datetime(df.index)
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        df.index = idx
        df.index.name = "Date"
        body = df.to_csv(float_format="%.10g").encode()
        rel = f"yf/{t}.csv"
        with open(os.path.join(B9_INPUTS, rel), "wb") as fh:
            fh.write(body)
        files[rel] = _md5_bytes(body)
    man = {"task": "T-380 (B-9)", "prereg": "docs/Sources/prereg_b9_combo_tilts_2026-11-11.md",
           "frozen_at": "16432da", "amendment_1": "60e51a5",
           "snapshot_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
           "yfinance_version": yf.__version__, "yf_asof_exclusive": B9_YF_ASOF,
           "yf_start": B9_YF_START, "ff_files": B9_FF_FILES, "md5": files}
    with open(B9_MANIFEST, "w") as fh:
        json.dump(man, fh, indent=1, sort_keys=True)
    print(f"[b9] snapshot written: {B9_INPUTS}")
    for k, v in sorted(files.items()):
        print(f"  {v}  {k}")
    return man


def _b9_read_snapshot():
    """Read the snapshot, verifying every md5 against the manifest (HALT on any mismatch)."""
    import json
    if not os.path.exists(B9_MANIFEST):
        raise B9Halt(f"no snapshot at {B9_MANIFEST}: run --b9-snapshot first (once)")
    with open(B9_MANIFEST) as fh:
        man = json.load(fh)
    raw = {}
    for rel, want in sorted(man["md5"].items()):
        with open(os.path.join(B9_INPUTS, rel), "rb") as fh:
            b = fh.read()
        got = _md5_bytes(b)
        if got != want:
            raise B9Halt(f"snapshot file {rel} md5 {got} != manifest {want} — HALT")
        raw[rel] = b
    return man, raw


def _b9_month_ends(s, name):
    """Daily level -> calendar-month-end level (PeriodIndex 'M'). FAIL-CLOSED: inside the window,
    the last bar of each month must fall in that month's final 5 calendar days."""
    import pandas as pd
    s = s[s.notna()].sort_index()       # non-trading rows only; month coverage is asserted below
    per = s.index.to_period("M")
    last_dt = pd.Series(s.index, index=s.index).groupby(per).max()
    lvl = s.groupby(per).last()
    short = last_dt[(last_dt.dt.days_in_month - last_dt.dt.day) > 4]
    short = short[short.index <= pd.Period(B9_WINDOW[1], "M")]
    if len(short):
        raise B9Halt(f"{name}: month(s) whose last bar is >4 days before month-end: "
                     f"{[str(p) for p in short.index[:10]]}")
    return lvl


def _b9_require(series, periods, name):
    """Every period present and finite — no dropna that shortens a window."""
    import numpy as np
    x = series.reindex(periods)
    bad = x.index[~np.isfinite(x.to_numpy(dtype=float))]
    if len(bad):
        raise B9Halt(f"{name}: missing/non-finite for {len(bad)} month(s), first {[str(p) for p in bad[:6]]}")
    return x.astype(float)


def _b9_load(man, raw):
    """All legs as monthly PeriodIndex series + the input-validation census (checks a–d)."""
    import pandas as pd
    census = {"input_md5": dict(sorted(man["md5"].items()))}
    # ---- French: the first table of each file (VW monthly) ----
    f3 = _ff_parse(raw[f"ff/{B9_FF_FILES['factors']}"])
    m6 = _ff_parse(raw[f"ff/{B9_FF_FILES['mom6']}"])
    b32 = _ff_parse(raw[f"ff/{B9_FF_FILES['bmop32']}"])
    for df in (f3, m6, b32):
        df.index = df.index.to_period("M")
    ff = {"FFMKT": (f3["Mkt-RF"] + f3["RF"]), "MOM_F": m6[B9_MOM_COL], "SVP_F": b32[B9_SVP_COL]}
    for k, v in ff.items():
        if (v <= -0.99).any():
            raise B9Halt(f"French {k}: sentinel value (<= -0.99) present — HALT")
    census["ff_span"] = {k: [str(v.index[0]), str(v.index[-1])] for k, v in ff.items()}
    # ---- yfinance snapshot ----
    yfd = {t: pd.read_csv(io.BytesIO(raw[f"yf/{t}.csv"]), index_col="Date", parse_dates=["Date"])
           for t in B9_YF_TICKERS}
    census["yf_span"] = {t: [str(d.index[0].date()), str(d.index[-1].date())] for t, d in yfd.items()}

    # check (a): split-jump detector vs the Stooq split-adjusted close (T-256 rule)
    chk_a = {}
    for t in B9_YF_TICKERS:
        st = pd.read_csv(os.path.join(ROOT, B9_STOOQ[t]))
        st.index = pd.to_datetime(st["<DATE>"].astype(str), format="%Y%m%d")
        j = pd.concat({"s": st["<CLOSE>"].astype(float), "y": yfd[t]["Close"]}, axis=1,
                      sort=True, join="inner")
        div = float((j["s"].pct_change() - j["y"].pct_change()).abs().max())
        chk_a[t] = {"overlap_days": int(len(j)), "max_daily_return_divergence": div}
        if len(j) < 250 or not div <= B9_SPLIT_JUMP_TOL:
            raise B9Halt(f"check (a) {t}: overlap {len(j)} / max divergence {div} vs tol "
                         f"{B9_SPLIT_JUMP_TOL} — HALT")
    census["check_a_split_jump"] = chk_a

    # check (b): fetched SPY Adj Close year-end level ratio vs both local SPY TR files, constant ±0.5%
    chk_b = {}
    for lbl, (rel, y0, y1) in B9_LOCAL_SPY.items():
        loc = pd.read_csv(os.path.join(ROOT, rel), usecols=["Date", "Close"])
        loc.index = pd.to_datetime(loc["Date"].astype(str).str[:10])
        j = pd.concat({"f": yfd["SPY"]["AdjClose"], "l": loc["Close"].astype(float)}, axis=1,
                      sort=True, join="inner")
        ye = j.groupby(j.index.year).tail(1)
        ye = ye[(ye.index.year >= y0) & (ye.index.year <= y1)]
        ratio = ye["f"] / ye["l"]
        dev = float((ratio / ratio.median() - 1.0).abs().max())
        chk_b[lbl] = {"years": [y0, y1], "n_year_ends": int(len(ye)), "ratio_median": float(ratio.median()),
                      "max_abs_dev_from_median": dev}
        if len(ye) != (y1 - y0 + 1) or not dev <= B9_YE_RATIO_TOL:
            raise B9Halt(f"check (b) SPY vs {lbl}: {len(ye)} year-ends, max dev {dev} vs tol "
                         f"{B9_YE_RATIO_TOL} — HALT")
    census["check_b_spy_class"] = chk_b

    # month-end levels and monthly returns of the ETFs (the first return needs a prior month-end)
    me_adj = {t: _b9_month_ends(yfd[t]["AdjClose"], t) for t in B9_YF_TICKERS}
    me_cls = {t: _b9_month_ends(yfd[t]["Close"], t + " Close") for t in B9_YF_TICKERS}
    etf_r = {t: me_adj[t].pct_change().iloc[1:] for t in B9_YF_TICKERS}

    # splice months (mechanical rule, §4) — HALT if not the declared ones
    found = {t: str(etf_r[t].index[0]) for t in ("VOO", "MTUM", "AVUV")}
    census["splice_months"] = found
    if found != B9_SPLICE:
        raise B9Halt(f"splice months {found} != prereg {B9_SPLICE} — HALT for a director ruling")
    if etf_r["SPY"].index[0] > pd.Period(B9_WINDOW[0], "M"):
        raise B9Halt(f"SPY first return {etf_r['SPY'].index[0]} is after the window start — HALT")

    # check (c): corporate-action guard on every ETF monthly return inside the window
    end = pd.Period(B9_WINDOW[1], "M")
    chk_c = {}
    for t in B9_YF_TICKERS:
        r = etf_r[t][etf_r[t].index <= end]
        chk_c[t] = float(r.abs().max())
        if chk_c[t] > B9_MAX_ABS_MONTHLY:
            raise B9Halt(f"check (c) {t}: |monthly return| {chk_c[t]} > {B9_MAX_ABS_MONTHLY} — HALT")
    census["check_c_max_abs_monthly"] = chk_c

    # check (d) (amendment 1): dividends present in VOO/MTUM/AVUV over their actual-ETF months
    chk_d = {}
    for t in ("VOO", "MTUM", "AVUV"):
        p0 = pd.Period(B9_SPLICE[t], "M") - 1
        d0 = yfd[t].index[yfd[t].index.to_period("M") == p0].max()
        d1 = yfd[t].index[yfd[t].index.to_period("M") == end].max()
        yrs = (d1 - d0).days / 365.25
        gap = ((me_adj[t].loc[end] / me_adj[t].loc[p0]) ** (1 / yrs)
               - (me_cls[t].loc[end] / me_cls[t].loc[p0]) ** (1 / yrs))
        chk_d[t] = {"from": str(d0.date()), "to": str(d1.date()), "years": yrs, "gap_per_yr": float(gap)}
        if not (B9_DIV_GAP[0] <= gap <= B9_DIV_GAP[1]):
            raise B9Halt(f"check (d) {t}: Adj-Close-minus-Close CAGR gap {gap:.4%} outside "
                         f"[{B9_DIV_GAP[0]:.1%}, {B9_DIV_GAP[1]:.1%}] — HALT")
    census["check_d_dividend_gap"] = chk_d
    return ff, etf_r, census


def _b9_main_legs(ff, etf_r):
    """§4/§5 legs on the main window: SPY benchmark; VOO/MTUM/AVUV spliced proxy→actual, haircut."""
    import pandas as pd
    per = pd.period_range(B9_WINDOW[0], B9_WINDOW[1], freq="M")
    if len(per) != B9_N_MONTHS:
        raise B9Halt(f"main window has {len(per)} months, prereg says {B9_N_MONTHS}")
    spy = _b9_require(etf_r["SPY"], per, "SPY")
    mkt = _b9_require(ff["FFMKT"], per, "FF market")
    legs, census = {"SPY": spy}, {"haircut": {}, "months_by_source": {}}
    sp = pd.Period(B9_SPLICE["VOO"], "M")      # VOO: SPY-TR + (ER_SPY − ER_VOO)/12 pre-splice
    pre = per[per < sp]
    legs["VOO"] = pd.concat([spy.loc[pre] + (B9_ER["SPY"] - B9_ER["VOO"]) / 12.0,
                             _b9_require(etf_r["VOO"], per[per >= sp], "VOO actual")]).reindex(per)
    census["months_by_source"]["VOO"] = {"proxy_spy_plus_er_diff": int(len(pre)),
                                         "actual": int((per >= sp).sum())}
    for etf, fk in (("MTUM", "MOM_F"), ("AVUV", "SVP_F")):
        sp = pd.Period(B9_SPLICE[etf], "M")
        pre = per[per < sp]
        prox = _b9_require(ff[fk], pre, f"{fk} proxy")
        alpha = float((prox - mkt.loc[pre]).mean())               # monthly, gross of ER
        shift = B9_HAIRCUT * max(alpha, 0.0)
        legs[etf] = pd.concat([prox - shift - B9_ER[etf] / 12.0,
                               _b9_require(etf_r[etf], per[per >= sp], f"{etf} actual")]).reindex(per)
        census["haircut"][etf] = {"proxy": fk, "proxy_months": [str(pre[0]), str(pre[-1])],
                                  "alpha_hat_monthly": alpha, "alpha_hat_annual_x12": alpha * 12,
                                  "shift_monthly": shift}
        census["months_by_source"][etf] = {"proxy_french_haircut": int(len(pre)),
                                           "actual": int((per >= sp).sum())}
    df = pd.DataFrame(legs)[["SPY", "VOO", "MTUM", "AVUV"]]
    if df.isna().any().any():
        raise B9Halt("main legs contain NaN after splice — HALT")
    return df, mkt, census


def _b9_french_legs(ff):
    """§7 French-only sign-test legs (1963-07 → 2026-06), every leg French, haircut over the window."""
    import pandas as pd
    per = pd.period_range(B9_FR_WINDOW[0], B9_FR_WINDOW[1], freq="M")
    if len(per) != B9_FR_N_MONTHS:
        raise B9Halt(f"French window has {len(per)} months, prereg says {B9_FR_N_MONTHS}")
    mkt = _b9_require(ff["FFMKT"], per, "FF market (French-only)")
    legs, census = {"SPY": mkt - B9_ER["SPY"] / 12.0, "VOO": mkt - B9_ER["VOO"] / 12.0}, {}
    for etf, fk in (("MTUM", "MOM_F"), ("AVUV", "SVP_F")):
        prox = _b9_require(ff[fk], per, f"{fk} (French-only)")
        alpha = float((prox - mkt).mean())
        shift = B9_HAIRCUT * max(alpha, 0.0)
        legs[etf] = prox - shift - B9_ER[etf] / 12.0
        census[etf] = {"alpha_hat_monthly": alpha, "alpha_hat_annual_x12": alpha * 12, "shift_monthly": shift}
    return pd.DataFrame(legs)[["SPY", "VOO", "MTUM", "AVUV"]], census


def b9_simulate(legs, w):
    """Annual-rebalance portfolio (§5). Holdings drift monthly; at each December close that is not
    the last month, rebalance to target with cost = B9_COST × Σ|target − pre| deducted that month.
    Path-dependent (drift), hence the loop. Returns (monthly returns, {month: cost/gross})."""
    import numpy as np
    import pandas as pd
    w = np.asarray(w, dtype=float)
    if abs(w.sum() - 1.0) > 1e-12 or (w < 0).any():
        raise B9Halt(f"arm weights {w} do not sum to 1 / negative — HALT")
    R = legs[["VOO", "MTUM", "AVUV"]].to_numpy(dtype=float)
    idx = legs.index
    V = w.copy()
    out = np.empty(len(idx))
    costs = {}
    for k, p in enumerate(idx):
        v0 = V.sum()
        V = V * (1.0 + R[k])
        gross = V.sum()
        if p.month == 12 and k != len(idx) - 1:
            cost = B9_COST * float(np.abs(w * gross - V).sum())
            if cost < 0:
                raise B9Halt("negative rebalance cost — HALT")
            costs[str(p)] = cost / gross
            V = w * (gross - cost)
        out[k] = V.sum() / v0 - 1.0
    return pd.Series(out, index=idx), costs


def _b9_boot(d, block=None):
    """Project-standard moving-block bootstrap of Σd (MetricsEngine.bootstrap_distribution)."""
    import pandas as pd
    from core.metrics_engine import MetricsEngine
    return MetricsEngine.bootstrap_distribution(
        pd.Series(d.to_numpy(), index=d.index.to_timestamp("M")),
        metric_fn=lambda s: float(s.to_numpy().sum()),
        n_iterations=B9_N_BOOT, block_length=block, seed=B9_SEED, confidence=0.95)


def _b9_stats(r_arm, r_bench, with_sens=True):
    """Paired Δ log TW + CI + t + α/TE/IR + regret (§7)."""
    import numpy as np
    d = np.log1p(r_arm) - np.log1p(r_bench)
    n = len(d)
    sd = float(d.std(ddof=1))
    if not np.isfinite(sd) or sd < 1e-12:
        raise B9Halt("degenerate active-return std — HALT")
    b = _b9_boot(d)
    tot = float(d.sum())
    out = {"n_months": n, "dlogtw": tot, "dlogtw_per_yr": tot / (n / 12.0), "tw_ratio": float(np.exp(tot)),
           "ci_low": b["ci_low"], "ci_high": b["ci_high"], "block": b["block_length"],
           "boot_std": b["std"], "p_above_zero": b["p_above_zero"],
           "t_iid": float(d.mean() / (sd / np.sqrt(n))),
           "boot_z": tot / b["std"] if b["std"] > 1e-12 else float("nan"),
           "alpha_ann_log": float(d.mean() * 12), "te_ann": sd * float(np.sqrt(12)),
           "ir_ann": float(d.mean() * 12) / (sd * float(np.sqrt(12)))}
    if with_sens:
        s = _b9_boot(d, B9_SENS_BLOCK)
        out.update(ci_low_b60=s["ci_low"], ci_high_b60=s["ci_high"])
    ra, rb = r_arm.copy(), r_bench.copy()
    ra.index = ra.index.to_timestamp("M")
    rb.index = rb.index.to_timestamp("M")
    worst, rec, recovered = regret(ra, rb)
    out.update(regret_dd=worst, regret_per_10k=10000 * abs(worst), regret_recover_yrs=rec,
               regret_recovered=bool(recovered))
    return out


def _b9_honest_n():
    """§10: read-only honest-N via mbl_gate; N_eff at the pinned registry count + 1 (this trial)."""
    from core.measurement import mbl_gate as g
    n_raw = g.compute_n_effective()
    neff_code = g.compute_n_effective_correlated()           # verifies BOTH pins first
    gi = g.load_n_effective_artifact()["gate_inputs"]

    def neff(n):
        eq = g.n_eff_equicorrelated(n, float(gi["rho_bar"]))
        onc = max(g.N_EFF_FLOOR, min(float(n), n * float(gi["onc_compression"])))
        return max(eq, onc)
    if abs(neff(n_raw) - neff_code) > 1e-9:
        raise B9Halt(f"honest-N identity mismatch {neff(n_raw)} vs {neff_code} — HALT")
    return {"n_raw_registry": n_raw, "n_eff_registry": neff_code, "n_raw_with_this_trial": n_raw + 1,
            "n_eff_with_this_trial": neff(n_raw + 1), "brief_n": B9_BRIEF_N, "brief_n_eff": neff(B9_BRIEF_N),
            "rho_bar": float(gi["rho_bar"]), "onc_compression": float(gi["onc_compression"])}, g


def _b9_smoke(legs, mkt, ff, census):
    import json
    import pandas as pd
    first = legs.index[:12]
    show = legs.loc[first].copy()
    show["FFMKT"] = mkt.loc[first]
    show["MOM_F_raw"] = ff["MOM_F"].reindex(first)
    show["SVP_F_raw"] = ff["SVP_F"].reindex(first)
    pd.set_option("display.width", 200)
    print("[b9 smoke] legs, FIRST 12 months of the window (monthly simple returns):")
    print(show.round(5).to_string())
    print("[b9 smoke] haircut + sources:", json.dumps({k: census[k] for k in ("haircut", "months_by_source")},
                                                       indent=1))
    print("[b9 smoke] input checks:", json.dumps({k: census[k] for k in census if k.startswith("check")
                                                  or k.endswith("span") or k == "splice_months"}, indent=1))
    sub = legs.loc[legs.index[:13]]              # 13 months so the 2000-12 rebalance executes
    for name, w in B9_ARMS.items():
        r, costs = b9_simulate(sub, w)
        print(f"  {name:22} r[0:12] {' '.join(f'{x:+.4f}' for x in r.values[:12])}  cost/gross {costs}")
    print("[b9 smoke] mechanics only — no CI, no headline computed.")


def b9_run(smoke=False):
    import json
    import numpy as np
    import pandas as pd
    from core.metrics_engine import MetricsEngine
    man, raw = _b9_read_snapshot()
    ff, etf_r, census = _b9_load(man, raw)
    legs, mkt, c2 = _b9_main_legs(ff, etf_r)
    census.update(c2)
    if smoke:
        _b9_smoke(legs, mkt, ff, census)
        return None

    res = {"task": "T-380 (B-9)", "prereg": "docs/Sources/prereg_b9_combo_tilts_2026-11-11.md",
           "window": list(B9_WINDOW), "arms": {}, "census": census,
           "conventions": {"er": B9_ER, "cost_per_rebalanced_dollar": B9_COST, "haircut": B9_HAIRCUT,
                           "n_boot": B9_N_BOOT, "seed": B9_SEED, "sens_block": B9_SENS_BLOCK,
                           "rebalance": "annual, December month-end close; none at window end"}}
    rets = {}
    for name, w in B9_ARMS.items():
        r, costs = b9_simulate(legs, w)
        st = _b9_stats(r, legs["SPY"])
        st.update(weights=list(w), n_rebalances=len(costs), total_cost_frac=float(sum(costs.values())))
        res["arms"][name] = st
        rets[name] = r
    # independent recompute of the decision arm's headline from terminal wealth (a second code path)
    tw_arm = float(np.prod(1.0 + rets[B9_DECISION_ARM].to_numpy()))
    tw_spy = float(np.prod(1.0 + legs["SPY"].to_numpy()))
    indep = float(np.log(tw_arm / tw_spy))
    if abs(indep - res["arms"][B9_DECISION_ARM]["dlogtw"]) > 1e-9:
        raise B9Halt(f"headline recompute disagrees: {indep} vs {res['arms'][B9_DECISION_ARM]['dlogtw']}")
    res["decision_arm_independent_recompute"] = {"tw_arm": tw_arm, "tw_spy": tw_spy, "dlogtw": indep}
    res["arm_i_vs_ref"] = _b9_stats(rets[B9_DECISION_ARM], rets[B9_REF_ARM])     # secondary (§3.1)
    a_m, a_v = legs["MTUM"] - legs["SPY"], legs["AVUV"] - legs["SPY"]            # the power premise
    res["power_premise"] = {"rho_active_mtum_avuv": float(np.corrcoef(a_m, a_v)[0, 1]),
                            "te_ann_mtum_leg": float(a_m.std(ddof=1) * np.sqrt(12)),
                            "te_ann_avuv_leg": float(a_v.std(ddof=1) * np.sqrt(12)),
                            "mean_active_ann_mtum_leg": float(a_m.mean() * 12),
                            "mean_active_ann_avuv_leg": float(a_v.mean() * 12),
                            "brief_rho": -0.3, "predicted_t_arm_i": B9_PREDICTED_T}
    subs = {}                                     # descriptive sub-windows: same path, subset of d
    for lbl, start in (("MTUM actual 2013-05..2026-06", "2013-05"), ("both actual 2019-10..2026-06", "2019-10")):
        subs[lbl] = {}
        for name in B9_ARMS:
            m = rets[name].index >= pd.Period(start, "M")
            st = _b9_stats(rets[name][m], legs["SPY"][m], with_sens=False)
            subs[lbl][name] = {k: st[k] for k in ("n_months", "dlogtw", "dlogtw_per_yr", "ci_low",
                                                   "ci_high", "block", "t_iid")}
    res["sub_windows"] = subs
    hn, g = _b9_honest_n()                        # DSR + MinBTL lines (§7, §10)
    d_i = np.log1p(rets[B9_DECISION_ARM]) - np.log1p(legs["SPY"])
    d_ser = pd.Series(d_i.to_numpy(), index=d_i.index.to_timestamp("M"))
    ir = res["arms"][B9_DECISION_ARM]["ir_ann"]
    hn["dsr_decision_arm"] = {
        lbl: {"n": n, "dsr": float(MetricsEngine.deflated_sharpe_ratio(d_ser, n_trials=n, periods=12))}
        for lbl, n in (("n_eff_with_this_trial", hn["n_eff_with_this_trial"]),
                       ("n_raw_with_this_trial", hn["n_raw_with_this_trial"]), ("brief_n_264", B9_BRIEF_N))}
    hn["minbtl_years_at_n_eff"] = (float(g.compute_mbl_min(hn["n_eff_with_this_trial"], ir)) if ir > 0
                                   else float("inf"))
    hn["window_years"] = B9_N_MONTHS / 12.0
    res["honest_n"] = hn
    fl, fc = _b9_french_legs(ff)                  # secondary: French-only sign test
    fr = {"window": list(B9_FR_WINDOW), "haircut": fc, "arms": {}}
    for name, w in B9_ARMS.items():
        r, _costs = b9_simulate(fl, w)
        st = _b9_stats(r, fl["SPY"])
        ra, rb = r.copy(), fl["SPY"].copy()
        ra.index = ra.index.to_timestamp("M")
        rb.index = rb.index.to_timestamp("M")
        frac, nwin, _ci40, _med = rolling_win_and_ci(ra, rb)
        st.update(sign="+" if st["dlogtw"] > 0 else "-", win40y=frac, n40y_windows=nwin)
        fr["arms"][name] = st
    res["french_only"] = fr
    res["h1"] = {"decision_arm": B9_DECISION_ARM, "ci_low": res["arms"][B9_DECISION_ARM]["ci_low"],
                 "met": bool(res["arms"][B9_DECISION_ARM]["ci_low"] > 0)}
    os.makedirs(B9_DIR, exist_ok=True)
    with open(B9_RESULTS, "w") as fh:
        fh.write(json.dumps(res, indent=1, sort_keys=True) + "\n")
    _b9_print(res)
    print(f"\n[b9] results: {B9_RESULTS}  md5 {_md5_file(B9_RESULTS)}")
    return res


def _b9_print(res):
    def rec(st):
        r = st["regret_recover_yrs"]
        return (f"{r:.1f}y" if st["regret_recovered"] else f"NEVER (>={r:.1f}y)") if r == r else "—"
    print("=" * 140)
    print(f"B-9 / T-380 — window {res['window'][0]}→{res['window'][1]}; paired Δ log TW vs 1× SPY-TR; "
          f"block bootstrap {B9_N_BOOT} it, seed {B9_SEED}")
    print("=" * 140)
    print(f"  {'arm':22}{'ΔlogTW':>9}{'/yr':>8}{'ci_low':>9}{'ci_high':>9}{'blk':>4}{'ci_low60':>10}"
          f"{'t_iid':>7}{'α/yr':>8}{'TE':>7}{'regretDD':>10}{'$/10k':>8}{'recover':>14}")
    for name, st in res["arms"].items():
        print(f"  {name:22}{st['dlogtw']:+9.4f}{st['dlogtw_per_yr']*100:+7.2f}%{st['ci_low']:+9.4f}"
              f"{st['ci_high']:+9.4f}{st['block']:>4}{st['ci_low_b60']:+10.4f}{st['t_iid']:7.2f}"
              f"{st['alpha_ann_log']*100:+7.2f}%{st['te_ann']*100:6.2f}%{st['regret_dd']*100:9.1f}%"
              f"{st['regret_per_10k']:8.0f}{rec(st):>14}")
    h = res["h1"]
    print(f"\n  H1 (arm {h['decision_arm']} ci_low > 0): ci_low {h['ci_low']:+.4f} -> "
          f"{'MET' if h['met'] else 'NOT MET'}")
    s = res["arm_i_vs_ref"]
    print(f"  arm (i) vs REF 85/15: dlogTW {s['dlogtw']:+.4f} CI [{s['ci_low']:+.4f},{s['ci_high']:+.4f}] "
          f"(60-blk ci_low {s['ci_low_b60']:+.4f}) t {s['t_iid']:.2f}")
    pp = res["power_premise"]
    print(f"  power premise: realized rho(active MTUM, active AVUV) {pp['rho_active_mtum_avuv']:+.3f} "
          f"(brief -0.3); predicted t {pp['predicted_t_arm_i']} vs measured "
          f"{res['arms'][B9_DECISION_ARM]['t_iid']:.2f}")
    for lbl, d in res["sub_windows"].items():
        print(f"  sub-window {lbl}: " + "; ".join(
            f"{k.split()[0]} {v['dlogtw']:+.3f} [{v['ci_low']:+.3f},{v['ci_high']:+.3f}]" for k, v in d.items()))
    hn = res["honest_n"]
    print("  DSR (arm i): " + "; ".join(f"{k} N={v['n']:.2f} DSR={v['dsr']:.3f}"
                                        for k, v in hn["dsr_decision_arm"].items())
          + f"; MinBTL at N_eff {hn['minbtl_years_at_n_eff']:.1f}y vs window {hn['window_years']:.1f}y")
    print(f"\n  French-only {res['french_only']['window'][0]}->{res['french_only']['window'][1]} sign test:")
    for name, st in res["french_only"]["arms"].items():
        print(f"    {name:22} sign {st['sign']}  dlogTW {st['dlogtw']:+.4f} CI [{st['ci_low']:+.4f},"
              f"{st['ci_high']:+.4f}] blk {st['block']} (60-blk ci_low {st['ci_low_b60']:+.4f})  "
              f"regret {st['regret_dd']*100:.1f}% {rec(st)}  win40y {st['win40y']*100:.0f}%")


if __name__ == "__main__":
    if "--b9-snapshot" in sys.argv:
        b9_snapshot()
    elif "--b9-smoke" in sys.argv:
        b9_run(smoke=True)
    elif "--b9" in sys.argv:
        b9_run()
    else:
        main()
