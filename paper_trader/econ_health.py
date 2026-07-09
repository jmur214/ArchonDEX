# paper_trader/econ_health.py
"""EconHealth — the economic/behavioral tripwires the dead-man's-switch can't see.

The T-185 heartbeat answers "did a canonical run happen today?" — an OPERATIONAL
question. But a loop can be canonical every single day while the STRATEGY has
silently gone wrong in a way the reconcile/census gates never look at:

  * no-trade-in-N-days — the loop keeps running, reconciles clean, pushes
    state… and hasn't placed an order in a month. Legitimate for a buffered
    sleeve over a short stretch; a red flag over a long one (frozen signals,
    a stuck constructor, a data feed that stopped moving). A HIGH threshold
    tripwire, not a daily nag.
  * stale-data freshness — the run fetched *something*, so the census passes,
    but the freshest bar feeding today's signals is days old. Signals computed
    on stale prices look healthy and are wrong.
  * positions-without-exit-coverage — the account holds a ticker that is NOT in
    the strategy's managed universe. No rule the constructor runs will ever emit
    a sell for it, so it sits forever — an orphan the reconcile treats as
    "explained" (it came from a known fill) yet nothing will ever close.

These are REPORT-ONLY by design: an economically-stale day is a signal to
INVESTIGATE, not an operational failure. Unlike the reconcile/census gates they
must NEVER flip a run's ``canonical`` verdict (that would fail the Batch job and
fire the trading alarm for a non-trading condition). They ride the same loud
notify channel as the alt-data/news health blocks (``PaperHeartbeat`` records an
``econ_health`` status block + notifies on a trip) so a silent economic drift
can't hide behind a green operational light.

Pure + dependency-light (numpy only) so it is unit-testable with fixed dates and
zero I/O. Each channel is independently fail-open: a channel with missing inputs
is simply not evaluated (reported ``skipped``), never a crash or a false trip.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date
from typing import Callable, Dict, List, Optional

import numpy as np

# Defaults chosen as tripwires, not nags. A buffered/deadband sleeve can hold for
# weeks; 20 trading days (~1 month) without ANY order is the "have you gone inert"
# line. Data older than 3 trading days is stale for a daily loop.
DEFAULT_NO_TRADE_MAX_TRADING_DAYS = 20
DEFAULT_DATA_STALE_MAX_TRADING_DAYS = 3

# (start, end] trading-day count. Injected form (calendar-backed) is exact;
# default form counts weekdays via numpy (ignores holidays → counts SLIGHTLY MORE
# than true trading days → a "> threshold" trip fires marginally EARLY, never
# late; conservative for an investigate-signal tripwire).
TradingDayCounter = Callable[[_date, _date], int]


def _weekday_count(start: _date, end: _date) -> int:
    """Weekday count in (start, end] — 0 if end <= start."""
    if end <= start:
        return 0
    # busday_count is [start, end); shift both by one day to get (start, end].
    return int(np.busday_count(
        np.datetime64(start) + np.timedelta64(1, "D"),
        np.datetime64(end) + np.timedelta64(1, "D")))


@dataclass
class EconHealthFinding:
    channel: str            # "no_trade" | "stale_data" | "orphan_positions"
    status: str             # "ok" | "tripped" | "skipped"
    detail: str
    value: Optional[float] = None   # the measured quantity (days, count), if any

    @property
    def tripped(self) -> bool:
        return self.status == "tripped"


@dataclass
class EconHealthReport:
    degraded: bool                              # any channel tripped
    findings: List[EconHealthFinding] = field(default_factory=list)

    def to_status_dict(self) -> Dict[str, object]:
        return {
            "degraded": self.degraded,
            "findings": [
                {"channel": f.channel, "status": f.status,
                 "detail": f.detail, "value": f.value}
                for f in self.findings
            ],
            "_schema": "paper_econ_health/v1",
        }

    def summary_line(self) -> str:
        tripped = [f.channel for f in self.findings if f.tripped]
        if tripped:
            return "DEGRADED: " + "; ".join(
                f"{f.channel} ({f.detail})" for f in self.findings if f.tripped)
        skipped = [f.channel for f in self.findings if f.status == "skipped"]
        base = "all channels ok"
        return base + (f" ({len(skipped)} skipped: {','.join(skipped)})" if skipped else "")


def evaluate_econ_health(
    *,
    today: _date,
    managed_universe: Optional[List[str]] = None,
    broker_positions: Optional[Dict[str, int]] = None,
    last_trade_date: Optional[_date] = None,
    latest_bar_date: Optional[_date] = None,
    no_trade_max_trading_days: int = DEFAULT_NO_TRADE_MAX_TRADING_DAYS,
    data_stale_max_trading_days: int = DEFAULT_DATA_STALE_MAX_TRADING_DAYS,
    trading_day_counter: Optional[TradingDayCounter] = None,
) -> EconHealthReport:
    """Evaluate the three economic tripwires. Each channel is independently
    fail-open: absent inputs ⇒ that channel is ``skipped``, never a crash or a
    false trip. Report-only — the caller must NOT let ``degraded`` flip
    ``canonical``."""
    count = trading_day_counter or _weekday_count
    findings: List[EconHealthFinding] = []

    # --- Channel A: no-trade-in-N-days ------------------------------------- #
    if last_trade_date is None:
        # No order has ever been placed. A fresh loop that hasn't traded yet is
        # NOT a trip — there is no baseline to have gone stale from.
        findings.append(EconHealthFinding(
            "no_trade", "skipped", "no prior order on record (fresh loop)"))
    else:
        days = count(last_trade_date, today)
        if days > no_trade_max_trading_days:
            findings.append(EconHealthFinding(
                "no_trade", "tripped",
                f"{days} trading days since last order ({last_trade_date.isoformat()}) "
                f"> {no_trade_max_trading_days} — loop may be economically inert",
                float(days)))
        else:
            findings.append(EconHealthFinding(
                "no_trade", "ok",
                f"{days} trading days since last order (≤ {no_trade_max_trading_days})",
                float(days)))

    # --- Channel B: stale-data freshness ----------------------------------- #
    if latest_bar_date is None:
        findings.append(EconHealthFinding(
            "stale_data", "skipped", "no bar date supplied"))
    else:
        stale = count(latest_bar_date, today)
        if stale > data_stale_max_trading_days:
            findings.append(EconHealthFinding(
                "stale_data", "tripped",
                f"freshest bar {latest_bar_date.isoformat()} is {stale} trading days "
                f"old > {data_stale_max_trading_days} — signals ran on stale prices",
                float(stale)))
        else:
            findings.append(EconHealthFinding(
                "stale_data", "ok",
                f"freshest bar {latest_bar_date.isoformat()} is {stale} trading days old "
                f"(≤ {data_stale_max_trading_days})",
                float(stale)))

    # --- Channel C: positions-without-exit-coverage ------------------------ #
    if managed_universe is None or broker_positions is None:
        findings.append(EconHealthFinding(
            "orphan_positions", "skipped", "universe or positions not supplied"))
    else:
        managed = {t.upper() for t in managed_universe}
        orphans = sorted(t for t, q in broker_positions.items()
                         if int(q) != 0 and t.upper() not in managed)
        if orphans:
            findings.append(EconHealthFinding(
                "orphan_positions", "tripped",
                f"held {orphans} outside managed universe {sorted(managed)} — "
                f"no constructor rule will ever exit these",
                float(len(orphans))))
        else:
            findings.append(EconHealthFinding(
                "orphan_positions", "ok",
                "all holdings are inside the managed universe", 0.0))

    degraded = any(f.tripped for f in findings)
    return EconHealthReport(degraded=degraded, findings=findings)
