# paper_trader/paper_config.py
"""PaperConfig — the paper-loop configuration, with the allocator choice
made EXPLICIT and logged (T-158 lesson: never let the allocator be
inherited silently from a learned artifact).

The Roth-emulation defaults are the user-approved T-159 §5 numbers:
$5K, dyn-opt ON (whole-share integer book — auction orders are
whole-share-only). The allocator (`adaptive | mean_variance |
parrondo_fixed`) is a named field, surfaced in `log_dict()` for
per-cycle logging; the allocator-IDENTITY decision is director-held and
a go-live gate — this config makes it VISIBLE and configurable, not
decided here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict

VALID_ALLOCATORS = ("adaptive", "mean_variance", "parrondo_fixed")


@dataclass
class PaperConfig:
    account: str = "roth"                  # Roth-emulation (T-141 verdict)
    starting_equity: float = 5_000.0       # T-159 §5
    # ALLOCATOR VISIBILITY (T-158): explicit, never silently inherited.
    allocator: str = "adaptive"
    # whole-share integer book — REQUIRED for auction (OPG/CLS) orders.
    dynamic_optimization_enabled: bool = True
    position_buffering_enabled: bool = False
    buffer_fraction: float = 0.10
    auction_safety_bps: float = 1.0
    # auction routing: "moo" (all OPG) or "moo_moc" (entries OPG / exits CLS)
    auction_execution: str = "moo_moc"
    fixed_allocations: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if self.allocator not in VALID_ALLOCATORS:
            raise ValueError(
                f"allocator must be one of {VALID_ALLOCATORS}, got "
                f"'{self.allocator}' — make the choice EXPLICIT (T-158)"
            )

    def config_hash(self) -> str:
        """Deterministic hash of the config — folded into every
        client_order_id so a config change can't silently collide ids
        with a prior config's orders."""
        payload = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha1(payload.encode()).hexdigest()[:12]

    def portfolio_policy_config(self):
        """Build the Engine C PortfolioPolicyConfig with the EXPLICIT
        allocator + dyn-opt ON. Imported lazily (read-only) so this
        module stays import-light for tests that don't need engines."""
        from engines.engine_c_portfolio.policy import PortfolioPolicyConfig
        return PortfolioPolicyConfig(
            mode=self.allocator,
            fixed_allocations=self.fixed_allocations,
            dynamic_optimization_enabled=self.dynamic_optimization_enabled,
            position_buffering_enabled=self.position_buffering_enabled,
            buffer_fraction=self.buffer_fraction,
        )

    def log_dict(self) -> Dict[str, Any]:
        """The per-cycle allocator-visibility record (T-158): the
        allocator choice is logged EVERY cycle, never assumed."""
        return {
            "account": self.account,
            "allocator": self.allocator,            # the visible choice
            "dyn_opt": self.dynamic_optimization_enabled,
            "buffering": self.position_buffering_enabled,
            "auction_execution": self.auction_execution,
            "config_hash": self.config_hash(),
        }
