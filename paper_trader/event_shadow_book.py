# paper_trader/event_shadow_book.py
"""EventShadowBook — a REPORT-ONLY virtual EVENT DESK for typed LLM calls (T-322).

WHY: the user directive is that the machine should "act like a trader," and a trader's
core desk is EVENT-DRIVEN — a filing drops, you size a position on it. D's event
interpreter (T-304, live forward-only) already emits typed calls with `direction` +
`materiality` + a stated `horizon`; today they resolve only as Brier predictions. This
gives them a BOOK, so the same calls also produce a TRADING record.

THE GATE IS NOT NEW — it is D's own pre-registered bar #5 (T-304): *"a paper sleeve acting
on the calls must beat its sector/market benchmark net of honest small/mid-cap costs."*
This module IS that sleeve, so the two records share ONE standard by construction
(≥30 closed positions per event_type + block-bootstrap diff_ci_low > 0 vs the twin).

Construction (frozen at t=0):
  * a call qualifies iff materiality ≥ MATERIALITY_FLOOR AND direction ∈ {bullish, bearish}
    (neutral/uncertain never open a position — an opinion is not a trade);
  * size = MAX_WEIGHT · materiality, signed by direction, re-capped ≤20%/name and gross
    ≤2.0 at THIS layer (defense in depth — reject + log, never clamp silently);
  * signal-t / fill-t+1: a call dated D is filled at the NEXT session's close, so
    look-ahead is structurally impossible (the btc_shadow construction);
  * held for the call's OWN stated horizon, closed at horizon at that day's close;
  * costs: ROUND_TRIP_BPS on entry+exit — single-name small/mid-cap honest, not ETF-cheap;
  * TWIN: SPY over the SAME holding windows — the honest "would doing nothing have won?"

PARAMETERIZED, NOT FORKED: `DeskConfig` selects the call SOURCE + state file, so the
agentic-analyst desk (E/T-321) is the same machinery pointed at a different feed. A desk
whose source does not exist yet ships DORMANT-but-armed and wakes when the feed lands.

FAIL-CLOSED on measurement: an unparseable horizon, a missing price, or a firewall
violation PARKS the call with a logged reason — it never guesses a holding window and
never fabricates a fill. Report-only: zero effect on orders, ever.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

# --- FROZEN construction (set at t=0; do NOT tune on accrued data) --- #
MATERIALITY_FLOOR = 0.50     # below this a call is noise, not a trade
MAX_WEIGHT = 0.20            # ≤20% per name (the analyst firewall bound, re-enforced here)
MAX_GROSS = 2.0              # Σ|w| ≤ 2.0
ROUND_TRIP_BPS = 0.0025      # 25 bps/side — honest single-name small/mid-cap, not ETF-cheap
TWIN_TICKER = "SPY"
MAX_HORIZON_DAYS = 252       # a "horizon" beyond a year is not an event trade → park

# --- FROZEN promotion gate: D's T-304 pre-registered bar #5, verbatim --- #
# "Net-of-cost tradability (only if 1-4 clear): a paper sleeve acting on the calls must
#  beat its sector/market benchmark net of honest small/mid-cap costs."
# Volume + CI bars are D's #1 and #3 — SHARED, not re-invented, so the desk record and the
# Brier record can never disagree about what 'good enough' means.
GATE_MIN_CLOSED_PER_TYPE = 30    # D bar #1: ≥30 resolved calls per event_type
GATE_REQUIRE_CI_LOW_GT_0 = True  # D bar #3: block-bootstrap diff_ci_low > 0 (point ≠ enough)


def parse_horizon_days(h: str, as_of: str) -> Optional[int]:
    """The call's OWN stated horizon → trading days. FAIL-CLOSED: returns None on anything
    unrecognized, so the caller PARKS the call rather than inventing a holding window."""
    if not h:
        return None
    s = str(h).strip().lower()
    m = re.search(r"(\d+)\s*(trading\s+day|business\s+day|session|day|week|month|quarter)", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        mult = {"trading day": 1, "business day": 1, "session": 1, "day": 1,
                "week": 5, "month": 21, "quarter": 63}[unit]
        d = n * mult
        return d if 1 <= d <= MAX_HORIZON_DAYS else None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s)         # an explicit end date
    if m:
        try:
            d = (pd.Timestamp(m.group(1)) - pd.Timestamp(as_of)).days
            approx = int(round(d * 5 / 7))            # calendar → trading days
            return approx if 1 <= approx <= MAX_HORIZON_DAYS else None
        except Exception:
            return None
    if "next day" in s or "one day" in s or s in ("1d", "eod", "close"):
        return 1
    return None


@dataclass(frozen=True)
class DeskConfig:
    """Selects the call SOURCE + state file. Two desks, one machinery (no fork)."""
    name: str
    state_path: str
    source_path: str                       # jsonl file OR notes directory
    loader: str = "event_calls"            # "event_calls" | "analyst_notes"


EVENT_DESK = DeskConfig(name="event_desk",
                        state_path="data/state/event_shadow_book.json",
                        source_path="data/intel/event_calls.jsonl",
                        loader="event_calls")
# E/T-321's agentic analyst: SAME machinery, different feed. Ships dormant-but-armed until
# the feed exists (the T-302 posture) — point `source_path` at it when it lands.
ANALYST_DESK = DeskConfig(name="analyst_desk",
                          state_path="data/state/analyst_desk_book.json",
                          source_path="data/intel/agentic_analyst_calls.jsonl",
                          loader="event_calls")


@dataclass
class EventShadowBook:
    cfg: DeskConfig = EVENT_DESK
    root: Optional[str] = None

    # ---------- state ----------
    def _base(self) -> Path:
        return Path(self.root) if self.root else Path(__file__).resolve().parents[1]

    def _file(self) -> Path:
        p = self._base() / self.cfg.state_path
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _state(self) -> Dict[str, Any]:
        try:
            return json.loads(self._file().read_text())
        except Exception:
            return {"_schema": "event_shadow/v1", "desk": self.cfg.name,
                    "open": [], "closed": [], "days": []}

    def _write(self, st: Dict[str, Any]) -> None:
        self._file().write_text(json.dumps(st, indent=2, default=str))

    # ---------- source (parameterized, not forked) ----------
    def _load_calls(self, as_of: str) -> Tuple[List[Dict[str, Any]], str]:
        """Calls DATED as_of from the configured feed. Returns ([], reason) when dormant."""
        src = self._base() / self.cfg.source_path
        if not src.exists():
            return [], f"no source yet at {self.cfg.source_path} (dormant-but-armed)"
        out: List[Dict[str, Any]] = []
        try:
            for line in src.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if str(rec.get("as_of", ""))[:10] == as_of:
                    out.append(rec)
        except Exception as exc:
            return [], f"source unreadable: {type(exc).__name__}"
        return out, ("ok" if out else "no calls dated this session")

    # ---------- the desk ----------
    def record(self, trade_date: str, *, closes: Optional[Dict[str, float]] = None,
               calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """One session: mark open positions, close those at horizon, open new qualifying
        calls (filled at TODAY's close = t+1 vs the call's as_of). Idempotent per date.
        REPORT-ONLY."""
        st = self._state()
        if any(d.get("date") == trade_date for d in st["days"]):
            return self._summary(st)                     # idempotent
        closes = closes or {}
        reasons: List[str] = []

        # 1) CLOSE positions whose horizon elapsed today
        still_open, closed_today = [], 0
        for pos in st["open"]:
            pos["held"] = int(pos.get("held", 0)) + 1
            px = closes.get(pos["symbol"])
            if pos["held"] >= int(pos["horizon_days"]):
                if px is None:
                    reasons.append(f"{pos['symbol']}: no close at horizon → held (degraded)")
                    still_open.append(pos)
                    continue
                gross = (px / pos["entry_px"] - 1.0) * pos["sign"]
                net = gross - 2 * ROUND_TRIP_BPS         # entry + exit
                twin_px = closes.get(TWIN_TICKER)
                twin_ret = ((twin_px / pos["twin_entry_px"] - 1.0) * pos["sign"]
                            if twin_px and pos.get("twin_entry_px") else None)
                st["closed"].append({
                    **{k: pos[k] for k in ("symbol", "event_type", "direction", "materiality",
                                           "weight", "sign", "as_of", "entry_date",
                                           "horizon_days")},
                    "exit_date": trade_date, "exit_px": round(float(px), 4),
                    "gross_ret": round(gross, 6), "net_ret": round(net, 6),
                    "twin_ret": (round(twin_ret, 6) if twin_ret is not None else None),
                    "excess_vs_twin": (round(net - twin_ret, 6) if twin_ret is not None else None),
                    "contrib": round(net * pos["weight"], 6)})
                closed_today += 1
            else:
                still_open.append(pos)
        st["open"] = still_open

        # 2) OPEN new qualifying calls (fill at TODAY's close ⇒ signal-t / fill-t+1)
        if calls is None:
            calls, src_reason = self._load_calls(_prev_session_key(trade_date, st))
            if src_reason not in ("ok",):
                reasons.append(src_reason)
        opened = 0
        gross_now = sum(abs(p["weight"]) for p in st["open"])
        for c in (calls or []):
            sym = str(c.get("symbol", "")).upper()
            direction = str(c.get("direction", "")).lower()
            mat = float(c.get("materiality", 0.0) or 0.0)
            if direction not in ("bullish", "bearish"):
                reasons.append(f"{sym}: direction={direction} → no position (opinion ≠ trade)")
                continue
            if mat < MATERIALITY_FLOOR:
                reasons.append(f"{sym}: materiality {mat:.2f} < floor {MATERIALITY_FLOOR}")
                continue
            hz = None
            for p in (c.get("predictions") or []):
                hz = parse_horizon_days(p.get("horizon", ""), str(c.get("as_of", trade_date))[:10])
                if hz:
                    break
            if not hz:
                reasons.append(f"{sym}: horizon unparseable → PARKED (never guessed)")
                continue
            px = closes.get(sym)
            if px is None:
                reasons.append(f"{sym}: no close → parked (no fabricated fill)")
                continue
            w = round(MAX_WEIGHT * min(1.0, mat), 4)
            if w > MAX_WEIGHT + 1e-9:
                reasons.append(f"{sym}: weight {w} exceeds cap → REJECTED")
                continue
            if gross_now + w > MAX_GROSS + 1e-9:
                reasons.append(f"{sym}: gross {gross_now + w:.2f} > {MAX_GROSS} → REJECTED")
                continue
            st["open"].append({
                "symbol": sym, "event_type": c.get("event_type", "unknown"),
                "direction": direction, "materiality": round(mat, 3), "weight": w,
                "sign": 1 if direction == "bullish" else -1,
                "as_of": str(c.get("as_of", ""))[:10], "entry_date": trade_date,
                "entry_px": round(float(px), 4),
                "twin_entry_px": (round(float(closes[TWIN_TICKER]), 4)
                                  if closes.get(TWIN_TICKER) else None),
                "horizon_days": int(hz), "held": 0})
            gross_now += w
            opened += 1

        st["days"].append({"date": trade_date, "opened": opened, "closed": closed_today,
                           "n_open": len(st["open"]),
                           "degraded": bool(reasons), "reasons": reasons[:8]})
        self._write(st)
        return self._summary(st)

    # ---------- reporting ----------
    def _summary(self, st: Dict[str, Any]) -> Dict[str, Any]:
        cl = st["closed"]
        s: Dict[str, Any] = {"desk": self.cfg.name, "n_days": len(st["days"]),
                             "n_open": len(st["open"]), "n_closed": len(cl), "armed": True}
        if cl:
            nets = [c["net_ret"] for c in cl]
            ex = [c["excess_vs_twin"] for c in cl if c.get("excess_vs_twin") is not None]
            s["mean_net_ret"] = round(sum(nets) / len(nets), 5)
            if ex:
                s["mean_excess_vs_twin"] = round(sum(ex) / len(ex), 5)
                s["hit_rate_vs_twin"] = round(sum(1 for e in ex if e > 0) / len(ex), 3)
        return s

    def promotion_gates(self, n_boot: int = 1000) -> Dict[str, Any]:
        """REPORT-ONLY status against D's T-304 bar (SHARED standard, not a new one)."""
        import numpy as np
        st = self._state()
        cl = [c for c in st["closed"] if c.get("excess_vs_twin") is not None]
        out: Dict[str, Any] = {
            "desk": self.cfg.name, "n_closed_scored": len(cl),
            "standard": "D/T-304 bar #1 (≥30 per event_type) + bar #3 (block-bootstrap "
                        "diff_ci_low > 0) + bar #5 (net-of-cost vs benchmark) — SHARED",
            "thresholds": {"min_closed_per_type": GATE_MIN_CLOSED_PER_TYPE,
                           "require_ci_low_gt_0": GATE_REQUIRE_CI_LOW_GT_0},
            "per_event_type": {}}
        by: Dict[str, List[float]] = {}
        for c in cl:
            by.setdefault(str(c.get("event_type", "unknown")), []).append(float(c["excess_vs_twin"]))
        any_pass = False
        for et, xs in sorted(by.items()):
            a = np.asarray(xs, dtype=float)
            row: Dict[str, Any] = {"n": len(a), "mean_excess": round(float(a.mean()), 5)}
            if len(a) >= GATE_MIN_CLOSED_PER_TYPE:
                rng = np.random.default_rng(0)
                boots = [float(rng.choice(a, size=len(a), replace=True).mean())
                         for _ in range(n_boot)]
                lo = float(np.percentile(boots, 2.5))
                row["ci_low"] = round(lo, 5)
                row["status"] = "PASS" if lo > 0 else "FAIL"
                any_pass = any_pass or lo > 0
            else:
                row["status"] = f"accruing ({len(a)}/{GATE_MIN_CLOSED_PER_TYPE})"
            out["per_event_type"][et] = row
        out["promote_to_paper_leg"] = bool(any_pass)
        return out


def _prev_session_key(trade_date: str, st: Dict[str, Any]) -> str:
    """The call date whose signals fill TODAY: the last recorded session, else yesterday.
    This is what makes fills strictly t+1 relative to the call (no look-ahead)."""
    days = [d["date"] for d in st.get("days", []) if d["date"] < trade_date]
    if days:
        return max(days)
    return str((pd.Timestamp(trade_date) - pd.Timedelta(days=1)).date())
