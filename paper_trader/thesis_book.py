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
                    "open": [], "closed": [], "days": [], "pending": []}

    def _write(self, st: Dict[str, Any]) -> None:
        self._file().write_text(json.dumps(st, indent=2, default=str))

    @property
    def origin(self) -> str:
        return _ORIGIN_FOR.get(self.cfg.name, "machine")

    # ---------- source (channel-filtered: the firewall) ----------
    def _load_all(self) -> tuple[List[Dict[str, Any]], str]:
        """Every record on this sub-book's channel, unfiltered by date."""
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
                out.append(rec)
        except Exception as exc:
            return [], f"source unreadable: {type(exc).__name__}"
        return out, "ok"

    def _due_theses(self, trade_date: str,
                    st: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[str]]:
        """Every thesis this session should try to open.

        T-343: the old rule loaded exactly ONE filing date — the prior recorded session —
        so a thesis that parked for want of a price became unreachable the moment the book
        recorded another day. That is precisely what stranded the machine's first two
        theses (filed 08-19, parked 08-20; from 08-21 onward the loader only ever looked at
        08-20). The rule is now: filed strictly BEFORE today (no look-ahead, t+1 at the
        earliest), within `RECOVERY_WINDOW_DAYS`, and not already open/closed/pending.

        Past the window a thesis is EXPIRED, said once, and never opened — entering months
        later at a drifted price would be a fabricated entry wearing a real timestamp.
        Silent-drop is the failure mode being closed here, so expiry is always announced.
        """
        recs, why = self._load_all()
        reasons: List[str] = [] if why == "ok" else [why]
        seen = ({str(p.get("thesis_id", "")) for p in st.get("open", [])}
                | {str(c.get("thesis_id", "")) for c in st.get("closed", [])}
                | {str(t.get("thesis_id", "")) for t in st.get("pending", [])}
                | set(st.get("expired", [])))
        td = pd.Timestamp(trade_date)
        due: List[Dict[str, Any]] = []
        for rec in recs:
            tid = str(rec.get("thesis_id", ""))
            if tid in seen:
                continue
            asof = str(rec.get("as_of", ""))[:10]
            try:
                age = (td - pd.Timestamp(asof)).days
            except Exception:
                reasons.append(f"{tid}: unparseable as_of {asof!r} → skipped (fail-closed)")
                continue
            if age < 1:
                continue                               # filed today or later — not due yet
            if age > RECOVERY_WINDOW_DAYS:
                st.setdefault("expired", []).append(tid)
                reasons.append(f"{tid}: filed {asof} ({age}d ago) — EXPIRED past the "
                               f"{RECOVERY_WINDOW_DAYS}d recovery window; NOT opened at a "
                               f"stale price")
                continue
            rec = dict(rec)
            if age > 1:                                # late, and the lateness is recorded
                rec["_pending_since"] = rec.get("_pending_since") or asof
            due.append(rec)
        if not due and why == "ok" and not reasons:
            reasons.append("no theses due this session")
        return due, reasons

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
                        ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Absolute basket weights from the thesis's own `weight_hint` PROPORTIONS.

        Returns ({weights, sizing_scale, binding_cap, unconstrained_scale, downsized},
        None) or (None, reason). The APPLIED SCALE and WHICH CAP BOUND IT are returned so
        every position record carries them — a down-sized basket must be visible in the
        book's history, never reconstructed by archaeology (director ruling, T-326).

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
        by_gross = MAX_THESIS_GROSS * min(1.0, conviction)
        by_name = (MAX_WEIGHT / top) if top > 0 else MAX_THESIS_GROSS
        scale = min(by_gross, by_name)
        # WHICH cap bound the sizing — stamped on the record so a down-sized basket is
        # visible in the book's history, never discovered by archaeology (director ruling).
        binding = "per_name" if by_name < by_gross - 1e-12 else "gross_x_conviction"
        w = {s: round(sh * scale, 5) for s, sh in shares.items()}
        # belt and braces: the constructed basket must satisfy both caps.
        if any(abs(v) > MAX_WEIGHT + 1e-9 for v in w.values()):
            return None, f"constructed leg weight exceeds {MAX_WEIGHT} → REJECTED"
        g = sum(abs(v) for v in w.values())
        if g > min(MAX_THESIS_GROSS, MAX_GROSS) + 1e-9:
            return None, f"basket gross {g:.3f} > {MAX_THESIS_GROSS} → REJECTED"
        return {"weights": w, "sizing_scale": round(scale, 5), "binding_cap": binding,
                "unconstrained_scale": round(by_gross, 5),
                "downsized": bool(by_name < by_gross - 1e-12)}, None

    def pending_symbols(self, as_of: Optional[str] = None) -> List[str]:
        """Every ticker the next run must price: PENDING legs + OPEN legs + the twin.

        T-343: nobody can pre-list what the machine will pick (FN and AMTM proved it), so
        the price fetch has to FOLLOW the book rather than a static universe. Also includes
        theses filed in the prior session, because those are what `record()` will consume —
        gathering symbols from a different day than the one consumed is exactly the bug
        that parked the machine's first two theses."""
        st = self._state()
        syms = {TWIN_TICKER}
        for pos in st.get("open", []):
            syms |= set(pos.get("weights", {}))
        for th in st.get("pending", []):
            syms |= {str(l.get("symbol", "")).upper()
                     for l in (th.get("instruments") or []) if l.get("symbol")}
        if as_of:
            newly, _ = self._due_theses(as_of, dict(st))   # dict() → never mutates state
            for th in newly:
                syms |= {str(l.get("symbol", "")).upper()
                         for l in (th.get("instruments") or []) if l.get("symbol")}
        return sorted(s for s in syms if s)

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
            # T-343: the thesis's clock runs from ITS FILING date, so days spent PENDING
            # (awaiting prices) consume horizon rather than extending it — a thesis is a
            # claim about a period, not about however long we took to open it. Returns are
            # still measured from the ACTUAL entry prices. Both dates are on the record.
            _filed = pos.get("filed_date") or pos.get("entry_date")
            try:
                _elapsed = (pd.Timestamp(trade_date) - pd.Timestamp(_filed)).days
            except Exception:
                _elapsed = pos["held"]          # unparseable filing date → session count
            at_horizon = _elapsed >= int(pos["horizon_days"])
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
                "legs": pos["weights"],
                "sizing_scale": pos.get("sizing_scale"),
                "binding_cap": pos.get("binding_cap"),
                "downsized": pos.get("downsized"),
                "gross_ret": round(ret, 6), "net_ret": round(net, 6),
                "twin_ret": round(twin, 6), "excess_vs_twin": round(net - twin, 6),
                "killed_by_falsifier": bool(kill), "exit_reason": kill or "horizon"})
            closed_today += 1
        st["open"] = still_open

        # 2) open new qualifying theses (fill at TODAY's close ⇒ t+1 vs the filing date)
        #
        # T-343: candidates are the PENDING queue PLUS anything newly filed. Before this,
        # a thesis whose legs had no price was simply skipped and NEVER retried — the
        # loader only ever looks at the prior session, so the machine's first two theses
        # would have been silently LOST rather than merely delayed. A parked thesis now
        # persists in `pending` and is retried every run until it opens.
        if theses is None:
            theses, _why = self._due_theses(trade_date, st)
            reasons.extend(_why)
        pend = {str(t.get("thesis_id", "")): t for t in st.get("pending", [])}
        for t in (theses or []):
            pend.setdefault(str(t.get("thesis_id", "")), t)
        candidates = list(pend.values())
        still_pending: List[Dict[str, Any]] = []
        opened = 0
        for th in candidates:
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
            sized, why = self._basket_weights(th.get("instruments") or [], conv)
            if sized is None:
                reasons.append(f"{tid}: {why}")
                continue
            w = sized["weights"]
            if sized["downsized"]:
                reasons.append(f"{tid}: sized to {sized['sizing_scale']:.4f} "
                               f"(cap={sized['binding_cap']}, unconstrained "
                               f"{sized['unconstrained_scale']:.4f}) — recorded, not silent")
            entry = {s: closes.get(s) for s in w}
            if any(p is None for p in entry.values()) or twin_px is None:
                # TRANSIENT: prices may arrive next run → stay PENDING and retry.
                missing = sorted([s for s, v in entry.items() if v is None]
                                 + ([TWIN_TICKER] if twin_px is None else []))
                th = dict(th)
                th["_pending_since"] = th.get("_pending_since") or trade_date
                th["_pending_reason"] = f"awaiting price for {', '.join(missing)}"
                still_pending.append(th)
                reasons.append(f"{tid}: missing price for {', '.join(missing)} → PENDING "
                               f"(retried next run; no fabricated fill)")
                continue
            st["open"].append({
                "thesis_id": tid, "theme_class": th.get("theme_class", "unknown"),
                "conviction": round(conv, 3), "weights": w,
                # the applied sizing, ON THE RECORD (director ruling)
                "sizing_scale": sized["sizing_scale"],
                "binding_cap": sized["binding_cap"],
                "unconstrained_scale": sized["unconstrained_scale"],
                "downsized": sized["downsized"],
                "entry_px": {s: round(float(p), 4) for s, p in entry.items()},
                "twin_entry_px": round(float(twin_px), 4),
                # BOTH dates travel (T-343): the thesis's clock runs from its FILING date,
                # while returns are measured from the ACTUAL entry prices on the day the
                # basket could really be opened. Parked days are pre-entry, never backfilled.
                "filed_date": str(th.get("as_of", ""))[:10] or trade_date,
                "entry_date": trade_date,
                "days_pending": (0 if not th.get("_pending_since") else
                                 max(0, (pd.Timestamp(trade_date)
                                         - pd.Timestamp(th["_pending_since"])).days)),
                "horizon_days": hz, "held": 0,
                "thesis": {"thesis_id": tid, "falsifiers": th.get("falsifiers") or []}})
            opened += 1

        st["pending"] = still_pending
        expiring = _expiry_warnings(still_pending, trade_date)
        for w in expiring:
            reasons.append(f"{w['thesis_id']}: {w['days_to_expiry']}d from EXPIRY "
                           f"(filed {w['filed_date']}, age {w['age_days']}d of "
                           f"{RECOVERY_WINDOW_DAYS}d) — {w['blocked_on']}")
        st["days"].append({"date": trade_date, "opened": opened, "closed": closed_today,
                           "n_open": len(st["open"]), "n_pending": len(still_pending),
                           "expiring": expiring,
                           "degraded": bool(reasons), "reasons": reasons[:8]})
        self._write(st)
        return self._summary(st)

    # ---------- reporting ----------
    def _summary(self, st: Dict[str, Any]) -> Dict[str, Any]:
        cl = st["closed"]
        s: Dict[str, Any] = {"desk": self.cfg.name, "origin": self.origin,
                             "n_days": len(st["days"]), "n_open": len(st["open"]),
                             "n_closed": len(cl),
                             # T-343: a parked thesis must be VISIBLE in the summary —
                             # an invisible queue is how one gets silently lost.
                             "n_pending": len(st.get("pending", [])),
                             # T-347: the approaching-expiry warning has to reach the
                             # notify path, so it must be on the SUMMARY the pulse reads
                             # — a warning buried in state is the silence it exists to end.
                             "expiring": (st.get("days") or [{}])[-1].get("expiring", []),
                             "armed": True}
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


EXPIRY_WARN_FRACTION = 0.5
"""T-347: warn once a pending thesis has burned HALF its recovery window.

The receipt is the machine's own first two theses: they opened at age 7 of a 10-day
window. Three days of margin, and nothing warned — the window silently counts down and
then, correctly and loudly, throws the thesis away. A bound that only speaks at the
moment it destroys something is not a guard, it is a trapdoor. Half the window leaves
enough runway to actually fix the cause.

The warning runs on the SAME CLOCK as the expiry — age since FILING, not time spent in
the pending queue. Those differ (a thesis parked on its first due day has queue-age
filed+1), and a guard measured on a different clock than the bound it guards is a guard
that fires at the wrong time.
"""

RECOVERY_WINDOW_DAYS = 10
"""How far back a still-unopened thesis stays recoverable. Long enough to survive a long
weekend or a multi-day outage (the Jul 13-24 outage ran 10 trading days); short enough that
nothing is ever opened at a price that has drifted away from the call it is scoring."""


def _expiry_warnings(pending: List[Dict[str, Any]],
                     trade_date: str) -> List[Dict[str, Any]]:
    """Pending theses that have burned at least `EXPIRY_WARN_FRACTION` of the window.

    Read-only over the queue. Each warning names the thesis, how long it has left, and
    WHAT IT IS BLOCKED ON — "3 days from expiry" without the blocking leg is an alarm
    nobody can act on."""
    import math
    threshold = max(1, math.ceil(RECOVERY_WINDOW_DAYS * EXPIRY_WARN_FRACTION))
    out: List[Dict[str, Any]] = []
    for th in pending:
        filed = str(th.get("as_of", ""))[:10]
        try:
            age = (pd.Timestamp(trade_date) - pd.Timestamp(filed)).days
        except Exception:
            continue                      # _due_theses already reports an unparseable as_of
        if age < threshold:
            continue
        out.append({"thesis_id": str(th.get("thesis_id", "")), "filed_date": filed,
                    "age_days": age,
                    "days_to_expiry": max(0, RECOVERY_WINDOW_DAYS - age),
                    "blocked_on": str(th.get("_pending_reason", "reason not recorded")),
                    "window_days": RECOVERY_WINDOW_DAYS})
    return sorted(out, key=lambda w: w["days_to_expiry"])


def _prev_key(trade_date: str, st: Dict[str, Any]) -> str:
    """The filing date whose theses fill TODAY — strictly t+1, so no look-ahead."""
    days = [d["date"] for d in st.get("days", []) if d["date"] < trade_date]
    return max(days) if days else str((pd.Timestamp(trade_date) - pd.Timedelta(days=1)).date())
