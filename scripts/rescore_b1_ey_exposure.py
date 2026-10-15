"""scripts/rescore_b1_ey_exposure.py — POST-HOC exposure re-score of the two B-1 value signals.

Director ruling 2026-10-15 (the AZO/MTD/NVR HIGH, `1bb076b`): AZO, MTD and NVR sit at exactly
1/10 of their true price across their whole history in the canonical cache. Returns are
unaffected (a uniform factor), but two signals take the price LEVEL through
market_cap = latest_close × shares_diluted: `value_earnings_yield_v1`
(value_earnings_yield_edge.py:87) and `value_book_to_market_v1` (value_book_to_market_edge.py:81).
Extended to both on 2026-10-15 by the director's correction.

The re-score: the three are REMOVED from the existing panel (the ruled treatment is a ticker-kind
exclusion, so removal — never a ×10 repair). The method is the run's, by import — the harness's
own `evaluate_signal`, `leg_series`, `bh_adjust` and `classify` — on the same short-window months,
seed, bootstrap and BH family. The family is the SHORT-WINDOW one (6 members), where the run
placed both signals: their two re-scored p-values replace the recorded ones, and the other four
keep their recorded p-values from the run's own results.

Stated limitation: removing rows does not recompute the edge's quintile basket. The names the
three displaced from the top quintile stay out; restoring them means re-running the edge, a
reconstruction this unit does not do.

DECISION RULE (ruled before any number, `1bb076b`), PER SIGNAL: one-sided. Still fails after BH →
a dated "no change to the verdict" note. CLEARS → "CONTAMINATED — UNTESTED", never "clear". The
other signals and H1 NOT MET stand either way. +1 trial per re-scored signal: N_trials 4 → 6.

    PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    OMP_DYNAMIC=FALSE python -m scripts.rescore_b1_ey_exposure \
        --panel data/research/b1/full_2a/signal_panel_d9d449d17f8f.parquet \
        --recorded data/research/b1/run1/results_5de36b89e0ad.json \
        --out data/research/b1/rescore_ey_ex3/
"""
from __future__ import annotations

import sys

from scripts.build_signal_panel_b1 import ENV_PINS, env_pin_violations  # noqa: E402

if __name__ == "__main__":
    _bad = env_pin_violations()
    if _bad:
        print("[B1-RESCORE] REFUSING: determinism env pins wrong — " + "; ".join(_bad),
              file=sys.stderr)
        sys.exit(3)

import argparse  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import List, Optional, Tuple  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scripts import build_signal_panel_b1 as panel_mod  # noqa: E402
from scripts import raw_signal_decile_b1 as h  # noqa: E402

SIGNALS = ("value_earnings_yield_v1", "value_book_to_market_v1")
SIGNAL = SIGNALS[0]
REMOVED = ("AZO", "MTD", "NVR")
FAMILY = "short_window"


def rescore(panel: pd.DataFrame, census: dict, recorded: dict, price_root: Path,
            seed: int, iters: int, block: int) -> Tuple[dict, List[str]]:
    halts: List[str] = []
    for sig in SIGNALS:
        if panel_mod.FAMILY.get(sig) != FAMILY:
            return {}, [f"{sig} is not in the {FAMILY} family"]
    present = sorted(set(panel.index.get_level_values("ticker")) & set(REMOVED))
    if present != sorted(REMOVED):
        return {}, [f"expected all of {REMOVED} in the panel, found {present}"]
    reduced = panel.drop(index=list(REMOVED), level="ticker")
    end = max(reduced.index.get_level_values("month_end"))
    months, frames = h.window_frames(reduced, panel_mod.SHORT_WINDOW_START, end)
    rec_bench = recorded["benchmarks"][FAMILY]
    if len(months) != rec_bench["n_months"]:
        halts.append(f"{len(months)} months != the run's {rec_bench['n_months']}")
    spy_df = panel_mod.load_ohlcv("SPY", price_root)
    all_me = panel_mod.month_ends(spy_df.index, h.MAIN_START,
                                  (end + pd.offsets.MonthBegin(1)).strftime("%Y-%m"))
    spy = []
    for m in months:
        r, how = panel_mod.forward_return(spy_df, m, all_me[all_me.index(m) + 1])
        if how != "full":
            halts.append(f"SPY forward return at {m.date()} is {how}")
        spy.append(r)
    spy = np.asarray(spy)
    ew_legs = [fr.index[fr[h.FWD].notna()] for fr in frames]
    E = h.leg_series(ew_legs, [fr[h.FWD] for fr in frames])
    ew = (E["gross"] - E["cost"]).to_numpy()
    rows = {sig: h.evaluate_signal(sig, bool(census["signals"][sig]["sparse"]), frames, spy, ew,
                                   ew_legs, seed, iters, block) for sig in SIGNALS}

    fam_rows = [r for r in recorded["rows"] if r["family"] == FAMILY]
    if len(fam_rows) != 6:
        halts.append(f"recorded {FAMILY} family has {len(fam_rows)} members, not 6")
    ps = [rows[r["signal"]]["ic_p"] if r["signal"] in rows else r["ic_p"] for r in fam_rows]
    adj, rej = h.bh_adjust(ps)
    for r, a, j in zip(fam_rows, adj, rej):
        if r["signal"] in rows:
            rows[r["signal"]]["ic_p_bh"], rows[r["signal"]]["ic_bh_reject"] = a, j
    out = {}
    for sig in SIGNALS:
        h.classify(rows[sig])
        # the ruled rule keys on BH alone: "still fails after BH" → no change; "clears" →
        # CONTAMINATED — UNTESTED (never "clear"). The wealth leg is reported beside it.
        out[sig] = {"recorded": next(r for r in fam_rows if r["signal"] == sig),
                    "rescored": rows[sig],
                    "decision": ("CONTAMINATED — UNTESTED" if rows[sig]["clears_ic"]
                                 else "no change to the verdict")}
    return {"signals": out, "family": FAMILY, "removed": list(REMOVED), "n_months": len(months),
            "family_p_used": dict(zip([r["signal"] for r in fam_rows], ps)),
            "label": "POST-HOC EXPOSURE CHECK — not a measurement of record; one-sided"}, halts


def forbid_network() -> None:
    """OFFLINE BY CONSTRUCTION, not by declaration. This script reads three local files (the
    panel, the run's results JSON, SPY's cached CSV) and never fetches. Its imports reach the
    data layer, where a keyless process silently falls back to yfinance (the env lock's reason),
    so every socket connect and DNS lookup is made to RAISE for the life of the process: a
    fetch from here cannot succeed quietly."""
    import socket

    def _refuse(*_a, **_k):
        raise RuntimeError("rescore_b1_ey_exposure is offline by design: network access refused")
    socket.socket.connect = _refuse
    socket.socket.connect_ex = _refuse
    socket.create_connection = _refuse
    socket.getaddrinfo = _refuse


def main(argv: Optional[List[str]] = None) -> int:
    forbid_network()                                     # FIRST — before any import does work
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--panel", required=True)
    ap.add_argument("--recorded", required=True, help="the run's results JSON (run1)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if Path.cwd().resolve() != panel_mod.ROOT:
        print(f"[B1-RESCORE] REFUSING: cwd {Path.cwd()} is not the worktree root", file=sys.stderr)
        return 5
    panel, census, halts = h.load_panel_checked(Path(a.panel))
    recorded = json.loads(Path(a.recorded).read_text())
    meta = recorded.get("meta", {})
    if meta.get("panel_canonical_md5") != census.get("panel_canonical_md5"):
        halts.append("the recorded results were not computed on this panel")
    res: dict = {}
    if not halts:
        res, halts = rescore(panel, census, recorded, panel_mod.ROOT / "data" / "processed",
                             int(meta["seed"]), int(meta["boot_iter"]), int(meta["boot_block_months"]))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    panel_mod.assert_disk_floor(out)
    if halts:
        (out / "halt.json").write_text(json.dumps({"halt_reasons": halts}, indent=2))
        print("[B1-RESCORE] HALT — " + "; ".join(halts), file=sys.stderr)
        return 2
    body = {"rows": [v["rescored"] for v in res["signals"].values()], "calendar": [],
            "benchmarks": {}, "families": {},
            "h1": {s: v["decision"] for s, v in res["signals"].items()}}
    digest = h.canonical_results_md5(body)
    res["meta"] = {"panel_canonical_md5": census["panel_canonical_md5"],
                   "recorded_results_md5": meta.get("results_canonical_md5"),
                   "seed": meta["seed"], "boot_iter": meta["boot_iter"],
                   "boot_block_months": meta["boot_block_months"],
                   "env_pins": {k: os.environ.get(k) for k in ENV_PINS},
                   "rescore_canonical_md5": digest}
    (out / f"rescore_{digest[:12]}.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"[B1-RESCORE] -> {out / f'rescore_{digest[:12]}.json'}  canonical md5 {digest}  "
          f"decisions: {json.dumps({s: v['decision'] for s, v in res['signals'].items()})}")
    return 0


if __name__ == "__main__":
    # load_local_env: offline by design — reads only the panel, the run's results and SPY's
    # cached CSV; main() calls forbid_network() first, so any fetch RAISES instead of falling
    # back to a keyless provider (tests/test_rescore_b1_ey_exposure.py locks both).
    sys.exit(main())
