# paper_trader/market_calendar.py
"""Trading-calendar + auction-window awareness for the paper loop (T-185).

Two host-independent concerns the persistent loop needs:
  1. **Trading-day awareness** — run only on trading days; skip
     weekends/holidays/early-closes (don't fire-and-error on a closed
     day). Backed by Alpaca's calendar API when a client is supplied,
     with a deterministic offline fallback (weekday minus the US market
     holiday set) so tests + offline runs still work.
  2. **Auction submission windows** — the T-169 live finding: Alpaca
     accepts an **OPG** order only in the **7:00pm (prev day) → 9:28am
     ET** window (code 40310000 otherwise), and **CLS** before
     **15:50 ET**. The scheduler gates submission on these.

All times are America/New_York. Pure/deterministic given an injected
`now_et`; never raises (calendar fetch failure → fallback).
"""
from __future__ import annotations

from datetime import date as _date, datetime, time
from typing import Optional, Set
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

OPG_OPEN = time(19, 0)        # 7:00pm prev day
OPG_CLOSE = time(9, 28)       # 9:28am
CLS_CUTOFF = time(15, 50)     # 3:50pm

# US equity market holidays (fixed + observed) used by the OFFLINE
# fallback only — the live path uses the broker calendar (authoritative,
# incl. ad-hoc closures). Kept deliberately small + current-era.
_FALLBACK_HOLIDAYS_2026: Set[_date] = {
    _date(2026, 1, 1), _date(2026, 1, 19), _date(2026, 2, 16),
    _date(2026, 4, 3), _date(2026, 5, 25), _date(2026, 6, 19),  # Juneteenth
    _date(2026, 7, 3), _date(2026, 9, 7), _date(2026, 11, 26),
    _date(2026, 12, 25),
}


def now_et() -> datetime:
    return datetime.now(ET)


class MarketCalendar:
    def __init__(self, client=None, holidays: Optional[Set[_date]] = None):
        """`client`: an AlpacaPaperClient (or anything exposing
        ``trading_days(start, end)`` → set[date]). None ⇒ offline
        fallback. `holidays`: override the fallback holiday set (tests)."""
        self.client = client
        self._holidays = holidays if holidays is not None else _FALLBACK_HOLIDAYS_2026
        self._trading_day_cache: Optional[Set[_date]] = None

    # ------------------------------------------------------------------ #
    def is_trading_day(self, d: Optional[_date] = None) -> bool:
        d = d or now_et().date()
        # Live: ask the broker calendar (authoritative). Never raise.
        if self.client is not None:
            try:
                days = self._broker_trading_days(d)
                if days is not None:
                    return d in days
            except Exception:
                pass
        # Offline fallback: weekday and not a known holiday.
        return d.weekday() < 5 and d not in self._holidays

    def _broker_trading_days(self, around: _date) -> Optional[Set[_date]]:
        if self._trading_day_cache is None:
            fn = getattr(self.client, "trading_days", None)
            if fn is None:
                return None
            start = around.replace(day=1)
            # cover a generous window so caching is useful
            end = _date(around.year + (1 if around.month == 12 else 0),
                        1 if around.month == 12 else around.month + 1, 1)
            self._trading_day_cache = set(fn(start.isoformat(), end.isoformat()))
        return self._trading_day_cache

    # ------------------------------ windows --------------------------- #
    def is_opg_window(self, now: Optional[datetime] = None) -> bool:
        """True iff submitting an OPG order is currently allowed
        (7:00pm prev → 9:28am ET). Spans midnight."""
        t = (now or now_et()).astimezone(ET).time()
        return t >= OPG_OPEN or t < OPG_CLOSE

    def is_cls_window(self, now: Optional[datetime] = None) -> bool:
        """True iff submitting a CLS order is currently allowed (before
        15:50 ET on a trading day)."""
        t = (now or now_et()).astimezone(ET).time()
        return t < CLS_CUTOFF

    def auction_window_open(self, tif: str, now: Optional[datetime] = None) -> bool:
        tif = str(tif).lower()
        if tif == "opg":
            return self.is_opg_window(now)
        if tif == "cls":
            return self.is_cls_window(now)
        return True   # non-auction TIFs unrestricted

    def window_reason(self, tif: str, now: Optional[datetime] = None) -> str:
        t = (now or now_et()).astimezone(ET)
        if str(tif).lower() == "opg":
            return (f"OPG window is 7:00pm–9:28am ET; now {t:%H:%M} ET → "
                    f"{'OPEN' if self.is_opg_window(now) else 'CLOSED (defer to window)'}")
        if str(tif).lower() == "cls":
            return (f"CLS cutoff 15:50 ET; now {t:%H:%M} ET → "
                    f"{'OPEN' if self.is_cls_window(now) else 'CLOSED'}")
        return "no window restriction"
