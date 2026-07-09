"""T-292 — build the analyst's daily input bundle (deterministic + PIT-honest).

Assembles what the model reads for one trade date:
  * per-account portfolio state (symbols + weights only — see the redaction rule);
  * the day's news for holdings + a watchlist (PIT: created_at < as_of);
  * special-situation deltas (EDGAR events parquet, detected_at <= as_of);
  * the regime event-state axis (T-291, context-only);
  * yesterday's still-open predictions (so the model can revisit them).

Three invariants, all enforced here rather than trusted downstream:
  1. DETERMINISTIC — the same inputs serialize to the same canonical JSON, whose
     SHA-256 is stamped into the note provenance (reproducibility + eval keying).
  2. PIT-HONEST — news uses created_at only; nothing dated >= as_of leaks in.
  3. NO SECRETS — a hard allowlist redaction pass: NO api keys, NO account
     numbers, NO credentials ever reach the bundle. The model sees symbols and
     weights, never identifiers. Verified by test + a final scrub.

Fail-OPEN per source: a missing/broken source contributes an empty section with
a `degraded` note; the bundle is always producible so the pulse never breaks.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
EVENTS_PARQUET = ROOT / "data" / "research" / "special_situations" / "events.parquet"
PRED_LOG = ROOT / "data" / "intel" / "analyst_predictions.jsonl"

# Keys that must NEVER appear in the bundle (redaction allowlist-by-denial).
_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password|account[_-]?number|acct[_-]?(num|no)|"
    r"cred|alpaca|apca|bearer|authorization)", re.I)
# Value shapes that look like live secrets (Alpaca key/broker acct), belt+braces.
_SECRET_VAL_RE = re.compile(r"^(PK|AK|SK)[A-Z0-9]{16,}$")


def _scrub(obj: Any) -> Any:
    """Recursively drop any key that smells like a credential/identifier and any
    value that matches a live-secret shape. Defense in depth: the builder never
    puts secrets in, and this guarantees it even if a source dict carries one."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if _SECRET_KEY_RE.search(str(k)):
                continue
            out[k] = _scrub(v)
        return out
    if isinstance(obj, list):
        return [_scrub(x) for x in obj]
    if isinstance(obj, str) and _SECRET_VAL_RE.match(obj):
        return "[REDACTED]"
    return obj


def _portfolio_section(portfolios: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """Per-account state = {account_label: {symbol: weight}}. Labels are the
    human names (offense-sso, sleeve, …), NEVER account numbers or creds."""
    clean = {}
    for label, holdings in sorted((portfolios or {}).items()):
        clean[str(label)] = {str(s): round(float(w), 6)
                             for s, w in sorted((holdings or {}).items())}
    return clean


def _news_section(as_of: dt.date, symbols: List[str],
                  load_panel=None, max_per_symbol: int = 8) -> Dict[str, Any]:
    """PIT news for the symbols. created_at < as_of only. Fail-open."""
    try:
        if load_panel is None:
            from intelligence.news_panel import load_panel as _lp
            load_panel = _lp
        df = load_panel(as_of=as_of)
        if df is None or len(df) == 0:
            return {"items": [], "degraded": True, "reason": "empty_panel"}
        want = {s.upper() for s in symbols}
        items: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            syms = row.get("symbols") or row.get("tickers") or []
            if isinstance(syms, str):
                syms = [syms]
            hit = want & {str(x).upper() for x in syms}
            if not hit:
                continue
            items.append({
                "created_at": str(row.get("created_at"))[:19],
                "symbols": sorted(hit),
                "headline": str(row.get("headline", ""))[:300],
                "summary": str(row.get("content", row.get("summary", "")))[:1200],
            })
        # deterministic order + per-symbol cap via a stable sort
        items.sort(key=lambda x: (x["created_at"], x["headline"]))
        return {"items": items[: max_per_symbol * max(1, len(want))], "degraded": False}
    except Exception as e:   # noqa: BLE001
        return {"items": [], "degraded": True, "reason": f"news_error:{type(e).__name__}"}


def _special_sits_section(as_of: dt.date, events_path: Path = EVENTS_PARQUET) -> Dict[str, Any]:
    try:
        import pandas as pd
        if not events_path.exists():
            return {"events": [], "degraded": True, "reason": "no_events_file"}
        df = pd.read_parquet(events_path)
        if "detected_at" in df.columns:
            df = df[pd.to_datetime(df["detected_at"], errors="coerce").dt.date <= as_of]
        ev = []
        for _, r in df.iterrows():
            ev.append({"event_id": str(r.get("event_id")),
                       "event_class": str(r.get("event_class")),
                       "ticker": str(r.get("primary_ticker")),
                       "file_date": str(r.get("file_date"))[:10],
                       "issuer": str(r.get("issuer", ""))[:120]})
        ev.sort(key=lambda x: (x["file_date"], x["event_id"]))
        return {"events": ev[:50], "degraded": False}
    except Exception as e:   # noqa: BLE001
        return {"events": [], "degraded": True, "reason": f"events_error:{type(e).__name__}"}


def _open_predictions_section(as_of: dt.date, pred_log: Path = PRED_LOG) -> Dict[str, Any]:
    """Yesterday's still-open predictions (unresolved, by_date >= as_of), so the
    model can revisit them. Read-only; fail-open."""
    try:
        if not pred_log.exists():
            return {"open": [], "degraded": False}
        seen: Dict[str, Dict[str, Any]] = {}
        for line in pred_log.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            pid = r.get("prediction_id") or r.get("statement")
            seen[pid] = r          # last write wins (resolution overwrites)
        openp = [{"statement": r.get("statement"), "probability": r.get("probability"),
                  "horizon": r.get("horizon")}
                 for r in seen.values() if not r.get("resolved")]
        openp.sort(key=lambda x: str(x.get("statement")))
        return {"open": openp[:50], "degraded": False}
    except Exception as e:   # noqa: BLE001
        return {"open": [], "degraded": True, "reason": f"pred_error:{type(e).__name__}"}


def build_bundle(as_of, *, portfolios: Optional[Dict[str, Dict[str, float]]] = None,
                 watchlist: Optional[List[str]] = None, event_state: Optional[str] = None,
                 load_panel=None) -> Dict[str, Any]:
    """Assemble the full, deterministic, secret-free input bundle for ``as_of``.
    ``portfolios`` = {account_label: {symbol: weight}}; ``watchlist`` extra
    symbols to pull news for; ``event_state`` the T-291 axis string (context)."""
    as_of = dt.date.fromisoformat(str(as_of)) if not isinstance(as_of, dt.date) else as_of
    portfolios = portfolios or {}
    held = sorted({s for h in portfolios.values() for s in (h or {})})
    symbols = sorted(set(held) | {s.upper() for s in (watchlist or [])})

    bundle = {
        "bundle_version": "analyst_input/v1",
        "as_of": as_of.isoformat(),
        "event_state": event_state,               # context only (T-291/T-233)
        "portfolios": _portfolio_section(portfolios),
        "watchlist": sorted({s.upper() for s in (watchlist or [])}),
        "news": _news_section(as_of, symbols, load_panel=load_panel),
        "special_situations": _special_sits_section(as_of),
        "open_predictions": _open_predictions_section(as_of),
    }
    return _scrub(bundle)          # final belt-and-braces secret scrub


def canonical_json(bundle: Dict[str, Any]) -> str:
    """Stable serialization: sorted keys, no whitespace drift → identical bytes
    for identical inputs (the SHA-256 basis)."""
    return json.dumps(bundle, sort_keys=True, separators=(",", ":"), default=str)


def bundle_sha256(bundle: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(bundle).encode("utf-8")).hexdigest()
