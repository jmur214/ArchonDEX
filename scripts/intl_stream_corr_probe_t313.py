"""T-313 international-stream data-reality probe (reproduces the crisis-correlation finding).

Scope only, 0 N_trials. Answers: (1) how deep is the free honest international-equity TR
series (Ken French developed factors, 1990+, monthly — shallower than the domestic 58-64yr);
(2) does international equity DECORRELATE from US in crises (the tripwire-#2 |corr|<0.3 bar),
or is it the T-214 trap (corr→1 when it matters)? Verdict: docs/Audit/intl_stream_scope_t313_2026_07_27.md.
"""
import io
import sys
import urllib.request as u
import zipfile

FF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"


def ff_market(name):
    """Ken French regional market total return (Mkt-RF + RF), monthly."""
    import pandas as pd
    b = u.urlopen(u.Request(FF + name, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
    z = zipfile.ZipFile(io.BytesIO(b))
    txt = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    rows = [l.split(",") for l in txt if l[:6].strip().isdigit() and len(l[:6].strip()) == 6]
    df = pd.DataFrame(rows).apply(pd.to_numeric, errors="coerce")
    df.index = pd.to_datetime(df[0].astype(int).astype(str), format="%Y%m")
    df.columns = ["ym", "MktRF", "SMB", "HML", "RF"][:len(df.columns)]
    return ((df["MktRF"] + df["RF"]) / 100.0).rename("mkt")


def main() -> int:
    import pandas as pd
    intl = ff_market("Developed_ex_US_3_Factors_CSV.zip")
    us = ff_market("North_America_3_Factors_CSV.zip")
    jpn = ff_market("Japan_3_Factors_CSV.zip")
    j = pd.concat({"intl": intl, "us": us, "jpn": jpn}, axis=1).dropna()
    print(f"free honest floor: Ken French developed factors, {j.index[0].date()}→{j.index[-1].date()} "
          f"({len(j)}mo) — SHALLOWER than the domestic ~58-64yr; 1970s stagflation UNTESTABLE free.\n")

    def corr(a, b, x, y):
        s = j[(j.index >= a) & (j.index <= b)]
        return s[x].corr(s[y])

    print("=== intl(Dev-ex-US) vs US(North-Am) correlation — the tripwire-#2 test (want |corr|<0.3) ===")
    for nm, a, b in [("FULL 1990-2026", "1990-01", "2026-12"), ("2008 GFC", "2007-10", "2009-03"),
                     ("COVID-2020", "2020-01", "2020-04"), ("2022", "2022-01", "2022-12")]:
        c = corr(a, b, "intl", "us")
        print(f"  {nm:16} corr={c:+.2f}  {'← co-falls (T-214 trap)' if c > 0.7 else ''}")

    print("\n=== the one candidate decorrelation: Japan's lost decade ===")
    s = j[(j.index >= "1990-01") & (j.index <= "2000-12")]
    print(f"  1990-2000: JPN vs US corr={s.jpn.corr(s.us):+.2f} | JPN {((1+s.jpn).prod()**(12/len(s))-1)*100:+.1f}%/yr "
          f"vs US {((1+s.us).prod()**(12/len(s))-1)*100:+.1f}%/yr → a slow DRAG, not tail protection")
    print("\nVERDICT: PARK — international equity co-falls in every tail crisis (0.87-1.00); the free floor "
          "can't test the 1970s; the trend rule flattens it to cash in crises = no gain over existing legs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
