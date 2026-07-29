# paper_trader/live_books.py
"""LiveBook — REPORT-ONLY NAV-vs-twin books for the performance laboratory (T-328).

Performance testing scales through BOOKS, not accounts. This is the NAV-tracking shape of
the shadow machinery (as in the BTC/DBMF shadows), parameterized so a new stream is a
`BookSpec`, not a module. Four instances ship here:

  1. SPY_NULL        — plain buy-hold SPY. The explicit DOLLAR-DENOMINATED null every other
                       stream reads against; its twin is itself, so "vs just buying SPY" is
                       a first-class row in the digest rather than an implied comparison.
  2. DAMPED_OFFENSE  — the T-298 asymmetric-damping config whose backtest edge STRADDLED at
                       depth. A live forward record is the ONLY evidence that can revive or
                       bury it. Twin = SPY.
  3. QUALITY_SAT     — 80/20 SPY/quality: the gentle, non-decayed, CI-straddling tilt from
                       T-320. Twin = SPY.
  4. SLEEVE_TIER50K  — the validated sleeve at $50K notional. Twin = the SAME sleeve at
                       $10K, scaled — THE DIVERGENCE IS THE TIER LESSON (whole-share
                       granularity bites harder at $10K, which is why both sides are held
                       in WHOLE SHARES rather than abstract weights).

EVERY book holds SHARES + CASH from a starting notional — not abstract weights — because
rounding to whole shares is precisely the effect book 4 exists to measure, and a
weight-space book would silently hide it.

WHAT A BOOK CAN AND CANNOT EVIDENCE (stated at t=0, displayed with every report):
  CAN: live behavior — that the config runs, at what turnover/cost, with what realized
       path, against a named twin, over N ACCRUED DAYS (always displayed).
  CANNOT: make a straddling backtest significant on any short horizon. Days-accrued is
       shown on every line so a 20-day record can never be read as a verdict. No book
       promotes anything on its own; the pre-registered gates below are the only bar.

Report-only: zero effect on orders, ever. Fail-closed parking, S3-durable, zero new deps.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

ETF_TXN_BPS = 0.00015          # 1.5 bps/side — liquid ETFs (the T-255 harness rate)

# --- T-332a CASH-DRAG ANNOTATION (measurement-side only; NEVER a restatement) --- #
# The backtest credits idle cash at the daily short rate (T-255), but Alpaca paper pays
# NOTHING on cash. Every live NAV is therefore biased AGAINST its own backtest spec by
# ~short-rate x time-in-cash — and the sleeve's regime-option premium depends on actually
# EARNING that yield. So each book accrues what its cash WOULD have earned and reports it
# ALONGSIDE the raw NAV. The raw number stays PRIMARY and is never overwritten: we
# annotate a record, we do not restate it.
# The rate comes from a T-bill ETF's own daily total return (BIL), fetched through the
# SAME Alpaca stock path the books already use — zero new deps, and it is the honest
# counterfactual (what a cash sweep could really have earned, net of the fund's ER).
CASH_RATE_TICKER = "BIL"
DEFAULT_NOTIONAL = 100_000.0   # the book's own unit; twins share it unless stated


@dataclass(frozen=True)
class BookSpec:
    """One live book: what it holds, what it is measured against, and its frozen gate."""
    name: str
    state_path: str
    symbols: tuple                       # prices the book needs (book + twin)
    weights_fn: Callable[[Dict[str, float], float], Dict[str, float]]
    twin_weights_fn: Callable[[Dict[str, float], float], Dict[str, float]]
    notional: float = DEFAULT_NOTIONAL
    twin_notional: float = DEFAULT_NOTIONAL
    whole_shares: bool = True
    gate: str = ""                       # the FROZEN t=0 bar, verbatim
    can_evidence: str = ""
    cannot_evidence: str = ""


# ---------------- weight functions (pure; closes+equity → target weights) ---------------- #
def _static(w: Dict[str, float]) -> Callable[[Dict[str, float], float], Dict[str, float]]:
    return lambda closes, equity: dict(w)


def _sleeve_weights(closes: Dict[str, float], equity: float) -> Dict[str, float]:
    """The deploying {2,5,10}mo ensemble sleeve, in WEIGHT space, from the shared trend
    rule. Prices arrive as a single day's closes, so the trend state is supplied by the
    caller through `closes['_sleeve_expo_<TKR>']` when available; absent that the book
    parks (fail-closed) rather than inventing an exposure."""
    out: Dict[str, float] = {}
    legs = ("SPY", "AGG", "GLD")
    for t in legs:
        e = closes.get(f"_sleeve_expo_{t}")
        if e is None:
            return {}                    # → caller parks the day; never a fabricated stance
        out[t] = float(e) / len(legs)
    return out


def _offense_weights(closes: Dict[str, float], equity: float) -> Dict[str, float]:
    """T-298 damped offense: SSO at the damped ensemble fraction, remainder in cash.
    Same fail-closed contract as the sleeve."""
    e = closes.get("_offense_expo_SSO")
    if e is None:
        return {}
    return {"SSO": float(e)}


SPY_NULL = BookSpec(
    name="spy_null", state_path="data/state/book_spy_null.json", symbols=("SPY",),
    weights_fn=_static({"SPY": 1.0}), twin_weights_fn=_static({"SPY": 1.0}),
    whole_shares=False,
    gate="NONE — this book IS the null. It is never promoted or refuted; it exists so every "
         "other stream's 'vs just buying SPY' is a first-class measured row, not an implied one.",
    can_evidence="the realized dollar path of plain buy-hold SPY over the accrual window.",
    cannot_evidence="anything about any other stream — it is the yardstick, not a contender.")

DAMPED_OFFENSE = BookSpec(
    name="damped_offense_t298", state_path="data/state/book_damped_offense.json",
    symbols=("SSO", "SPY"), weights_fn=_offense_weights, twin_weights_fn=_static({"SPY": 1.0}),
    gate="T-298 carried forward: Δwealth vs SPY must be POSITIVE at block-bootstrap CI over "
         "the accrual AND realized MaxDD must stay within the backtest's −30.6% bound. "
         "Neither is evaluable until the record is long enough to bootstrap — days-accrued "
         "is displayed so a short record is never mistaken for a verdict.",
    can_evidence="that the damped config RUNS live at the measured slippage, its realized "
                 "exposure path (~1.1× mean), turnover, and drawdown behavior.",
    cannot_evidence="a revival of the straddling backtest edge on a short horizon. T-298's "
                    "Δwealth CI straddled at depth; only a long forward record can move that, "
                    "and this book cannot shorten the wait.")

QUALITY_SAT = BookSpec(
    name="quality_satellite", state_path="data/state/book_quality_satellite.json",
    symbols=("SPY", "QUAL"), weights_fn=_static({"SPY": 0.80, "QUAL": 0.20}),
    twin_weights_fn=_static({"SPY": 1.0}),
    gate="T-320 carried forward: the tilt's log-wealth ratio vs SPY must exceed zero at "
         "block-bootstrap CI. T-320 measured the full-sample CI as STRADDLING (and quality "
         "as the only non-decayed premium) — the live record is a behavior check, not a "
         "significance shortcut.",
    can_evidence="the realized tracking behavior, turnover and regret path of the gentlest "
                 "tilt (T-320 regret −4.1%, $414 per $10k) in live conditions.",
    cannot_evidence="that the quality premium is significant. T-320's CI straddled zero over "
                    "63 YEARS; no live window of months can settle it.")

SLEEVE_TIER50K = BookSpec(
    name="sleeve_tier_50k", state_path="data/state/book_sleeve_tier50k.json",
    symbols=("SPY", "AGG", "GLD"), weights_fn=_sleeve_weights,
    twin_weights_fn=_sleeve_weights, notional=50_000.0, twin_notional=10_000.0,
    whole_shares=True,
    gate="No promotion gate — this is a MEASUREMENT of capital-adaptive behavior. The "
         "reported quantity is the $50K-vs-$10K divergence (whole-share granularity drag), "
         "annualized, with days-accrued displayed.",
    can_evidence="how much realized performance the $10K tier loses to whole-share rounding "
                 "and rebalance granularity vs the same sleeve at $50K — the capital-adaptive "
                 "lesson, measured live instead of assumed.",
    cannot_evidence="which tier is 'better' as a strategy — the STRATEGY is identical by "
                    "construction; only the granularity differs.")

ALL_BOOKS: tuple = (SPY_NULL, DAMPED_OFFENSE, QUALITY_SAT, SLEEVE_TIER50K)


@dataclass
class LiveBook:
    spec: BookSpec
    root: Optional[str] = None

    def _file(self) -> Path:
        base = Path(self.root) if self.root else Path(__file__).resolve().parents[1]
        p = base / self.spec.state_path
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _state(self) -> Dict[str, Any]:
        try:
            return json.loads(self._file().read_text())
        except Exception:
            return {"_schema": "live_book/v1", "book": self.spec.name,
                    "side": {"book": None, "twin": None}, "days": []}

    def _write(self, st: Dict[str, Any]) -> None:
        self._file().write_text(json.dumps(st, indent=2, default=str))

    # ---------- one side (book or twin): shares + cash, rebalanced to target ----------
    @staticmethod
    def _step(side: Optional[Dict[str, Any]], targets: Dict[str, float],
              px: Dict[str, float], notional: float, whole: bool) -> Dict[str, Any]:
        if side is None:
            side = {"shares": {}, "cash": float(notional), "nav": float(notional)}
        nav = side["cash"] + sum(q * px[s] for s, q in side["shares"].items() if s in px)
        new_shares, cost = dict(side["shares"]), 0.0
        for s, w in targets.items():
            if s not in px or px[s] <= 0:
                continue
            want = (nav * w) / px[s]
            want = float(int(want)) if whole else want        # whole-share granularity
            delta = want - new_shares.get(s, 0.0)
            if abs(delta * px[s]) > 1e-9:
                cost += abs(delta * px[s]) * ETF_TXN_BPS
            new_shares[s] = want
        for s in list(new_shares):                            # exit names no longer targeted
            if s not in targets and new_shares[s] != 0.0 and s in px:
                cost += abs(new_shares[s] * px[s]) * ETF_TXN_BPS
                new_shares[s] = 0.0
        invested = sum(q * px[s] for s, q in new_shares.items() if s in px)
        cash = nav - invested - cost
        return {"shares": {k: round(v, 6) for k, v in new_shares.items()},
                "cash": round(cash, 4), "nav": round(cash + invested, 4)}

    # ---------- the daily record ----------
    def record(self, trade_date: str, closes: Dict[str, float]) -> Dict[str, Any]:
        """One session. Idempotent per date. REPORT-ONLY; parks fail-closed when a needed
        price or a strategy stance is missing (never fabricates either)."""
        st = self._state()
        if any(d["date"] == trade_date for d in st["days"]):
            return self.summary()
        closes = closes or {}
        missing = [s for s in self.spec.symbols if s not in closes]
        w_book = self.spec.weights_fn(closes, self.spec.notional)
        w_twin = self.spec.twin_weights_fn(closes, self.spec.twin_notional)
        reason = None
        if missing:
            reason = f"missing prices {missing} → parked (no fabricated marks)"
        elif not w_book or not w_twin:
            reason = "strategy stance unavailable → parked (no fabricated exposure)"
        if reason:
            st["days"].append({"date": trade_date, "degraded": True, "reason": reason,
                               "book_nav": (st["side"]["book"] or {}).get("nav"),
                               "twin_nav": (st["side"]["twin"] or {}).get("nav")})
            self._write(st)
            return self.summary()

        # --- T-332a: what the PREVIOUS day's idle cash would have earned overnight.
        # Uses the cash held BEFORE today's rebalance, priced by BIL's realized daily
        # return. FAIL-CLOSED: no rate today -> no accrual + the day is counted in
        # `cash_rate_missing_days`; a missing rate is never silently treated as 0%.
        _rate = None
        _bil = closes.get(CASH_RATE_TICKER)
        _bil_prev = st.get("cash_rate_prev_px")
        if _bil is not None and _bil_prev:
            _rate = float(_bil) / float(_bil_prev) - 1.0
        prev_cash_book = (st["side"]["book"] or {}).get("cash", 0.0)
        prev_cash_twin = (st["side"]["twin"] or {}).get("cash", 0.0)

        st["side"]["book"] = self._step(st["side"]["book"], w_book, closes,
                                        self.spec.notional, self.spec.whole_shares)
        st["side"]["twin"] = self._step(st["side"]["twin"], w_twin, closes,
                                        self.spec.twin_notional, self.spec.whole_shares)
        b, t = st["side"]["book"]["nav"], st["side"]["twin"]["nav"]

        if _rate is None:
            st["cash_rate_missing_days"] = int(st.get("cash_rate_missing_days", 0)) + 1
        else:
            st["cash_adj_book"] = round(float(st.get("cash_adj_book", 0.0))
                                        + prev_cash_book * _rate, 6)
            st["cash_adj_twin"] = round(float(st.get("cash_adj_twin", 0.0))
                                        + prev_cash_twin * _rate, 6)
        if _bil is not None:
            st["cash_rate_prev_px"] = float(_bil)
        st["days"].append({
            "date": trade_date, "degraded": False,
            "book_nav": b, "twin_nav": t,
            "book_growth": round(b / self.spec.notional, 6),
            "twin_growth": round(t / self.spec.twin_notional, 6),
            # scale-free: the twin may start at a DIFFERENT notional (the tier book), so
            # the comparison is growth-vs-growth, never raw dollars.
            "excess_growth": round(b / self.spec.notional - t / self.spec.twin_notional, 6),
            # T-332a ANNOTATION — travels WITH the raw, never replaces it.
            "cash_adj_book": st.get("cash_adj_book"),
            "cash_adj_twin": st.get("cash_adj_twin"),
            "cash_rate_available": _rate is not None})
        self._write(st)
        return self.summary()

    # ---------- reporting: days-accrued is ALWAYS displayed ----------
    def summary(self) -> Dict[str, Any]:
        st = self._state()
        clean = [d for d in st["days"] if not d.get("degraded")]
        s: Dict[str, Any] = {
            "book": self.spec.name, "n_days": len(st["days"]), "n_clean": len(clean),
            "n_degraded": len(st["days"]) - len(clean), "armed": True,
            "days_accrued": len(clean),                  # displayed on EVERY line, by design
            "notional": self.spec.notional, "twin_notional": self.spec.twin_notional}
        if clean:
            last = clean[-1]
            s.update({"book_nav": last["book_nav"], "twin_nav": last["twin_nav"],
                      "book_growth": last["book_growth"], "twin_growth": last["twin_growth"],
                      "excess_growth": last["excess_growth"]})
            navs = pd.Series([d["book_nav"] for d in clean])
            s["max_drawdown"] = round(float((navs / navs.cummax() - 1).min()), 5)
            # --- T-332a ANNOTATION: what idle cash WOULD have earned. Reported BESIDE the
            # raw NAV above, never in place of it — the raw keys are already set and are
            # not touched here. `*_cash_adj` is a SECOND number the reader may use; the
            # record itself is never restated. -------------------------------------------
            adj_b = float(st.get("cash_adj_book", 0.0))
            adj_t = float(st.get("cash_adj_twin", 0.0))
            miss = int(st.get("cash_rate_missing_days", 0))
            s["cash_adj"] = {
                "book_accrued": round(adj_b, 4), "twin_accrued": round(adj_t, 4),
                "book_nav_cash_adj": round(last["book_nav"] + adj_b, 4),
                "twin_nav_cash_adj": round(last["twin_nav"] + adj_t, 4),
                "excess_growth_cash_adj": round(
                    (last["book_nav"] + adj_b) / self.spec.notional
                    - (last["twin_nav"] + adj_t) / self.spec.twin_notional, 6),
                "rate_missing_days": miss,
                "note": ("ANNOTATION ONLY — the raw NAV above is the record. Live paper "
                         "cash earns 0%; the backtest spec credits the short rate, so this "
                         "shows what that gap is worth. Never a restatement."
                         + (f" INCOMPLETE: {miss} day(s) had no rate and accrued NOTHING "
                            f"(fail-closed, never assumed 0%)." if miss else ""))}
        return s

    def status(self) -> Dict[str, Any]:
        """The frozen t=0 contract + where the record stands. The CAN/CANNOT lines travel
        WITH the numbers so a short record is never read as a verdict."""
        s = self.summary()
        return {**s, "gate": self.spec.gate,
                "can_evidence": self.spec.can_evidence,
                "cannot_evidence": self.spec.cannot_evidence,
                "verdict": f"NOT EVALUABLE — {s['days_accrued']} clean days accrued; "
                           f"no book promotes anything on its own."}
