# paper_trader/dbmf_shadow.py
"""DbmfShadowBook — REPORT-ONLY forward shadow of a 5% managed-futures (DBMF) sleeve leg.

WHY THIS EXISTS (T-316): the "awaits a genuinely-independent 3rd return stream" gap
(T-248/T-263, tripwire #2) has survived every backtest attempt because each proxy hit a
data wall, not a verdict: T-296 (RSST/return-stack) was walled by a ±5%/yr hypothetical-
replication basis; T-313 (international equity) was REFUTED at the data stage (crisis corr
+0.87..+1.00 — the T-214 trap). A LIVE forward record is the only honest way left to learn
whether a managed-futures leg is genuinely tail-independent. This starts that clock.

Construction (frozen at shadow start): the deploying sleeve is the 3-asset {SPY,AGG,GLD}
ensemble, so the variant daily return is exactly
    variant_ret = (1 - DBMF_W) * actual_sleeve_return + DBMF_W * dbmf_return
— it reuses the REAL sleeve return (no re-derivation) and adds an UNGATED DBMF leg. The
leg is deliberately NOT trend-ruled: DBMF is ITSELF a trend program, and T-296 measured
that stacking our gate on an internally-overlaid fund INTERFERES (our gate reads the
combined price; the MF up-trend masks the equity decline → protects LESS). So the MF leg
rides raw — that finding is designed into this shadow.

REPORT-ONLY + FAIL-OPEN ([NN-FAIL-CLOSED] in the honest direction for a report-only path):
no DBMF price → the day is degraded=True with the leg parked at 0 (never a fabricated
return) and the gates exclude it. Zero effect on orders, ever. S3-durable via the pulse's
DURABLE_PATHS. Idempotent per trade_date.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from core.metrics_engine import MetricsEngine as ME

DEFAULT_PATH = "data/state/dbmf_shadow_tracking.json"
TD = 252

# --- FROZEN construction (set at shadow start; do NOT tune on accrued data) --- #
DBMF_W = 0.05                # 5% MF sleeve leg (base scaled to 0.95)
DBMF_TICKER = "DBMF"

# --- FROZEN forward PROMOTION gates (pre-registered BEFORE the first record, [NN-MBL]) --- #
# The promotion question is NOT "did MF make money" — it is whether the MF leg delivers the
# TAIL INDEPENDENCE that every backtest proxy failed to prove. Passing BOTH promotes the MF
# leg from report-only shadow to a REAL PAPER leg — never straight to live.
# Do NOT loosen a threshold to make it pass; the QUESTION changes, the bar does not
# (feedback_decompose_dont_require_allweather).
GATE_A_CRISIS_TRIGGER = 0.10      # (A) fires on a sustained sleeve-or-SPY peak→trough ≥ 10%
GATE_A_CORR_MAX = 0.30            # (A) in-crisis daily corr(DBMF, sleeve) must be ≤ +0.30
#      → the tripwire-#2 bar, measured LIVE in the crisis window (what T-313 failed at +0.93)
GATE_B_MIN_FORWARD_MONTHS = 24    # (B) carry-drag window: MF bleeds in calm markets
GATE_B_DWEALTH_FLOOR = -0.03      # (B) cumulative Δwealth(variant−base) ≥ −3% over ≥24mo
#      → "insurance that also returns" is FALSIFIABLE: if the leg costs more than 3% of
#        terminal wealth while never proving crisis independence, it is a losing hedge.


@dataclass
class DbmfShadowBook:
    path: str = DEFAULT_PATH
    root: Optional[str] = None

    def _file(self) -> Path:
        base = Path(self.root) if self.root else Path(__file__).resolve().parents[1]
        p = (base / self.path) if not Path(self.path).is_absolute() else Path(self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self._file().read_text()).get("points", [])
        except Exception:
            return []

    def record(self, trade_date: str, sleeve_daily_return: float, *,
               dbmf_close: Optional[float] = None) -> Dict[str, Any]:
        """Append today's shadow point (idempotent on trade_date); return the heartbeat
        summary. `dbmf_close` is today's DBMF close (from the pulse's existing Alpaca
        fetch_daily_closes); None → degraded day, leg parked at 0. REPORT-ONLY."""
        pts = [p for p in self._load() if p["date"] != trade_date]
        prev = max(pts, key=lambda p: p["date"]) if pts else None

        dbmf_ret, degraded = 0.0, True
        if dbmf_close is not None and prev is not None and prev.get("dbmf_close"):
            try:
                dbmf_ret = float(dbmf_close) / float(prev["dbmf_close"]) - 1.0
                degraded = False
            except Exception:
                dbmf_ret, degraded = 0.0, True
        elif dbmf_close is not None and prev is None:
            degraded = False          # first day: price captured, no return yet (0.0 is honest)

        variant_ret = (1 - DBMF_W) * float(sleeve_daily_return) + DBMF_W * dbmf_ret
        base_nav = (prev["base_nav"] if prev else 1.0) * (1 + float(sleeve_daily_return))
        var_nav = (prev["variant_nav"] if prev else 1.0) * (1 + variant_ret)

        pt = {"date": trade_date, "degraded": degraded,
              "sleeve_ret": round(float(sleeve_daily_return), 6),
              "dbmf_ret": round(dbmf_ret, 6),
              "dbmf_close": (round(float(dbmf_close), 4) if dbmf_close is not None else None),
              "variant_ret": round(variant_ret, 6),
              "base_nav": round(base_nav, 6), "variant_nav": round(var_nav, 6)}
        pts.append(pt)
        pts.sort(key=lambda p: p["date"])
        summary = self._summarize(pts)
        self._file().write_text(json.dumps(
            {"_schema": "dbmf_shadow/v1", "points": pts, "summary": summary},
            indent=2, default=str))
        return summary

    def _summarize(self, pts: List[Dict[str, Any]]) -> Dict[str, Any]:
        clean = [p for p in pts if not p.get("degraded")]
        s: Dict[str, Any] = {"n_days": len(pts), "n_clean": len(clean),
                             "n_degraded": len(pts) - len(clean), "armed": True}
        if len(clean) >= 2:
            idx = pd.to_datetime([p["date"] for p in clean])
            base = pd.Series([p["base_nav"] for p in clean], index=idx)
            var = pd.Series([p["variant_nav"] for p in clean], index=idx)
            s["base_nav"] = round(float(base.iloc[-1]), 4)
            s["variant_nav"] = round(float(var.iloc[-1]), 4)
            s["delta_wealth"] = round(float(var.iloc[-1] - base.iloc[-1]), 4)
            sr = pd.Series([p["sleeve_ret"] for p in clean], index=idx)
            dr = pd.Series([p["dbmf_ret"] for p in clean], index=idx)
            if len(clean) >= 20:
                s["corr_dbmf_sleeve_todate"] = round(float(dr.corr(sr)), 3)
        return s

    def forward_gates(self) -> Dict[str, Any]:
        """REPORT-ONLY status of the frozen promotion gates. Never changes trading."""
        pts = [p for p in self._load() if not p.get("degraded")]
        out: Dict[str, Any] = {
            "n_clean_days": len(pts),
            "thresholds": {"A_crisis_trigger": GATE_A_CRISIS_TRIGGER,
                           "A_corr_max": GATE_A_CORR_MAX,
                           "B_min_months": GATE_B_MIN_FORWARD_MONTHS,
                           "B_dwealth_floor": GATE_B_DWEALTH_FLOOR}}
        if len(pts) < 2:
            out["status"] = "accruing"
            return out
        idx = pd.to_datetime([p["date"] for p in pts])
        base = pd.Series([p["base_nav"] for p in pts], index=idx)
        var = pd.Series([p["variant_nav"] for p in pts], index=idx)
        sr = pd.Series([p["sleeve_ret"] for p in pts], index=idx)
        dr = pd.Series([p["dbmf_ret"] for p in pts], index=idx)
        months = (idx[-1] - idx[0]).days / 30.44

        # Gate A — the LIVE tail-independence test, measured inside a real crisis window
        dd = base / base.cummax() - 1.0
        a: Dict[str, Any] = {"status": "no crisis ≥10% yet"}
        if dd.min() <= -GATE_A_CRISIS_TRIGGER:
            t1 = dd.idxmin()
            t0 = base.loc[:t1].idxmax()
            win_d, win_s = dr.loc[t0:t1], sr.loc[t0:t1]
            c = float(win_d.corr(win_s)) if len(win_d) >= 10 else float("nan")
            a = {"status": ("PASS" if (c == c and c <= GATE_A_CORR_MAX) else "FAIL"),
                 "peak": str(t0.date()), "trough": str(t1.date()),
                 "crisis_corr": (round(c, 3) if c == c else None),
                 "sleeve_dd": round(float(dd.min()), 4)}
        out["gate_A_crisis_independence"] = a

        d_wealth = float(var.iloc[-1] - base.iloc[-1])
        out["gate_B_carry_drag"] = {
            "status": ("accruing" if months < GATE_B_MIN_FORWARD_MONTHS
                       else ("PASS" if d_wealth >= GATE_B_DWEALTH_FLOOR else "FAIL")),
            "months": round(months, 1), "delta_wealth": round(d_wealth, 4)}
        out["corr_todate"] = (round(float(dr.corr(sr)), 3) if len(pts) >= 20 else None)
        out["promote_to_paper_leg"] = (
            out["gate_A_crisis_independence"]["status"] == "PASS"
            and out["gate_B_carry_drag"]["status"] == "PASS")
        return out
