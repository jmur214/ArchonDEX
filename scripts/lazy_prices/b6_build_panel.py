"""scripts/lazy_prices/b6_build_panel.py
=======================================
T-383 (B-6) — build the S&P PIT text panel (10-K + 10-Q; Risk Factors + MD&A).

Subcommands (run in order; each is resumable and writes only under data/b6_local/):

  universe   Fetch each candidate CIK's own 10-K/10-Q list (data.sec.gov submissions; the
             'recent' block fresh, older pages from the shared cache read-only), then decide the
             member CIK per (membership interval, month) with the rule documented in
             b6_cik_map.py, plus a uniqueness pass (one CIK cannot be two different members in
             the same month: the interval whose symbol the CIK used keeps it; a bankruptcy-suffix
             match loses to an exact one). Writes:
               sp_candidate_filings.parquet, sp_candidate_meta.parquet,
               sp_universe_months.parquet (ticker, iv_id, month, cik, rule),
               sp_fetch_list.parquet (the filings to fetch).
  fetch      Fetch each listed primary document INTO MEMORY, parse it with b6_parse (the raw
             document is never written), and append the parsed record to a zstd parquet shard.
             Checks free disk before every company and halts cleanly under the floor.

Window: membership months from 2005-01 on; filings accepted from 2004-10-01 (so 2005-2006
filings have priors), each member's filings from 15 months before its first member month to 3
months after its last.

[NN-FAIL-CLOSED]: every listed filing gets a row — fetch failures with the provider's status and
reason, unparseable sections with their status. A 403 halts the run (EdgarRefused). Nothing is
dropped silently.

Usage:
  python -m scripts.lazy_prices.b6_build_panel universe
  python -m scripts.lazy_prices.b6_build_panel fetch [--limit-ciks N] [--ciks 1,2,3]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts.lazy_prices import b6_edgar as E
from scripts.lazy_prices import b6_parse as P

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "data" / "b6_local"
MAPDIR = LOCAL / "cik_map"
SHARED_RAW = ROOT / "data" / "edgar" / "raw"
CAND_FILINGS = LOCAL / "sp_candidate_filings.parquet"
CAND_META = LOCAL / "sp_candidate_meta.parquet"
UNIVERSE = LOCAL / "sp_universe_months.parquet"
FETCH_LIST = LOCAL / "sp_fetch_list.parquet"
SHARD_DIR = LOCAL / "sp_sections"
LOG_DIR = LOCAL / "logs"

PARSER_VERSION = "b6_parse/2"   # review F4, 2026-11-12 (b6_parse/1: sp_sections/)
SHARD_DIR_V2 = LOCAL / "sp_sections_v2"
MONTH_START = pd.Timestamp("2005-01-01")
FILING_FLOOR = pd.Timestamp("2004-10-01")
TODAY = pd.Timestamp("2026-11-30")
SIZE_OVERRIDE = 1.5
SYMBOL_PAD = pd.Timedelta(days=90)


def _log(msg: str, logfile: Path | None = None) -> None:
    line = f"{pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
    print(line, flush=True)
    if logfile is not None:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        with logfile.open("a") as fh:
            fh.write(line + "\n")


# --------------------------------------------------------------------------- #
# universe
# --------------------------------------------------------------------------- #
def fetch_candidates(ciks: list[int], logfile: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Periodic filings + meta for every candidate CIK (resumable, saved every 50)."""
    have_f = pd.read_parquet(CAND_FILINGS) if CAND_FILINGS.is_file() else pd.DataFrame()
    have_m = pd.read_parquet(CAND_META) if CAND_META.is_file() else pd.DataFrame()
    done = set(have_m["cik"].astype(int)) if len(have_m) else set()
    todo = [c for c in ciks if c not in done]
    _log(f"[universe] candidates {len(ciks)}; cached {len(done)}; to fetch {len(todo)}", logfile)
    f_rows, m_rows = [], []

    def _save() -> None:
        nonlocal have_f, have_m, f_rows, m_rows
        if f_rows:
            have_f = pd.concat([have_f, pd.DataFrame(f_rows)], ignore_index=True)
        if m_rows:
            have_m = pd.concat([have_m, pd.DataFrame(m_rows)], ignore_index=True)
        LOCAL.mkdir(parents=True, exist_ok=True)
        have_f.to_parquet(CAND_FILINGS, index=False)
        have_m.to_parquet(CAND_META, index=False)
        f_rows, m_rows = [], []

    for i, cik in enumerate(todo, 1):
        rows, meta, results = E.company_periodic_filings(cik, SHARED_RAW)
        ok = all(r.ok for r in results) and bool(results)
        reason = "; ".join(r.reason for r in results if not r.ok)
        for r in rows:
            f_rows.append({"cik": cik, "form": r["form"], "accession": r["accessionNumber"],
                           "acceptance_dt": r["acceptanceDateTime"], "filing_date": r["filingDate"],
                           "period_end": r["reportDate"], "primary_doc": r["primaryDocument"],
                           "size": r["size"]})
        m_rows.append({"cik": cik, "name": meta.get("name", ""),
                       "tickers": ",".join(meta.get("tickers", [])),
                       "former_names": " | ".join(meta.get("former_names", [])),
                       "submissions_ok": ok, "submissions_reason": reason,
                       "n_periodic": len(rows)})
        if i % 50 == 0:
            _save()
            _log(f"[universe] {i}/{len(todo)} fetched; requests {E.stats['requests']}", logfile)
    _save()
    return have_f, have_m


def _filer_span(filings: pd.DataFrame) -> dict[int, tuple[pd.Timestamp, pd.Timestamp]]:
    f = filings.assign(d=pd.to_datetime(filings["acceptance_dt"].str[:10], errors="coerce"))
    g = f.dropna(subset=["d"]).groupby("cik").d.agg(["min", "max"])
    return {int(c): (r["min"], r["max"]) for c, r in g.iterrows()}


def _is_filer(span: dict, cik: int | None, t: pd.Timestamp) -> bool:
    if cik is None or cik not in span:
        return False
    lo, hi = span[cik]
    return lo <= t + pd.Timedelta(days=45) and hi >= t - pd.Timedelta(days=200)


def decide_months(ivs: pd.DataFrame, users: pd.DataFrame, act: pd.DataFrame,
                  span: dict) -> pd.DataFrame:
    """Per (interval, month) member CIK + the rule that chose it.

    Candidates at month t, each only while it is a periodic FILER at t:
      - every issuer that USED the symbol around t (its first..last insider filing under the
        symbol, +/- 90 days; the earliest user is extended back to the interval start, since the
        Form 3/4/5 data begin 2006-01 and the window 2005-01);
      - the LAST chain user (the membership file lists a company under its last ticker for its
        whole history: L Brands = LB since 1996, Waste Management = WM since 1998);
      - the live-map CIK (the symbol's current owner: Parametric = PTC).
    One candidate -> it. Several -> the one with the most insider filings (any symbol) over the
    whole interval, if >= 1.5x the runner-up (CB 2006-15: Chubb Corp 2.3x ACE; LB: L Brands 5x
    LaBarge); otherwise a TIE, resolved in favour of a symbol user at t (MRK 2006-09: old Merck
    over Schering-Plough, which was SGP) and flagged `tie_symbol_user`. Interval-level activity
    keeps the choice stable across years. No candidate -> NOT_COVERED (cik NA, rule 'none')."""
    actd: dict[int, dict[int, int]] = {}
    for c, y, n in act[["cik", "year", "n"]].itertuples(index=False):
        actd.setdefault(int(c), {})[int(y)] = int(n)
    out = []
    for _, iv in ivs.iterrows():
        u = users[users.iv_id == iv.iv_id].sort_values("first")
        start = max(pd.Timestamp(iv.iv_start), MONTH_START)
        end = min(pd.Timestamp(iv.iv_end) if pd.notna(iv.iv_end) else TODAY, TODAY)
        if end < start:
            continue
        live = int(iv.live_cik) if pd.notna(iv.live_cik) else None
        last_user = int(u.sort_values("last").iloc[-1].cik) if len(u) else None
        windows = []
        for k, r in enumerate(u.itertuples()):
            lo = pd.Timestamp(iv.iv_start) if k == 0 else r.first - SYMBOL_PAD
            windows.append((int(r.cik), lo, r.last + SYMBOL_PAD))
        y0, y1 = max(start.year, 2006), end.year
        cand_all = {c for c, _, _ in windows} | ({live} if live else set()) | (
            {last_user} if last_user else set())
        iv_act = {c: sum(n for y, n in actd.get(c, {}).items() if y0 <= y <= y1) for c in cand_all}
        for t in pd.date_range(start, end, freq="MS"):
            using = {c for c, lo, hi in windows if lo <= t <= hi and _is_filer(span, c, t)}
            cands = set(using)
            for extra in (last_user, live):
                if extra is not None and _is_filer(span, extra, t):
                    cands.add(extra)
            if not cands:
                choice, rule = None, "none"
            elif len(cands) == 1:
                choice = next(iter(cands))
                rule = "single_symbol_user" if choice in using else (
                    "single_last_user" if choice == last_user else "single_live")
            else:
                ranked = sorted(cands, key=lambda c: iv_act.get(c, 0), reverse=True)
                top, second = ranked[0], ranked[1]
                if iv_act.get(top, 0) >= SIZE_OVERRIDE * max(iv_act.get(second, 0), 1):
                    choice, rule = top, "size"
                else:
                    pool = [c for c in ranked if c in using] or ranked
                    choice, rule = pool[0], "tie_symbol_user" if pool[0] in using else "tie_other"
            out.append({"iv_id": int(iv.iv_id), "ticker": iv.ticker, "method": iv.method,
                        "month": t, "cik": choice, "rule": rule,
                        "symbol_users": ",".join(map(str, sorted(using))),
                        "candidates": ",".join(map(str, sorted(cands)))})
    df = pd.DataFrame(out)
    df["cik"] = df["cik"].astype("Int64")
    return df


def uniqueness_pass(months: pd.DataFrame) -> pd.DataFrame:
    """One CIK cannot be two DIFFERENT members in the same month.
    1. A bankruptcy-suffix (qstrip) claimant always loses to an exact-symbol claimant
       (SUNEQ -> Sunoco is wrong: Sunoco is SUN).
    2. Share classes of one company (GOOG/GOOGL, FOX/FOXA, UA/UAA ...) legitimately share a CIK:
       kept when every remaining claimant's symbol was used by that CIK.
    3. Otherwise the claimant whose symbol the CIK used keeps it; the others fall back to another
       candidate that month (most insider activity is not re-derived here: first other symbol
       user) or to NOT_COVERED."""
    m = months.copy()
    m["dup_flag"] = ""
    claimed = m.dropna(subset=["cik"]).groupby(["cik", "month"]).ticker.nunique()
    for cik, month in claimed[claimed > 1].index:
        idx = list(m.index[(m.cik == cik) & (m.month == month)])
        exact = [i for i in idx if m.at[i, "method"] != "insider_qstrip"]
        losers = [i for i in idx if i not in exact] if exact else []
        rest = [i for i in idx if i not in losers]
        users_ok = {i: str(int(cik)) in (m.at[i, "symbol_users"] or "").split(",") for i in rest}
        if len(rest) > 1 and all(users_ok.values()):
            for i in rest:
                m.at[i, "dup_flag"] = "share_class"
        elif len(rest) > 1:
            keep = [i for i in rest if users_ok[i]][:1] or rest[:1]
            losers += [i for i in rest if i not in keep]
            for i in keep:
                m.at[i, "dup_flag"] = "dup_kept"
        for i in losers:
            alt = [int(c) for c in (m.at[i, "symbol_users"] or "").split(",")
                   if c and int(c) != int(cik)]
            if alt:
                m.at[i, "cik"], m.at[i, "rule"] = alt[0], "dup_fallback_user"
            else:
                m.at[i, "cik"], m.at[i, "rule"] = pd.NA, "dup_dropped"
            m.at[i, "dup_flag"] = "dup_lost"
    return m


def build_fetch_list(months: pd.DataFrame, filings: pd.DataFrame) -> pd.DataFrame:
    mm = months.dropna(subset=["cik"])
    spans = mm.groupby("cik").month.agg(["min", "max"])
    f = filings.copy()
    f["acc_date"] = pd.to_datetime(f["acceptance_dt"].str[:10], errors="coerce")
    keep = []
    for cik, r in spans.iterrows():
        lo = max(r["min"] - pd.DateOffset(months=15), FILING_FLOOR)
        hi = r["max"] + pd.DateOffset(months=4)
        sub = f[(f.cik == int(cik)) & (f.acc_date >= lo) & (f.acc_date < hi)]
        keep.append(sub)
    out = pd.concat(keep, ignore_index=True).drop_duplicates("accession")
    out = out.sort_values(["cik", "acc_date"]).reset_index(drop=True)
    return out


def cmd_universe(_args: argparse.Namespace) -> int:
    logfile = LOG_DIR / "universe.log"
    ivs = pd.read_parquet(MAPDIR / "sp_intervals.parquet")
    users = pd.read_parquet(MAPDIR / "sp_interval_users.parquet")
    act = pd.read_parquet(MAPDIR / "cik_year_activity.parquet")
    ciks = sorted(set(users.cik.astype(int)) | set(ivs.live_cik.dropna().astype(int)))
    E.assert_disk()
    filings, meta = fetch_candidates(ciks, logfile)
    bad = meta[~meta.submissions_ok]
    if len(bad):
        _log(f"[universe] submissions failures: {len(bad)} CIKs: "
             f"{bad[['cik', 'submissions_reason']].head(20).to_dict('records')}", logfile)
    span = _filer_span(filings)
    months = decide_months(ivs, users, act, span)
    months = uniqueness_pass(months)
    months.to_parquet(UNIVERSE, index=False)
    fl = build_fetch_list(months, filings)
    fl.to_parquet(FETCH_LIST, index=False)
    cov = months.assign(has=months.cik.notna())
    _log(f"[universe] member-months {len(months)}; with CIK {int(cov.has.sum())} "
         f"({cov.has.mean():.1%}); rules {months.rule.value_counts().to_dict()}", logfile)
    _log(f"[universe] dup flags {months.dup_flag.value_counts().to_dict()}", logfile)
    _log(f"[universe] fetch list: {len(fl)} filings, {fl.cik.nunique()} CIKs, "
         f"forms {fl.form.value_counts().to_dict()}, est. bytes {int(fl['size'].fillna(0).sum()):,}",
         logfile)
    return 0


# --------------------------------------------------------------------------- #
# fetch + parse
# --------------------------------------------------------------------------- #
SHARD_SCHEMA_COLS = [
    "cik", "form", "accession", "acceptance_dt", "filing_date", "period_end", "primary_doc",
    "fetch_ok", "fetch_status", "fetch_reason", "fetch_seconds", "doc_bytes", "doc_chars",
    "n_headings", "parser_version",
    "risk_status", "risk_source", "risk_text", "risk_tier", "risk_terminator", "risk_n_cand",
    "risk_n_valid", "risk_words",
    "mda_status", "mda_source", "mda_text", "mda_tier", "mda_terminator", "mda_n_cand",
    "mda_n_valid", "mda_words",
]


def latest_by_accession(df: pd.DataFrame) -> pd.DataFrame:
    """One row per accession across shards: a successful fetch beats a failed one; among equals
    the later shard wins (a `--retry-failed` pass appends a new shard, never rewrites an old one).
    Every reader of the shards goes through this."""
    if "fetch_ok" not in df.columns:
        return df.drop_duplicates("accession", keep="last")
    order = df.assign(_ok=df["fetch_ok"].fillna(False).astype(bool),
                      _pos=range(len(df))).sort_values(["_ok", "_pos"])
    return order.drop_duplicates("accession", keep="last").drop(columns=["_ok", "_pos"])


def _done_accessions(include_failed: bool = True) -> set[str]:
    """Accessions already in a shard. With include_failed=False, only those with a SUCCESSFUL fetch
    (so `--retry-failed` re-attempts a transient failure; its new row wins via latest_by_accession)."""
    if not SHARD_DIR.is_dir():
        return set()
    parts = [pq.read_table(p, columns=["accession", "fetch_ok"]).to_pandas()
             for p in sorted(SHARD_DIR.glob("shard_*.parquet"))]
    if not parts:
        return set()
    d = latest_by_accession(pd.concat(parts, ignore_index=True))
    if not include_failed:
        d = d[d["fetch_ok"].fillna(False).astype(bool)]
    return set(d["accession"])


def _write_shard(rows: list[dict], shard_dir: Path | None = None) -> Path:
    shard_dir = SHARD_DIR if shard_dir is None else shard_dir
    shard_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(shard_dir.glob("shard_*.parquet")))
    path = shard_dir / f"shard_{n:05d}.parquet"
    df = pd.DataFrame(rows, columns=SHARD_SCHEMA_COLS)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path, compression="zstd", compression_level=15,
                   data_page_size=8 << 20, use_dictionary=["cik", "form", "risk_status",
                                                           "mda_status", "parser_version"])
    return path


def process_filing(row: pd.Series) -> dict:
    url = E.doc_url(int(row.cik), str(row.accession), str(row.primary_doc))
    rec: dict = {c: None for c in SHARD_SCHEMA_COLS}
    rec.update({"cik": int(row.cik), "form": row.form, "accession": row.accession,
                "acceptance_dt": row.acceptance_dt, "filing_date": row.filing_date,
                "period_end": row.period_end, "primary_doc": row.primary_doc,
                "parser_version": PARSER_VERSION})
    if not row.primary_doc:
        rec.update(fetch_ok=False, fetch_reason="missing_primary_document",
                   risk_status="FETCH_FAILED", mda_status="FETCH_FAILED", risk_text="", mda_text="")
        return rec
    res = E.fetch(url)
    rec.update(fetch_ok=res.ok, fetch_status=res.status, fetch_reason=res.reason,
               fetch_seconds=round(res.seconds, 3), doc_bytes=len(res.body) if res.body else 0)
    if not res.ok or res.body is None:
        rec.update(risk_status="FETCH_FAILED", mda_status="FETCH_FAILED", risk_text="", mda_text="")
        return rec
    try:
        parsed = P.parse_document(P.decode(res.body), str(row.form), str(row.period_end or ""))
    except Exception as e:  # noqa: BLE001 — recorded, never dropped
        rec.update(risk_status=f"PARSE_ERROR:{type(e).__name__}",
                   mda_status=f"PARSE_ERROR:{type(e).__name__}", risk_text="", mda_text="")
        return rec
    rec.update(parsed)
    return rec


def cmd_fetch(args: argparse.Namespace) -> int:
    logfile = LOG_DIR / "fetch_sp.log"
    E.MIN_INTERVAL = args.min_interval
    fl = pd.read_parquet(FETCH_LIST)
    if args.ciks:
        keep = {int(x) for x in args.ciks.split(",")}
        fl = fl[fl.cik.isin(keep)]
    order = list(dict.fromkeys(fl.cik.astype(int)))
    if args.limit_ciks:
        order = order[: args.limit_ciks]
    done = _done_accessions(include_failed=not args.retry_failed)
    todo = fl[fl.cik.isin(order) & ~fl.accession.isin(done)]
    _log(f"[fetch] list {len(fl)}; already done {len(done)}; to do {len(todo)} filings over "
         f"{todo.cik.nunique()} CIKs; free disk {E.disk_free_gb():.2f} GB", logfile)
    buf: list[dict] = []
    t0 = time.time()
    n_done = 0
    try:
        for i, cik in enumerate(order, 1):
            sub = todo[todo.cik == cik]
            if sub.empty:
                continue
            free = E.assert_disk(args.disk_floor)
            for _, row in sub.iterrows():
                buf.append(process_filing(row))
                n_done += 1
            if len(buf) >= args.shard_rows:
                _write_shard(buf)
                buf = []
            if i % 10 == 0:
                rate = n_done / max(1.0, time.time() - t0)
                _log(f"[fetch] {i}/{len(order)} CIKs; {n_done}/{len(todo)} filings; "
                     f"{rate:.2f} docs/s; requests {E.stats['requests']} retries "
                     f"{E.stats['retries']} failures {E.stats['failures']}; "
                     f"bytes {E.stats['bytes']/1e9:.2f} GB; free {free:.2f} GB", logfile)
    except E.DiskFloor as e:
        _log(f"[fetch] HALT (disk): {e}", logfile)
        if buf:
            _write_shard(buf)
        return 3
    except E.EdgarRefused as e:
        _log(f"[fetch] HALT (SEC refused): {e}", logfile)
        if buf:
            _write_shard(buf)
        return 4
    if buf:
        _write_shard(buf)
    _log(f"[fetch] DONE {n_done} filings in {time.time() - t0:.0f}s; requests "
         f"{E.stats['requests']}; failures {E.stats['failures']}; "
         f"bytes {E.stats['bytes']/1e9:.2f} GB", logfile)
    return 0


def cmd_reparse(args: argparse.Namespace) -> int:
    """b6_parse/2 over the complete S&P panel (review F4), into sp_sections_v2/ (sp_sections/ stays
    as the b6_parse/1 record). A row whose MD&A came from the title fallback or failed is RE-FETCHED
    and re-parsed (only those rows can carve differently under b6_parse/2); every other row keeps its
    item-carved text and is re-checked against the widened `_CONTAMINATION` on its stored text (the
    patterns are whitespace-insensitive, so the check equals the parser's). Resumable by accession."""
    logfile = LOG_DIR / "reparse_sp.log"
    E.MIN_INTERVAL = args.min_interval
    cols = SHARD_SCHEMA_COLS
    meta_cols = ["accession", "fetch_ok", "mda_status", "mda_source"]
    shards = sorted(SHARD_DIR.glob("shard_*.parquet"))
    # winners per accession from METADATA only (memory: the text is read one shard at a time)
    meta = pd.concat([pq.read_table(p, columns=meta_cols).to_pandas().assign(_shard=i, _row=range(
        pq.ParquetFile(p).metadata.num_rows)) for i, p in enumerate(shards)], ignore_index=True)
    win = latest_by_accession(meta)
    done = set()
    if SHARD_DIR_V2.is_dir():
        for p in SHARD_DIR_V2.glob("shard_*.parquet"):
            done |= set(pq.read_table(p, columns=["accession"]).column("accession").to_pylist())
    ok = win["fetch_ok"].fillna(False).astype(bool)
    win["refetch"] = ok & ((win["mda_status"] != "OK")
                           | win["mda_source"].isin(["title_fallback", "title_fallback_eof"]))
    win = win[~win.accession.isin(done)]
    _log(f"[reparse] v1 rows {len(meta)} -> {len(win) + len(done)} accessions; re-fetch "
         f"{int(win.refetch.sum())}; revalidate {int((~win.refetch).sum())}; already in v2 "
         f"{len(done)}", logfile)
    buf: list[dict] = []
    todo_rows: list[pd.Series] = []
    n_contam = {"risk": 0, "mda": 0}
    for i, p in enumerate(shards):
        w = win[win._shard == i]
        if w.empty:
            continue
        d = pq.read_table(p).to_pandas()[cols].iloc[w._row.to_numpy()]
        flags = dict(zip(w.accession, w.refetch))
        for _, r in d.iterrows():
            if flags[r.accession]:
                todo_rows.append(r[["cik", "form", "accession", "acceptance_dt", "filing_date",
                                    "period_end", "primary_doc"]])
                continue
            rec = r.to_dict()
            rec["parser_version"] = "b6_parse/2(revalidated)"
            for sec in ("risk", "mda"):
                if rec[f"{sec}_status"] == "OK" and P._CONTAMINATION.search(rec[f"{sec}_text"] or ""):
                    rec[f"{sec}_status"], rec[f"{sec}_text"] = "CONTAMINATED", ""
                    rec[f"{sec}_source"] = ""
                    n_contam[sec] += 1
            buf.append(rec)
            if len(buf) >= args.shard_rows:
                _write_shard(buf, SHARD_DIR_V2)
                buf = []
    if buf:
        _write_shard(buf, SHARD_DIR_V2)
        buf = []
    _log(f"[reparse] revalidated rows written; newly CONTAMINATED: {n_contam}", logfile)
    todo = pd.DataFrame(todo_rows)
    t0 = time.time()
    try:
        for i, (_, r) in enumerate(todo.iterrows(), 1):
            if i % 200 == 1:
                E.assert_disk(args.disk_floor)
            buf.append(process_filing(r))
            if len(buf) >= args.shard_rows:
                _write_shard(buf, SHARD_DIR_V2)
                buf = []
            if i % 200 == 0:
                _log(f"[reparse] re-fetched {i}/{len(todo)}; {i / max(1.0, time.time() - t0):.2f} "
                     f"docs/s; failures {E.stats['failures']}", logfile)
    except (E.DiskFloor, E.EdgarRefused) as e:
        if buf:
            _write_shard(buf, SHARD_DIR_V2)
        _log(f"[reparse] HALT: {e}", logfile)
        return 3
    if buf:
        _write_shard(buf, SHARD_DIR_V2)
    _log(f"[reparse] DONE: re-fetched {len(todo)}; failures {E.stats['failures']}", logfile)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B-6 S&P PIT text panel builder.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("universe", help="decide member CIKs per month; build the fetch list")
    pf = sub.add_parser("fetch", help="fetch + parse + store sections (resumable)")
    pf.add_argument("--limit-ciks", type=int, default=None)
    pf.add_argument("--ciks", default=None, help="comma list of CIKs (smoke tests)")
    pf.add_argument("--shard-rows", type=int, default=400)
    pf.add_argument("--disk-floor", type=float, default=E.DISK_FLOOR_GB)
    pf.add_argument("--min-interval", type=float, default=E.MIN_INTERVAL)
    pf.add_argument("--retry-failed", action="store_true",
                    help="re-attempt accessions whose recorded fetch failed (e.g. a transient DNS "
                         "outage); the new row is appended and preferred by every reader")
    pr = sub.add_parser("reparse", help="b6_parse/2 over the S&P panel -> sp_sections_v2/")
    pr.add_argument("--shard-rows", type=int, default=400)
    pr.add_argument("--disk-floor", type=float, default=E.DISK_FLOOR_GB)
    pr.add_argument("--min-interval", type=float, default=E.MIN_INTERVAL)
    args = ap.parse_args(argv)
    if args.cmd == "universe":
        return cmd_universe(args)
    if args.cmd == "reparse":
        return cmd_reparse(args)
    return cmd_fetch(args)


if __name__ == "__main__":
    np.seterr(all="ignore")
    sys.exit(main())
