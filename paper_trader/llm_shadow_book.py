# paper_trader/llm_shadow_book.py
"""LlmShadowBook — REPORT-ONLY virtual book of the LLM analyst's hypothetical actions.

Generalizes the T-276 btc_shadow pattern (Agent C) to the info-layer analyst. From the
analyst's FIRST validated note it runs a virtual book alongside the real paper machine —
zero real orders, zero risk (it consumes only schema-validated `hypothetical_actions`, and
an invalid note already means no action). It exists so the analyst's directional capability
accrues an honest forward record from day 1; G0/G1 gate PROMOTION, not OBSERVATION.

Construction (look-ahead structurally impossible, exactly the btc_shadow discipline):
  * consume YESTERDAY's note (`as_of` < trade_date) — the note is generated after that day's
    close, so the earliest possible fill is TODAY's close (signal-t / fill-t+1);
  * mark the current book to today's close (return earned by yesterday's positions), THEN
    rebalance to the note's target weights at today's close, with an honest turnover haircut.

DEFENSE IN DEPTH — the semantic firewall (E) already bounded the actions (shadow-only,
allowlist, ±20%) before they reach here; this layer RE-ENFORCES ≤20%/name, gross ≤2.0,
turnover ≤50% NAV/day and REJECTS + logs a violating note (never clamps silently).

THE BENCHMARK TWIN: a 60/40 SPY/AGG book at identical haircuts, in this same file — the
analyst's directional record is only meaningful against it.

FAIL-CLOSED: no note, or missing prices for a held name → positions HOLD, the day is flagged
`degraded` (never a fabricated fill). Idempotent per trade_date; S3-persisted
(`data/state/llm_shadow_book.json`, added to cloud_state.DURABLE_PATHS). Report-only —
nothing here can place, size, or influence a real order.
"""
from __future__ import annotations

import glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DEFAULT_PATH = "data/state/llm_shadow_book.json"
NOTES_DIR = "data/intel/analyst_notes"

# --- firewall re-enforcement (defense in depth; must match the Stage-1 caps) --- #
MAX_WEIGHT = 0.20            # ≤20% per name
MAX_GROSS = 2.0             # Σ|w| ≤ 2.0
MAX_TURNOVER = 0.50         # ≤50% NAV/day rebalance turnover
HAIRCUT = 0.0010            # 10 bps/side honest fill haircut on turnover
TWIN = {"SPY": 0.60, "AGG": 0.40}   # the 60/40 benchmark twin


def _firewall(targets: Dict[str, float]) -> Optional[str]:
    """Return a rejection reason if the target book violates a cap, else None."""
    for s, w in targets.items():
        if abs(w) > MAX_WEIGHT + 1e-9:
            return f"name {s} weight {w:.3f} exceeds ±{MAX_WEIGHT}"
    gross = sum(abs(w) for w in targets.values())
    if gross > MAX_GROSS + 1e-9:
        return f"gross {gross:.2f} exceeds {MAX_GROSS}"
    return None


@dataclass
class LlmShadowBook:
    path: str = DEFAULT_PATH
    root: Optional[str] = None
    notes_dir: str = NOTES_DIR

    def _file(self) -> Path:
        base = Path(self.root) if self.root else Path(__file__).resolve().parents[1]
        p = (base / self.path) if not Path(self.path).is_absolute() else Path(self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _state(self) -> Dict[str, Any]:
        try:
            return json.loads(self._file().read_text())
        except Exception:
            return {"_schema": "llm_shadow_book/v1", "points": [],
                    "book": {"positions": {}, "nav": 1.0, "last_close": {}},
                    "twin": {"nav": 1.0, "last_close": {}}}

    # ---- note loading (yesterday's validated note) ----
    def _load_yesterday_note(self, trade_date: str) -> Tuple[Optional[dict], Optional[str]]:
        """The latest schema-valid note with as_of < trade_date. (None, reason) if none."""
        base = Path(self.root) if self.root else Path(__file__).resolve().parents[1]
        d = base / self.notes_dir
        if not d.exists():
            return None, "no notes dir yet (dormant-but-armed)"
        try:
            from intelligence.analyst.note_schema import validate_note
        except Exception:                       # pragma: no cover - defensive
            validate_note = None
        cands = []
        for f in glob.glob(str(d / "*.json")):
            try:
                payload = json.loads(Path(f).read_text())
            except Exception:
                continue
            as_of = payload.get("as_of", "")
            if as_of and as_of < trade_date:
                cands.append((as_of, payload))
        if not cands:
            return None, "no note with as_of < trade_date yet"
        _, payload = max(cands, key=lambda x: x[0])
        if validate_note is not None:
            note, reason = validate_note(payload)
            if note is None:
                return None, f"note failed re-validation: {reason}"
            payload = note.model_dump()
        return payload, None

    def _targets(self, note: dict) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for a in note.get("hypothetical_actions", []):
            if a.get("account") == "shadow":
                out[a["symbol"]] = float(a["target_weight"])
        return out

    # ---- the daily virtual fill ----
    def record(self, trade_date: str, *, closes: Optional[Dict[str, float]] = None,
               note: Optional[dict] = None, note_reason: Optional[str] = None) -> Dict[str, Any]:
        """One report-only pulse. `closes` = {symbol: today's adjusted close}; `note` may be
        injected (tests) else loaded from the notes dir. Returns the heartbeat summary."""
        st = self._state()
        book, twin = st["book"], st["twin"]
        if note is None and note_reason is None:
            note, note_reason = self._load_yesterday_note(trade_date)

        def ret(sym: str, store: Dict[str, float]) -> Optional[float]:
            if closes is None or sym not in closes:
                return None
            last = store.get(sym)
            store[sym] = float(closes[sym])          # update AFTER computing return
            return None if last in (None, 0) else float(closes[sym]) / last - 1.0

        # --- degraded-day parking: no prices at all → HOLD, flag ---
        degraded = closes is None or len(closes) == 0
        pt: Dict[str, Any] = {"date": trade_date, "degraded": bool(degraded)}

        # --- 1. mark BOTH books to today's close (return earned by held positions) ---
        if not degraded:
            b_ret, missing = 0.0, False
            for s, w in list(book["positions"].items()):
                r = ret(s, book["last_close"])
                if r is None and closes is not None and s not in closes:
                    missing = True                    # a held name has no price → degraded
                b_ret += w * (r or 0.0)
            if missing:
                pt["degraded"] = degraded = True
            else:
                book["nav"] = float(book["nav"]) * (1 + b_ret)
                t_ret = sum(w * (ret(s, twin["last_close"]) or 0.0) for s, w in TWIN.items())
                twin["nav"] = float(twin["nav"]) * (1 + t_ret)
                pt["book_ret"] = round(b_ret, 6)
                pt["twin_ret"] = round(t_ret, 6)

        # --- 2. rebalance to yesterday's note (firewall re-enforced) ---
        applied = False
        if not degraded:
            if note is None:
                pt["action"] = f"no_note:{note_reason or 'none'}"
            else:
                targets = self._targets(note)
                reason = _firewall(targets)
                turn = sum(abs(targets.get(s, 0.0) - book["positions"].get(s, 0.0))
                           for s in set(targets) | set(book["positions"]))
                if reason is None and turn > MAX_TURNOVER + 1e-9:
                    reason = f"turnover {turn:.2f} exceeds {MAX_TURNOVER}"
                if reason is not None:
                    pt["action"] = f"REJECTED:{reason}"     # log, do NOT clamp; hold old book
                else:
                    book["nav"] = float(book["nav"]) * (1 - turn * HAIRCUT)
                    book["positions"] = {s: w for s, w in targets.items() if abs(w) > 1e-9}
                    # set each held name's price reference to TODAY's fill close, so
                    # tomorrow's return is measured from the fill (not a stale/None base).
                    for s in book["positions"]:
                        if s in closes:
                            book["last_close"][s] = float(closes[s])
                    pt.update(action="applied", turnover=round(turn, 4),
                              n_actions=len(targets), note_as_of=note.get("as_of"))
                    applied = True

        pt["book_nav"] = round(float(book["nav"]), 6)
        pt["twin_nav"] = round(float(twin["nav"]), 6)
        pt["positions"] = {s: round(w, 4) for s, w in book["positions"].items()}
        pt["applied"] = applied

        pts = [p for p in st["points"] if p["date"] != trade_date]     # idempotent per date
        pts.append(pt)
        pts.sort(key=lambda p: p["date"])
        st["points"] = pts
        self._file().write_text(json.dumps(st, indent=2, default=str))
        return self.heartbeat(st)

    def heartbeat(self, st: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Report-only one-line status: analyst-book NAV vs the 60/40 twin + Δ."""
        st = st or self._state()
        pts = st["points"]
        clean = [p for p in pts if not p.get("degraded")]
        hb = {"schema": "llm_shadow_book/v1", "n_days": len(pts), "n_clean": len(clean),
              "n_degraded": len(pts) - len(clean),
              "book_nav": round(float(st["book"]["nav"]), 4),
              "twin_nav": round(float(st["twin"]["nav"]), 4),
              "delta_vs_twin": round(float(st["book"]["nav"]) - float(st["twin"]["nav"]), 4),
              "n_rejected": sum(1 for p in pts if str(p.get("action", "")).startswith("REJECTED")),
              "armed": len(pts) > 0}
        hb.update(self._cohort_annotation(pts))
        return hb

    # ---------------------------------------------------------------------------------
    # T-342 DARK-COHORT ANNOTATION — a framing field, raw record byte-unchanged.
    #
    # E's ignition hold found this book spent its early life rehearsing a STRUCTURALLY
    # EMPTY channel: 0/17 notes ever carried a `hypothetical_action`, because the daily_v2
    # prompt told the model those actions "are never executed" and to omit the list. The
    # book reported action:'applied' every day and was TELLING THE TRUTH — applying nothing
    # IS applying the note. So the record is honest and the days are real, but they are NOT
    # allocation decisions and must never be scored as though a model chose 100% cash.
    #
    # Same class as the NOT-EVALUABLE guard: the framing travels WITH the numbers, because
    # a doc does not. The persisted points are untouched.
    # ---------------------------------------------------------------------------------
    def _cohort_annotation(self, pts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Label days whose consumed channel was structurally empty. Read-only."""
        empty_days = [p for p in pts
                      if not p.get("degraded") and not (p.get("targets") or p.get("positions"))]
        if not pts or len(empty_days) != len(
                [p for p in pts if not p.get("degraded")]):
            return {}                    # channel has carried something → no dark cohort
        return {"cohort": {
            "label": "daily_v2 era — channel structurally empty; NOT an allocation decision",
            "n_days": len(empty_days),
            "can_evidence": ("that the book, the firewall and the fill path RAN correctly "
                             "end-to-end on validated notes — the plumbing is proven."),
            "cannot_evidence": ("ANY judgement about the analyst's allocation skill. The "
                                "consumed field carried nothing in its entire observed "
                                "history (the daily_v2 prompt said the actions are never "
                                "executed and to omit the list), so 100% cash was the "
                                "PROMPT's behaviour, not the model's choice. Do NOT score "
                                "this stretch against the twin as if a decision was made."),
            "re_baseline": ("when a new prompt version lands, this book RE-BASELINES at the "
                            "version boundary together with the real account — that is the "
                            "clean A/B; comparing across the boundary is not."),
            "source": "T-342 / E's ignition hold"}}
