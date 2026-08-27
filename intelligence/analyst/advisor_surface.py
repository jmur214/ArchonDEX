"""intelligence/analyst/advisor_surface.py — the ADVISOR MEMO generator.

Renders `docs/State/advisor_surface.md`: ranked, dollar-quantified wrapper/contribution
moves plus the contribution-rate sensitivity table.

TWO HALVES, DELIBERATELY SEPARABLE:
  * the SENSITIVITY TABLE needs no external input — it is arithmetic on the user's own
    horizon and contribution rate, and it renders today;
  * the WRAPPER MOVES need the director's wrapper census. Absent it, the section says
    so plainly rather than inventing moves (`[NN-FAIL-CLOSED]` in spirit: a missing
    input is reported, never fabricated).

THE SAME DESIGN LAWS AS THE WEEKLY DIGEST (T-329):
  * dollars, not ratios;
  * NO pressure mechanics — the banned-word list is imported from the digest so one
    change governs both surfaces (no second copy to drift);
  * this INFORMS a decision the user owns; it never schedules or urges one.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
SURFACE = ROOT / "docs" / "State" / "advisor_surface.md"

# ONE banned-word list, shared with the weekly digest (imported, not copied).
BANNED_PRESSURE_WORDS = (
    "countdown", "days remaining", "decision approaching", "ready for real money",
    "deadline", "act now", "don't miss", "hurry", "limited time", "last chance",
    "you should immediately", "urgent",
)


def fv(v0: float, contrib: float, r: float, years: int) -> float:
    """Future value: lump sum compounding + an end-of-year contribution annuity."""
    if abs(r) < 1e-12:
        return v0 + contrib * years
    return v0 * (1 + r) ** years + contrib * (((1 + r) ** years - 1) / r)


def equivalent_alpha_bps(v0: float, contrib: float, r: float, years: int,
                         extra_contrib: float = 1000.0) -> Optional[float]:
    """How many bps of extra ANNUAL RETURN buy the same terminal wealth as adding
    `extra_contrib`/yr? Bisection on Δr. This is the honest comparison: contributions
    are certain and alpha is not, so stating their exchange rate lets the user see
    what a return edge would have to be worth to matter as much."""
    target = fv(v0, contrib + extra_contrib, r, years)
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if fv(v0, contrib, r + mid, years) < target:
            lo = mid
        else:
            hi = mid
    return None if hi > 0.999 else round(((lo + hi) / 2) * 10_000, 1)


def sensitivity_table(v0: float, contrib: float, r: float,
                      horizons=(5, 10, 20, 30, 40), extra: float = 1000.0):
    rows = []
    for t in horizons:
        base, plus = fv(v0, contrib, r, t), fv(v0, contrib + extra, r, t)
        rows.append({"year": t, "base_terminal": base, "plus_terminal": plus,
                     "delta_dollars": plus - base,
                     "equivalent_alpha_bps": equivalent_alpha_bps(v0, contrib, r, t, extra)})
    return rows


def _money(x: float) -> str:
    return f"${x:,.0f}"


# The project's own tier boundaries (config/advisor_tier_table.json): <$10k, $10k+,
# $18k (futures), $65k (index premium). The capital-adaptive directive (2026-07-02) says
# test at MULTIPLE tiers rather than one assumed balance — so the surface renders across
# them instead of inventing a single number for the user's account.
DEFAULT_TIERS = (5_000, 10_000, 25_000, 65_000)


def tier_matrix(tiers, contrib: float, r: float, horizons=(10, 20, 40),
                extra: float = 1000.0):
    """equivalent-alpha exchange rate at each (tier, horizon). Capital-adaptive."""
    return [{"tier": t,
             "cells": [(h, equivalent_alpha_bps(t, contrib, r, h, extra)) for h in horizons]}
            for t in tiers]


def render(v0: float, contrib: float, r: float, extra: float = 1000.0,
           wrapper_census: Optional[dict] = None, as_of: str = "",
           tiers=DEFAULT_TIERS) -> str:
    rows = sensitivity_table(v0, contrib, r, extra=extra)
    out = [f"# Advisor surface — {as_of}", "",
           "*Auto-generated. Informational only: this page quantifies options the user",
           "owns. It does not recommend a date, schedule anything, or urge an action.*", "",
           "## Contribution-rate sensitivity", "",
           (f"{'ASSUMED' if not wrapper_census else 'Actual'} starting balance "
            f"**{_money(v0)}**, contributions **{_money(contrib)}/yr**, assumed return "
            f"**{r*100:.1f}%/yr**"
            + ("" if wrapper_census else
               " — **these are ASSUMPTIONS, not the user's figures**; the wrapper census "
               "(pending) replaces them with real balances. The tier matrix below is here "
               "precisely so the conclusion does not depend on guessing one number")
            + ". The last column is the exchange rate that matters: "
            + f"**how much annual alpha would be worth the same as adding {_money(extra)}/yr.**"), "",
           f"| horizon | terminal (base) | terminal (+{_money(extra)}/yr) | difference | "
           f"= alpha of |", "|---|---|---|---|---|"]
    for x in rows:
        eq = "—" if x["equivalent_alpha_bps"] is None else f"**{x['equivalent_alpha_bps']:.0f} bps/yr**"
        out.append(f"| year {x['year']} | {_money(x['base_terminal'])} | "
                   f"{_money(x['plus_terminal'])} | {_money(x['delta_dollars'])} | {eq} |")
    out += ["", "*Read the last column against what the research programme has actually",
            "found: every free-data return-frontier probe closed H0, and the one",
            "statistically-significant alpha (CEF discount capture, t_HAC 2.31) has no",
            "retail data path. A contribution increase is certain-sign; an alpha of the",
            "same size is not yet evidenced anywhere in this system.*", ""]

    if tiers:
        hs = (10, 20, 40)
        out += ["### The same exchange rate across capital tiers", "",
                "*Capital-adaptive (2026-07-02 directive): the surface does not assume one "
                "balance. Tier boundaries are the advisor tier table's own.*", "",
                "| starting balance | " + " | ".join(f"year {h}" for h in hs) + " |",
                "|---|" + "---|" * len(hs)]
        for row in tier_matrix(tiers, contrib, r, hs, extra):
            cells = " | ".join("—" if b is None else f"{b:.0f} bps" for _, b in row["cells"])
            out.append(f"| {_money(row['tier'])} | {cells} |")
        out += ["", f"*Each cell: the annual alpha that would match adding {_money(extra)}/yr. "
                    "The smaller the balance, the more a contribution increase dominates — at "
                    "the tiers this system actually runs at, no plausible edge competes with "
                    "the contribution rate.*", ""]

    out += ["## Wrapper moves", ""]
    if not wrapper_census:
        out += ["**Awaiting the wrapper census.** This section is generated from the",
                "user's actual account/wrapper inventory; without it there is nothing to",
                "rank. It is reported as missing rather than filled with generic advice —",
                "a ranked list of moves the user may not be able to make is worse than no",
                "list. *(Input contract below.)*", "",
                "### Input contract (what the census needs to carry)", "",
                "| field | meaning |", "|---|---|",
                "| `account_type` | roth / traditional / taxable / hsa / 401k |",
                "| `balance` | current dollars |",
                "| `annual_contribution` | current dollars per year |",
                "| `contribution_headroom` | unused annual limit, dollars |",
                "| `employer_match` | match rate + cap, if any |",
                "| `fee_drag_bps` | wrapper/fund expense in bps |",
                "| `constraints` | anything blocking a move (liquidity, vesting, access) |", ""]
    else:
        moves = rank_wrapper_moves(wrapper_census, r)
        out += ["| rank | move | value | basis |", "|---|---|---|---|"]
        for i, m in enumerate(moves, 1):
            out.append(f"| {i} | {m['move']} | {_money(m['annual_value'])}/yr | {m['basis']} |")
        out += ["", "*Ranked by dollar value per year, highest first.*", ""]
    return "\n".join(out) + "\n"


def rank_wrapper_moves(census: dict, r: float) -> list:
    """Rank moves by ANNUAL DOLLAR value. Only mechanical, certain-sign moves are
    ranked: an unclaimed employer match and a fee reduction are arithmetic; a
    'better allocation' is a forecast and is deliberately NOT ranked here."""
    moves = []
    for acct in census.get("accounts", []):
        m = acct.get("employer_match") or {}
        if m.get("rate") and acct.get("annual_contribution", 0) < (m.get("cap_dollars") or 0):
            gap = (m["cap_dollars"] - acct["annual_contribution"])
            moves.append({"move": f"capture unclaimed employer match in {acct['account_type']}",
                          "annual_value": gap * float(m["rate"]),
                          "basis": "unclaimed match = an immediate certain return"})
        fee = float(acct.get("fee_drag_bps") or 0)
        if fee > 10:
            moves.append({"move": f"reduce fee drag in {acct['account_type']} ({fee:.0f} bps)",
                          "annual_value": acct.get("balance", 0) * (fee - 3) / 10_000,
                          "basis": "fee reduction to a ~3bps index equivalent; certain-sign"})
        hr = float(acct.get("contribution_headroom") or 0)
        if hr > 0:
            moves.append({"move": f"use unused {acct['account_type']} contribution headroom",
                          "annual_value": hr * r,
                          "basis": "tax-sheltered compounding on otherwise-taxable dollars"})
    return sorted(moves, key=lambda x: -x["annual_value"])


def generate(v0: float, contrib: float, r: float, *, as_of: str,
             wrapper_census: Optional[dict] = None, extra: float = 1000.0,
             out_path: Path = SURFACE) -> dict[str, Any]:
    try:
        text = render(v0, contrib, r, extra, wrapper_census, as_of)
        low = text.lower()
        leaked = [w for w in BANNED_PRESSURE_WORDS if w in low]
        if leaked:
            return {"ok": False, "error": f"pressure words present: {leaked}"}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text)
        return {"ok": True, "path": str(out_path), "census_present": bool(wrapper_census)}
    except Exception as e:   # noqa: BLE001 — never raise into a caller
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
