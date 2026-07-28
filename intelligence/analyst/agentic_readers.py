"""T-321 — the REAL read-only store-readers for the agentic analyst's tools.

``intelligence.analyst.agentic_tools.AgenticTools(readers=...)`` takes a dict
``{tool_name: callable}``; each callable receives ONE dict (the model's already
shape-checked tool input) and returns a JSON-able value. This module builds that
dict of six readers, each bound to a fixed ``root`` (repo root) and ``as_of``
(the note's trade date) via a closure.

Three invariants, enforced HERE so the tool surface can trust them:

  1. READ-ONLY — every reader only ever reads; none writes, appends, or mutates.
  2. PIT-GUARDED — nothing dated on-or-after ``as_of`` reaches the model (news
     uses ``created_at`` strictly < ``as_of``; every other store filters its
     record timestamp ≤ ``as_of``). No look-ahead can leak through a tool.
  3. FAIL-CLOSED — a missing store, an unreadable file, a malformed row: the
     reader returns ``[]`` (never raises, never fabricates a plausible value).
     ``AgenticTools.execute`` also try/excepts, but readers must not lean on it.

Every result is additionally row-capped (``MAX_ROWS``) so a tool call stays
small — the size-bound in ``agentic_tools`` is the second line of defence.

Store map (paths are root-relative; a store that does not exist yet simply
returns ``[]`` until it is populated):
  * query_news              → data/intel/news_panel/news_YYYYMM.parquet  (EXISTS)
  * query_prices            → data/processed/tr_reconciled/<TKR>_1d.csv  (EXISTS)
  * query_rate_path         → data/macro_data/alt/fred_rate_path.parquet (accrues)
  * query_events            → data/intel/event_calls.jsonl               (accrues)
  * query_own_notes         → data/intel/analyst_notes_agentic/*.json    (accrues)
  * query_resolved_predictions → data/intel/analyst_predictions.jsonl    (accrues)
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd

# Hard row cap on any single reader result — keeps a tool result small regardless
# of what the model asks for (belt to agentic_tools' char-size braces).
MAX_ROWS = 50

Reader = Callable[[Dict[str, Any]], Any]


# ── small pure helpers ─────────────────────────────────────────────────────────
def _as_date(value: Union[str, dt.date, dt.datetime]) -> dt.date:
    """Normalize a date / datetime / ISO string to a ``date``. Raises on garbage
    (only ever called on the factory's ``as_of``, which the caller controls)."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def _opt_date(value: Any) -> Optional[dt.date]:
    """Best-effort date parse of an arbitrary field; ``None`` on anything unparseable
    (a malformed timestamp must never crash a PIT filter — it is simply excluded)."""
    if value is None:
        return None
    try:
        return _as_date(value)
    except Exception:  # noqa: BLE001 — unparseable → treat as absent
        return None


def _cap(value: Any) -> int:
    """Clamp a model-supplied ``limit`` into ``[1, MAX_ROWS]``; default to the cap."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return MAX_ROWS
    return max(1, min(n, MAX_ROWS))


def _symbols_of(cell: Any) -> set[str]:
    """Row ``symbols`` may be a list, a numpy array, or a bare string → upper set."""
    if cell is None:
        return set()
    if isinstance(cell, str):
        return {cell.upper()}
    try:
        return {str(x).upper() for x in cell}
    except TypeError:
        return {str(cell).upper()}


# ── the factory ────────────────────────────────────────────────────────────────
def build_readers(root: Union[str, Path],
                  as_of: Union[str, dt.date, dt.datetime]) -> Dict[str, Reader]:
    """Return the six read-only, PIT-guarded, fail-closed readers bound to
    ``root`` (repo/app root) and ``as_of`` (the note's trade date)."""
    root_p = Path(root)
    as_of_date = _as_date(as_of)
    # Strict PIT cutoff for tz-aware ``created_at`` (news): midnight UTC of as_of.
    news_cutoff = pd.Timestamp(as_of_date, tz="UTC")

    # -- query_news ------------------------------------------------------------
    def query_news(inp: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            ticker = str(inp.get("ticker", "")).upper().strip()
            if not ticker:
                return []
            panel_dir = root_p / "data" / "intel" / "news_panel"
            if not panel_dir.is_dir():
                return []
            frames = []
            for p in sorted(panel_dir.glob("news_*.parquet")):
                try:
                    frames.append(pd.read_parquet(p))
                except Exception:  # noqa: BLE001 — skip one bad monthly file
                    continue
            if not frames:
                return []
            df = pd.concat(frames, ignore_index=True)
            if "created_at" not in df.columns or "symbols" not in df.columns:
                return []
            created = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
            mask = created.notna() & (created < news_cutoff)  # PIT: created_at ONLY
            cdate = created.dt.date
            dfrom, dto = _opt_date(inp.get("date_from")), _opt_date(inp.get("date_to"))
            if dfrom is not None:
                mask &= cdate >= dfrom
            if dto is not None:
                mask &= cdate <= dto
            mask &= df["symbols"].map(lambda s: ticker in _symbols_of(s))
            sub = df.assign(_ca=created)[mask].sort_values("_ca").tail(MAX_ROWS)
            return [{
                "created_at": str(r["_ca"])[:19],
                "headline": str(r.get("headline", ""))[:300],
                "summary": str(r.get("content") or r.get("summary") or "")[:800],
            } for _, r in sub.iterrows()]
        except Exception:  # noqa: BLE001 — fail-closed
            return []

    # -- query_prices ----------------------------------------------------------
    def query_prices(inp: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            ticker = str(inp.get("ticker", "")).upper().strip()
            if not ticker:
                return []
            path = root_p / "data" / "processed" / "tr_reconciled" / f"{ticker}_1d.csv"
            if not path.exists():
                return []
            df = pd.read_csv(path)
            if "Date" not in df.columns or "Close" not in df.columns:
                return []
            ddate = pd.to_datetime(df["Date"], errors="coerce").dt.date
            close = pd.to_numeric(df["Close"], errors="coerce")
            mask = ddate.notna() & close.notna() & (ddate <= as_of_date)  # PIT: ≤ as_of
            dfrom, dto = _opt_date(inp.get("date_from")), _opt_date(inp.get("date_to"))
            if dfrom is not None:
                mask &= ddate >= dfrom
            if dto is not None:
                mask &= ddate <= dto
            sub = df.assign(_d=ddate, _c=close)[mask].sort_values("_d").tail(MAX_ROWS)
            return [{"date": str(r["_d"]), "close": round(float(r["_c"]), 6)}
                    for _, r in sub.iterrows()]
        except Exception:  # noqa: BLE001
            return []

    # -- query_rate_path -------------------------------------------------------
    def query_rate_path(inp: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            path = root_p / "data" / "macro_data" / "alt" / "fred_rate_path.parquet"
            if not path.exists():
                return []
            df = pd.read_parquet(path)
            need = {"series", "observation_date", "value"}
            if not need.issubset(df.columns):
                return []
            odate = pd.to_datetime(df["observation_date"], errors="coerce").dt.date
            mask = odate.notna() & (odate <= as_of_date)  # PIT: ≤ as_of
            dfrom, dto = _opt_date(inp.get("date_from")), _opt_date(inp.get("date_to"))
            if dfrom is not None:
                mask &= odate >= dfrom
            if dto is not None:
                mask &= odate <= dto
            sub = df[mask].assign(_d=odate[mask].map(str))
            if sub.empty:
                return []
            # long → wide: {date, DFEDTARL?, DFEDTARU?, EFFR?}
            piv = sub.pivot_table(index="_d", columns="series", values="value",
                                  aggfunc="last").sort_index().tail(MAX_ROWS)
            rows: List[Dict[str, Any]] = []
            for day, row in piv.iterrows():
                rec: Dict[str, Any] = {"date": str(day)}
                for series_id, val in row.items():
                    if pd.notna(val):
                        rec[str(series_id)] = round(float(val), 4)
                rows.append(rec)
            return rows
        except Exception:  # noqa: BLE001
            return []

    # -- query_events ----------------------------------------------------------
    def query_events(inp: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            path = root_p / "data" / "intel" / "event_calls.jsonl"
            if not path.exists():
                return []
            symbol = inp.get("symbol")
            symbol = str(symbol).upper().strip() if symbol else None
            limit = _cap(inp.get("limit"))
            rows: List[Dict[str, Any]] = []
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                stamp = r.get("note_date") or r.get("as_of")
                rec_date = _opt_date(stamp)
                if rec_date is None or rec_date > as_of_date:  # PIT: ≤ as_of
                    continue
                ec = r.get("event_call") or {}
                sym = str(r.get("symbol") or ec.get("symbol") or "").upper()
                if symbol and sym != symbol:
                    continue
                rows.append({
                    "as_of": str(stamp)[:19],
                    "symbol": sym,
                    "event_type": ec.get("event_type"),
                    "materiality": ec.get("materiality"),
                    "direction": ec.get("direction"),
                    "document_ref": ec.get("document_ref"),
                })
            rows.sort(key=lambda x: str(x["as_of"]))
            return rows[-limit:]
        except Exception:  # noqa: BLE001
            return []

    # -- query_own_notes -------------------------------------------------------
    def query_own_notes(inp: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            notes_dir = root_p / "data" / "intel" / "analyst_notes_agentic"
            if not notes_dir.is_dir():
                return []
            limit = _cap(inp.get("limit"))
            notes: List[Dict[str, Any]] = []
            for p in sorted(notes_dir.glob("*.json")):
                try:
                    n = json.loads(p.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                note_date = _opt_date(n.get("as_of"))
                if note_date is None or note_date > as_of_date:  # PIT: ≤ as_of
                    continue
                preds = n.get("predictions") or []
                notes.append({
                    "as_of": n.get("as_of"),
                    "market_assessment": str(n.get("market_assessment", ""))[:800],
                    "predictions": [{
                        "statement": str(pr.get("statement", ""))[:200],
                        "probability": pr.get("probability"),
                        "horizon": pr.get("horizon"),
                    } for pr in preds[:10]],
                })
            notes.sort(key=lambda x: str(x.get("as_of")))
            return notes[-limit:]
        except Exception:  # noqa: BLE001
            return []

    # -- query_resolved_predictions --------------------------------------------
    def query_resolved_predictions(inp: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            path = root_p / "data" / "intel" / "analyst_predictions.jsonl"
            if not path.exists():
                return []
            limit = _cap(inp.get("limit"))
            rows: List[Dict[str, Any]] = []
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                res_date = _opt_date(r.get("resolved_at") or r.get("resolve_date"))
                if res_date is None or res_date > as_of_date:  # PIT: ≤ as_of
                    continue
                if not r.get("resolvable"):     # only genuinely-scored rows
                    continue
                prob, outcome = r.get("probability"), r.get("outcome")
                brier = None
                if isinstance(prob, (int, float)) and outcome in (0, 1):
                    brier = round((float(prob) - float(outcome)) ** 2, 4)
                rows.append({
                    "statement": str(r.get("statement", ""))[:200],
                    "probability": prob,
                    "outcome": outcome,
                    "brier": brier,
                    "resolve_date": r.get("resolve_date"),
                    "category": r.get("category"),
                })
            return rows[-limit:]
        except Exception:  # noqa: BLE001
            return []

    return {
        "query_news": query_news,
        "query_prices": query_prices,
        "query_rate_path": query_rate_path,
        "query_events": query_events,
        "query_own_notes": query_own_notes,
        "query_resolved_predictions": query_resolved_predictions,
    }
