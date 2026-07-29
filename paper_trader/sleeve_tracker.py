# paper_trader/sleeve_tracker.py
"""SleeveTracker — forward-track the paper sleeve vs both robos (T-238 Part 2).

The whole point of the paper validation: does the trend sleeve's DRAWDOWN edge
(T-236: MaxDD −12% vs robos −27%) hold FORWARD on REAL ETF fills? So this
records, each trading day, the sleeve's real paper equity + the SPY/AGG/GLD
closes, and derives the robo proxies (`60_40`, `schwab_like` — the canonical
`ROBO_PROXIES` from the scorecard) from the SAME closes — an apples-to-apples
forward comparison. Metrics are DRAWDOWN-LED (per the 2026-06-25 directive:
Sortino/Calmar/MaxDD over Sharpe). The robo curves are net-of-ER (the adjusted
closes already net the ETF expense ratio) but carry NO fill cost — the sleeve's
equity is the real account (real slippage), so the comparison is honest-but-
slightly-robo-favourable on costs (flagged).

Persisted to ``data/state/sleeve_tracking.json`` (schema ``sleeve_tracking/v1``)
and pushed to S3 with the rest of the durable paper state.

EXECUTION-FIDELITY gates (T-238, pre-registered 2026-07-02 —
``docs/Audit/paper_execution_gates_t238_2026_07_02.md``): a MONTHLY-signal
sleeve yields ~1-2 independent performance observations in a 6-12mo paper
window, so paper CANNOT confirm Sortino/tail — only EXECUTION fidelity. The
tracker therefore also REPORTS (never auto-kills; trading is unchanged) four
pre-registered gate statuses when the driver supplies per-day execution data:
(a) position tracking error, (b) fill slippage vs the assumed ~1.5bps auction,
(c) order-state error count, (d) clean-day duration. These gate performance's
ADMISSIBILITY, not performance itself.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from core.combined_candidate_scorecard import ROBO_PROXIES
from core.metrics_engine import MetricsEngine as ME

DEFAULT_PATH = "data/state/sleeve_tracking.json"
RF_ANNUAL = 0.04

# --- Pre-registered EXECUTION-FIDELITY gate thresholds (T-238, 2026-07-02) --- #
# Fixed BEFORE data accrual (`[NN-MBL]`). Report-only — the tracker never acts
# on these; they gate the go-live EXECUTION verdict, not trading. See the audit
# doc for rationale. Do NOT loosen a threshold to make a run pass — the QUESTION
# changes, the bar does not (`feedback_decompose_dont_require_allweather`).
GATE_TE_MEDIAN_MAX = 0.02        # (a) |held_w − target_w| summed / 3 ETFs, median
GATE_TE_P95_MAX = 0.05           # (a) p95
GATE_SLIPPAGE_MEDIAN_BPS_MAX = 5.0   # (b) realized fill vs expected auction print
GATE_SLIPPAGE_P95_BPS_MAX = 20.0     # (b) p95 (the T-146 §5.2 bar; sim assumes ~1.5)
GATE_ORDER_ERRORS_MAX = 0        # (c) rejects / ORDER_UNKNOWN / halts / non-canonical
GATE_MIN_CLEAN_DAYS = 60         # (d) canonical trading days (the §5.1 duration bar)


def _robo_returns(closes: pd.DataFrame, name: str, rf_daily: float) -> pd.Series:
    """Daily return of a robo proxy from the tracked ETF closes + cash@rf."""
    w = ROBO_PROXIES[name]
    rets = closes.pct_change()
    out = pd.Series(0.0, index=rets.index)
    for tkr, wt in w.items():
        if tkr == "_cash":
            out = out + wt * rf_daily
        elif tkr in rets.columns:
            out = out + wt * rets[tkr].fillna(0.0)
    return out.iloc[1:]


def _curve_metrics(equity: pd.Series) -> Dict[str, float]:
    """Drawdown-led metrics from an equity curve. MaxDD (the LEAD metric) is
    reported from the first return; the ratio metrics need ≥2 returns."""
    if len(equity) < 2:
        return {"n_days": max(0, len(equity) - 1)}
    rets = equity.pct_change().dropna()
    yrs = max(1e-9, (equity.index[-1] - equity.index[0]).days / 365.25)
    cagr = float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / yrs) - 1.0
    mdd = float(ME.max_drawdown(equity))
    out: Dict[str, float] = {"max_drawdown": round(mdd, 4),    # the LEAD metric
                             "cagr": round(cagr, 4), "n_days": int(len(rets))}
    if len(rets) >= 2:
        out["sortino"] = round(float(ME.sortino_ratio(rets)), 3)
        out["sharpe"] = round(float(ME.sharpe_ratio(rets)), 3)   # secondary
        out["calmar"] = round(cagr / abs(mdd), 3) if mdd < 0 else None
    return out


@dataclass
class SleeveTracker:
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

    def record(self, trade_date: str, sleeve_equity: float,
               closes: Dict[str, float], *,
               target_weights: Optional[Dict[str, float]] = None,
               held_weights: Optional[Dict[str, float]] = None,
               slippage_bps: Optional[float] = None,
               order_errors: int = 0,
               canonical: bool = True,
               cash_balance: Optional[float] = None,
               cash_rate: Optional[float] = None) -> Dict[str, Any]:
        """Append today's point (idempotent on trade_date) + return the rolling
        summary. When ``target_weights`` is supplied the point ALSO carries an
        ``exec`` block feeding the pre-registered execution-fidelity gates
        (report-only). The bare 3-arg form is unchanged — no ``exec`` block, so
        existing (non-sleeve) callers behave byte-identically."""
        pt: Dict[str, Any] = {
            "date": trade_date, "sleeve_equity": round(float(sleeve_equity), 2),
            "closes": {k: round(float(v), 4) for k, v in closes.items()}}
        # T-332a CASH-DRAG ANNOTATION (measurement-side only). Live paper cash earns 0%
        # while the backtest spec credits the short rate — so record what the idle cash
        # WOULD have earned, BESIDE the raw equity. `sleeve_equity` above is untouched and
        # remains the record: we annotate, we never restate. Both inputs required; either
        # missing → no accrual (fail-closed, never assumed 0%).
        if cash_balance is not None and cash_rate is not None:
            pt["cash_adj"] = {"cash_balance": round(float(cash_balance), 2),
                              "day_accrual": round(float(cash_balance) * float(cash_rate), 4),
                              "note": "ANNOTATION ONLY — sleeve_equity is the record."}
        if target_weights is not None:
            tw = {k: float(v) for k, v in target_weights.items()}
            # position tracking error = Σ|held_w − target_w|, but ONLY when a
            # SETTLED held book is supplied. held_weights=None (e.g. a rebalance
            # morning, book still pre-fill) → te=None so gate (a) treats the day
            # as no-data (accruing), NOT a spurious full-weight drift.
            if held_weights is not None:
                hw = {k: float(v) for k, v in held_weights.items()}
                te = round(sum(abs(hw.get(k, 0.0) - tw.get(k, 0.0))
                               for k in set(tw) | set(hw)), 4)
            else:
                hw, te = {}, None
            pt["exec"] = {
                "target_w": {k: round(v, 4) for k, v in tw.items()},
                "held_w": {k: round(v, 4) for k, v in hw.items()},
                "te": te,
                "slippage_bps": (round(float(slippage_bps), 2)
                                 if slippage_bps is not None else None),
                "order_errors": int(order_errors),
                "canonical": bool(canonical),
            }
        pts = [p for p in self._load() if p["date"] != trade_date]
        pts.append(pt)
        pts.sort(key=lambda p: p["date"])
        summary = self._summarize(pts)
        self._file().write_text(json.dumps(
            {"_schema": "sleeve_tracking/v1", "points": pts, "summary": summary},
            indent=2, default=str))
        return summary

    def execution_gates(self) -> Dict[str, Any]:
        """Report-only status of the four pre-registered execution-fidelity
        gates over the accrued sleeve days. Never changes trading."""
        return self._eval_gates([p for p in self._load() if "exec" in p])

    @staticmethod
    def _eval_gates(exec_pts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate gates a-d from the per-day ``exec`` blocks. Each gate is
        pass / fail / accruing. 'accruing' = not enough data to judge yet;
        'fail' = a pre-registered threshold is breached (report loudly)."""
        te = [p["exec"]["te"] for p in exec_pts if p["exec"].get("te") is not None]
        slip = [p["exec"]["slippage_bps"] for p in exec_pts
                if p["exec"].get("slippage_bps") is not None]
        errs = sum(int(p["exec"].get("order_errors", 0)) for p in exec_pts)
        clean = sum(1 for p in exec_pts if p["exec"].get("canonical"))

        def _band(vals, med_max, p95_max, scale=1.0):
            if not vals:
                return {"status": "accruing", "n": 0}
            med = float(np.median(vals)) * scale
            p95 = float(np.percentile(vals, 95)) * scale
            ok = med <= med_max and p95 <= p95_max
            return {"status": "pass" if ok else "fail", "n": len(vals),
                    "median": round(med, 4), "p95": round(p95, 4),
                    "median_max": med_max, "p95_max": p95_max}

        gates = {
            "a_tracking_error": _band(te, GATE_TE_MEDIAN_MAX, GATE_TE_P95_MAX),
            "b_slippage_bps": _band(slip, GATE_SLIPPAGE_MEDIAN_BPS_MAX,
                                    GATE_SLIPPAGE_P95_BPS_MAX),
            "c_order_errors": ({"status": "accruing", "n": 0} if not exec_pts else
                               {"status": "pass" if errs <= GATE_ORDER_ERRORS_MAX
                                else "fail", "count": errs,
                                "max": GATE_ORDER_ERRORS_MAX}),
            "d_clean_days": {"status": "pass" if clean >= GATE_MIN_CLEAN_DAYS
                             else "accruing", "count": clean,
                             "min": GATE_MIN_CLEAN_DAYS},
        }
        statuses = [g["status"] for g in gates.values()]
        overall = ("fail" if "fail" in statuses
                   else "pass" if all(s == "pass" for s in statuses)
                   else "accruing")
        return {"overall": overall, "gates": gates,
                "note": ("EXECUTION fidelity only — performance (Sortino/tail) "
                         "is NOT confirmable in a 6-12mo paper window; a string "
                         "of good months is NOT validated edge.")}

    @staticmethod
    def _cash_adj_summary(pts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cumulative cash-drag ANNOTATION. Reported next to the raw equity, never in
        place of it; days without a rate contribute NOTHING and are counted."""
        rows = [p["cash_adj"]["day_accrual"] for p in pts if "cash_adj" in p]
        missing = len(pts) - len(rows)
        return {"accrued": round(sum(rows), 4), "n_days_accrued": len(rows),
                "n_days_no_rate": missing,
                "note": ("ANNOTATION ONLY — the raw sleeve_equity/NAV is the record. Live "
                         "paper cash earns 0%; the backtest spec credits the short rate."
                         + (f" INCOMPLETE: {missing} day(s) accrued NOTHING (fail-closed)."
                            if missing else ""))}

    def _summarize(self, pts: List[Dict[str, Any]]) -> Dict[str, Any]:
        exec_pts = [p for p in pts if "exec" in p]
        if len(pts) < 2:
            base: Dict[str, Any] = {"status": "accruing", "n_days": len(pts)}
            if exec_pts:
                base["execution_gates"] = self._eval_gates(exec_pts)
            return base
        idx = pd.to_datetime([p["date"] for p in pts])
        sleeve_eq = pd.Series([p["sleeve_equity"] for p in pts], index=idx)
        closes = pd.DataFrame([p["closes"] for p in pts], index=idx)
        rf_daily = RF_ANNUAL / 252.0
        out: Dict[str, Any] = {"status": "tracking", "window": [str(idx[0].date()), str(idx[-1].date())],
                               "sleeve": _curve_metrics(sleeve_eq), "robos": {}}
        for name in ROBO_PROXIES:
            r = _robo_returns(closes, name, rf_daily)
            if len(r) >= 1:
                robo_eq = (1.0 + r).cumprod() * float(sleeve_eq.iloc[0])
                out["robos"][name] = _curve_metrics(robo_eq)
        # the headline forward read: is the sleeve's MaxDD shallower than both robos'?
        s_mdd = out["sleeve"].get("max_drawdown")
        if s_mdd is not None and out["robos"]:
            out["sleeve_mdd_shallower_than_both"] = all(
                s_mdd > rb.get("max_drawdown", 0) for rb in out["robos"].values())
        if exec_pts:
            out["execution_gates"] = self._eval_gates(exec_pts)
        out['cash_adj'] = self._cash_adj_summary(pts)
        return out
