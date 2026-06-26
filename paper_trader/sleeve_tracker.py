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
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from core.combined_candidate_scorecard import ROBO_PROXIES
from core.metrics_engine import MetricsEngine as ME

DEFAULT_PATH = "data/state/sleeve_tracking.json"
RF_ANNUAL = 0.04


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
               closes: Dict[str, float]) -> Dict[str, Any]:
        """Append today's point (idempotent on trade_date) + return the
        rolling summary."""
        pts = [p for p in self._load() if p["date"] != trade_date]
        pts.append({"date": trade_date, "sleeve_equity": round(float(sleeve_equity), 2),
                    "closes": {k: round(float(v), 4) for k, v in closes.items()}})
        pts.sort(key=lambda p: p["date"])
        summary = self._summarize(pts)
        self._file().write_text(json.dumps(
            {"_schema": "sleeve_tracking/v1", "points": pts, "summary": summary},
            indent=2, default=str))
        return summary

    def _summarize(self, pts: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(pts) < 2:
            return {"status": "accruing", "n_days": len(pts)}
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
        return out
