"""T-320 aggressive-tilt ADVERSARY probe (reproduces the measured priors; scope only, 0 N_trials).

Measures the two adversaries that SET the per-arm honest priors, so the pre-registration
rests on numbers rather than factor-lore:
  1. momentum crash risk (FF MOM 1927+): 1932 / 2009 / 2001 + the full-sample worst MaxDD;
  2. the QQQ regret: dot-com MaxDD, YEARS underwater, and the RELATIVE-to-SPY drawdown in
     dollars per $10k + whether the relative high was ever regained.
Pre-reg: docs/Audit/aggressive_tilt_prereg_t320_2026_07_27.md.
"""
import io
import sys
import urllib.request as u
import warnings
import zipfile

warnings.filterwarnings("ignore")
FF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"


def ff_monthly(fn, col=1):
    import pandas as pd
    b = u.urlopen(u.Request(FF + fn, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
    z = zipfile.ZipFile(io.BytesIO(b))
    txt = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    rows = [l.split(",") for l in txt if l[:6].strip().isdigit() and len(l[:6].strip()) == 6]
    df = pd.DataFrame(rows).apply(pd.to_numeric, errors="coerce")
    df.index = pd.to_datetime(df[0].astype(int).astype(str), format="%Y%m")
    return df[col] / 100.0


def main() -> int:
    import pandas as pd
    import yfinance as yf

    mom = ff_monthly("F-F_Momentum_Factor_CSV.zip")
    print("=== ADVERSARY 1 — momentum crash risk (FF MOM, monthly) ===")
    for nm, a, b in [("1932 crash", "1932-01", "1932-12"), ("2009 crash", "2009-01", "2009-12"),
                     ("2001", "2001-01", "2001-12")]:
        s = mom[(mom.index >= a) & (mom.index <= b)]
        eq = (1 + s).cumprod()
        print(f"  MOM {nm:11} year={((1+s).prod()-1)*100:+7.1f}%  worst-month={s.min()*100:+6.1f}%  "
              f"in-window MaxDD={((eq/eq.cummax()-1).min())*100:+6.1f}%")
    eq = (1 + mom).cumprod()
    print(f"  MOM full {mom.index[0].date()}→{mom.index[-1].date()}: "
          f"{((1+mom).prod()**(12/len(mom))-1)*100:+.1f}%/yr, worst MaxDD {((eq/eq.cummax()-1).min())*100:.1f}%")

    def m(t):
        h = yf.Ticker(t).history(period="max", auto_adjust=True)["Close"]
        h.index = pd.to_datetime(h.index).tz_localize(None)
        return h.resample("ME").last()

    j = pd.concat({"q": m("QQQ"), "s": m("SPY")}, axis=1).dropna()
    print("\n=== ADVERSARY 2 — the QQQ regret (dollars, not vibes) ===")
    dd = j.q / j.q.cummax() - 1
    t1 = dd.idxmin()
    t0 = j.q.loc[:t1].idxmax()
    rec = j.q[(j.q.index > t1) & (j.q >= j.q.loc[t0])]
    print(f"  dot-com: peak {t0.date()} → trough {t1.date()}  MaxDD={dd.min()*100:.1f}%  "
          f"reclaimed {rec.index[0].date() if len(rec) else 'never'} "
          f"({(rec.index[0]-t0).days/365.25:.1f} yrs underwater)" if len(rec) else "")
    rel = j.q / j.s
    rdd = rel / rel.cummax() - 1
    rt1 = rdd.idxmin()
    rt0 = rel.loc[:rt1].idxmax()
    rrec = rel[(rel.index > rt1) & (rel >= rel.loc[rt0])]
    print(f"  RELATIVE (QQQ/SPY) worst DD={rdd.min()*100:.1f}% → a $10k tilt trails by "
          f"${10000*abs(rdd.min()):,.0f} at the worst point")
    print(f"  relative peak {rt0.date()} → trough {rt1.date()}; regained relative high: "
          f"{rrec.index[0].date() if len(rrec) else 'NEVER (26yr and counting)'}")
    print(f"  era: QQQ {((j.q.iloc[-1]/j.q.iloc[0])**(12/len(j))-1)*100:+.1f}%/yr vs "
          f"SPY {((j.s.iloc[-1]/j.s.iloc[0])**(12/len(j))-1)*100:+.1f}%/yr — ONE era, QQQ is its survivor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
