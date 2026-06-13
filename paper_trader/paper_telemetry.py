# paper_trader/paper_telemetry.py
"""Paper-loop telemetry — the SHADOW kill layer + the paper-only
measurement agenda (forward_plan 2026-06-13), all read-only over the
shipped engines.

  * DivergenceShadow — T-152 CUSUM/Page-Hinkley monitors consuming the
    paper return stream at the CALIBRATED operating points. SHADOW:
    computes + logs alarms, takes NO action (arming reduce/flatten is a
    later step).
  * PromotionReport — captures the paper-ONLY measurements from day one:
    realized auction slippage vs the T-146 model (the number that
    re-opens T-157 LPS), the rejection-rate map, and the divergence null
    distribution (paper − backtest-expected). Plus §5 promotion-criteria
    status.
  * RouterShadow — T-141 cross-account wash-sale checker in shadow.
  * SafefWeeklyJob — T-151 safe-f/CAR25 weekly scaffold (fires once the
    rolling paper record clears min_history_days).

Nothing here gates or acts; it observes and reports.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------- #
# T-152 — divergence monitors in SHADOW
# --------------------------------------------------------------------- #
class DivergenceShadow:
    """Feeds (realized − expected) innovations to the calibrated T-152
    monitors and LOGS alarms. Expectation = the BACKTEST's rolling
    stats (passed per cycle), not self-stats — the live semantics from
    the T-152 calibration. SHADOW: alarms are recorded, never acted."""

    def __init__(self, cusum_k: float = 1.0, cusum_h: float = 5.0,
                 var_k: float = 2.0, var_h: float = 12.0,
                 ph_delta: float = 0.05, ph_lambda: float = 20.0):
        from backtester.divergence_monitors import CusumMonitor, PageHinkleyMonitor
        self.cusum_mean = CusumMonitor(cusum_k, cusum_h)
        self.cusum_var = CusumMonitor(var_k, var_h)
        self.ph = PageHinkleyMonitor(ph_delta, ph_lambda)
        self.alarms: List[Dict[str, Any]] = []
        self.n_obs = 0

    def update(self, realized_return: float, expected_mean: float,
               expected_std: float, date: Optional[str] = None) -> Dict[str, Any]:
        """Update all three monitors on one day's innovation. Returns the
        per-day alarm record (also appended to ``self.alarms`` when any
        channel fires). SHADOW — the caller LOGS this, never acts."""
        if expected_std is None or not math.isfinite(expected_std) or expected_std < 1e-12:
            return {"date": date, "skipped": "no_valid_sigma"}
        z = (realized_return - expected_mean) / expected_std
        zv = ((z ** 2) - 1.0) / math.sqrt(2.0)
        self.n_obs += 1
        fired = {
            "date": date, "z": round(z, 4),
            "cusum_mean": self.cusum_mean.update(z),
            "cusum_var": self.cusum_var.update(zv),
            "page_hinkley": self.ph.update(z),
        }
        fired["any"] = bool(fired["cusum_mean"] or fired["cusum_var"]
                            or fired["page_hinkley"])
        if fired["any"]:
            self.alarms.append(fired)
        return fired


# --------------------------------------------------------------------- #
# Promotion report — the paper-only measurement telemetry
# --------------------------------------------------------------------- #
@dataclass
class PromotionReport:
    """Captures the §5 promotion inputs + the 2026-06-13 paper-only
    measurement agenda from day one."""
    # realized auction slippage vs the T-146 expected print (bps, signed
    # adverse-positive): the number that re-opens T-157 LPS.
    slippage_bps: List[float] = field(default_factory=list)
    # rejection-rate map by sub-class.
    rejects: Dict[str, int] = field(default_factory=dict)
    # divergence null distribution: paper − backtest-expected innovations.
    divergence_z: List[float] = field(default_factory=list)
    n_trading_days: int = 0
    n_fills: int = 0
    reconcile_clean_cycles: int = 0
    reconcile_total_cycles: int = 0

    def record_fill(self, ticker: str, side: str, fill_price: float,
                    expected_price: float) -> Optional[float]:
        """Slippage vs the T-146 expected auction print, signed so that
        POSITIVE = adverse (paid more on a buy / received less on a
        sell). Returns the bps."""
        if expected_price is None or expected_price <= 0:
            return None
        raw_bps = (fill_price - expected_price) / expected_price * 1e4
        adverse = raw_bps if side.lower() == "buy" else -raw_bps
        self.slippage_bps.append(adverse)
        self.n_fills += 1
        return adverse

    def record_reject(self, subclass: str) -> None:
        self.rejects[subclass] = self.rejects.get(subclass, 0) + 1

    def record_divergence_z(self, z: float) -> None:
        if math.isfinite(z):
            self.divergence_z.append(float(z))

    def record_cycle(self, clean: bool) -> None:
        self.reconcile_total_cycles += 1
        if clean:
            self.reconcile_clean_cycles += 1

    def _pctl(self, xs: List[float], q: float) -> Optional[float]:
        if not xs:
            return None
        s = sorted(xs)
        k = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
        return s[k]

    def snapshot(self) -> Dict[str, Any]:
        """The report — slippage truth, reject map, divergence null, and
        §5 promotion-criteria status (operational, not performance)."""
        abs_slip = [abs(x) for x in self.slippage_bps]
        clean_rate = (self.reconcile_clean_cycles / self.reconcile_total_cycles
                      if self.reconcile_total_cycles else None)
        zs = self.divergence_z
        z_mean = (sum(zs) / len(zs)) if zs else None
        z_std = (math.sqrt(sum((z - z_mean) ** 2 for z in zs) / len(zs))
                 if zs and len(zs) > 1 else None)
        return {
            "n_trading_days": self.n_trading_days,
            "n_fills": self.n_fills,
            "slippage_vs_t146": {
                "median_abs_bps": self._pctl(abs_slip, 0.50),
                "p95_abs_bps": self._pctl(abs_slip, 0.95),
                "mean_signed_bps": (sum(self.slippage_bps) / len(self.slippage_bps)
                                    if self.slippage_bps else None),
                "n": len(self.slippage_bps),
            },
            "rejection_map": dict(self.rejects),
            "divergence_null": {"mean": z_mean, "std": z_std, "n": len(zs)},
            "reconcile_clean_rate": clean_rate,
            # §5 promotion criteria status (thresholds = T-159 §5).
            "promotion_criteria": {
                "duration_ok": self.n_trading_days >= 60,
                "slippage_ok": (self._pctl(abs_slip, 0.50) is not None
                                and self._pctl(abs_slip, 0.50) <= 5.0
                                and self._pctl(abs_slip, 0.95) <= 20.0
                                and len(abs_slip) >= 100),
                "reconcile_ok": (clean_rate is not None and clean_rate >= 0.99),
                "_note": "operational criteria; alpha is NOT paper-learnable",
            },
        }


# --------------------------------------------------------------------- #
# T-141 — cross-account wash-sale checker in SHADOW
# --------------------------------------------------------------------- #
class RouterShadow:
    """Runs the T-141 CrossAccountWashSaleChecker over staged orders in
    SHADOW (logs verdicts; never blocks). Per the §4 design, taxable
    losses come from a simulated taxable twin so the blackout logic
    accumulates operational history pre-enforcement."""

    def __init__(self):
        from core.account_router import CrossAccountWashSaleChecker
        self.checker = CrossAccountWashSaleChecker()
        self.verdicts: List[Dict[str, Any]] = []

    def feed_taxable_loss(self, ticker: str, date: Any) -> None:
        self.checker.record_taxable_loss(ticker, date)

    def shadow_check(self, ticker: str, account: str, date: Any) -> Dict[str, Any]:
        v = self.checker.check_trade(ticker, account, date)
        self.verdicts.append(v)
        return v


# --------------------------------------------------------------------- #
# T-151 — safe-f/CAR25 weekly job scaffold
# --------------------------------------------------------------------- #
class SafefWeeklyJob:
    """Fires safe-f/CAR25 on the rolling paper return record once it
    clears min_history_days; otherwise reports insufficient (scaffold —
    the paper record won't clear it for ~6 months)."""

    def __init__(self, min_history_days: int = 126):
        self.min_history_days = min_history_days

    def run(self, daily_returns: List[float]) -> Dict[str, Any]:
        import pandas as pd
        from backtester.safef_car25 import SafeFConfig, compute_safef_car25
        if len(daily_returns) < self.min_history_days:
            return {"fired": False, "reason": "insufficient_history",
                    "n_obs": len(daily_returns),
                    "need": self.min_history_days}
        rep = compute_safef_car25(pd.Series(daily_returns), SafeFConfig())
        return {"fired": True, "safe_f": rep.get("safe_f"),
                "car25_pct": rep.get("car25_pct")}
