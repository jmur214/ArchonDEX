"""T-304 — forward "new documents today" feed for the event-interpreter.

Two discrete-document sources, each yielding ONE `EventDocument` per new item:
  * 8-K items — `data/edgar/8k/panel_8k_items.parquet` (item CODES per accession). The 8-K
    panel has no `load_panel`/delta accessor (unlike news_panel), so this provides the small
    PIT accessor: filter by `filing_date`, split `items`, apply the materiality allowlist.
  * special-situations deltas — `data/research/special_situations/events.parquet` (already
    text-bearing: issuer/terms/event_class). PIT filter on `detected_at ≤ as_of`.

FORWARD-ONLY (`[NN-AI-GATE]`): callers pass `as_of`; documents whose PIT date is after `as_of`
are excluded. Idempotency (one call per document, ever) is the caller's `seen` set on
`document_ref`, mirroring eval_harness's `logged` set.

The 8-K BODY TEXT is a live-phase dependency: the panel gives the item code + accession, not the
filing text. `EventDocument.text` is populated from what's on disk now (special-sit terms; 8-K
metadata); the EDGAR full-text fetch for 8-K bodies attaches at the same time as the model adapter
(both are the "when it lands" seam). Design + schema + feed are complete now.
"""
from __future__ import annotations

import datetime as _dt
import pathlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
# The batch-built RESEARCH panel (T-137): in no image and no sync, frozen at 2026-06-10.
# It stays the default for offline callers; the daily pulse reads the forward panel below.
PANEL_8K = ROOT / "data" / "edgar" / "8k" / "panel_8k_items.parquet"
SPECIAL_SITS = ROOT / "data" / "research" / "special_situations" / "events.parquet"
# T-412: the FORWARD panel the cloud fetches each morning (scripts/archive_altdata_t136
# pull_8k_items, via paper_trader.altdata_archive.run_8k_feed), relative to a run's root.
# Same columns as the research panel plus primary_document/index_date/fetched_at, so one
# reader serves both. It lives in the synced alt-data directory.
FORWARD_PANEL_REL = "data/macro_data/alt/edgar_8k_items.parquet"
# Stale when the newest FILING is older than this: ~25 tracked 8-Ks land every business
# day, so 5 calendar days covers a weekend plus a holiday and still catches a dead feed.
PANEL_MAX_AGE_DAYS = 5
# What the reader below cannot work without.
REQUIRED_COLUMNS = ("ticker", "cik", "accession", "filing_date", "items")


def filing_dates(values: pd.Series) -> pd.Series:
    """Panel filing dates as timestamps; an unparseable one is NaT. ONE coercion for the
    status check and the reader: the status used to tolerate a bad date while the reader
    raised on it, so a panel called fresh produced no document at all."""
    return pd.to_datetime(values, errors="coerce", format="mixed")


def panel_status(panel_path: pathlib.Path, as_of, *,
                 max_age_days: int = PANEL_MAX_AGE_DAYS) -> Dict:
    """Is the 8-K panel at ``panel_path`` usable for a forward run on ``as_of``?

    ``{"ok", "reason", "n_rows", "newest_filing_date", "age_days"}``. NOT ok when the
    file is absent, unreadable, empty, has no parseable filing date, or its newest filing
    is older than ``max_age_days`` — each with its own reason. A missing panel used to read
    as "0 documents today" (T-411): the caller must report this as degraded, never as a
    quiet day."""
    out: Dict = {"ok": False, "path": str(panel_path), "n_rows": 0,
                 "newest_filing_date": None, "age_days": None}
    if not panel_path.exists():
        return {**out, "reason": f"8k_panel_absent: {panel_path.name} is not on disk"}
    try:
        df = pd.read_parquet(panel_path)
        missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
        if missing:
            return {**out, "n_rows": int(len(df)),
                    "reason": f"8k_panel_malformed: no column {', '.join(missing)}"}
        fd = filing_dates(df["filing_date"])
    except Exception as exc:
        return {**out, "reason": f"8k_panel_unreadable: {type(exc).__name__}"}
    out["n_rows"] = int(len(fd))
    out["n_bad_dates"] = int(fd.isna().sum())
    fd = fd.dropna()
    if fd.empty:
        return {**out, "reason": "8k_panel_empty: no row carries a parseable filing_date"}
    newest = fd.max().date()
    age = (_dt.date.fromisoformat(_iso(as_of)) - newest).days
    out.update(newest_filing_date=newest.isoformat(), age_days=int(age))
    if age > max_age_days:
        return {**out, "reason": (f"8k_panel_stale: newest filing {newest} is {age}d old "
                                  f"(budget {max_age_days}d)")}
    return {**out, "ok": True, "reason": "ok"}

# ---- the pre-registered materiality pre-filter (8-K item allowlist) ------------------
# Rationale: the interpreter earns its call budget only where an LLM plausibly beats a
# dictionary — i.e. on items carrying an interpretable free-text BODY about a discrete,
# potentially-material event. Boilerplate / pointer-only / vote-tally items are EXCLUDED.
ITEM_ALLOWLIST: Dict[str, str] = {
    "1.01": "material_definitive_agreement", "1.02": "termination_of_agreement",
    "1.03": "bankruptcy_or_receivership", "2.01": "acquisition_or_disposition",
    "2.02": "results_of_operations", "2.03": "creation_of_direct_financial_obligation",
    "2.04": "triggering_event_accelerating_obligation", "2.05": "exit_or_disposal_costs",
    "2.06": "material_impairment", "3.01": "delisting_or_listing_deficiency",
    "3.03": "material_modification_to_security_holders_rights",
    "4.01": "change_in_accountant", "4.02": "non_reliance_on_prior_financials",
    "5.01": "change_in_control", "5.02": "director_or_officer_change",
    "7.01": "reg_fd_disclosure", "8.01": "other_material_event",
}
# EXCLUDED (stated so the exclusion is auditable, not silent):
#   9.01 financial-statements-&-exhibits (no standalone interpretable body — attachment pointer);
#   5.03 bylaw amendments, 5.04 trading-blackout, 5.05 ethics-code, 5.06 shell-status,
#   5.07 submission-of-matters-to-a-vote (tally, not narrative), 5.08 shareholder-nominations,
#   3.02 unregistered-sales (usually routine), 6.x asset-backed-securities.
ITEM_EXCLUDED = {"9.01", "5.03", "5.04", "5.05", "5.06", "5.07", "5.08", "3.02",
                 "6.01", "6.02", "6.03", "6.04", "6.05"}


@dataclass
class EventDocument:
    """ONE discrete document handed to ONE model call."""
    document_ref: str            # '{accession}#{item}' (8-K) or the special-sit event_id
    source: str                  # "8k" | "special_situation"
    symbol: str
    file_date: str               # ISO YYYY-MM-DD (the doc's PIT date)
    item_code: Optional[str] = None
    event_class_hint: Optional[str] = None     # 8-K item label, or special-sit event_class
    text: str = ""               # interpretable body available on disk NOW
    meta: Dict = field(default_factory=dict)


def _iso(x) -> str:
    return pd.Timestamp(x).date().isoformat()


def new_8k_documents(as_of, *, universe: Optional[Set[str]] = None,
                     since: Optional[str] = None, allowlist: Dict[str, str] = None,
                     panel_path: pathlib.Path = PANEL_8K) -> List[EventDocument]:
    """New 8-K item-documents on/through `as_of` (PIT). One row per (accession, allowlisted item).

    `since` (ISO date, exclusive) bounds the lower edge for a daily 'new today' pull; default =
    just `as_of`'s day. `universe` (uppercased tickers) restricts the surface. Items not in the
    allowlist are dropped (the materiality pre-filter)."""
    allowlist = ITEM_ALLOWLIST if allowlist is None else allowlist
    if not panel_path.exists():
        return []
    df = pd.read_parquet(panel_path)
    df = df.assign(fd=filing_dates(df["filing_date"])).dropna(subset=["fd"])
    df["fd"] = df["fd"].dt.date
    hi = _dt.date.fromisoformat(_iso(as_of))
    lo = _dt.date.fromisoformat(since) if since else hi
    df = df[(df["fd"] >= lo) & (df["fd"] <= hi)]
    if universe is not None:
        df = df[df["ticker"].astype(str).str.upper().isin({u.upper() for u in universe})]
    # One row per (accession, item code), vectorised: split the items list, explode, and
    # apply the materiality allowlist as a column filter. The research panel has no
    # primary_document column; the forward panel (T-412) does.
    df = df.reindex(columns=[*df.columns.drop("primary_document", errors="ignore"),
                             "primary_document"])
    df = df.assign(code=df["items"].fillna("").astype(str).str.split(",")).explode("code")
    df["code"] = df["code"].astype(str).str.strip()
    df = df[df["code"].isin(list(allowlist))]               # materiality pre-filter
    return [EventDocument(
        document_ref=f"{r.accession}#{r.code}", source="8k", symbol=str(r.ticker).upper(),
        file_date=_iso(r.fd), item_code=r.code, event_class_hint=allowlist[r.code],
        text="",   # EDGAR body fetch is the live-phase seam (see module docstring)
        meta={"cik": r.cik, "accession": r.accession,
              "acceptance_dt": str(getattr(r, "acceptance_dt", "") or ""),
              # T-412: the forward panel records the primary document, so the body fetch
              # can skip its own submissions lookup (half the SEC requests per document)
              "primary_document": (r.primary_document
                                   if isinstance(r.primary_document, str)
                                   and r.primary_document else None)})
        for r in df.itertuples(index=False)]


def new_special_situation_documents(as_of, *, since: Optional[str] = None,
                                    path: pathlib.Path = SPECIAL_SITS) -> List[EventDocument]:
    """New special-situations deltas with `detected_at ≤ as_of` (PIT). Text-bearing already."""
    if not path.exists():
        return []
    df = pd.read_parquet(path)
    if "detected_at" not in df.columns or not len(df):
        return []
    df = df.copy(); df["det"] = pd.to_datetime(df["detected_at"]).dt.date
    hi = _dt.date.fromisoformat(_iso(as_of))
    lo = _dt.date.fromisoformat(since) if since else None
    df = df[df["det"] <= hi]
    if lo is not None:
        df = df[df["det"] >= lo]
    out: List[EventDocument] = []
    for _, r in df.iterrows():
        terms = r.get("terms")
        text = terms if isinstance(terms, str) else (str(terms) if terms is not None else "")
        out.append(EventDocument(
            document_ref=str(r["event_id"]), source="special_situation",
            symbol=str(r.get("primary_ticker", "")).upper(),
            file_date=_iso(r.get("file_date", r["det"])),
            event_class_hint=str(r.get("event_class", "")),
            text=f"{r.get('issuer','')}: {text}".strip(),
            meta={"form_type": r.get("form_type"), "filing_url": r.get("filing_url"),
                  "terms_flag": r.get("terms_flag")}))
    return out


def new_documents(as_of, *, universe: Optional[Set[str]] = None, since: Optional[str] = None,
                  seen: Optional[Set[str]] = None,
                  panel_path: Optional[pathlib.Path] = None) -> List[EventDocument]:
    """The full forward surface: allowlisted 8-K items + special-sit deltas, minus `seen`
    document_refs (idempotency). One EventDocument == one model call. ``panel_path``
    selects the 8-K panel (default: the research panel)."""
    docs = new_8k_documents(as_of, universe=universe, since=since,
                            panel_path=panel_path or PANEL_8K) + \
        new_special_situation_documents(as_of, since=since)
    # One call per document, ever — within this batch too: a filing listed twice in the
    # panel would otherwise be paid for twice before the ledger could see the first.
    unique: Dict[str, EventDocument] = {}
    for d in docs:
        unique.setdefault(d.document_ref, d)              # first listing wins, order kept
    docs = list(unique.values())
    if seen:
        docs = [d for d in docs if d.document_ref not in seen]
    return docs
