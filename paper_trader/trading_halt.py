# paper_trader/trading_halt.py
"""TradingHalt — the stage-2 (account-3) TRADING kill switch.

The pre-existing ``llm.kill_switch`` (``intelligence/analyst/cost_governor.py``)
gates LLM **spend**: trip it and no new note/scan/watchdog call is made. That was
sufficient while every LLM output was report-only. It is NOT sufficient once an
LLM note drives REAL paper orders, because of a timing hole:

    the constructor consumes YESTERDAY's note (signal-t / fill-t+1). Halting spend
    on day D stops day-D's note — but day D's ORDERS come from day D-1's note,
    which already exists on disk. Spend-halt alone therefore still trades for one
    more day, and keeps trading for as long as an unconsumed note remains.

So this module answers a different question: *may this account place a new order
at all?* Semantics are the ones codified for every halt path in this system
(``docs/Sources/info_layer_program_2026_07_07.md``, T-292 spec addition 3):

    A HALT STOPS NEW AUTOMATED ACTIONS. IT NEVER LIQUIDATES.

That is why a halt refuses BUYS AND SELLS alike. A "kill switch" that let sells
through would force-sell the book — the exact capitulation this system exists to
prevent — and would do it at the worst possible moment, since the switch is most
likely to be pulled during a disorderly market.

THREE INDEPENDENT SOURCES, any one of which halts. They exist because they have
different latencies, and an operator control you cannot reach in time is not a
control:

  1. ``data/state/TRADING_HALT``  — a durable-state file. It rides ``DURABLE_PATHS``,
     so writing ONE S3 object halts the next run. No deploy, no revision, seconds.
  2. ``ARCHONDEX_TRADING_KILL_SWITCH`` env — a jobdef revision. No image rebuild.
  3. ``config/llm_settings.json`` → ``llm.trading_kill_switch`` (and ``llm.kill_switch``,
     which implies it — see the timing hole above) — baked in the image, needs a rev.

FAIL-CLOSED. An unreadable/unparseable settings file HALTS. A safety control that
degrades toward "trade anyway" is not a safety control ([NN-FAIL-CLOSED]); and unlike
the measurement path, halting costs at most a day of paper orders while the
alternative risks orders placed on a config nobody could read.

The halt is LOUD, never silent: every refused order is journaled with a typed
reason, the driver prints a banner, and the reason string names the source.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

HALT_FILE = "data/state/TRADING_HALT"
ENV_VAR = "ARCHONDEX_TRADING_KILL_SWITCH"
SETTINGS = "config/llm_settings.json"

# Truthy spellings accepted for the env var. Anything else (including "" and
# unset) is NOT a trip — but note the asymmetry: an UNPARSEABLE settings file
# IS a trip. The env var's absence is a normal state; a broken config is not.
_TRUTHY = {"1", "true", "yes", "on", "halt", "halted"}


class TradingHalted(Exception):
    """Raised by ``OrderManager.submit`` when a halt is in force. The order is
    journaled REJECTED with a typed reason and NEVER reaches the broker."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class HaltStatus:
    halted: bool
    reason: str = ""          # typed, source-naming; "" iff not halted

    def banner(self) -> str:
        return (f"[TRADING-HALT] NEW ORDERS REFUSED — {self.reason} "
                f"(halt = stop new actions; positions are NEVER liquidated)"
                if self.halted else "trading-halt: clear")


def check_trading_halt(root: Optional[str] = None,
                       settings_path: Optional[str] = None) -> HaltStatus:
    """Resolve the halt from all three sources. READ-ONLY; never raises."""
    base = Path(root) if root else Path(__file__).resolve().parents[1]

    # 1. the durable file — the fastest operator surface (one S3 object).
    try:
        if (base / HALT_FILE).exists():
            return HaltStatus(True, "halt_file:data/state/TRADING_HALT present")
    except Exception as exc:                       # pragma: no cover — defensive
        return HaltStatus(True, f"halt_file_unreadable:{type(exc).__name__}")

    # 2. the env var — a jobdef revision, no image rebuild.
    env = os.getenv(ENV_VAR)
    if env is not None and str(env).strip().lower() in _TRUTHY:
        return HaltStatus(True, f"env:{ENV_VAR}={env}")

    # 3. the baked settings block. Unreadable/unparseable ⇒ HALT (fail-closed).
    p = Path(settings_path) if settings_path else (base / SETTINGS)
    try:
        block = json.loads(p.read_text()).get("llm", {})
    except Exception as exc:
        return HaltStatus(True, f"settings_unreadable:{type(exc).__name__} ({p.name})")
    if not isinstance(block, dict):
        return HaltStatus(True, "settings_unreadable:llm block is not an object")
    if bool(block.get("trading_kill_switch", False)):
        return HaltStatus(True, "config:llm.trading_kill_switch")
    if bool(block.get("kill_switch", False)):
        # The spend switch IMPLIES the trading switch — closing the one-day
        # timing hole described in this module's docstring.
        return HaltStatus(True, "config:llm.kill_switch (spend halt implies trading halt)")
    return HaltStatus(False)
