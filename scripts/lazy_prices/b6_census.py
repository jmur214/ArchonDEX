"""scripts/lazy_prices/b6_census.py
=================================
T-383 (B-6) step 5 — the parse-coverage census, BEFORE (T-237) and AFTER (B-6), per year.

BEFORE reads the shared T-237 `data/edgar/sections.parquet` read-only and streamed (one text
column at a time) and re-derives, beside T-237's own `parse_ok`, the B-6 audit's unambiguous
contamination test: an "ok" section containing the signature-page boilerplate or the auditor's
report ran past its own end.
AFTER reads the B-6 shards (`data/b6_local/sp_sections/`) and signals (`signals_sp.parquet`)
and the member-month universe (`sp_universe_months.parquet`).
Writes CSVs under data/b6_local/census/ and prints markdown tables. No returns.

Usage:
  python -m scripts.lazy_prices.b6_census [--skip-before]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from scripts.lazy_prices.b6_parse import _END_MARKERS

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "data" / "b6_local"
T237 = ROOT / "data" / "edgar" / "sections.parquet"
SHARDS = LOCAL / "sp_sections"
SIGNALS = LOCAL / "signals_sp.parquet"
UNIVERSE = LOCAL / "sp_universe_months.parquet"
OUT = LOCAL / "census"


def md(df: pd.DataFrame, index: bool = True) -> str:
    """Markdown table without a new dependency (pandas.to_markdown needs `tabulate`)."""
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in d.itertuples(index=False)]
    return "\n".join(lines)


def census_before() -> pd.DataFrame:
    meta = pd.read_parquet(T237, columns=["accession", "acceptance_dt", "parse_ok"])
    pf = pq.ParquetFile(T237)
    for col in ("item_1a_text", "item_7_text"):
        flags = []
        for b in pf.iter_batches(batch_size=300, columns=[col]):
            flags.extend(bool(_END_MARKERS.search(t or "")) for t in b.column(col).to_pylist())
        meta[col + "_marker"] = flags
    meta["year"] = meta.acceptance_dt.str[:4]
    meta["ok_clean"] = meta.parse_ok & ~meta.item_1a_text_marker & ~meta.item_7_text_marker
    g = meta.groupby("year")
    return pd.DataFrame({"filings_10k": g.size(), "t237_parse_ok": g.parse_ok.sum(),
                         "t237_ok_marker_free": g.ok_clean.sum()}).astype(int)


def _shards() -> pd.DataFrame:
    cols = ["cik", "form", "accession", "acceptance_dt", "fetch_ok", "risk_status", "mda_status",
            "mda_source", "risk_words", "mda_words"]
    parts = [pq.read_table(p, columns=cols).to_pandas() for p in sorted(SHARDS.glob("shard_*.parquet"))]
    from scripts.lazy_prices.b6_build_panel import latest_by_accession
    return latest_by_accession(pd.concat(parts, ignore_index=True))


def census_after() -> tuple[pd.DataFrame, pd.DataFrame]:
    s = _shards()
    s["year"] = s.acceptance_dt.str[:4]
    s["risk_ok"] = s.risk_status == "OK"
    s["mda_ok"] = s.mda_status == "OK"
    s["both_ok"] = s.risk_ok & s.mda_ok
    tab = (s.groupby(["form", "year"])
             .agg(filings=("accession", "size"), fetch_ok=("fetch_ok", "sum"),
                  risk_ok=("risk_ok", "sum"), mda_ok=("mda_ok", "sum"), both_ok=("both_ok", "sum"))
             .astype(int))
    if SIGNALS.is_file():
        sig = pd.read_parquet(SIGNALS, columns=["accession", "form", "acceptance_dt",
                                                "yoy_combo_why", "yoy_risk_why", "yoy_mda_why"])
        sig["year"] = sig.acceptance_dt.str[:4]
        st = (sig.assign(combo_pair=sig.yoy_combo_why == "ok", risk_pair=sig.yoy_risk_why == "ok",
                         mda_pair=sig.yoy_mda_why == "ok")
                 .groupby(["form", "year"])[["combo_pair", "risk_pair", "mda_pair"]].sum().astype(int))
        tab = tab.join(st, how="left").fillna(0).astype(int)
    status = pd.concat({"risk": s.groupby("form").risk_status.value_counts(),
                        "mda": s.groupby("form").mda_status.value_counts()}).rename("n")
    return tab, status.reset_index()


def universe_coverage() -> pd.DataFrame:
    u = pd.read_parquet(UNIVERSE)
    u["year"] = u.month.dt.year
    u["has_cik"] = u.cik.notna()
    return u.groupby("year").agg(member_months=("has_cik", "size"),
                                 with_cik=("has_cik", "sum")).astype(int)


def price_coverage() -> pd.DataFrame:
    """Share of S&P member-months (resolved CIK) with a price FILE in each candidate source.
    File existence only — no price is read (Phase 1 computes no returns).
      t265     data/research/t265/prices/<ticker>.parquet via the CIK (Alpaca adjustment='all',
               verified total return; starts 2016)
      processed data/processed/<ticker>_1d.csv by the membership ticker (clean only AFTER each
               name's seam, i.e. from 2020-04-09 for every name; see main's dividend-era HIGH)"""
    u = pd.read_parquet(UNIVERSE).dropna(subset=["cik"])
    u["year"] = u.month.dt.year
    t265 = ROOT / "data" / "research" / "t265"
    ct = pd.read_parquet(t265 / "cik_ticker_final.parquet")
    files = {p.stem for p in (t265 / "prices").glob("*.parquet")}
    priced = set(ct[ct.ticker.isin(files)].cik.astype(int))
    proc = {p.name[:-7] for p in (ROOT / "data" / "processed").glob("*_1d.csv")}  # ticker-exclusions: bypassed — file-name existence census only, no price read; the exclusions bind the Phase-2 price reader
    u["t265_file"] = u.cik.astype(int).isin(priced)
    u["processed_file"] = u.ticker.str.replace(".", "-", regex=False).isin(proc) | u.ticker.isin(proc)
    g = u.groupby("year")
    return pd.DataFrame({"member_months_with_cik": g.size(),
                         "t265_price_file": g.t265_file.mean().round(3),
                         "processed_file": g.processed_file.mean().round(3)})


def rebalance_coverage(start: str = "2007-03-31", end: str = "2025-12-31") -> pd.DataFrame:
    """Per quarter-end rebalance: how many PIT S&P members (with a CIK) carry a USABLE ranking signal
    under the proposed text rule (R6: 10-K -> YoY combo; 10-Q -> YoY MD&A) from their latest filing
    with decision_floor_date <= t and acceptance within 6 months. Counts names, reads no price."""
    sig = pd.read_parquet(SIGNALS, columns=["cik", "form", "acceptance_dt", "decision_floor_date",
                                            "yoy_combo_why", "yoy_mda_why"])
    sig["floor"] = pd.to_datetime(sig.decision_floor_date)
    sig["acc"] = pd.to_datetime(sig.acceptance_dt.str[:10])
    sig["usable"] = ((sig.form == "10-K") & (sig.yoy_combo_why == "ok")) | (
        (sig.form == "10-Q") & (sig.yoy_mda_why == "ok"))
    sig = sig.sort_values("floor")
    u = pd.read_parquet(UNIVERSE).dropna(subset=["cik"])
    u["cik"] = u.cik.astype(int)
    rows = []
    for t in pd.date_range(start, end, freq="QE"):
        m = u[u.month == t.to_period("M").to_timestamp()]
        members = set(m.cik)
        s = sig[(sig.floor <= t) & (sig.acc > t - pd.DateOffset(months=6)) & sig.cik.isin(members)]
        latest = s.groupby("cik").tail(1)
        usable = latest[latest.usable]
        rows.append({"rebalance": t.date().isoformat(), "members_with_cik": len(members),
                     "with_recent_filing": len(latest), "usable_signal": len(usable),
                     "usable_share": round(len(usable) / max(1, len(members)), 3),
                     "usable_10k": int((usable.form == "10-K").sum()),
                     "usable_10q": int((usable.form == "10-Q").sum())})
    return pd.DataFrame(rows).set_index("rebalance")


# --------------------------------------------------------------------------- #
# T-265 arm census (text only, b6_parse/2) — no price, no ADV, no ranking, no return
# --------------------------------------------------------------------------- #
T265_DIR = LOCAL / "t265_signals"
SP_V2_SHARDS = LOCAL / "sp_sections_v2"
SP_V2_SIGNALS = LOCAL / "signals_sp_v2.parquet"
T265_MAP = ROOT / "data" / "research" / "t265" / "cik_ticker_final.parquet"
T265_PRICES = ROOT / "data" / "research" / "t265" / "prices"


def _t265_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    def cat(prefix):
        parts = [pd.read_parquet(p) for p in sorted(T265_DIR.glob(f"{prefix}_*.parquet"))]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    return cat("done"), cat("filings"), cat("signals")


def t265_universe_ciks() -> set[int]:
    """The T-265 priced CIKs (file names only — no price is read)."""
    ct = pd.read_parquet(T265_MAP)
    files = {p.stem for p in T265_PRICES.glob("*.parquet")}
    return set(ct[ct.ticker.isin(files)].cik.astype(int))


SP_FETCH_LIST = LOCAL / "sp_fetch_list.parquet"
SP_CANDIDATES = LOCAL / "sp_candidate_filings.parquet"
FILL_SINCE = "2015-01-01"
FILL_TOL_PP = 3.0          # AMENDMENT 7, condition (a): two-sided, percentage points
FILL_MAX_FAIL = 0.01       # AMENDMENT 7, condition (a): filing-level fetch failures


def overlap_gap_ciks(universe: set[int] | None = None) -> list[int]:
    """AMENDMENT 7 (A7.1) — the overlap firms whose text has a hole: T-265 priced CIKs in the S&P
    fetch list (the stream skipped them) with >= 1 10-K/10-Q accepted from 2015 in the cached S&P
    candidate list that the fetch list lacks (outside their S&P fetch window). Deterministic from
    the two files; keyed on (cik, accession) so a co-registrant's shared accession never hides a
    gap."""
    universe = t265_universe_ciks() if universe is None else universe
    fl = pd.read_parquet(SP_FETCH_LIST, columns=["cik", "accession"])
    cand = pd.read_parquet(SP_CANDIDATES, columns=["cik", "form", "accession", "acceptance_dt"])
    fl["cik"] = fl.cik.astype(int)
    cand["cik"] = cand.cik.astype(int)
    ov = universe & set(fl.cik)
    c = cand[cand.cik.isin(ov) & cand.form.isin(["10-K", "10-Q"])
             & (cand.acceptance_dt.astype(str).str[:10] >= FILL_SINCE)]
    have = set(zip(fl.cik, fl.accession))
    miss = c[[(a, b) not in have for a, b in zip(c.cik, c.accession)]]
    return sorted(int(x) for x in miss.cik.unique())


def overlap_gap_accessions(universe: set[int] | None = None) -> set[tuple[int, str]]:
    """The (cik, accession) pairs of the hole itself (the A7.1 5,502), for the gap-only report."""
    universe = t265_universe_ciks() if universe is None else universe
    fl = pd.read_parquet(SP_FETCH_LIST, columns=["cik", "accession"])
    cand = pd.read_parquet(SP_CANDIDATES, columns=["cik", "form", "accession", "acceptance_dt"])
    fl["cik"] = fl.cik.astype(int)
    cand["cik"] = cand.cik.astype(int)
    ov = universe & set(fl.cik)
    c = cand[cand.cik.isin(ov) & cand.form.isin(["10-K", "10-Q"])
             & (cand.acceptance_dt.astype(str).str[:10] >= FILL_SINCE)]
    have = set(zip(fl.cik, fl.accession))
    return {(int(a), b) for a, b in zip(c.cik, c.accession) if (a, b) not in have}


def harness_grid(start: str, end: str) -> list[pd.Timestamp]:
    """AMENDMENT 7 (A7.2) — the S&P harness's rebalance rule, imported (one code path): the last
    SPY TR twin bar on or before each calendar quarter-end. Reads the twin's bar DATES only."""
    from scripts.lazy_prices.b6_harness_sp import TWINS, rebalance_dates
    d = pd.read_csv(TWINS / "SPY_1d.csv", usecols=["Date"], parse_dates=["Date"])
    cal = pd.DatetimeIndex(d["Date"]).drop_duplicates().sort_values()
    return rebalance_dates(cal, start, end)


def _rates(name: str, f: pd.DataFrame, g: pd.DataFrame) -> list[dict]:
    """The six A7.1 rates per form: parse rates on acceptance from 2015, pair rates from 2016."""
    a = f[f.acceptance_dt.astype(str).str[:4] >= "2015"]
    b = g[g.acceptance_dt.astype(str).str[:4] >= "2016"]
    rows = []
    for form in ("10-K", "10-Q"):
        x, y = a[a.form == form], b[b.form == form]
        pre = x.risk_status.astype(str).str.startswith("NOT_COVERED")
        rows.append({"panel": name, "form": form, "filings": len(x),
                     "risk_ok_pct": round(100 * (x.risk_status == "OK").mean(), 1),
                     "risk_ok_excl_not_covered_pct": round(100 * (x.risk_status[~pre] == "OK").mean(), 1),
                     "risk_not_covered_pct": round(100 * pre.mean(), 1),
                     "mda_ok_pct": round(100 * (x.mda_status == "OK").mean(), 1),
                     "combo_pair_pct_2016on": round(100 * (y.yoy_combo_why == "ok").mean(), 1),
                     "mda_pair_pct_2016on": round(100 * (y.yoy_mda_why == "ok").mean(), 1),
                     "qoq_mda_pair_pct_2016on": round(100 * (y.qoq_mda_why == "ok").mean(), 1)
                     if form == "10-Q" else float("nan")})
    return rows


FILL_RATES = ("risk_ok_pct", "risk_ok_excl_not_covered_pct", "mda_ok_pct", "combo_pair_pct_2016on",
              "mda_pair_pct_2016on", "qoq_mda_pair_pct_2016on")


def fill_check(rates: pd.DataFrame, base: str, fill: str) -> pd.DataFrame:
    """AMENDMENT 7 condition (a), rates half: |fill − base| <= 3.0 pp on each rate, per form."""
    rows = []
    for form in ("10-K", "10-Q"):
        b = rates[(rates.panel == base) & (rates.form == form)].iloc[0]
        f = rates[(rates.panel == fill) & (rates.form == form)].iloc[0]
        for k in FILL_RATES:
            if pd.isna(b[k]) and pd.isna(f[k]):
                continue
            diff = float(f[k]) - float(b[k])
            ok = bool(abs(diff) <= FILL_TOL_PP) if pd.notna(diff) else False
            rows.append({"form": form, "rate": k, "base": b[k], "fill": f[k], "diff_pp": round(diff, 1),
                         "within_3pp": ok})
    return pd.DataFrame(rows)


def _eligibility(allsig: pd.DataFrame, dates: list[pd.Timestamp], overlap: set[int]) -> pd.DataFrame:
    """Per rebalance: CIKs whose latest usable filing (floor <= t, accepted within 6 months — the
    harness's `signals_at` rule) carries a defined gate / H_OOS ranking signal. Counts only."""
    reb = []
    for t in dates:
        s_ = allsig[(allsig.floor <= t) & (allsig.acc > t - pd.DateOffset(months=6))]
        latest = s_.groupby("cik").tail(1)
        ov = latest[latest.cik.isin(overlap)]
        reb.append({"rebalance": t.date().isoformat(), "ciks_with_recent_filing": len(latest),
                    "gate_usable": int(latest.gate_ok.sum()),
                    "gate_usable_10k": int((latest.gate_ok & (latest.form == "10-K")).sum()),
                    "gate_usable_10q": int((latest.gate_ok & (latest.form == "10-Q")).sum()),
                    "hoos_usable": int(latest.hoos_ok.sum()),
                    "hoos_usable_10q": int((latest.hoos_ok & (latest.form == "10-Q")).sum()),
                    "overlap_with_recent_filing": len(ov),
                    "overlap_without_recent_filing": len(overlap) - len(ov)})
    return pd.DataFrame(reb).set_index("rebalance")


def census_t265(start: str = "2016-03-31", end: str = "2025-12-31") -> dict[str, pd.DataFrame]:
    """The T-265 arm's parse-coverage census under b6_parse/2. Counts only: no signal VALUE or
    distribution is read (H_OOS stays clean), no price, ADV, ranking or return. CIKs that are
    also in the S&P panel take their text from signals_sp_v2 (the stream skipped them) — except
    the AMENDMENT-7 fill CIKs, whose full 2015+ history the stream now holds."""
    done, fil, sig = _t265_frames()
    out: dict[str, pd.DataFrame] = {}
    universe = t265_universe_ciks()
    done["cik"] = done.cik.astype(int)
    streamed = set(done.cik)
    gap = set(overlap_gap_ciks(universe))
    fill = gap & streamed
    base = streamed - fill
    overlap = universe - streamed
    # (cik, accession): a co-registrant filing is one accession under two CIKs — both rows are real
    fil = fil.assign(cik=fil.cik.astype(int)).drop_duplicates(["cik", "accession"], keep="last")
    sig = sig.assign(cik=sig.cik.astype(int)).drop_duplicates(["cik", "accession"], keep="last")
    last_err = done.drop_duplicates("cik", keep="last")
    transient = last_err.error.fillna("").str.startswith(("error:", "submissions_"))
    ff = fil[fil.cik.isin(fill)]
    out["completeness"] = pd.DataFrame([{
        "t265_priced_ciks": len(universe), "streamed_ciks": len(base),
        "fill_ciks_streamed": len(fill), "fill_ciks_selected": len(gap),
        "overlap_ciks_from_sp_panel": len(overlap),
        "no_periodic_filings_since_2015": int((last_err.error == "no_periodic_filings_since_2015").sum()),
        "transient_errors_remaining": int(transient.sum()),
        "fill_transient_errors_remaining": int((transient & last_err.cik.isin(gap)).sum()),
        "filings": len(fil), "fetch_ok": int(fil.fetch_ok.fillna(False).sum()),
        "fetch_failed": int((~fil.fetch_ok.fillna(False)).sum()),
        "fill_filings": len(ff), "fill_fetch_failed": int((~ff.fetch_ok.fillna(False)).sum()),
        "fill_fetch_failed_share": round(float((~ff.fetch_ok.fillna(False)).mean()), 5) if len(ff) else float("nan")}])
    out["fetch_failures"] = fil.loc[~fil.fetch_ok.fillna(False),
                                    ["cik", "form", "accession", "acceptance_dt", "fetch_status", "fetch_reason"]]
    f = fil.assign(year=fil.acceptance_dt.str[:4], risk_ok=fil.risk_status == "OK",
                   mda_ok=fil.mda_status == "OK")
    f["both_ok"] = f.risk_ok & f.mda_ok
    g = sig.assign(year=sig.acceptance_dt.str[:4],
                   combo_pair=sig.yoy_combo_why == "ok", mda_pair=sig.yoy_mda_why == "ok",
                   qoq_mda_pair=sig.get("qoq_mda_why", pd.Series(index=sig.index, dtype=object)) == "ok")
    tab = (f.groupby(["form", "year"]).agg(filings=("accession", "size"), fetch_ok=("fetch_ok", "sum"),
                                           risk_ok=("risk_ok", "sum"), mda_ok=("mda_ok", "sum"),
                                           both_ok=("both_ok", "sum")).astype(int)
           .join(g.groupby(["form", "year"])[["combo_pair", "mda_pair", "qoq_mda_pair"]].sum().astype(int),
                 how="left").fillna(0).astype(int))
    out["by_year_form"] = tab
    out["status"] = pd.concat({"risk": f.groupby("form").risk_status.value_counts(),
                               "mda": f.groupby("form").mda_status.value_counts()}).rename("n").reset_index()
    # rates: the 4,099 streamed (the T-265 panel's own), the AMENDMENT-7 fill, its gap-only subset,
    # all streamed, and the S&P panel (b6_parse/2), same acceptance years
    sp = pd.concat([pd.read_parquet(p, columns=["cik", "accession", "form", "acceptance_dt", "fetch_ok",
                                                "risk_status", "mda_status"])
                    for p in sorted(SP_V2_SHARDS.glob("shard_*.parquet"))], ignore_index=True)
    sp = sp.assign(cik=sp.cik.astype(int)).drop_duplicates(["cik", "accession"], keep="last")
    spsig = pd.read_parquet(SP_V2_SIGNALS, columns=["cik", "accession", "form", "acceptance_dt",
                                                    "yoy_combo_why", "yoy_mda_why", "qoq_mda_why"])
    gap_acc = overlap_gap_accessions(universe)
    in_gap_f = pd.Series([(c, a) in gap_acc for c, a in zip(fil.cik, fil.accession)], index=fil.index, dtype=bool)
    in_gap_g = pd.Series([(c, a) in gap_acc for c, a in zip(sig.cik, sig.accession)], index=sig.index, dtype=bool)
    rows = (_rates("T-265 streamed", fil[fil.cik.isin(base)], sig[sig.cik.isin(base)])
            + (_rates("fill", fil[fil.cik.isin(fill)], sig[sig.cik.isin(fill)]) if fill else [])
            + (_rates("fill gap-only", fil[in_gap_f], sig[in_gap_g]) if fill else [])
            + _rates("T-265 all streamed", fil, sig)
            + _rates("S&P (v2)", sp, spsig))
    out["rates_vs_sp"] = pd.DataFrame(rows)
    if fill:
        out["fill_check"] = fill_check(out["rates_vs_sp"], "T-265 streamed", "fill")
    # per-rebalance text eligibility (counts of CIKs) on the S&P harness's grid (A7.2), and the
    # difference from the 6e52752 calendar-quarter-end grid
    cols = ["cik", "form", "acceptance_dt", "decision_floor_date", "yoy_combo_why", "yoy_mda_why", "qoq_mda_why"]
    spov = pd.read_parquet(SP_V2_SIGNALS, columns=cols)
    spov = spov[spov.cik.astype(int).isin(overlap)]
    allsig = pd.concat([sig[cols], spov], ignore_index=True)
    allsig["cik"] = allsig.cik.astype(int)
    allsig["floor"] = pd.to_datetime(allsig.decision_floor_date)
    allsig["acc"] = pd.to_datetime(allsig.acceptance_dt.str[:10])
    allsig = allsig.sort_values(["floor", "acceptance_dt"])
    allsig["gate_ok"] = ((allsig.form == "10-K") & (allsig.yoy_combo_why == "ok")) | (
        (allsig.form == "10-Q") & (allsig.yoy_mda_why == "ok"))
    allsig["hoos_ok"] = ((allsig.form == "10-K") & (allsig.yoy_combo_why == "ok")) | (
        (allsig.form == "10-Q") & (allsig.qoq_mda_why == "ok"))
    grid = harness_grid(start, end)
    elig = _eligibility(allsig, grid, overlap)
    cal_q = _eligibility(allsig, list(pd.date_range(start, end, freq="QE")), overlap)
    out["rebalance_text_eligibility"] = elig
    diff = elig.reset_index(drop=True) - cal_q.reset_index(drop=True)
    diff.insert(0, "calendar_qe", list(cal_q.index))
    diff.insert(0, "rebalance", list(elig.index))
    out["grid_vs_calendar"] = diff.set_index("rebalance")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B-6 parse-coverage census (before/after).")
    ap.add_argument("--skip-before", action="store_true")
    ap.add_argument("--t265", action="store_true", help="the T-265 arm's text census only (b6_parse/2)")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.t265:
        res = census_t265()
        for k, v in res.items():
            ix = k in ("by_year_form", "rebalance_text_eligibility", "grid_vs_calendar")
            v.to_csv(OUT / f"t265_{k}.csv", index=ix)
            print(f"\n## T-265 {k}\n" + md(v, index=ix))
        return 0
    if not args.skip_before:
        before = census_before()
        before.to_csv(OUT / "before_t237.csv")
        print("## BEFORE (T-237, 10-K only)\n" + md(before))
    after, status = census_after()
    after.to_csv(OUT / "after_b6.csv")
    status.to_csv(OUT / "after_b6_status.csv", index=False)
    print("\n## AFTER (B-6)\n" + md(after))
    print("\n## AFTER status counts\n" + md(status, index=False))
    if UNIVERSE.is_file():
        uc = universe_coverage()
        uc.to_csv(OUT / "universe_coverage.csv")
        print("\n## S&P member-months with a resolved CIK\n" + md(uc))
        pc = price_coverage()
        pc.to_csv(OUT / "price_source_coverage.csv")
        print("\n## Price-source FILE coverage of S&P member-months (no prices read)\n" + md(pc))
        if SIGNALS.is_file():
            rc = rebalance_coverage()
            rc.to_csv(OUT / "rebalance_signal_coverage.csv")
            print("\n## Usable ranking signals per quarter-end rebalance (R6 rule; no prices)\n"
                  + md(rc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
