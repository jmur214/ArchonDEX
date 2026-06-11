# core/account_router.py
"""Roth/taxable account router (T-141) — config schema + validation.

The deployment context runs BOTH a taxable (Illinois) account and a
Roth. Strategy-to-account routing is a real decision the system could
not previously express. This module is the CONFIG + CHECK layer only:
it validates a routing config against the two research rules and
exposes a backtest-time checker stub. It does NOT place or block real
orders — live enforcement arrives with paper trading.

The two rules (sources: Research_2026_06_10_system Q8.1/AREA 6,
Research_2026_06_10_blindspots §4.3):

  RULE A — ST-heavy strategies don't belong in taxable. A sleeve
  declared ``st_heavy: true`` (high-turnover / short-holding) may route
  to ``taxable`` only with after-tax evidence: a positive
  ``after_tax_sharpe_taxable`` (CI-aware when available — pass
  ``ci_low`` and it is used instead of the point estimate, per the
  CLAUDE.md kill-threshold discipline).

  RULE B — cross-account wash sale (Rev. Rul. 2008-5): a loss realized
  in taxable followed by a substantially-identical purchase in the IRA
  within the +-30-day window is disallowed PERMANENTLY (no basis
  adjustment in the IRA). Enforcement options, per config
  ``rules.cross_account_wash_sale``:
    * ``"disjoint_universes"`` — a ticker is tradable in EXACTLY ONE
      account's universe (validated statically here), or
    * ``"blackout_31d"`` — after any taxable realized loss in a ticker,
      the OTHER account may not buy it for 31 calendar days (the sale
      day plus the 30-day window) — checked at trade time by
      ``CrossAccountWashSaleChecker`` (backtest-time stub; logs only).

Config lives in ``config/account_routing.json``. Tax rates do NOT live
here — they stay in ``backtest_settings.json::tax_drag_model`` (single
source; see backtester/after_tax_metrics.py). We are not tax advisors;
the rules encode published IRS guidance as engineering constraints.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

__all__ = [
    "RoutingViolation",
    "load_routing_config",
    "validate_routing",
    "CrossAccountWashSaleChecker",
    "VALID_ACCOUNTS",
    "BLACKOUT_DAYS",
]

VALID_ACCOUNTS = ("taxable", "roth", "either")
# Rev. Rul. 2008-5 window: the sale day + 30 days after (the before-side
# is handled by not holding the replacement when the loss is realized).
BLACKOUT_DAYS = 31


@dataclass
class RoutingViolation:
    rule: str          # "schema" | "st_heavy_taxable" | "universe_overlap"
    sleeve: Optional[str]
    message: str
    severity: str = "error"   # "error" | "warning"

    def __str__(self) -> str:
        where = f" [{self.sleeve}]" if self.sleeve else ""
        return f"{self.severity.upper()}:{self.rule}{where} {self.message}"


def load_routing_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load config/account_routing.json (repo-root-anchored default)."""
    cfg_path = (
        Path(path)
        if path
        else Path(__file__).resolve().parents[1] / "config" / "account_routing.json"
    )
    with open(cfg_path, "r") as fh:
        return json.load(fh)


def validate_routing(
    config: Dict[str, Any],
    after_tax_evidence: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[RoutingViolation]:
    """Validate a routing config against the schema + research rules.

    Parameters
    ----------
    config : parsed account_routing.json.
    after_tax_evidence : optional ``{sleeve_id: {"after_tax_sharpe_taxable":
        float, "ci_low": float}}``. RULE A consults ``ci_low`` when
        present, else the point estimate (and says so in the violation
        message when only a point estimate cleared).

    Returns a list of violations; empty list = config valid.
    """
    violations: List[RoutingViolation] = []
    evidence = after_tax_evidence or {}

    sleeves: Dict[str, Any] = config.get("sleeves") or {}
    if not isinstance(sleeves, dict) or not sleeves:
        violations.append(RoutingViolation(
            rule="schema", sleeve=None,
            message="config has no 'sleeves' mapping",
        ))
        return violations

    rules_cfg: Dict[str, Any] = config.get("rules") or {}
    wash_mode = str(rules_cfg.get("cross_account_wash_sale", "disjoint_universes"))
    if wash_mode not in ("disjoint_universes", "blackout_31d"):
        violations.append(RoutingViolation(
            rule="schema", sleeve=None,
            message=f"rules.cross_account_wash_sale must be 'disjoint_universes' "
                    f"or 'blackout_31d', got '{wash_mode}'",
        ))

    # --- per-sleeve schema + RULE A -----------------------------------
    universes_by_account: Dict[str, Dict[str, str]] = {"taxable": {}, "roth": {}}
    for sleeve_id in sorted(sleeves.keys()):
        entry = sleeves[sleeve_id]
        if not isinstance(entry, dict):
            violations.append(RoutingViolation(
                rule="schema", sleeve=sleeve_id,
                message="sleeve entry must be an object",
            ))
            continue
        account = str(entry.get("account", "")).lower()
        if account not in VALID_ACCOUNTS:
            violations.append(RoutingViolation(
                rule="schema", sleeve=sleeve_id,
                message=f"account must be one of {VALID_ACCOUNTS}, got '{account}'",
            ))
            continue

        st_heavy = bool(entry.get("st_heavy", False))
        if st_heavy and account in ("taxable", "either"):
            ev = evidence.get(sleeve_id) or {}
            ci_low = ev.get("ci_low")
            point = ev.get("after_tax_sharpe_taxable")
            if ci_low is not None and ci_low > 0.0:
                pass  # CI-aware evidence clears RULE A
            elif ci_low is None and point is not None and point > 0.0:
                violations.append(RoutingViolation(
                    rule="st_heavy_taxable", sleeve=sleeve_id, severity="warning",
                    message=(
                        "st_heavy sleeve routed to taxable on a POINT-ESTIMATE "
                        f"after-tax Sharpe ({point:.3f}) with no ci_low — "
                        "CI-aware evidence required before deploy "
                        "(CLAUDE.md kill-threshold discipline)"
                    ),
                ))
            else:
                violations.append(RoutingViolation(
                    rule="st_heavy_taxable", sleeve=sleeve_id,
                    message=(
                        "st_heavy sleeve routed to "
                        f"'{account}' without surviving after-tax evidence "
                        "(needs after_tax_sharpe_taxable ci_low > 0); "
                        "route to roth or supply evidence"
                    ),
                ))

        # Collect universes for RULE B (an 'either' sleeve's universe
        # belongs to both account pools for overlap purposes).
        universe = entry.get("universe") or []
        accounts_touched = ["taxable", "roth"] if account == "either" else [account]
        for acct in accounts_touched:
            for ticker in universe:
                universes_by_account[acct][str(ticker).upper()] = sleeve_id

    # --- RULE B: disjoint universes -----------------------------------
    if wash_mode == "disjoint_universes":
        overlap = sorted(
            set(universes_by_account["taxable"]) & set(universes_by_account["roth"])
        )
        for ticker in overlap:
            violations.append(RoutingViolation(
                rule="universe_overlap", sleeve=None,
                message=(
                    f"ticker {ticker} is tradable in BOTH accounts "
                    f"(taxable via '{universes_by_account['taxable'][ticker]}', "
                    f"roth via '{universes_by_account['roth'][ticker]}') — "
                    "Rev. Rul. 2008-5 cross-account wash-sale exposure; "
                    "make universes disjoint or switch to blackout_31d"
                ),
            ))
    return violations


class CrossAccountWashSaleChecker:
    """Backtest-time checker STUB for ``blackout_31d`` mode (logs only).

    Records taxable realized losses per ticker; ``check_trade`` answers
    whether a buy in the OTHER account falls inside the 31-day blackout.
    This is the reporting/validation half — live enforcement (rejecting
    real orders) arrives with the paper-trading milestone and will need
    user-gated wiring into the order path (Engine B coordination).
    """

    def __init__(self, blackout_days: int = BLACKOUT_DAYS):
        self.blackout_days = int(blackout_days)
        self._taxable_losses: Dict[str, pd.Timestamp] = {}  # ticker -> last loss date
        self.events: List[Dict[str, Any]] = []              # audit trail

    def record_taxable_loss(self, ticker: str, date: Any) -> None:
        ts = pd.Timestamp(date)
        key = str(ticker).upper()
        prev = self._taxable_losses.get(key)
        if prev is None or ts > prev:
            self._taxable_losses[key] = ts

    def check_trade(self, ticker: str, account: str, date: Any) -> Dict[str, Any]:
        """Would this buy violate the cross-account blackout?

        Returns ``{"allowed": bool, "reason": str|None, ...}``. The stub
        never blocks — callers log the verdict; enforcement is a later,
        user-gated step.
        """
        key = str(ticker).upper()
        ts = pd.Timestamp(date)
        verdict: Dict[str, Any] = {
            "ticker": key, "account": str(account), "date": str(ts.date()),
            "allowed": True, "reason": None,
        }
        if str(account).lower() == "roth":
            loss_dt = self._taxable_losses.get(key)
            if loss_dt is not None:
                days = (ts - loss_dt).days
                if 0 <= days < self.blackout_days:
                    verdict["allowed"] = False
                    verdict["reason"] = (
                        f"taxable loss in {key} {days}d ago — inside the "
                        f"{self.blackout_days}d cross-account blackout "
                        "(Rev. Rul. 2008-5: loss would be disallowed permanently)"
                    )
        self.events.append(verdict)
        return verdict
