---
task_id: T-402
title: Where the real money would live if it were automated
date: 2026-11-17
type: DESIGN STUDY (public web pages only; no account opened, no form started, no quote requested)
status: PROPOSAL. Nothing built or run. N_trials 0.
---

# T-402: where an automated Roth would live, and what certain dollars ride on the choice

**Summary.** Three venues can plausibly run the system's daily job unattended inside a Roth IRA:
**Alpaca** (works today; pays nothing), **Public** (official free API that names IRAs; pays 1 % on
the transfer, spread over five years, plus 1 % on contributions) and **Webull with Premium** (pays the
most, but its API token dies after 15 idle days and a human must type an SMS code to revive it). The
biggest incentives at brokers with no usable IRA API are Robinhood Gold's 3 % contribution match and
E*TRADE's bonus. Taking either one means giving up automation. The money is small and does not grow
with the account. Contribution matches stop at the $7,500 limit (at most about $220 a year net of the
subscription), and transfer bonuses are a one-off 1 %. The project audit's "roughly 1–3 %" is right
for the rates, but 3–3.5 % applies only to the $7,500 contribution. The transfer rate is 1 %
(E*TRADE's flat-dollar tiers work out to 0.6–1.5 % at these sizes).
Staying at Schwab self-directed pays $0. Its API needs a browser login every seven days.

**Markers.** **[S n]** = source n at the end, read 2026-11-17. **UNCONFIRMED** = third-party page or
search excerpt, not the broker's own terms. **[R]** = recalled, not checked today. **[REPO]** = this repo.
**†** = needs the broker's or a tax professional's confirmation before acting.

## 1. Decision table

Assumptions (mine): the whole Roth moves from Schwab by ACATS at the stated size, and one $7,500
contribution is made each year at the new venue. Schwab charges $50 for a full transfer out [S8], and
that $50 is deducted unless the venue reimburses it. Subscriptions are priced per year. Trading cost
assumes about 250 orders a year (roughly one a day). "Year 1" is the first 12 months after the move.

**Certain dollars (bonus − fees − subscription), $ per year:**

| Venue | $10k, yr 1 | $25k, yr 1 | $50k, yr 1 | Each later year | 5-yr total at $10k / $25k / $50k |
|---|---|---|---|---|---|
| **Alpaca** | 0 (−50 if its transfer credit is gone) | 0 | 0 | 0 | 0 / 0 / 0 |
| **Public** | +45 | +75 | +125 | +95 / +125 / +175 (yrs 2–5), then +75 | +425 / +575 / +825 |
| **Webull + Premium** | +273 | +423 | +673 | +223 while Premium is kept and terms last | +1,163 / +1,313 / +1,563 |
| Webull, no Premium | +25 | +25 | +25 | +75 ("limited-time") | — |
| Robinhood + Gold | +215 | +365 | +615 | +165 | +875 / +1,025 / +1,275 |
| Robinhood, no Gold | +125 | +275 | +525 | +75 | +425 / +575 / +825 |
| E*TRADE (RETIRE26) | +100 | +250 | +250 | 0 | +100 / +250 / +250 |
| tastytrade | −50 to −75 | same | same | 0 to −25 | — |
| Schwab self-directed | 0 | 0 | 0 | 0 | 0 |
| IBKR Pro | about −140 | same | same | about −90 | — |
| Tradier | about −170 | same | same | about −120 | — |

Only year 1 is close to certain. Every later-year figure assumes terms that the broker can end at any
time without notice. Public is the partial exception: the payment schedule for a deposit that has
already settled is fixed on its settlement date [S32 §4(j)].

**Automation and lock-in:**

| Venue | Can an unattended daily job trade the IRA? | Lock-in |
|---|---|---|
| **Alpaca** | **Yes.** Same Trading API the paper fleet uses [S16]. Static keys [REPO, R] | None. $25 to leave [S20] |
| **Public** | **Probably.** Official, free, no approval; the API page says "IRA" [S33]. Key lifetime not stated | Low. A withdrawal stops future installments; paid amounts stay (barring fraud or bad standing). $100 to leave [S37] |
| **Webull** | **Fragile.** Official API, 1–2 day approval. Token dies after 15 days with no calls; reviving it needs an SMS code within 5 minutes [S44]. IRA order placement not stated | 5-year hold, 1-year Premium. $75 to leave [S43] |
| Robinhood | **No.** No official API for IRAs. Agents trade only a separate individual account [S28, S29] | 5-year hold; fee = the match. Gold 1 year or lose ⅔ of the Gold match [S26]. $100 to leave (UNCONFIRMED) [S30] |
| E*TRADE | **No.** Token dies at midnight ET and after 2 idle hours; renewal needs a human login [S47] | 12-month hold; the bonus is clawed back [S46] |
| tastytrade | **Yes.** Personal refresh token never expires [S53]. IRA by API probable, not stated [S54] | None. $75 ACATS + $60 IRA closing [S51] |
| Schwab | **Fragile.** Refresh token lasts 7 days; a browser login every week (UNCONFIRMED) [S13]. IRA by API: third-party reports yes [S14] | None |
| IBKR | **Fragile.** IBKR Pro only; whole shares only. Gateway login needs a browser; sessions reset at midnight [S57–S59] | None |
| Tradier | Probably (API on every plan [S63]); IRA by API not stated | $60 termination + $75 ACATS [S63] |
| Fidelity | **No.** No retail trading API (UNCONFIRMED) [S66] | n/a |

## 2. The verdict, plainly

1. **Alpaca: the automation default.** It costs nothing and pays nothing. Its undated "$50 transfer
   credit" for transfers of $10,000 or more [S21] would cover Schwab's $50 fee. It is the only venue
   where the exact code path already runs every day [REPO]. Open question: Alpaca's IRA pages never say
   whether fractional or notional orders work in a live IRA [S16, S24].
2. **Public: the only venue with both a stated IRA API and a no-subscription incentive.** It pays
   $45–125 in year 1 and $425–825 over five years. Two checks first, both on a tiny live account: that
   an order posts to the Roth through the API, and that the secret key does not expire [S40].
3. **Webull with Premium: the most money, the weakest automation.** It pays $273–673 in year 1. One
   missed 15-day window, or any token loss, halts the job until a human types an SMS code. The 5-year
   hold turns a broken API into a choice between paying back the match and running the Roth by hand.

**The forced choice.** Robinhood Gold (3 % on contributions) and E*TRADE (a $150–300 bonus) are bonus
venues without automation. Robinhood's only official automation is an AI-agent channel. It trades a
separate individual account, not an IRA [S29]. Its unofficial APIs are reverse-engineered. Taking
either bonus means running the Roth by hand.

**Scale.** At $10k, Webull's year-1 haul (about $270) is 2.7 % of the account. That is more than the
1 %/yr alpha the program is hunting, and its sign is known. At $50k it is 1.3 % once, then about
0.45 %/yr. The gap between Alpaca and the best automatable venue is $45–675 in year 1 and about
$95–225 a year after that. One silent outage of the kind this fleet has had before costs more than that.

## 3. Moving out of the Schwab robo

- **Convert in place, no sale: probably yes †.** Schwab's Intelligent Portfolios brochure (dated
  2026-10-15) says clients "may terminate enrollment from the Program at any time." It also says
  "that account will have its own sweep feature" and "will no longer be managed" [S6]. The account
  survives unmanaged. The brochure does not say in words that the positions stay. One forum user
  reports they did (UNCONFIRMED) [S15]. Confirm by phone before acting.
- **ACATS out:** the April 2026 pricing guide lists full transfer $50 per account and partial $0 [S8].
  Whether moving every position counts as "partial" is Schwab's call †. The robo buys whole ETF shares
  (the brochure cites "the inability to buy or sell at least one share of an ETF") [S6], so the whole
  account can move in kind. Schwab liquidates fractional shares on a transfer [S12].
- **Selling inside an IRA has no tax effect.** "Under § 408(e)(1), generally, an individual retirement
  account is exempt from taxation" [S4]. Tax arises only on distribution, and qualified Roth
  distributions are tax-free. **If the robo account is taxable, not the Roth, every sale is a taxable
  event; move it in kind.**
- **Move by trustee-to-trustee transfer (ACATS), not a 60-day rollover.** A direct transfer "is not a
  rollover" and is outside the one-rollover-per-year limit (IRS release, excerpt) [S5].

## 4. Rules that bind the comparison

- **2026 limit: $7,500** ($8,600 at 50+), or taxable compensation if less [S1, S2]. **2027: still
  $7,500**, catch-up still $1,100 (IR-2026-136, 2026-11-12) [S3]. Contribution matches therefore stop at
  $262.50 (3.5 %), $225 (3 %) or $75 (1 %) a year.
- **Does a broker "match" count as a contribution?** Every broker that states a position says no.
  Robinhood: the match "will not be subject to, or impact, the maximum annual dollar contribution
  limit" [S26]. Public treats it as interest that "does not impact" the limit [S32 §7]. Webull treats it
  as IRA interest [S41]. E*TRADE characterizes it as "interest or other earnings" [S46]. **I found no
  IRS ruling either way.** This is the brokers' characterization. All of them warn that a match may be
  taxable in a backdoor-Roth conversion †.
- **Wash sales across accounts (Rev. Rul. 2008-5):** if you sell at a loss in a taxable account and your
  IRA or Roth buys substantially identical stock within 30 days, "the loss on the Sale of stock is
  disallowed" and "A's basis in the individual retirement account or Roth IRA is not increased" [S4].
  The loss is gone for good. This binds only if a taxable account exists. The repo's guard
  (`engines/engine_b_risk/cross_account_wash_guard.py`) works on one account in practice [REPO; T-400].
  Splitting the household across two venues makes that gap real.

## 5. Per-broker facts

### Alpaca
- Roth and Traditional IRAs for Trading API users. "Equities and options … through the same API." Deposits
  and withdrawals are web-portal only. Published 2026-05-13, updated 2026-07-06 [S16]. An active trading
  account is required [S19].
- IRA limits: options up to level 2 [S17]. "Limited margin and shorting is disabled" [S18]. No futures
  are mentioned [S16]. Fractional/notional in a live IRA: **not stated** [S16, S24].
- Fees: commission-free. Outgoing ACATS $25. Inbound free. Fee schedule revised 2026-11-17 [S20]. No
  IRA fee appears in the schedule.
- Incentive: none found. The $50 transfer-fee credit (transfers of $10,000+, first transfer per account
  type and firm, undated, terminable) [S21].
- Rate limit: 200 requests/min per account (support page, excerpt only) [S22].

### Public
- Traditional and Roth IRAs. "Trade through cash, margin, IRA, or business accounts." "Available to all
  Public members—no approval required." Free. For "personal, non-commercial use" [S33].
- API: a secret key is exchanged for an access token with a validity you choose. The page does not
  say whether the secret key expires [S34, S40]. Rate limit 10 requests/s [S34]. Market and limit
  orders take a fractional quantity or a dollar `amount`; the fractional minimum is $5 [S34, S35, S39].
  The accounts endpoint "includes brokerage, retirement" accounts [S36].
- Fees: $0 on US stocks and ETFs. Outgoing ACATS $100. Fee schedule updated 2026-10-13 [S37].
- **Match terms** (one T&C file, dated 2026-10-13, served at three URLs) [S32]:
  - 1 % on contributions, paid in 12 monthly installments.
  - 1 % on IRA transfers, no cap, paid in 60 monthly installments.
  - No subscription required.
  - The portion of a contribution above the annual limit is excluded.
  - Offer periods: contributions from 2025-03-24, IRA transfers from 2026-09-14. Both run "until
    such time as Public Investing shall end this Offer Period … without notice." No expiry date.
  - Leaving: any withdrawal or transfer out "can reduce future Monthly Match Payments." Closing the
    account ends payments. Nothing already paid is clawed back, except for errors or fraud.
  - Tax: treated "as interest earned," not counted toward the limit.
- Old-broker fee reimbursement (up to $100): tied to a 2025 promotion. Current scope unclear [S38].

### Webull
- Traditional, Roth and Rollover IRAs (account-list enum) [S44].
- **Match** [S41]:
  - Premium: 3.5 % on contributions ("ongoing") and 1 % on transfers ("limited-time"). The transfer
    match is capped at $2,500 on $250,000.
  - Non-Premium: 1 % on contributions ("limited-time"), no transfer match.
  - Conditions: "Maintain Webull Premium for 1 full year." The contribution or transfer must stay in
    the account "a minimum of five years." The match is credited in 2–3 business days and treated as
    IRA interest.
  - No end dates are given. The exact fee if you leave early is in the full T&C, which I did not read
    (UNCONFIRMED).
  - An older 2024 promo page is stale [S45].
- Premium price: $3.99/month or $40/year [S42].
- Fees: $0 commissions for IRAs. Outgoing stock transfer $75 [S43].
- API:
  - Products: stocks (fractional, short selling), options, futures and crypto [S44].
  - Access: retail individuals apply; review takes 1–2 business days [S44].
  - Token: becomes INVALID after "no API calls made for 15 consecutive days." A new one must be
    verified by SMS code in the app within 5 minutes [S44].
  - Rate limits: Place Order 600/60 s; Account Balance 2/2 s [S44].
  - IRA: the account-list enum includes ROTH_IRA [S44]. Order placement in an IRA is **not stated**.

### Robinhood
- **Match** [S25, S26]:
  - Contributions: 3 % with Gold ($5/month), 1 % without.
  - Transfers and rollovers: 1 %, no Gold needed, no cap.
  - Five-year earn-out: the fee for removing matched money early equals the match.
  - Gold: cancel within one year and pay a fee of ⅔ of the match. The Gold T&C file is dated
    2026-07-28.
  - Not counted toward the limit.
  - A 2 % transfer bonus ended 2026-10-09 [S27].
- API:
  - None official for IRAs.
  - Agentic Trading (since 2026-05-27) works through an MCP server. "Your agent can only place trades
    in your Robinhood Agentic account," which is "a type of self-directed individual investing
    account" [S28, S29].
  - Unofficial libraries reverse-engineer private endpoints [R].
- Options in IRA: limited, no spreads (UNCONFIRMED) [S72]. Outgoing ACATS $100 (UNCONFIRMED) [S30].

### E*TRADE (Morgan Stanley)
- **RETIRE26** [S46]:
  - For new clients. Open by 2027-02-28 and fund within 60 days.
  - Tiers: $1k–4,999 → $50; $5k–19,999 → $150; $20k–99,999 → $300.
  - Hold for 12 months after the funding window. Otherwise "your cash credit(s) will be surrendered."
  - Covers Roth, Traditional and Rollover IRAs. Lifetime maximum of three new-account offers.
  - No subscription. $0 stock and ETF commissions.
- API: an individual key is available (UNCONFIRMED excerpt) [S48]. The token "expires at the end of
  the current calendar day, US Eastern time" and is "inactivated" after two hours without requests
  [S47]. Account types include ROTHIRA (excerpt) [S48]. Fractional orders via API: not found.

### tastytrade
- Traditional, Roth and SEP IRAs [S49].
- IRA trading levels [S49]:
  - Futures need "IRA The Works."
  - Naked calls need The Works plus $25,000 net liquidation.
  - Not allowed: short stock, borrowing, crypto.
- Fees: stocks and ETFs $0 plus $0.0008/share clearing. Fractional $0 plus $0.10 per transaction.
  Annual IRA fee free. IRA closing $60. Outgoing ACATS $75. PDF updated 2026-10-28 [S50, S51].
- **Bonus: none for IRAs.** SWEETBONUS ($50–2,000) excludes "IRAs (including Traditional, Roth, and
  SEP)." Its deposits run 2026-10-01 to 11-30 and the money is held 12 months [S52].
- API: personal OAuth; "Refresh tokens are long-lived and do not expire." Access tokens last 15 minutes
  [S53]. The order types include "Notional Market" [S55]. The docs say a customer's accounts include
  "a retirement account" [S54]. IRA order restrictions via API are not stated.

### Interactive Brokers
- Cash or margin IRAs, Roth included [S56]:
  - No borrowing and no short stock.
  - Futures allowed, at margin up to twice the non-IRA overnight requirement.
  - No MLPs.
  - No custody fees.
- API [S57–S60]:
  - Individuals: "The live account must also be of the 'IBKR Pro' type."
  - Since 2026-10-30 the gateway blocks LITE accounts and fractional orders.
  - Login: browser on the same machine as the gateway. Sessions last at most 24 hours and reset at
    midnight.
  - TWS/IB Gateway alternative: a daily auto-restart and a weekly two-factor login (IBKR doc, excerpt)
    [S61].
- Commission: Pro tiered $0.0035/share, minimum $0.35 per order. Fixed: $0.005/share, minimum $1.00
  [S60].
- Bonus: none found. IRA closing and transfer-out $0 (UNCONFIRMED) [S62].

### Tradier
- IRA offered [S63].
- Plans: Lite $0/month ($0.35 per stock trade, $30/yr IRA fee). Pro $10/month ($0 trades, IRA fee
  waived). Pro Plus $35/month.
- API access on every plan. IRA termination $60. Outgoing ACATS $75. Inactivity $50/yr under 2
  trades.
- Fractional shares are not mentioned. Bonus: none found.

### Schwab (self-directed, staying)
- IRAs: $0 opening, maintenance and minimum [S9].
- Options $0.65/contract. Futures $2.25/contract [S9]. Futures in an IRA need $25,000 net liquidation,
  at 125 % of initial margin [S11].
- Fractional shares in 7,000+ stocks and ETFs [S12]. Whether that works through the API, or in an IRA,
  is not stated.
- **Bonus: $0.** The referral offer is only for people who "do not currently have a Charles Schwab &
  Co., Inc. ('Schwab') account" and only for "outside assets new to Schwab" [S10].
- API: approval for "Trader API – Individual." 30-minute access tokens; the refresh token is "only good
  for seven days" with "no way to make a refresh token last longer" (schwab-py docs, UNCONFIRMED) [S13].
  The developer portal renders by script and I could not read it. Third parties say IRAs are tradable
  through the same login (UNCONFIRMED) [S14].

### Others checked
- **Fidelity:** Roth offered. No retail trading API (UNCONFIRMED) [S66]. No current IRA bonus found.
- **Composer:** IRAs. Full API only on Pro at $384/yr [S67]. That costs 0.8–3.8 %/yr at these sizes,
  more than any match.
- **TradeStation:** IRA $35/yr. Termination $50. Outgoing transfer $125 [S64]. Refresh tokens are
  "valid indefinitely" by default (excerpt) [S65]. Bonus not checked.
- **SoFi:** a 1 % IRA match (excerpt) and no API [S68].
- **moomoo:** reviews say no US IRA (UNCONFIRMED) [S69].
- **Ally Invest:** API reported retired (UNCONFIRMED) [S70].
- **Firstrade:** a 3 %/2 % IRA offer that has expired (third-party) [S71].

## 6. Options and futures in the IRA

| Venue | Options in IRA | Futures in IRA | Via API |
|---|---|---|---|
| Alpaca | up to level 2 [S17] | not offered [S16] | options: yes [S16] |
| IBKR | yes [S56] | yes, about 2× margin [S56] | yes, Pro only [S57] |
| tastytrade | yes; spreads at Basic IRA [S49] | yes, "IRA The Works" [S49] | API trades futures; IRA not stated |
| Schwab | yes [R] | yes, $25k NLV [S11] | API trades options, not futures (excerpt; T-400) |
| Webull | up to level 2 (UNCONFIRMED) [S72] | not found | API lists options and futures; IRA not stated |
| Robinhood | limited, no spreads (UNCONFIRMED) [S72] | not found | no IRA API |
| Public | API trades options [S34]; IRA level not found | not found | yes, if IRA orders work |

## 7. What I could not confirm

1. Whether the robo account **is** the Roth. Every IRA-transfer number above assumes it is.
2. Alpaca: fractional/notional orders in a live IRA. Whether the $50 transfer credit is still live.
3. Public: whether an API order actually posts to a Roth (the page says "IRA" but the order docs are
   silent). Secret-key lifetime.
4. Webull: IRA order placement via the API. The exact early-removal fee. End dates of the two
   "limited-time" rates.
5. Schwab: Trader API coverage of IRAs. The 7-day refresh token (both third-party). Fractional orders
   via API. Whether de-enrolling keeps positions untouched (brochure implies; does not state). Whether
   a "partial" ACATS of every position escapes the $50.
6. tastytrade and Tradier: IRA order placement via the API.
7. Robinhood's $100 ACATS fee and IRA options level. IBKR's $0 IRA closing and transfer fees.
8. IRS treatment of broker matches: no ruling found. The brokers' position only †.
9. E*TRADE's outgoing transfer fee (not checked). Whether the owner counts as a "new client" anywhere.

**Owner questions:**
- Is the robo account the Roth?
- Has the 2026 contribution already been made?
- Any past account at Public, Webull, E*TRADE or tastytrade (new-client conditions)?
- Is a weekly browser login (Schwab) or an occasional SMS code (Webull) acceptable, or must the job
  run with no human at all?

## Sources (all read 2026-11-17)

Pages fetched in full unless marked "excerpt" (search-result excerpt only) or "third-party."

**IRS**
1. IR-2025-111 / Notice 2025-67: irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500
2. IRA contribution limits (page reviewed 2026-09-23): irs.gov/retirement-plans/plan-participant-employee/retirement-topics-ira-contribution-limits
3. IR-2026-136, 2027 limits (2026-11-12): irs.gov/node/167581
4. Rev. Rul. 2008-5, full text: irs.gov/pub/irs-drop/rr-08-05.pdf
5. IR-14-107, excerpt: irs.gov/pub/irs-news/IR-14-107.pdf

**Schwab**
6. Intelligent Portfolios Disclosure Brochure (2026-10-15): disclosures.schwab.com/SchwabDashboard/63969/REG83246.pdf (linked from schwab.com/resource/schwab-intelligent-portfolios-solutions-disclosure-brochure)
7. Automated investing FAQ: schwab.com/automated-investing/faqs
8. Pricing Guide for Individual Investors (April 2026): schwab.com/legal/schwab-pricing-guide-for-individual-investors
9. Pricing: schwab.com/pricing
10. Referral offer: schwab.com/client-referral
11. Futures FAQ: schwab.com/futures/faqs
12. Fractional shares: schwab.com/fractional-shares-stock-slices
13. Third-party, schwab-py auth docs: schwab-py.readthedocs.io/en/latest/auth.html
14. Third-party excerpts: tradelabs.org/docs/reference/brokers/schwab/ ; medium.com/@avetik.babayan/why-charles-schwab-api-choosing-the-right-trading-platform-for-automation-bot-6bf6a687bb83
15. Third-party forum, excerpt: bogleheads.org/forum/viewtopic.php?t=364152

**Alpaca**
16. IRA blog (2026-05-13, updated 2026-07-06): alpaca.markets/blog/alpaca-introduces-individual-retirement-accounts-for-trading-api-users/
17. alpaca.markets/support/can-ira-trade-options
18. alpaca.markets/support/can-ira-trade-on-margin-short
19. alpaca.markets/support/i-have-a-trading-account-at-alpaca-can-i-open-my-ira-account
20. Fee schedule (revised 2026-11-17): files.alpaca.markets/disclosures/library/BrokFeeSched.pdf
21. ACATS promotions T&C (undated): files.alpaca.markets/disclosures/library/ACATS+Promotions+Terms+%26+Conditions.pdf
22. Excerpt: alpaca.markets/support/usage-limit-api-calls
23. Broker API IRA doc (Broker API, not Trading API): docs.alpaca.markets/docs/ira-accounts-overview
24. alpaca.markets/support/fractional-shares

**Robinhood**
25. robinhood.com/us/en/support/articles/ira-match-faq/
26. Gold IRA Contribution Match T&C (file 2026-07-28): cdn.robinhood.com/assets/robinhood/legal/Gold%20IRA%20Match%20T%26Cs.pdf
27. robinhood.com/us/en/support/articles/2026-september-retirement-match/
28. robinhood.com/newsroom/robinhood-is-now-open-to-agents/
29. robinhood.com/us/en/support/articles/agentic-trading-overview/
30. Excerpt: robinhood.com/us/en/support/articles/transfer-stocks-out-of-your-robinhood-account/
31. Third-party: finder.com/stock-trading/robinhood-agentic-accounts

**Public**
32. ACATS & IRA Match Program T&C (file 2026-10-13): public.com/disclosures/matchprogram (same file at /disclosures/ira-match and /disclosures/ira-contribution-match)
33. public.com/api
34. public.com/api/docs/faq
35. public.com/api/docs/resources/order-placement/place-order
36. public.com/api/docs/resources/list-accounts/get-accounts
37. Fee schedule (2026-10-13): public.com/disclosures/fee-schedule
38. help.public.com/en/articles/6499808-transfer-account-bonus
39. public.com/api/docs/changelog
40. public.com/api/docs/templates/get-access-token

**Webull**
41. webull.com/help/faq/11063-Benefits-with-Premium
42. webull.com/help/faq/11064-Subscription-and-Fees
43. webull.com/pricing
44. developer.webull.com/apis/docs/trade-api/overview ; …/authentication/IndividualApplicationAPI/ ; …/authentication/token ; …/reference/account-list.md
45. Stale 2024 promo: webull.com/offers-promotions/ira-transfer-promo

**E*TRADE**
46. us.etrade.com/promo/retirement
47. apisb.etrade.com/docs/api/authorization/get_access_token.html
48. Excerpts: developer.etrade.com/getting-started ; us.etrade.com/l/f/agreement-library/api-developer-licensing-agreement

**tastytrade**
49. tastytrade.com/accounts/ira
50. tastytrade.com/pricing/
51. Commissions and fees PDF (2026-10-28): tastytrade.com/commissions-and-fees/
52. tastytrade.com/sweet-bonus/
53. developer.tastytrade.com/docs/authentication/oauth2/
54. developer.tastytrade.com/docs/concepts/accounts-and-customers/
55. developer.tastytrade.com/docs/guides/place-an-equity-order/

**Interactive Brokers**
56. interactivebrokers.com/en/trading/ira-information.php
57. interactivebrokers.com/docs/web-api/trading/getting-started/trading-access-for-individuals
58. Web API changelog: interactivebrokers.com/docs/web-api/changelog
59. interactivebrokers.com/docs/web-api/authentication/faq.md ; …/authentication/cpgw/limitations-of-the-client-portal-gateway.md
60. interactivebrokers.com/en/pricing/commissions-stocks.php
61. Excerpt: interactivebrokers.com/docs/tws-api/doc/tws-settings/daily-weekly-reauthentication.md
62. Third-party: stockbrokers.com/review/interactivebrokers/ira

**Others**
63. Tradier: tradier.com/individuals/pricing
64. TradeStation: tradestation.com/pricing/service-fees/
65. TradeStation, excerpt: api.tradestation.com/docs/fundamentals/authentication/refresh-tokens/
66. Fidelity, third-party: blog.traderspost.io/article/does-fidelity-have-an-api ; snaptrade.com/brokerage-integrations/fidelity-api
67. Composer: composer.trade/pricing
68. SoFi, excerpt: support.sofi.com/hc/en-us/articles/38104453270285-Invest-1-IRA-Deposit-Match
69. moomoo, third-party: stockbrokers.com/review/moomoo
70. Ally Invest, third-party: blog.traderspost.io/article/does-ally-invest-have-api
71. Firstrade, third-party (expired offer): doctorofcredit.com/firstrade-3-ira-contribution-match-2-transfer-boost/
72. IRA options, third-party: brokerage-review.com/online-trading/options/webull-options-trading.aspx ; firstcard.app/learn/robinhood-options
