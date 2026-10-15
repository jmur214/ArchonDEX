"""ONE Yahoo symbol table for the processed cache's tickers (director ruling, 2026-10-15).

Moved out of `scripts/fetch_missing_delisted.py` (its `YAHOO_OVERRIDES`), which now imports it, and used
by the total-return writer (`tr_writer.full_refetch`). Two kinds of mapping, kept apart because they
make different claims:

  * SHARE CLASS — a mechanical spelling. The cache names a class with a dot (BRK.B); Yahoo with a dash
    (BRK-B). Same security, same history: no identity claim.
  * RENAME — an IDENTITY claim. The security's history is said to live on under another Yahoo symbol
    after a delisting (FRC -> FRCB, SIVB -> SIVBQ). A wrong claim would splice another security's
    prices into the file, so a rename is never trusted on its own: the writer's span and overlap
    rails decide, and the write record carries "symbol mapped: X -> Y (rename)" so a reader sees the
    claim that was made.

Deliberately NOT here: "try several symbols and keep whichever returns the most rows". That is a
guess, and the writer's guard exists to refuse guesses. `fetch_missing_delisted.py` keeps its own
`YAHOO_FALLBACKS` for its own fetch path; the writer never sees it.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

SHARE_CLASS = "share class"
RENAME = "rename"

_SHARE_CLASS_RE = re.compile(r"^([A-Z]+)\.([A-Z])$")

#: Moved verbatim from scripts/fetch_missing_delisted.py (2026-10-15). An entry that maps a ticker to
#: itself records a delisted name known to keep its Yahoo history; it maps nothing.
YAHOO_OVERRIDES: dict[str, str] = {
    "BF.B": "BF-B",
    "BRK.B": "BRK-B",
    # Old-name -> last Yahoo-known symbol while listed
    "FRC": "FRCB",       # First Republic Bank — OTC pink sheet after FDIC
    "SIVB": "SIVBQ",     # SVB Financial Group — chapter 11 ticker
    "ATVI": "ATVI",      # Activision (acquired by MSFT)
    "TWTR": "TWTR",      # Twitter (delisted post-Musk)
    "DAY": "DAY",        # Dayforce (current ticker)
    "K": "K",            # Kellanova
    "WBA": "WBA",        # Walgreens (delisted Aug 2025)
    "ANSS": "ANSS",
    "JNPR": "JNPR",
    "DFS": "DFS",
    "HES": "HES",
    "IPG": "IPG",
    "CTLT": "CTLT",
    "MRO": "MRO",
    "PXD": "PXD",
    "CMA": "CMA",
    "ABMD": "ABMD",
    "ALXN": "ALXN",
    "CERN": "CERN",
    "CTXS": "CTXS",
    "CXO": "CXO",
    "DISCA": "DISCA",
    "DISCK": "DISCK",
    "DISH": "DISH",
    "DRE": "DRE",
    "FBHS": "FBHS",
    "FLIR": "FLIR",
    "GPS": "GPS",
    "HBI": "HBI",
    "HFC": "HFC",
    "KSU": "KSU",
    "MXIM": "MXIM",
    "NLSN": "NLSN",
    "PBCT": "PBCT",
    "TIF": "TIF",
    "VAR": "VAR",
    "XLNX": "XLNX",
}


def yahoo_symbol(ticker: str) -> Tuple[str, Optional[str]]:
    """(the Yahoo symbol to fetch, the kind of mapping: None, SHARE_CLASS or RENAME)."""
    target = YAHOO_OVERRIDES.get(ticker, ticker)
    if target != ticker:
        return target, (SHARE_CLASS if target == ticker.replace(".", "-") else RENAME)
    m = _SHARE_CLASS_RE.match(ticker)
    if m:
        return f"{m.group(1)}-{m.group(2)}", SHARE_CLASS
    return ticker, None
