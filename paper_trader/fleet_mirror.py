"""T-357 — the fleet mirror: the honest, tier-scaled view of each paper account.

WHY THIS EXISTS. The broker shows ~$100,000 in every paper account because that
is what Alpaca seeded them with, and Alpaca's reset button no longer exists. The
machine does not trade $100,000 — each account is capped to its tier (the
notional cap, contribution-grown). So the broker's number is real and almost
entirely meaningless, and any surface that shows it is telling the user
something true and misleading at once. This writes the number the machine
actually acts on.

DISPLAY-ONLY, per the advisor doctrine: it informs, it never steers. No
recommendation, no proposal, no pressure word, no date. Read-only end to end —
nothing here can mutate machine state and there is no route from the display
back into the trading path.

THE SLICE DESIGN (ruled 2026-09-17). Each account writes its OWN slice into its
OWN prefix; the serving layer assembles the pinned `accounts[]` array at read
time. The alternative — one account writing a whole-fleet object — cannot work
and would not be honest if it did: the accounts run in separate containers with
separate prefixes at separate times (09:45 / 09:50 / later), so no account can
see today's result for its siblings, and whichever wrote last would overwrite
the others. A single writer guessing for absent siblings is the sibling-number
tell in the one surface the user actually looks at. With slices, an account that
did not run today carries its own stale `run_date` and grays itself out on its
own evidence.

`canonical` is load-bearing for the same reason: the app grays a non-canonical
day rather than showing stale-as-fresh. The silent-wrongness rule, extended to
the user's pocket.

`[NN-FAIL-CLOSED]` in the numbers: a position whose price is missing makes
`tier_equity` UNKNOWN (null), never a partial sum that looks like a total. A
missing mark is reported as missing, never marked at a guess.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "fleet_mirror/v1"
SLICE_REL = "data/state/fleet_mirror_slice.json"

# Display names. Deliberately descriptive of the STRATEGY, not of the broker
# account, because the strategy is what the number means.
DISPLAY_NAMES = {
    "trend_sleeve": "Trend Sleeve",
    "deploy_candidate": "Deploy Candidate",
    "llm_analyst": "AI Analyst",
}


@dataclass(frozen=True)
class MirrorSlice:
    payload: Dict[str, Any]

    def write(self, root: str) -> Path:
        p = Path(root) / SLICE_REL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.payload, indent=2, sort_keys=True, default=str))
        return p


def _round(x: Optional[float], n: int = 2) -> Optional[float]:
    return None if x is None else round(float(x), n)


def build_slice(*, account_id: str, strategy: str, run_date: str, as_of: str,
                canonical: bool, positions: Dict[str, int],
                closes: Dict[str, float], tier_cap: float,
                tier_cash: Optional[float] = None,
                prev_tier_equity: Optional[float] = None,
                basis_dollars: Optional[float] = None,
                vs_spy_at_tier: Optional[float] = None) -> Dict[str, Any]:
    """One account's slice of `fleet_mirror/v1`.

    `tier_equity` is the number: positions x prices + tier cash. NOT the broker's
    equity — `sleeve_equity` in the family trackers is broker equity by fleet
    convention (~$100k), and reading it here would reintroduce the exact number
    this surface exists to replace.
    """
    rows: List[Dict[str, Any]] = []
    unpriced: List[str] = []
    invested = 0.0
    for tkr, qty in sorted((positions or {}).items()):
        q = int(qty)
        if q == 0:
            continue
        last = (closes or {}).get(tkr)
        if last is None:
            unpriced.append(tkr)
            rows.append({"ticker": tkr, "qty": q, "last": None, "value": None})
            continue
        val = q * float(last)
        invested += val
        rows.append({"ticker": tkr, "qty": q, "last": _round(last),
                     "value": _round(val)})

    # Cash INSIDE the tier — what the tier has NOT deployed. Never the broker's
    # cash balance, which carries the ~$90k the machine may not touch.
    #
    # CAUGHT IN THE FIRST SMOKE RUN, and worth the comment because it shipped a
    # plausible constant: deriving cash as `tier_cap - invested` makes
    # tier_equity == invested + (tier_cap - invested) == tier_cap, ALWAYS. The
    # headline number would have been the tier, frozen, for the life of the app,
    # with day_change and total_change computed off it and equally meaningless —
    # a number that is always exactly right and never true.
    #
    # Tier cash is what the tier did not SPEND: cap minus the BASIS of the
    # positions (their cost), not minus their current market value. Then
    # tier_equity moves with prices, which is the entire point.
    if tier_cash is not None:
        cash: Optional[float] = float(tier_cash)
    elif basis_dollars is not None:
        cash = max(float(tier_cap) - float(basis_dollars), 0.0)
    elif not rows:
        cash = float(tier_cap)          # nothing deployed yet: the tier is all cash
    else:
        cash = None                     # [NN-FAIL-CLOSED] — do not invent it

    if cash is None:
        unpriced.append("(tier cash unknown — no tier_cash and no basis supplied)")

    if unpriced:
        # [NN-FAIL-CLOSED]: a partial sum presented as a total is a wrong number
        # that looks right. The app renders "—" and the reason, not a subtotal.
        tier_equity: Optional[float] = None
        unknown_reason: Optional[str] = (
            f"no price for {', '.join(unpriced)} this session — tier_equity is "
            f"UNKNOWN rather than a partial sum")
    else:
        tier_equity = invested + float(cash)
        unknown_reason = None

    day_change = None
    if tier_equity is not None and prev_tier_equity:
        day_change = _round(tier_equity - float(prev_tier_equity))
    # Total change is measured against CONTRIBUTED CAPITAL (the tier cap), not
    # against the positions' basis. Measuring vs basis double-counts the
    # undeployed residue — with cash = cap - basis, tier_equity - basis credits
    # the tier with cash it merely failed to spend. It read +30.79 on a day the
    # book was actually +9.21. And measuring vs the cap stays correct as
    # contributions grow it, because a contribution raises capital and value
    # together.
    total_change = None
    if tier_equity is not None and tier_cap:
        total_change = _round(tier_equity - float(tier_cap))

    return {
        "id": account_id,
        "display_name": DISPLAY_NAMES.get(strategy, strategy),
        "tier_equity": _round(tier_equity),
        "tier_cap": _round(tier_cap),
        "cash": _round(cash),
        "day_change": day_change,
        "total_change": total_change,
        # null until evaluable — NEVER a fake 0. An unevaluable comparison shown
        # as 0.0 reads as "dead even", which is a claim the record cannot make.
        "vs_spy_at_tier": _round(vs_spy_at_tier, 4),
        "positions": rows,
        "canonical": bool(canonical),
        "run_date": run_date,
        "as_of": as_of,
        "schema": SCHEMA,
        **({"tier_equity_unknown_reason": unknown_reason} if unknown_reason else {}),
    }


def assemble(slices: List[Dict[str, Any]], as_of: str) -> Dict[str, Any]:
    """The serving layer's read-time assembly into the pinned envelope."""
    return {"schema": SCHEMA, "as_of": as_of,
            "accounts": sorted(slices, key=lambda a: str(a.get("id", "")))}
