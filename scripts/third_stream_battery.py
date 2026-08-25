"""Third-stream candidate battery — the standing same-day verdict tool (free data, $0).

Formalizes T-313's direct crisis-correlation measure into a reusable screen. Any
candidate proposed as the genuinely-independent 3rd return stream (tripwire #2 from
T-305/T-248: "awaits 3rd") gets the same fast-verdict panel, on the same free
substrate, against the same FROZEN bar — instead of a bespoke one-off probe.

WHY THIS SHAPE. T-313 refuted international equity at the DATA-REALITY stage for $0
by measuring crisis correlation DIRECTLY, before burning a trial on a backtest. That
is the reusable move: a 3rd stream must go uncorrelated-or-SHORT in FAST crashes, and
that property is cheap to falsify. The battery makes the cheap falsification standard.

THE BAR IS NOT RE-DECLARED HERE. `CORR_MAX` is imported from paper_trader.dbmf_shadow
(T-316 `GATE_A_CORR_MAX`) so the backtest screen and the live forward gate can never
drift apart.

MEASUREMENT DISCIPLINE
  * `[NN-SHARPE-CI]` — every correlation carries a paired block-bootstrap CI, and the
    verdict reads the CI, never the point estimate. A candidate is only PASSed when
    the whole interval clears the bar; a straddling interval is UNRESOLVED, not a pass.
    Crisis windows are SHORT by construction, so UNRESOLVED is a common and honest
    outcome — that is the screen telling you the window cannot settle the question.
  * `[NN-FAIL-CLOSED]` — a window the candidate's history does not span returns
    NOT_COVERED + the reason. It never silently shrinks to the overlap and reports the
    resulting number as if it were the window's answer.
  * T-256 — prices come from `data/processed/tr_reconciled/` (dividend-reconciled),
    never split-only Stooq.

SIGNED vs ABSOLUTE. The primary screen is the SIGNED T-316 form (corr <= +0.30):
a strongly NEGATIVE crisis correlation is the property we actually want (the stream
goes short when equity crashes), so |corr| would wrongly reject the best candidates.
The two-sided |corr| reading from the T-305 tripwire-#2 wording is reported alongside
for comparability; where they disagree the panel says so.

Usage:
  python scripts/third_stream_battery.py --ticker DBMF
  python scripts/third_stream_battery.py --file path.csv --file-kind price --label MYCAND
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paper_trader.dbmf_shadow import GATE_A_CORR_MAX as CORR_MAX   # noqa: E402  THE frozen bar

TR = ROOT / "data/processed/tr_reconciled"
CASH = ROOT / "data/research/substrate_multidecade/cash_daily.csv"
OUT_DIR = ROOT / "data/research"
BENCHMARK = "SPY"
TD = 252
BLOCK, ITERS, SEED, CONF = 21, 1000, 0, 95
MIN_OBS = 30            # below this a window cannot resolve a correlation at all
MIN_COVERAGE = 0.90     # candidate must span >=90% of the benchmark's days in a window

# The crisis windows. Fast crashes are the discriminating test (T-313/T-214:
# everything correlates in a fast crash; a real 3rd stream does not).
#
# WINDOW PROVENANCE — these are NOT re-invented here. GFC/COVID/2022 are taken
# VERBATIM from the merged T-311 deep re-verify (`scripts/deep_reverify_sleeve_t311.py`,
# CRISES) so the battery and the sleeve's own drawdown-structural test speak about
# the same calendar; 2018-Q4 is added in the identical month-boundary style because
# T-311's deep substrate predates it as a named crisis.
#
# A tight peak->trough COVID window (2020-02-19..2020-03-23) was REJECTED during
# construction: it holds only 24 trading days, which is below MIN_OBS and therefore
# UNSCOREABLE FOR EVERY CANDIDATE FOREVER — a standing tool whose most discriminating
# window can never return a verdict is broken. The window was chosen on OBSERVATION
# COUNT and repo convention, never on the answer it produced for any candidate.
CRISES: dict[str, tuple[str, str]] = {
    "2008 GFC":     ("2007-10-01", "2009-03-31"),
    "2018-Q4":      ("2018-10-01", "2018-12-31"),
    "COVID-2020":   ("2020-02-01", "2020-04-30"),
    "2022":         ("2022-01-01", "2022-10-31"),
}


def _tr_close(ticker: str) -> pd.Series:
    """Dividend-reconciled daily close (T-256 substrate). Fails loudly if absent."""
    f = TR / f"{ticker.upper()}_1d.csv"
    if not f.exists():
        raise SystemExit(
            f"FAIL-CLOSED: no TR-reconciled series for {ticker!r} at {f}.\n"
            f"  Available: {' '.join(sorted(p.stem.replace('_1d', '') for p in TR.glob('*_1d.csv')))}\n"
            f"  Do NOT substitute split-only Stooq (T-256: it misses dividends)."
        )
    df = pd.read_csv(f, parse_dates=["Date"], index_col="Date")
    return df["Close"].sort_index()


def load_candidate(args) -> tuple[pd.Series, str]:
    """Daily simple returns for the candidate + a display label."""
    if args.ticker:
        return _tr_close(args.ticker).pct_change().dropna(), args.ticker.upper()
    f = Path(args.file)
    if not f.exists():
        raise SystemExit(f"FAIL-CLOSED: candidate file not found: {f}")
    df = pd.read_csv(f, parse_dates=[0], index_col=0).sort_index()
    s = df.iloc[:, 0].astype(float).dropna()
    # Never GUESS price-vs-return: a return series read as prices is silently wrong.
    s = s.pct_change().dropna() if args.file_kind == "price" else s
    return s, (args.label or f.stem)


def load_cash() -> pd.Series:
    if not CASH.exists():
        raise SystemExit(f"FAIL-CLOSED: cash series missing at {CASH} (T-306 substrate).")
    return pd.read_csv(CASH, parse_dates=["date"], index_col="date")["cash_ret"].sort_index()


def block_ci_pairs(x: np.ndarray, y: np.ndarray, fn, block: int,
                   iters: int = ITERS, seed: int = SEED, conf: int = CONF) -> tuple[float, float]:
    """Paired stationary block-bootstrap CI (the `[NN-SHARPE-CI]` standard).

    Resamples ROW-blocks so x and y move together — bootstrapping the two series
    independently would destroy the very dependence being measured.
    """
    rng = np.random.default_rng(seed)
    n = len(x)
    nb = int(np.ceil(n / block))
    out = []
    for _ in range(iters):
        starts = rng.integers(0, n, nb)
        idx = np.concatenate([np.arange(s, s + block) % n for s in starts])[:n]
        v = fn(x[idx], y[idx])
        if v == v:                      # drop degenerate resamples (zero-variance block draw)
            out.append(v)
    if len(out) < iters // 10:
        return float("nan"), float("nan")
    lo, hi = np.percentile(out, [(100 - conf) / 2, 100 - (100 - conf) / 2])
    return float(lo), float(hi)


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.std() < 1e-12 or b.std() < 1e-12:      # `[NN-FP-GUARDS]` tolerance, never == 0
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def window_panel(cand: pd.Series, bench: pd.Series, start: str, end: str) -> dict:
    """Coverage-checked, CI-aware correlation verdict for one window."""
    bwin = bench.loc[start:end]
    if bwin.empty:
        return {"status": "NOT_COVERED", "reason": f"benchmark {BENCHMARK} has no data in {start}..{end}"}

    cwin = cand.loc[start:end]
    coverage = len(cwin) / len(bwin)
    c_first, c_last = cand.index.min().date(), cand.index.max().date()
    if len(cwin) == 0:
        side = "begins after" if cand.index.min() > pd.Timestamp(end) else "ends before"
        return {"status": "NOT_COVERED", "coverage": 0.0,
                "reason": f"candidate history ({c_first}..{c_last}) {side} this window"}
    if coverage < MIN_COVERAGE:
        return {"status": "PARTIAL", "coverage": round(coverage, 3),
                "reason": (f"candidate spans only {coverage:.0%} of the window's {len(bwin)} "
                           f"benchmark days (history {c_first}..{c_last}) — NOT scored: a "
                           f"correlation on the overlap is not this window's correlation")}

    j = pd.concat({"c": cwin, "b": bwin}, axis=1).dropna()
    n = len(j)
    if n < MIN_OBS:
        return {"status": "UNRESOLVED", "n": n, "coverage": round(coverage, 3),
                "reason": f"n={n} below MIN_OBS={MIN_OBS} — too few days to resolve a correlation"}

    x, y = j["c"].values, j["b"].values
    point = _corr(x, y)
    blk = max(5, min(BLOCK, n // 5))
    lo, hi = block_ci_pairs(x, y, _corr, block=blk)

    if lo != lo or point != point:
        return {"status": "UNRESOLVED", "n": n, "reason": "degenerate variance — CI not estimable"}
    if hi <= CORR_MAX:
        status, why = "PASS", f"whole CI clears the +{CORR_MAX:.2f} bar"
    elif lo > CORR_MAX:
        status, why = "FAIL", f"whole CI sits above the +{CORR_MAX:.2f} bar — co-moves"
    else:
        status, why = "UNRESOLVED", f"CI straddles +{CORR_MAX:.2f} — this window cannot settle it"
    return {"status": status, "n": n, "coverage": round(coverage, 3), "corr": round(point, 3),
            "ci": [round(lo, 3), round(hi, 3)], "block": blk, "reason": why,
            "abs_corr_screen": ("pass" if abs(point) <= CORR_MAX else "fail")}


def drag_vs_cash(cand: pd.Series, cash: pd.Series) -> dict:
    """Long-run carry: annualized excess-of-cash return, CI-aware (T-333 framing)."""
    j = pd.concat({"c": cand, "r": cash.reindex(cand.index).ffill()}, axis=1).dropna()
    ex = (j["c"] - j["r"]).values
    ann = float(np.mean(ex) * TD * 100)
    lo, hi = block_ci_pairs(ex, ex, lambda a, _b: float(np.mean(a) * TD * 100), block=BLOCK)
    if hi < 0:
        verdict = "DRAG — costs more than cash over the full sample (CI entirely below 0)"
    elif lo > 0:
        verdict = "CARRY-POSITIVE — beats cash over the full sample (CI entirely above 0)"
    else:
        verdict = "INDETERMINATE — CI straddles 0; the sample cannot call carry either way"
    return {"ann_excess_of_cash_pct": round(ann, 2), "ci": [round(lo, 2), round(hi, 2)],
            "n": len(j), "span": [str(j.index[0].date()), str(j.index[-1].date())],
            "verdict": verdict}


def main() -> int:
    p = argparse.ArgumentParser(description="Third-stream candidate fast-verdict battery")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--ticker", help=f"TR-reconciled ticker (from {TR.name}/)")
    g.add_argument("--file", help="CSV: date column + one value column")
    p.add_argument("--file-kind", choices=["price", "return"],
                   help="REQUIRED with --file; never guessed")
    p.add_argument("--label", help="display label for --file input")
    p.add_argument("--json", help="write the panel to this path")
    a = p.parse_args()
    if a.file and not a.file_kind:
        raise SystemExit("FAIL-CLOSED: --file needs --file-kind price|return (guessing is a silent-wrongness trap)")

    cand, label = load_candidate(a)
    bench = _tr_close(BENCHMARK).pct_change().dropna()
    cash = load_cash()

    windows = {nm: window_panel(cand, bench, s, e) for nm, (s, e) in CRISES.items()}
    full_s, full_e = str(max(cand.index.min(), bench.index.min()).date()), str(cand.index.max().date())
    windows["FULL sample"] = window_panel(cand, bench, full_s, full_e)
    drag = drag_vs_cash(cand, cash)

    scored = {k: v for k, v in windows.items() if k in CRISES and v["status"] in ("PASS", "FAIL", "UNRESOLVED")}
    n_cov = len(scored)
    if n_cov == 0:
        screen = "NO VERDICT — the candidate's history spans none of the crisis windows"
    elif any(v["status"] == "FAIL" for v in scored.values()):
        screen = "REJECT — co-moves with equity in at least one fast crash (the T-214 trap)"
    elif all(v["status"] == "PASS" for v in scored.values()):
        screen = (f"CANDIDATE CLEARS the crisis screen on {n_cov}/{len(CRISES)} windows"
                  + ("" if n_cov == len(CRISES) else " — but NOT on the full crisis set; history is short"))
    else:
        screen = (f"INCONCLUSIVE — {n_cov}/{len(CRISES)} windows covered, none FAIL but not all "
                  f"resolve; the backtest route cannot settle this candidate")

    w = max(len(k) for k in windows)
    print(f"\n=== THIRD-STREAM BATTERY — {label} vs {BENCHMARK} | bar: corr <= +{CORR_MAX:.2f} "
          f"(T-316 GATE_A_CORR_MAX, imported) ===")
    print(f"{'window':{w}}  {'n':>4} {'corr':>7} {'95% CI':>16}  status")
    for nm, r in windows.items():
        if "corr" in r:
            ci = f"[{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}]"
            print(f"{nm:{w}}  {r['n']:>4} {r['corr']:>+7.2f} {ci:>16}  {r['status']}")
        else:
            print(f"{nm:{w}}  {'—':>4} {'—':>7} {'—':>16}  {r['status']}")
        print(f"{'':{w}}    └─ {r['reason']}")

    print(f"\nlong-run carry vs cash ({drag['span'][0]}..{drag['span'][1]}, n={drag['n']}): "
          f"{drag['ann_excess_of_cash_pct']:+.2f}%/yr  CI [{drag['ci'][0]:+.2f}, {drag['ci'][1]:+.2f}]")
    print(f"  └─ {drag['verdict']}")
    print(f"\nSCREEN: {screen}\n")

    payload = {"label": label, "benchmark": BENCHMARK, "corr_max": CORR_MAX,
               "bar_source": "paper_trader.dbmf_shadow.GATE_A_CORR_MAX (T-316 frozen)",
               "substrate": "data/processed/tr_reconciled (T-256 dividend-reconciled)",
               "bootstrap": {"block": BLOCK, "iters": ITERS, "seed": SEED, "conf": CONF},
               "windows": windows, "carry_vs_cash": drag, "screen": screen}
    out = Path(a.json) if a.json else OUT_DIR / f"third_stream_battery_{label.lower()}.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"panel → {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
