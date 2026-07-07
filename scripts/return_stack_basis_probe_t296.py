"""T-296 return-stack data-reality probe (reproduces the RSST synthetic basis finding).

Scope only, 0 N_trials. Shows: (1) real RSST/RSBT are too short (2023+); (2) the correct
synthetic is SPY_TR + (MF_leg - cash) because the SPY is the collateral (naive SPY+MF
double-counts the ~5% T-bill yield); (3) even corrected, a ~+4.5%/yr basis vs real RSST
remains (DBMF's MF program != RSST's proprietary program + fees) → level unreliable, a
DIRECTIONAL scoping read only. Verdict/pre-reg: docs/Audit/return_stack_scope_prereg_t296_2026_07_08.md.
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    import numpy as np
    import pandas as pd
    import yfinance as yf

    def tr(t):
        h = yf.Ticker(t).history(period="max", auto_adjust=True)["Close"]
        h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
        return h.pct_change()

    print("=== fund depth (real RSST/RSBT too short for a standalone gauntlet) ===")
    for t in ["RSST", "RSBT", "DBMF"]:
        h = yf.Ticker(t).history(period="max")
        print(f"  {t:5} {h.index[0].date()}→{h.index[-1].date()} ({len(h)}d)")

    rsst, spy, dbmf = tr("RSST"), tr("SPY"), tr("DBMF")
    c = pd.read_parquet(os.path.join(ROOT, "data/macro/DGS3MO.parquet"))["value"].astype(float)
    c.index = pd.to_datetime(c.index)
    cash = (c.dropna() / 100 / 252)
    j = pd.concat({"rsst": rsst, "spy": spy, "dbmf": dbmf}, axis=1).dropna()
    j = j[j.index >= "2023-09-07"]
    tb = cash.reindex(j.index).ffill().fillna(0)

    print(f"\n=== synthetic vs real RSST, {j.index[0].date()}→{j.index[-1].date()} ({len(j)}d) ===")
    real_ann = (1 + j.rsst).prod() ** (252 / len(j)) - 1
    for nm, s in [("naive  SPY + DBMF", j.spy + j.dbmf),
                  ("CORRECT SPY + (DBMF - Tbill)", j.spy + (j.dbmf - tb))]:
        d = s - j.rsst
        ann = (1 + s).prod() ** (252 / len(j)) - 1
        print(f"  {nm:28} corr={s.corr(j.rsst):.3f}  ann-diff={d.mean()*252*100:+.2f}%/yr  "
              f"synth={ann*100:.1f}% (real {real_ann*100:.1f}%)")
    print("\n  → excess-return construction is mandatory (naive double-counts the T-bill yield);")
    print("    even corrected, ~+4.5%/yr basis remains → level unreliable, DIRECTIONAL scoping only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
