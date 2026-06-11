"""T-2026-06-10-142 — hermetic-run gate for network fallbacks.

Why this exists
---------------
T-134's cell profile found **52% of cloud-cell wall-time** inside yfinance
network wrappers: edges and the data-manager fall back to live Yahoo
fetches per call, the requests time out or rate-limit in containers, the
results are discarded or canon-irrelevant — pure burn. The same fallback
is also a CORRECTNESS hazard flagged by the 2026-05-31 silent-bug audit
(`data_manager._fetch_yfinance` writes into the split-only cache; a
total-return frame mixed in silently shifts the substrate).

Hermetic mode makes measured runs network-free: every yfinance fallback
site calls :func:`hermetic_block` BEFORE attempting the network. When
hermetic mode is ON the call is BLOCKED with a loud, structured,
greppable line naming the site, ticker and date range — and the caller
proceeds exactly as if the network had returned nothing (which is what
the profile showed it effectively did). When OFF (the local default)
behavior is byte-identical to pre-T-142.

Modes (env var ``ARCHONDEX_HERMETIC``)
--------------------------------------
  unset/0   off — fallbacks behave exactly as before (local default).
  1/warn    BLOCK + loud ``[HERMETIC] BLOCKED …`` line; caller receives
            the no-data outcome. Cloud default (set by the campaign
            launchers since T-142).
  strict    raise :class:`HermeticViolation` — for miss-inventory cells
            and CI where any network attempt should be fatal.

The blocked-call log doubles as the **miss inventory**: every line is
either a substrate gap (data we should bake) or a dead request (code
asking for data it never uses).

Local override documentation: ``ARCHONDEX_HERMETIC=0`` (or unset) keeps
yfinance fallbacks for interactive/research use; nothing changes for
local workflows unless explicitly opted in.
"""
from __future__ import annotations

import os
from typing import Optional

_COUNTS: dict[str, int] = {}


class HermeticViolation(RuntimeError):
    """A network fallback was attempted during a strict-hermetic run."""


def hermetic_mode() -> str:
    """'off' | 'warn' | 'strict' (reads env each call: test-friendly)."""
    v = os.environ.get("ARCHONDEX_HERMETIC", "").strip().lower()
    if v in ("", "0", "off", "false"):
        return "off"
    if v == "strict":
        return "strict"
    return "warn"  # "1", "warn", anything else truthy


def hermetic_block(site: str, ticker: Optional[str] = None,
                   start: Optional[str] = None, end: Optional[str] = None) -> bool:
    """Gate a network-fallback call site.

    Returns True if the call must be SKIPPED (hermetic active), False if
    the caller may proceed (hermetic off). In strict mode raises instead
    of returning.

    Call BEFORE the try/except that wraps the network call — several
    sites swallow Exception, so raising inside their try would be eaten.
    """
    mode = hermetic_mode()
    if mode == "off":
        return False
    detail = f"site={site}"
    if ticker:
        detail += f" ticker={ticker}"
    if start or end:
        detail += f" range={start}..{end}"
    _COUNTS[site] = _COUNTS.get(site, 0) + 1
    line = f"[HERMETIC] BLOCKED network fallback: {detail} (count[site]={_COUNTS[site]})"
    if mode == "strict":
        raise HermeticViolation(line)
    print(line, flush=True)
    return True
