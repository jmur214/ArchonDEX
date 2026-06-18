#!/usr/bin/env python3
"""T-206 Task 1 diagnostic — book-level factor decomposition (HAC).

Regresses a backtest book's daily excess return on Fama-French 5 + Momentum
(cached Ken-French data via core.factor_decomposition) with Newey-West/HAC SEs
(the honest path — un-inflates the alpha t-stat vs the OLS defect in
factor_decomposition.py:200-213). Answers "how much of the Sharpe is beta?".

Usage:
  python -m scripts.factor_decomp_book_t206 --book /path/to/portfolio_snapshots.csv
The book CSV needs a `timestamp` + `equity` column (the standard snapshot schema).
"""
import argparse
import pandas as pd
import numpy as np
import statsmodels.api as sm
import core.factor_decomposition as fd

FACTORS = ["MktRF", "SMB", "HML", "RMW", "CMA", "Mom"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="portfolio_snapshots.csv (timestamp,equity)")
    a = ap.parse_args()

    b = pd.read_csv(a.book, parse_dates=["timestamp"]).set_index("timestamp")
    r_book = b["equity"].pct_change().dropna()
    r_book.index = pd.to_datetime(r_book.index).tz_localize(None).normalize()

    ff = fd.load_factor_data()  # cached FF5_CACHE/MOM_CACHE; raises if absent
    ff.index = pd.to_datetime(ff.index).tz_localize(None).normalize()
    cols = [c for c in FACTORS if c in ff.columns]
    fac = ff[cols + (["RF"] if "RF" in ff.columns else [])].copy()
    if fac[cols].abs().mean().mean() > 0.05:   # percent -> decimal
        fac = fac / 100.0

    j = pd.concat([r_book.rename("rb"), fac], axis=1, join="inner").dropna()
    y = j["rb"] - (j["RF"] if "RF" in j else 0.0)
    X = sm.add_constant(j[cols])
    m = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": int(len(j) ** 0.25)})

    print(f"obs={len(j)} ({j.index.min().date()}..{j.index.max().date()})")
    print(f"R^2={m.rsquared:.3f}")
    print(f"alpha_ann={m.params['const']*252*100:.2f}%  t_HAC={m.tvalues['const']:.2f}  p={m.pvalues['const']:.3f}")
    for c in cols:
        print(f"  {c:6s} beta={m.params[c]:+.3f} t={m.tvalues[c]:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
