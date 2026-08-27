# Advisor surface — 2026-08-26

*Auto-generated. Informational only: this page quantifies options the user
owns. It does not recommend a date, schedule anything, or urge an action.*

## Contribution-rate sensitivity

ASSUMED starting balance **$10,000**, contributions **$7,000/yr**, assumed return **7.0%/yr** — **these are ASSUMPTIONS, not the user's figures**; the wrapper census (pending) replaces them with real balances. The tier matrix below is here precisely so the conclusion does not depend on guessing one number. The last column is the exchange rate that matters: **how much annual alpha would be worth the same as adding $1,000/yr.**

| horizon | terminal (base) | terminal (+$1,000/yr) | difference | = alpha of |
|---|---|---|---|---|
| year 5 | $54,281 | $60,031 | $5,751 | **374 bps/yr** |
| year 10 | $116,387 | $130,203 | $13,816 | **202 bps/yr** |
| year 20 | $325,665 | $366,661 | $40,995 | **99 bps/yr** |
| year 30 | $737,348 | $831,809 | $94,461 | **63 bps/yr** |
| year 40 | $1,547,190 | $1,746,825 | $199,635 | **45 bps/yr** |

*Read the last column against what the research programme has actually
found: every free-data return-frontier probe closed H0, and the one
statistically-significant alpha (CEF discount capture, t_HAC 2.31) has no
retail data path. A contribution increase is certain-sign; an alpha of the
same size is not yet evidenced anywhere in this system.*

### The same exchange rate across capital tiers

*Capital-adaptive (2026-07-02 directive): the surface does not assume one balance. Tier boundaries are the advisor tier table's own.*

| starting balance | year 10 | year 20 | year 40 |
|---|---|---|---|
| $5,000 | 235 bps | 109 bps | 48 bps |
| $10,000 | 202 bps | 99 bps | 45 bps |
| $25,000 | 144 bps | 78 bps | 38 bps |
| $65,000 | 81 bps | 50 bps | 26 bps |

*Each cell: the annual alpha that would match adding $1,000/yr. The smaller the balance, the more a contribution increase dominates — at the tiers this system actually runs at, no plausible edge competes with the contribution rate.*

## Wrapper moves

**Awaiting the wrapper census.** This section is generated from the
user's actual account/wrapper inventory; without it there is nothing to
rank. It is reported as missing rather than filled with generic advice —
a ranked list of moves the user may not be able to make is worse than no
list. *(Input contract below.)*

### Input contract (what the census needs to carry)

| field | meaning |
|---|---|
| `account_type` | roth / traditional / taxable / hsa / 401k |
| `balance` | current dollars |
| `annual_contribution` | current dollars per year |
| `contribution_headroom` | unused annual limit, dollars |
| `employer_match` | match rate + cap, if any |
| `fee_drag_bps` | wrapper/fund expense in bps |
| `constraints` | anything blocking a move (liquidity, vesting, access) |

