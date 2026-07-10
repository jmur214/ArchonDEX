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
PANEL_8K = ROOT / "data" / "edgar" / "8k" / "panel_8k_items.parquet"
SPECIAL_SITS = ROOT / "data" / "research" / "special_situations" / "events.parquet"

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
    df = df.dropna(subset=["filing_date"]).copy()
    df["fd"] = pd.to_datetime(df["filing_date"]).dt.date
    hi = _dt.date.fromisoformat(_iso(as_of))
    lo = _dt.date.fromisoformat(since) if since else hi
    df = df[(df["fd"] >= lo) & (df["fd"] <= hi)]
    if universe is not None:
        df = df[df["ticker"].astype(str).str.upper().isin({u.upper() for u in universe})]
    out: List[EventDocument] = []
    for _, r in df.iterrows():
        sym = str(r["ticker"]).upper()
        codes = [c.strip() for c in str(r.get("items", "")).split(",") if c.strip()]
        for code in codes:
            if code not in allowlist:
                continue                                   # materiality pre-filter
            out.append(EventDocument(
                document_ref=f"{r['accession']}#{code}", source="8k", symbol=sym,
                file_date=_iso(r["fd"]), item_code=code, event_class_hint=allowlist[code],
                text="",   # EDGAR body fetch is the live-phase seam (see module docstring)
                meta={"cik": r.get("cik"), "accession": r.get("accession"),
                      "acceptance_dt": str(r.get("acceptance_dt", ""))}))
    return out


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
                  seen: Optional[Set[str]] = None) -> List[EventDocument]:
    """The full forward surface: allowlisted 8-K items + special-sit deltas, minus `seen`
    document_refs (idempotency). One EventDocument == one model call."""
    docs = new_8k_documents(as_of, universe=universe, since=since) + \
        new_special_situation_documents(as_of, since=since)
    if seen:
        docs = [d for d in docs if d.document_ref not in seen]
    return docs
