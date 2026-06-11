"""
scripts/measure_survivor_inflation_t136.py
==========================================
T-2026-06-10-136 Part A.3 — the survivor-inflation measurement, 3 variants.

QUESTION: how much does the survivor-only substrate inflate baseline results,
and does the worst-case delisting band change any go/no-go conclusion (the
adopted Norgate $630 decision rule)?

PRE-REGISTERED:
  - Object: equal-weight daily log-return of the universe, 2000-01-01..2025-12-31
    (the substrate every deep measurement T-129/T-135 rode on). This is the
    SUBSTRATE-level inflation number. (A full PIT-correct arm0 ENGINE re-run
    needs a universe_resolver per-date hook — flagged follow-up, not here.)
  - SURVIVOR universe: every name in data/processed with data (status quo).
  - MEMBERSHIP-CORRECT universe: per date d, names with in_index(t,d)=True
    (fja05680 PIT panel) AND price data. Coverage gap (members lacking any
    price file) reported per year — that residual gap is exactly what
    imputation/Norgate addresses.
  - EXIT CLASSIFICATION (best-effort, flagged per brief): for each membership
    exit, look at the name's price path around the exit date:
      * path CONTINUES >30 trading days past exit  -> "still_listed" (index
        drop for size/sector/etc. — NO imputation; path keeps it honest)
      * path ENDS within 30d of exit AND trailing 126d return <= -30%
                                                   -> "performance" delist
      * path ENDS within 30d of exit, return > -30% -> "merger_like" (terminal
        price embeds deal terms — NO imputation per Shumway)
      * NO price file at all                        -> "missing_path"
        (classified performance for imputation purposes — conservative)
  - VARIANTS (EW portfolio return computed in ARITHMETIC space — a one-day
    -100% event is bounded at the name's 1/N weight, as in a real portfolio;
    log-space averaging would blow unboundedly and is wrong for big events):
      (a) membership-only: EW return of member names with data; no imputation.
      (b) + Shumway imputation: `performance`-class exits imputed at -30%
          (NYSE/AMEX per SEC exchange map) / -55% (Nasdaq or unknown);
          `missing_path` exits are UNCLASSIFIABLE individually -> apply the
          literature prior (~51% of delistings are mergers needing NO
          imputation): expected-value imputation = 0.49 x Shumway value.
      (c) worst-case band: ALL `performance` AND ALL `missing_path` exits at
          -100% on exit date — maximal pessimism (assumes every unknown exit
          was a total-loss delisting).
  - HEADLINE per variant: CAGR + Sharpe (block-bootstrap CI) vs the survivor
    universe; the (b)-vs-(c) spread is the Norgate decision input.
  - Seed 0; no wall-clock in artifact.

Usage: PYTHONHASHSEED=0 python -m scripts.measure_survivor_inflation_t136
"""
from __future__ import annotations

import glob
import json
import sys
import urllib.request
from pathlib import Path


import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine  # noqa: E402
from engines.data_manager.membership import load_membership  # noqa: E402

OUT_DIR = ROOT / "data" / "measurements" / "free_data_wave_t136"
OUT_JSON = OUT_DIR / "survivor_inflation.json"
UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}

START, END = "2000-01-01", "2025-12-31"
SHUMWAY_NYSE, SHUMWAY_NASDAQ, WORST = -0.30, -0.55, -1.00


def _norm(t: str) -> str:
    return str(t).strip().upper().replace(".", "-")


def load_price_panel() -> pd.DataFrame:
    cols = []
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True, usecols=lambda c: c in ("", "Close") or str(c).lower().startswith("date") or c == "Close")
        except Exception:
            continue
        if "Close" not in df.columns or len(df) < 60:
            continue
        df = df[(df.index >= START) & (df.index <= END)]
        if len(df) < 60:
            continue
        # SIMPLE returns: EW portfolio arithmetic must bound a -100% event at
        # the name's 1/N weight (log-space averaging blows up unboundedly).
        cols.append(df["Close"].astype(float).pct_change().rename(
            _norm(f.split("/")[-1].replace("_1d.csv", ""))))
    panel = pd.concat(cols, axis=1).sort_index()
    return panel.loc[:, ~panel.columns.duplicated()]


def exchange_map() -> dict:
    """SEC company_tickers_exchange.json → ticker -> exchange (best-effort)."""
    cache = ROOT / "data" / "universe" / "raw_membership_sources" / "company_tickers_exchange.json"
    try:
        if cache.exists():
            data = json.loads(cache.read_text())
        else:
            req = urllib.request.Request(
                "https://www.sec.gov/files/company_tickers_exchange.json", headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data))
        fields = data["fields"]
        ti, ei = fields.index("ticker"), fields.index("exchange")
        return {_norm(row[ti]): (row[ei] or "").lower() for row in data["data"]}
    except Exception as e:
        print(f"[T136-A3] WARN exchange map unavailable ({e}); all unknown -> -55%")
        return {}


def classify_exits(membership: pd.DataFrame, rets: pd.DataFrame) -> pd.DataFrame:
    """One row per membership exit inside the window, with classification."""
    cal = rets.index
    rows = []
    for _, r in membership.iterrows():
        if pd.isna(r["end"]) or not (pd.Timestamp(START) <= r["end"] <= pd.Timestamp(END)):
            continue
        t, exit_d = r["ticker"], r["end"]
        if t not in rets.columns:
            rows.append({"ticker": t, "exit": exit_d, "class": "missing_path"})
            continue
        path = rets[t].dropna()
        if path.empty:
            rows.append({"ticker": t, "exit": exit_d, "class": "missing_path"})
            continue
        last = path.index.max()
        days_past = int(((cal > exit_d) & (cal <= last)).sum())
        if days_past > 30:
            cls = "still_listed"
        else:
            trail = path.loc[exit_d - pd.Timedelta(days=270):exit_d]
            # trailing 126d compound simple return
            tot = float((1 + trail.tail(126)).prod() - 1) if len(trail) else 0.0
            cls = "performance" if tot <= -0.30 else "merger_like"
        rows.append({"ticker": t, "exit": exit_d, "class": cls})
    return pd.DataFrame(rows)


def ew_series(rets: pd.DataFrame, mask: pd.DataFrame | None) -> pd.Series:
    if mask is None:
        return rets.mean(axis=1)
    aligned = mask.reindex(index=rets.index, columns=rets.columns).fillna(False)
    # Portfolio arithmetic: divide by the MEMBER count, not the non-NaN count —
    # otherwise a day where only an imputed exit has data becomes a 1-name
    # portfolio at -100% and annihilates the compounding product. A member-day
    # with no print contributes 0 (held flat), exactly as a real EW book.
    masked = rets.where(aligned)
    numer = masked.sum(axis=1)              # NaN-skipping sum
    denom = aligned.sum(axis=1).astype(float)
    out = numer / denom
    return out.where(denom >= 50)           # drop thin-membership days


def stats(s: pd.Series) -> dict:
    r = s.dropna()  # daily SIMPLE portfolio returns
    bd = MetricsEngine.bootstrap_distribution(r, MetricsEngine.sharpe_ratio,
                                              n_iterations=1000, seed=0)
    years = len(r) / 252.0
    growth = float((1 + r).prod())
    cagr = growth ** (1 / years) - 1.0 if years > 0 and growth > 0 else -1.0
    return {"n_days": int(len(r)), "cagr_pct": round(cagr * 100, 2),
            "sharpe_point": round(bd["point_estimate"], 3),
            "sharpe_ci_low": round(bd["ci_low"], 3),
            "sharpe_ci_high": round(bd["ci_high"], 3)}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rets = load_price_panel()
    membership = load_membership()
    print(f"[T136-A3] price panel: {rets.shape[1]} names; "
          f"membership tickers: {membership.ticker.nunique()}")

    # membership mask on the price calendar (interval-vectorized)
    mask = pd.DataFrame(False, index=rets.index, columns=rets.columns)
    for _, r in membership.iterrows():
        t = r["ticker"]
        if t not in mask.columns:
            continue
        end = r["end"] if pd.notna(r["end"]) else rets.index[-1]
        mask.loc[(mask.index >= r["start"]) & (mask.index <= end), t] = True

    # coverage: members in index on date d with NO price file at all
    have_data = set(rets.columns)
    in_window = membership[(membership["start"] <= END) &
                           (membership["end"].isna() | (membership["end"] >= START))]
    cov = {
        "n_members_in_window": int(in_window.ticker.nunique()),
        "n_with_price_data": int(len(set(in_window.ticker) & have_data)),
        "n_missing_price_entirely": int(len(set(in_window.ticker) - have_data)),
    }
    print(f"[T136-A3] coverage: {cov}")

    exits = classify_exits(membership, rets)
    cls_counts = exits["class"].value_counts().to_dict()
    print(f"[T136-A3] exit classes: {cls_counts}")

    exch = exchange_map()

    # imputation overlays: add a one-day imputed SIMPLE return on exit date.
    # `missing_path` exits are individually unclassifiable -> variant (b)
    # applies the literature prior (~51% of delistings are mergers, Shumway/
    # CRSP): expected-value imputation = MERGER-free fraction (0.49) x value.
    MISSING_PERFORMANCE_PRIOR = 0.49

    def overlay(rets_in: pd.DataFrame, mode: str) -> pd.DataFrame:
        r2 = rets_in.copy()
        extra_cols = {}
        for _, e in exits.iterrows():
            if e["class"] not in ("performance", "missing_path"):
                continue
            pos = r2.index.searchsorted(e["exit"])
            if pos >= len(r2.index):
                continue
            d = r2.index[pos]
            if mode == "shumway":
                ex = exch.get(e["ticker"], "")
                val = SHUMWAY_NYSE if ("nyse" in ex or "amex" in ex) else SHUMWAY_NASDAQ
                if e["class"] == "missing_path":
                    val *= MISSING_PERFORMANCE_PRIOR
            else:  # worst case: every unknown exit assumed total loss
                val = WORST
            t = e["ticker"]
            if t in r2.columns:
                r2.loc[d, t] = val  # simple return on exit day
            else:
                extra_cols.setdefault(t, {})[d] = val
        if extra_cols:
            extras = pd.DataFrame(extra_cols, index=r2.index)
            r2 = pd.concat([r2, extras], axis=1)
        return r2

    # masks must cover imputed extra columns too
    def mask_for(r2: pd.DataFrame) -> pd.DataFrame:
        m2 = mask.reindex(columns=r2.columns).copy()
        for c in r2.columns.difference(mask.columns):
            col = pd.Series(False, index=m2.index)
            iv = membership[membership["ticker"] == c]
            for _, r in iv.iterrows():
                end = r["end"] if pd.notna(r["end"]) else m2.index[-1]
                col.loc[(m2.index >= r["start"]) & (m2.index <= end)] = True
            m2[c] = col
        return m2.fillna(False)

    survivor = ew_series(rets, None)
    var_a = ew_series(rets, mask)
    rets_b = overlay(rets, "shumway")
    var_b = ew_series(rets_b, mask_for(rets_b))
    rets_c = overlay(rets, "worst")
    var_c = ew_series(rets_c, mask_for(rets_c))

    results = {
        "task": "T-2026-06-10-136 PartA3",
        "window": [START, END],
        "coverage": cov,
        "exit_classification_counts": cls_counts,
        "exit_classification_note": "heuristic per pre-registration; Form-25 "
                                    "EDGAR verification deferred (flagged)",
        "survivor_universe": stats(survivor),
        "variant_a_membership_only": stats(var_a),
        "variant_b_shumway": stats(var_b),
        "variant_c_worst_case": stats(var_c),
    }
    sv = results["survivor_universe"]
    for k in ("variant_a_membership_only", "variant_b_shumway", "variant_c_worst_case"):
        r = results[k]
        r["sharpe_inflation_vs_this"] = round(sv["sharpe_point"] - r["sharpe_point"], 3)
        r["cagr_inflation_pct_vs_this"] = round(sv["cagr_pct"] - r["cagr_pct"], 2)

    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"[T136-A3] survivor: CAGR {sv['cagr_pct']}% Sharpe {sv['sharpe_point']} "
          f"ci[{sv['sharpe_ci_low']},{sv['sharpe_ci_high']}]")
    for k in ("variant_a_membership_only", "variant_b_shumway", "variant_c_worst_case"):
        r = results[k]
        print(f"[T136-A3] {k}: CAGR {r['cagr_pct']}% Sharpe {r['sharpe_point']} "
              f"ci[{r['sharpe_ci_low']},{r['sharpe_ci_high']}] | "
              f"inflation: ΔCAGR {r['cagr_inflation_pct_vs_this']}pp "
              f"ΔSharpe {r['sharpe_inflation_vs_this']}")
    print(f"[T136-A3] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
