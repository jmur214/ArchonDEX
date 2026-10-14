"""RR-1 RE-SCORE — window vs book, on series already recorded (N_trials 0).

§4's two books disagree in the sign of RR-1's Sharpe effect, and both their window and their
harness differ. This holds the window fixed: the 26-year anchor's series restricted to the
T-196 feature pairs' 3,269 days, against the foundry baseline book on the same days, all four
series resampled with the same block starts. Pre-registration (rules, gates, and the reading
of every outcome, fixed before computing):
docs/Measurements/2026-09/rr1_rescore/WINDOW_VS_BOOK_PREREG.md.

Usage (--out is the only way a file is written; omit it to re-check without touching records):
  python scripts/rr1_window_vs_book.py --records docs/Measurements/2026-09/rr1_rescore \
      --trade-logs data/trade_logs [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from rr1_paired_delta import _equity_returns, _gate, paired, sharpe

CELLS = ("t196_triple_witching", "t196_january", "t196_mom_12_1")
ARMS = ("before", "after")

READINGS = {
    1: "No result — a gate failed.",
    2: "The two books still disagree within the same window, and the disagreement is "
       "established: RR-1's effect on Sharpe depends on the book, not only on the period.",
    3: "The window is the likelier explanation: on 2012–2024 the anchor book moves the same way "
       "as the foundry book. Not established at 95%.",
    4: "Unresolved: the books point in opposite directions within the same window, but their "
       "difference is not established; neither window nor book is identified.",
}


def _day_index(s: pd.Series) -> pd.Series:
    s = s.copy()
    s.index = pd.to_datetime(s.index).normalize()
    return s


def _foundry(rec_dir: Path) -> tuple[dict, pd.DatetimeIndex, list]:
    """The baseline column per arm, the feature pairs' common days, and the gate rows."""
    gates, base, days = [], {}, None
    for arm in ARMS:
        cols = []
        for cell in CELLS:
            rec = json.loads((rec_dir / f"{cell}_{arm}.json").read_text())
            df = pd.read_csv(rec_dir / rec["series_file"], index_col="date", parse_dates=True)
            cols.append((_day_index(df["baseline"].dropna()), rec["harness_rows"][0]["baseline_sharpe"]))
            for c in ("with_candidate", "baseline"):
                ix = _day_index(df[c].dropna()).index
                days = ix if days is None else days.intersection(ix)
        same = all(cols[0][0].equals(s) for s, _ in cols[1:])
        print(f"  gate foundry {arm} baseline identical across the three cells: {'OK' if same else 'FAIL'}")
        gates.append({"series": f"foundry {arm} identical across cells", "ok": same})
        gates += _gate([(f"foundry {arm} baseline", sharpe(cols[0][0].to_numpy()), cols[0][1])])
        base[arm] = cols[0][0]
    return base, days, gates


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True, type=Path)
    ap.add_argument("--trade-logs", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=None,
                    help="where to write the result JSON. Omitted = print only, write nothing.")
    a = ap.parse_args()

    arec = {arm: json.loads((a.records / f"anchor26_{arm}.json").read_text()) for arm in ARMS}
    anchor = {arm: _day_index(_equity_returns(a.trade_logs / arec[arm]["run_id"] / "portfolio_snapshots.csv"))
              for arm in ARMS}
    gates = _gate([(f"anchor {arm} full window", sharpe(anchor[arm].to_numpy()), arec[arm]["sharpe"])
                   for arm in ARMS])
    base, days, fgates = _foundry(a.records)
    gates += fgates
    missing = {arm: int(len(days.difference(anchor[arm].index))) for arm in ARMS}
    print(f"  gate the {len(days)} feature-pair days present in both anchor arms: "
          f"missing {missing} {'OK' if not any(missing.values()) else 'FAIL'}")
    gates.append({"series": "anchor covers the window", "missing": missing, "ok": not any(missing.values())})

    res = {"n_days": len(days), "window": [str(days.min().date()), str(days.max().date())],
           "gate": gates, "n_trials": 0, "prereg": "WINDOW_VS_BOOK_PREREG.md",
           "method": "moving-block bootstrap, same block starts for all four series, "
                     "block 19, 1,000 iter, seed 0"}
    if not all(g["ok"] for g in gates):
        res.update({"row": 1, "reading": READINGS[1]})
    else:
        s = {"anchor_before": anchor["before"].loc[days].to_numpy(),
             "anchor_after": anchor["after"].loc[days].to_numpy(),
             "foundry_before": base["before"].loc[days].to_numpy(),
             "foundry_after": base["after"].loc[days].to_numpy()}
        d_anchor = lambda x: sharpe(x["anchor_after"]) - sharpe(x["anchor_before"])
        d_foundry = lambda x: sharpe(x["foundry_after"]) - sharpe(x["foundry_before"])
        res["deltas"] = paired(s, {"D_did": lambda x: d_anchor(x) - d_foundry(x),
                                   "d_anchor_window": d_anchor, "d_foundry": d_foundry})
        lo, hi = res["deltas"]["D_did"]["ci95"]
        row = 2 if (lo > 0 or hi < 0) else (3 if res["deltas"]["d_anchor_window"]["point"] <= 0 else 4)
        res.update({"row": row, "reading": READINGS[row]})
        for k, d in res["deltas"].items():
            print(f"  {k:<16} {d['point']:+.3f}  95% CI [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}]"
                  f"  share Δ≤0 {d['share_le_0']:.3f}")
    if a.out:
        a.out.write_text(json.dumps(res, indent=1))
    print(f"  row {res['row']}: {res['reading']}\n"
          + (f"-> {a.out}" if a.out else "(printed only; pass --out to write a record)"))
    return 2 if res["row"] == 1 else 0


if __name__ == "__main__":
    sys.exit(main())
