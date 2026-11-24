# paper_trader/report_prices.py
"""Closes for the REPORT-ONLY books and the prediction scorer (T-412 review, item 4).

The broker's data API rejects a whole batch when one symbol in it is invalid. The trading
paths ask for a fixed, known universe, so that never bites them; the report-only readers
ask for whatever a filing, a thesis or a model named. One such name emptied the batch: a
``BRK-B`` (the membership file's spelling; the broker's is ``BRK.B``) left the event desk
with no price for any of four valid calls, and one ``^GSPC`` left three predictions out of
four unresolved.

``fetch_closes`` maps spellings, sets aside what cannot be a US equity symbol before asking,
and — when a batch still fails — splits it to isolate the bad name, within a call limit.
Results are keyed by the symbol the CALLER used. A symbol with no price is simply absent,
with the reason in ``dropped``: the readers then park or fail closed on that name alone.

Never used for orders or sizing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

#: A US equity/ETF symbol as the broker spells it, with an optional share-class suffix.
_VALID = re.compile(r"^[A-Z]{1,5}(?:\.[A-Z]{1,2})?$")
#: Data-API calls one fetch may make. A full outage fails every call; this stops the split
#: from turning one failed request into dozens.
MAX_CALLS = 16


def broker_symbol(symbol: str) -> Optional[str]:
    """The broker's spelling of ``symbol`` (``BRK-B`` → ``BRK.B``), or None when it cannot
    be a US equity symbol at all (``^GSPC``, ``BTC-USD``, an empty string)."""
    s = str(symbol or "").strip().upper().replace("-", ".")
    return s if _VALID.match(s) else None


@dataclass
class ClosesResult:
    closes: Dict[str, pd.Series] = field(default_factory=dict)   # caller's symbol → series
    dropped: Dict[str, str] = field(default_factory=dict)        # caller's symbol → why
    calls: int = 0


def fetch_closes(client: Any, symbols: Iterable[str], *, lookback_days: int,
                 before: Optional[Any] = None) -> ClosesResult:
    """Daily closes for ``symbols``. ``before`` keeps only bars strictly before that date —
    the run is at 09:45 ET and the API already returns a partial bar dated today. Never
    raises: a failed lookup is a missing symbol with a reason."""
    out = ClosesResult()
    spelled: Dict[str, List[str]] = {}                           # broker spelling → callers'
    for raw in {str(s or "").strip() for s in symbols}:
        b = broker_symbol(raw)
        if b is None:
            if raw:
                out.dropped[raw] = "not a US equity symbol"
            continue
        spelled.setdefault(b, []).append(raw)

    got: Dict[str, pd.Series] = {}
    queue: List[List[str]] = [sorted(spelled)] if spelled else []
    while queue:
        batch = queue.pop(0)
        if out.calls >= MAX_CALLS:
            out.dropped.update({r: "price lookup call limit reached" for b in batch
                                for r in spelled[b]})
            continue
        out.calls += 1
        try:
            res = client.fetch_daily_closes(list(batch), lookback_days=lookback_days) or {}
        except Exception as exc:      # noqa: BLE001 — isolate the name, or report the failure
            if len(batch) == 1:
                out.dropped.update({r: f"price lookup failed ({type(exc).__name__})"
                                    for r in spelled[batch[0]]})
            else:
                mid = len(batch) // 2
                queue += [batch[:mid], batch[mid:]]
            continue
        got.update({str(k).upper(): v for k, v in res.items()})

    cut = pd.Timestamp(str(before)[:10]) if before is not None else None
    for b, raws in spelled.items():
        s = got.get(b)
        if s is not None and cut is not None:
            s = s[s.index < cut]
        for raw in raws:
            if raw in out.dropped:
                continue
            if s is None or not len(s):
                out.dropped[raw] = "no price returned"
            else:
                out.closes[raw] = s
    return out


def last_prices(result: ClosesResult) -> Dict[str, float]:
    """Caller's symbol → its newest close in the result."""
    return {k: float(v.iloc[-1]) for k, v in result.closes.items()}
