# paper_trader/btc_shadow.py
"""BtcShadowTracker — REPORT-ONLY forward validation of the T-272 +5%-BTC arm.

Runs a HYPOTHETICAL +5%-BTC-leg variant of the deploying sleeve alongside the
real paper track, starting the OOS clock at go-live. It NEVER touches orders,
weights, or the deploying spec — it only records what a 5% trend-ruled BTC leg
WOULD have done, so a pre-registered forward gate can later decide whether BTC
graduates from shadow to a real (still-paper) leg. Same report-only pattern as
the T-238 execution gates.

Construction (frozen, T-272): the deploying sleeve IS the 3-asset {SPY,AGG,GLD}
ensemble, so the variant daily return is exactly
    variant_ret = (1 - BTC_W) * actual_sleeve_return + BTC_W * btc_leg_return
— it reuses the REAL sleeve return (no re-derivation) and adds a BTC leg run
under the SAME multi-speed {42,105,210}d long/flat rule (flat → cash), BTC_W=0.05.
BTC signal from BTC-USD (24/7 spot); IBIT recorded alongside for the wrapper-basis
check ([NN-SUBSTRATE-REVERIFY]). Persisted to data/state/btc_shadow_tracking.json.

FAIL-CLOSED ([NN-FAIL-CLOSED]): if BTC history is unavailable / < the 210d warmup,
the day is recorded degraded=True with the BTC leg parked in cash (no fabricated
exposure) and the forward gates exclude it — never a silent fake. Report-only, so
a shadow failure has ZERO effect on trading.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay

DEFAULT_PATH = "data/state/btc_shadow_tracking.json"
TD = 252

# --- FROZEN construction (T-272 pre-registration; do NOT change on this sample) --- #
BTC_W = 0.05                 # BTC leg weight (base scaled to 0.95); risk-sensible at ~70% vol
SPEEDS = (42, 105, 210)      # multi-speed {2,5,10}mo — EXACTLY the deploying ensemble
BTC_ER_ANNUAL = 0.0025       # IBIT expense ratio
BTC_TXN = 0.00075            # 7.5 bps/flip (spot/ETF spread, honest)
WARMUP_DAYS = 210            # need the slowest speed before the signal is live

# --- FROZEN forward PROMOTION gates (pre-registered BEFORE the clock starts, [NN-MBL]) --- #
# Passing ALL THREE promotes BTC from report-only shadow to a REAL PAPER leg — NOT to
# live. Live still needs the full MBL/DSR bar, which BTC's single-bull-era sample cannot
# clear for years. Do NOT loosen a threshold to make it pass — the QUESTION changes, the
# bar does not (feedback_decompose_dont_require_allweather).
GATE_A_WINTER_DD_TRIGGER = 0.30    # (A) fires on the NEXT BTC peak→trough ≥ 30% in-forward
GATE_A_VARIANT_EXCESS_MAX = 0.04   # (A) variant in-window DD ≤ base in-window DD + 4pp
#      → proves the trend rule EXITS the winter OOS (in-sample it added +0.6..1.7pp; T-272)
GATE_B_MIN_FORWARD_MONTHS = 18     # (B) directional-consistency window (NOT MBL-clearing)
#      (B) over ≥18 forward months: Δwealth(variant−base) > 0 AND ΔSortino(variant−base) > 0
GATE_C_IBIT_BASIS_MAX = 0.015      # (C) fwd annualized |IBIT − BTC-USD| tracking, net of ER,
#      ≤ 1.5%/yr — else the BTC-USD-based shadow overstates vs the tradeable wrapper


def _btc_leg_today(btc_hist: pd.Series, date: pd.Timestamp,
                   cash_daily: float) -> Optional[float]:
    """The T-272 BTC leg's return for `date` from the BTC-USD history through date.
    Returns None when history is too short (< warmup) → caller degrades fail-closed."""
    b = btc_hist.astype(float).sort_index()
    if len(b) < WARMUP_DAYS + 2 or date not in b.index:
        return None
    pos = pd.concat([TrendOverlay(s, enabled=True).exposure(b) for s in SPEEDS],
                    axis=1).mean(axis=1).shift(1)          # act on yesterday's signal
    ret = b.pct_change()
    dpos = pos.diff().abs()
    if date not in pos.index or pd.isna(pos.loc[date]) or pd.isna(ret.loc[date]):
        return None
    p = float(pos.loc[date])
    leg = p * (float(ret.loc[date]) - BTC_ER_ANNUAL / TD) + (1 - p) * cash_daily
    leg -= float(dpos.loc[date]) * BTC_TXN
    return leg, p, (float(dpos.loc[date]) if not pd.isna(dpos.loc[date]) else 0.0)


@dataclass
class BtcShadowTracker:
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
               cash_daily_rate: float = 0.04 / TD,
               btc_hist: Optional[pd.Series] = None,
               ibit_close: Optional[float] = None,
               btc_close: Optional[float] = None) -> Dict[str, Any]:
        """Append today's shadow point (idempotent on trade_date) and return the
        rolling summary. `btc_hist` (BTC-USD close Series through trade_date) may be
        injected (tests / a pre-fetched panel); if None it is fetched fail-closed.
        REPORT-ONLY — never affects orders."""
        dt = pd.Timestamp(trade_date).normalize()
        if btc_hist is None:
            btc_hist, ibit_close, btc_close = self._fetch(dt)

        degraded, leg_ret, expo, dpos = True, cash_daily_rate, None, 0.0
        if btc_hist is not None and len(btc_hist):
            res = _btc_leg_today(btc_hist, dt, cash_daily_rate)
            if res is not None:
                leg_ret, expo, dpos = res
                degraded = False
            if btc_close is None:
                btc_close = float(btc_hist.dropna().iloc[-1])

        variant_ret = (1 - BTC_W) * float(sleeve_daily_return) + BTC_W * leg_ret
        pts = [p for p in self._load() if p["date"] != trade_date]
        prev = max(pts, key=lambda p: p["date"]) if pts else None
        base_nav = (prev["base_nav"] if prev else 1.0) * (1 + float(sleeve_daily_return))
        var_nav = (prev["variant_nav"] if prev else 1.0) * (1 + variant_ret)

        pt = {"date": trade_date, "degraded": degraded,
              "sleeve_ret": round(float(sleeve_daily_return), 6),
              "btc_exposure": (round(expo, 3) if expo is not None else None),
              "btc_would_be_trade": round(dpos * BTC_W, 4),   # notional turnover of the 5% leg
              "btc_leg_ret": round(leg_ret, 6),
              "variant_ret": round(variant_ret, 6),
              "base_nav": round(base_nav, 6), "variant_nav": round(var_nav, 6),
              "btc_close": (round(float(btc_close), 2) if btc_close is not None else None),
              "ibit_close": (round(float(ibit_close), 4) if ibit_close is not None else None)}
        pts.append(pt)
        pts.sort(key=lambda p: p["date"])
        summary = self._summarize(pts)
        self._file().write_text(json.dumps(
            {"_schema": "btc_shadow/v1", "points": pts, "summary": summary},
            indent=2, default=str))
        return summary

    def _fetch(self, dt: pd.Timestamp):
        """Trailing BTC-USD (for the signal) + IBIT (basis). Fail-closed → (None,..)."""
        try:
            import yfinance as yf
            start = (dt - pd.Timedelta(days=520)).strftime("%Y-%m-%d")
            end = (dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            b = yf.download("BTC-USD", start=start, end=end, progress=False,
                            auto_adjust=False, threads=False)["Close"]
            if hasattr(b, "columns"):
                b = b.iloc[:, 0]
            b.index = pd.to_datetime(b.index).tz_localize(None).normalize()
            b = b[~b.index.duplicated()]
            i = yf.download("IBIT", start=start, end=end, progress=False,
                            auto_adjust=False, threads=False)["Close"]
            ic = float(i.dropna().iloc[-1]) if len(i.dropna()) else None
            return b, ic, (float(b.dropna().iloc[-1]) if len(b.dropna()) else None)
        except Exception:
            return None, None, None

    def _summarize(self, pts: List[Dict[str, Any]]) -> Dict[str, Any]:
        clean = [p for p in pts if not p.get("degraded")]
        s: Dict[str, Any] = {"n_days": len(pts), "n_clean": len(clean),
                             "n_degraded": len(pts) - len(clean)}
        if len(clean) >= 2:
            idx = pd.to_datetime([p["date"] for p in clean])
            base = pd.Series([p["base_nav"] for p in clean], index=idx)
            var = pd.Series([p["variant_nav"] for p in clean], index=idx)
            s["base"] = {"nav": round(float(base.iloc[-1]), 4),
                         "maxdd": round(float(ME.max_drawdown(base)), 4)}
            s["variant"] = {"nav": round(float(var.iloc[-1]), 4),
                            "maxdd": round(float(ME.max_drawdown(var)), 4)}
            s["delta_wealth"] = round(float(var.iloc[-1] - base.iloc[-1]), 4)
        return s

    def forward_gates(self) -> Dict[str, Any]:
        """REPORT-ONLY status of the frozen promotion gates. Never changes trading."""
        pts = [p for p in self._load() if not p.get("degraded")]
        out: Dict[str, Any] = {"n_clean_days": len(pts),
                               "thresholds": {"A_winter_excess_max": GATE_A_VARIANT_EXCESS_MAX,
                                              "B_min_months": GATE_B_MIN_FORWARD_MONTHS,
                                              "C_ibit_basis_max": GATE_C_IBIT_BASIS_MAX}}
        if len(pts) < 2:
            out["status"] = "accruing"
            return out
        idx = pd.to_datetime([p["date"] for p in pts])
        base = pd.Series([p["base_nav"] for p in pts], index=idx)
        var = pd.Series([p["variant_nav"] for p in pts], index=idx)
        months = (idx[-1] - idx[0]).days / 30.44
        bret, vret = base.pct_change().dropna(), var.pct_change().dropna()
        d_wealth = float(var.iloc[-1] - base.iloc[-1])
        d_sortino = float(ME.sortino_ratio(vret) - ME.sortino_ratio(bret))
        # Gate A — OOS winter test: the largest in-forward BTC drawdown ≥ trigger
        btc = pd.Series([p["btc_close"] for p in pts if p.get("btc_close")],
                        index=[pd.Timestamp(p["date"]) for p in pts if p.get("btc_close")])
        winter, a_status = None, "no winter ≥30% yet"
        if len(btc) > 2:
            dd = (btc / btc.cummax() - 1.0)
            if dd.min() <= -GATE_A_WINTER_DD_TRIGGER:
                t0 = btc.loc[:dd.idxmin()].idxmax()
                t1 = dd.idxmin()
                vin = float(ME.max_drawdown(var.loc[t0:t1]))
                bin_ = float(ME.max_drawdown(base.loc[t0:t1]))
                excess = bin_ - vin  # both negative; excess = how much MORE DD the variant took
                winter = {"peak": str(t0.date()), "trough": str(t1.date()),
                          "variant_dd": round(vin, 4), "base_dd": round(bin_, 4),
                          "excess_pp": round(-excess, 4)}
                a_status = "PASS" if (-excess) <= GATE_A_VARIANT_EXCESS_MAX else "FAIL"
        out["gate_A_oos_winter"] = {"status": a_status, "detail": winter}
        out["gate_B_directional"] = {
            "status": ("PASS" if (months >= GATE_B_MIN_FORWARD_MONTHS
                                  and d_wealth > 0 and d_sortino > 0)
                       else ("accruing" if months < GATE_B_MIN_FORWARD_MONTHS else "FAIL")),
            "months": round(months, 1), "delta_wealth": round(d_wealth, 4),
            "delta_sortino": round(d_sortino, 3)}
        out["gate_C_ibit_basis"] = self._basis_gate(pts)
        out["promote_to_paper_leg"] = (
            out["gate_A_oos_winter"]["status"] == "PASS"
            and out["gate_B_directional"]["status"] == "PASS"
            and out["gate_C_ibit_basis"]["status"] == "PASS")
        return out

    def _basis_gate(self, pts: List[Dict[str, Any]]) -> Dict[str, Any]:
        rows = [(pd.Timestamp(p["date"]), p.get("btc_close"), p.get("ibit_close"))
                for p in pts if p.get("btc_close") and p.get("ibit_close")]
        if len(rows) < 30:
            return {"status": "accruing", "n": len(rows)}
        df = pd.DataFrame(rows, columns=["d", "btc", "ibit"]).set_index("d").sort_index()
        diff = df["ibit"].pct_change() - df["btc"].pct_change()
        ann = float(diff.mean() * TD) + BTC_ER_ANNUAL   # add back the ER (expected drag)
        return {"status": "PASS" if abs(ann) <= GATE_C_IBIT_BASIS_MAX else "FAIL",
                "ann_tracking_diff": round(ann, 4), "n": len(rows)}
