# paper_trader/thesis_book.py
"""ThesisBook — the REPORT-ONLY virtual book for D's thesis desk (T-326).

Instance #3 of the shadow-desk parameterization (after the event desk + the agentic-analyst
desk, T-322). It reuses that machinery's `DeskConfig`, firewall bounds, cost rate, twin
ticker and fail-closed conventions, but the POSITION MECHANICS genuinely differ — which is
why the mechanics live here rather than being bent into the fixed-horizon desk:

  1. HOLD-UNTIL-FALSIFIED-OR-HORIZON. A thesis runs months-to-years. A falsifier that fires
     closes the basket at the NEXT close and marks the thesis FALSIFIED (a falsifier is not
     an opinion — it is the pre-stated condition under which the thesis was wrong).
  2. TWIN = SPY over MATCHED windows. D flagged this explicitly: a thesis is an EQUITY bet,
     so a 60/40 twin would flatter it. Every outcome is scored against SPY over the
     identical holding window.
  3. MULTI-INSTRUMENT BASKETS. A thesis names several legs (primary / second_order /
     sector_etf / hedge). The book holds the basket at the thesis's own `weight_hint`
     (renormalized), costing EVERY leg at the honest 25 bps single-name rate.

SCORING IS D'S, NOT MINE. The book's job is to produce `ThesisOutcome` records (realized
basket return + twin return over the SAME window); the verdict comes from D's
`thesis_scoring.promotion_check` — the pre-stated T-324 bar (≥20 RESOLVED per theme_class
AND bootstrap CI on the mean log-wealth ratio excluding zero), with A's skew-aware payoff
profile reported alongside. Re-implementing that here would create a second standard, which
is exactly what the handoff forbids.

CHANNEL FIREWALL: two SUB-BOOKS keyed on `origin` (machine / user_seeded). The records
never blend — the bias-firewall directive applies to scoring attribution, so a user-seeded
thesis can never inflate the machine's record (or vice versa).

Report-only: zero effect on orders, ever. Fail-closed parking + S3 durability as always.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from paper_trader.event_shadow_book import (MAX_GROSS, MAX_WEIGHT, ROUND_TRIP_BPS,
                                            TWIN_TICKER, DeskConfig)

# --- FROZEN construction (set at t=0; do NOT tune on accrued data) --- #
CONVICTION_FLOOR = 0.50      # below this a thesis is a musing, not a position
MAX_THESIS_GROSS = 0.60      # a single thesis basket ≤60% gross (it is a satellite, not the book)

# --- The two channel sub-books (the bias firewall on ATTRIBUTION) --- #
MACHINE_DESK = DeskConfig(name="thesis_machine",
                          state_path="data/state/thesis_book_machine.json",
                          source_path="data/intel/thesis_calls.jsonl",
                          loader="thesis_calls")
USER_DESK = DeskConfig(name="thesis_user_seeded",
                       state_path="data/state/thesis_book_user_seeded.json",
                       source_path="data/intel/thesis_calls.jsonl",
                       loader="thesis_calls")
_ORIGIN_FOR = {"thesis_machine": "machine", "thesis_user_seeded": "user_seeded"}


@dataclass
class ThesisBook:
    cfg: DeskConfig = MACHINE_DESK
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
            return {"_schema": "thesis_book/v1", "desk": self.cfg.name,
                    "origin": _ORIGIN_FOR.get(self.cfg.name, "machine"),
                    "open": [], "closed": [], "days": []}

    def _write(self, st: Dict[str, Any]) -> None:
        self._file().write_text(json.dumps(st, indent=2, default=str))

    @property
    def origin(self) -> str:
        return _ORIGIN_FOR.get(self.cfg.name, "machine")

    # ---------- source (channel-filtered: the firewall) ----------
    def _load_theses(self, as_of: str) -> tuple[List[Dict[str, Any]], str]:
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
                # THE CHANNEL FIREWALL: this sub-book only ever sees its own origin.
                if str(rec.get("origin", "machine")) != self.origin:
                    continue
                if str(rec.get("as_of", ""))[:10] == as_of:
                    out.append(rec)
        except Exception as exc:
            return [], f"source unreadable: {type(exc).__name__}"
        return out, ("ok" if out else "no theses dated this session")

    # ---------- basket construction ----------
    @staticmethod
    def _basket_weights(legs: List[Dict[str, Any]], conviction: float,
                        ) -> tuple[Optional[Dict[str, float]], Optional[str]]:
        """Absolute basket weights from the thesis's own `weight_hint` PROPORTIONS.

        `weight_hint` is a within-basket share (D's schema: [0,1], default 0), NOT an
        absolute portfolio weight — so the ABSOLUTE size is this book's decision and is
        constructed to satisfy BOTH firewall caps up front:
            scale = min(MAX_THESIS_GROSS · conviction,  MAX_WEIGHT / largest_share)
        That is a SIZING RULE, not a silent clamp: the model never requested an absolute
        weight, so nothing of its request is being quietly shrunk. Genuinely malformed
        input (no legs / no symbols) still REJECTS with a logged reason, and the resulting
        weights are re-asserted against both caps before use (belt and braces).
        """
        if not legs:
            return None, "no instrument legs"
        hints = {str(l.get("symbol", "")).upper(): float(l.get("weight_hint", 0.0) or 0.0)
                 for l in legs if l.get("symbol")}
        if not hints:
            return None, "no usable symbols"
        tot = sum(abs(v) for v in hints.values())
        if tot <= 0:                                   # no hints given → equal-weight the legs
            hints = {s: 1.0 / len(hints) for s in hints}
            tot = 1.0
        shares = {s: abs(v) / tot for s, v in hints.items()}      # within-basket proportions
        top = max(shares.values())
        scale = min(MAX_THESIS_GROSS * min(1.0, conviction),
                    MAX_WEIGHT / top if top > 0 else MAX_THESIS_GROSS)
        w = {s: round(sh * scale, 5) for s, sh in shares.items()}
        # belt and braces: the constructed basket must satisfy both caps.
        if any(abs(v) > MAX_WEIGHT + 1e-9 for v in w.values()):
            return None, f"constructed leg weight exceeds {MAX_WEIGHT} → REJECTED"
        g = sum(abs(v) for v in w.values())
        if g > min(MAX_THESIS_GROSS, MAX_GROSS) + 1e-9:
            return None, f"basket gross {g:.3f} > {MAX_THESIS_GROSS} → REJECTED"
        return w, None

    @staticmethod
    def _falsifier_fired(th: Dict[str, Any], trade_date: str,
                         fired_ids: Optional[Dict[str, bool]] = None) -> Optional[str]:
        """A falsifier fires when (a) an external resolution says so (`fired_ids`), or
        (b) its hard `check_by` date has passed WITHOUT resolution — an unresolved
        falsifier past its own deadline is FAIL-CLOSED as fired, never assumed benign."""
        fired_ids = fired_ids or {}
        tid = str(th.get("thesis_id", ""))
        if fired_ids.get(tid):
            return "falsifier resolved TRUE"
        for f in (th.get("falsifiers") or []):
            cb = str(f.get("check_by", ""))[:10]
            if cb and cb < trade_date:
                return f"falsifier past check_by {cb} unresolved (fail-closed)"
        return None

    # ---------- the book ----------
    def record(self, trade_date: str, *, closes: Optional[Dict[str, float]] = None,
               theses: Optional[List[Dict[str, Any]]] = None,
               falsifiers_fired: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """One session: mark open baskets, close those falsified or at horizon, open new
        qualifying theses (filled at TODAY's close ⇒ signal-t/fill-t+1). Idempotent per
        date. REPORT-ONLY."""
        st = self._state()
        if any(d.get("date") == trade_date for d in st["days"]):
            return self._summary(st)
        closes = closes or {}
        reasons: List[str] = []
        twin_px = closes.get(TWIN_TICKER)

        # 1) mark + close (falsifier first, then horizon)
        still_open, closed_today = [], 0
        for pos in st["open"]:
            pos["held"] = int(pos.get("held", 0)) + 1
            kill = self._falsifier_fired(pos["thesis"], trade_date, falsifiers_fired)
            at_horizon = pos["held"] >= int(pos["horizon_days"])
            if not (kill or at_horizon):
                still_open.append(pos)
                continue
            legs_px = {s: closes.get(s) for s in pos["weights"]}
            if any(p is None for p in legs_px.values()) or twin_px is None:
                reasons.append(f"{pos['thesis_id']}: missing leg/twin price at exit → HELD (degraded)")
                still_open.append(pos)
                continue
            gross = sum(w * (legs_px[s] / pos["entry_px"][s] - 1.0)
                        for s, w in pos["weights"].items())
            norm = sum(abs(w) for w in pos["weights"].values()) or 1.0
            ret = gross / norm                                   # basket return per unit gross
            # every LEG pays entry+exit at the honest single-name rate; because `ret` is
            # per-unit-gross, the weighted per-leg cost reduces to 2 × the round-trip rate.
            net = ret - 2 * ROUND_TRIP_BPS
            twin = twin_px / pos["twin_entry_px"] - 1.0
            st["closed"].append({
                "thesis_id": pos["thesis_id"], "theme_class": pos["theme_class"],
                "origin": self.origin, "conviction": pos["conviction"],
                "entry_date": pos["entry_date"], "exit_date": trade_date,
                "held_days": pos["held"], "horizon_days": pos["horizon_days"],
                "legs": pos["weights"], "gross_ret": round(ret, 6), "net_ret": round(net, 6),
                "twin_ret": round(twin, 6), "excess_vs_twin": round(net - twin, 6),
                "killed_by_falsifier": bool(kill), "exit_reason": kill or "horizon"})
            closed_today += 1
        st["open"] = still_open

        # 2) open new qualifying theses (fill at TODAY's close ⇒ t+1 vs the filing date)
        if theses is None:
            theses, why = self._load_theses(_prev_key(trade_date, st))
            if why != "ok":
                reasons.append(why)
        opened = 0
        for th in (theses or []):
            tid = str(th.get("thesis_id", ""))
            conv = float(th.get("conviction", 0.0) or 0.0)
            if conv < CONVICTION_FLOOR:
                reasons.append(f"{tid}: conviction {conv:.2f} < floor {CONVICTION_FLOOR}")
                continue
            hz = int(th.get("horizon_days", 0) or 0)
            if hz <= 0:
                reasons.append(f"{tid}: no horizon_days → PARKED")
                continue
            if not (th.get("falsifiers") or []):
                reasons.append(f"{tid}: NO falsifier → a story, not a position (parked)")
                continue
            w, why = self._basket_weights(th.get("instruments") or [], conv)
            if w is None:
                reasons.append(f"{tid}: {why}")
                continue
            entry = {s: closes.get(s) for s in w}
            if any(p is None for p in entry.values()) or twin_px is None:
                reasons.append(f"{tid}: missing leg/twin price → parked (no fabricated fill)")
                continue
            st["open"].append({
                "thesis_id": tid, "theme_class": th.get("theme_class", "unknown"),
                "conviction": round(conv, 3), "weights": w,
                "entry_px": {s: round(float(p), 4) for s, p in entry.items()},
                "twin_entry_px": round(float(twin_px), 4),
                "entry_date": trade_date, "horizon_days": hz, "held": 0,
                "thesis": {"thesis_id": tid, "falsifiers": th.get("falsifiers") or []}})
            opened += 1

        st["days"].append({"date": trade_date, "opened": opened, "closed": closed_today,
                           "n_open": len(st["open"]), "degraded": bool(reasons),
                           "reasons": reasons[:8]})
        self._write(st)
        return self._summary(st)

    # ---------- reporting ----------
    def _summary(self, st: Dict[str, Any]) -> Dict[str, Any]:
        cl = st["closed"]
        s: Dict[str, Any] = {"desk": self.cfg.name, "origin": self.origin,
                             "n_days": len(st["days"]), "n_open": len(st["open"]),
                             "n_closed": len(cl), "armed": True}
        if cl:
            ex = [c["excess_vs_twin"] for c in cl]
            s["mean_excess_vs_twin"] = round(sum(ex) / len(ex), 5)
            s["n_falsified"] = sum(1 for c in cl if c.get("killed_by_falsifier"))
        return s

    def outcomes(self) -> List[Any]:
        """Closed positions → D's `ThesisOutcome` records (the scoring interface)."""
        from intelligence.thesis_desk.thesis_scoring import ThesisOutcome
        return [ThesisOutcome(thesis_id=c["thesis_id"], theme_class=c["theme_class"],
                              conviction=float(c["conviction"]), ret=float(c["net_ret"]),
                              twin_ret=float(c["twin_ret"]), resolved=True,
                              killed_by_falsifier=bool(c.get("killed_by_falsifier")))
                for c in self._state()["closed"]]

    def promotion_gates(self) -> Dict[str, Any]:
        """REPORT-ONLY status against **D's pre-stated T-324 bar**, evaluated by D's own
        `promotion_check` (≥20 resolved per theme_class AND bootstrap log-wealth ci_low > 0),
        with A's skew-aware payoff profile alongside. ONE standard, not a second one."""
        from intelligence.thesis_desk.thesis_scoring import (MIN_RESOLVED_PER_CLASS,
                                                             promotion_check)
        outs = self.outcomes()
        classes = sorted({o.theme_class for o in outs})
        per = {c: promotion_check(outs, c) for c in classes}
        return {"desk": self.cfg.name, "origin": self.origin,
                "standard": "D/T-324 promotion_check — ≥%d RESOLVED per theme_class AND "
                            "bootstrap log-wealth ci_low > 0 (A's skew-aware metric); "
                            "channel-separated (no blending)" % MIN_RESOLVED_PER_CLASS,
                "n_closed": len(outs), "per_theme_class": per,
                "promote_any": any(bool(v.get("PROMOTED")) for v in per.values())}


def _prev_key(trade_date: str, st: Dict[str, Any]) -> str:
    """The filing date whose theses fill TODAY — strictly t+1, so no look-ahead."""
    days = [d["date"] for d in st.get("days", []) if d["date"] < trade_date]
    return max(days) if days else str((pd.Timestamp(trade_date) - pd.Timedelta(days=1)).date())
