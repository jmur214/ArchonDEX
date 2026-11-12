---
name: b6-pit-identity-and-price-sources
description: B-6 (T-383) — S&P PIT ticker->CIK identity from Form 3/4/5 symbol chains; the membership file's last-ticker convention; price-file coverage of S&P member-months in each clean source (survivorship holes)
metadata:
  type: project
---

**Membership-file convention (measured 2026-11-11):** `data/universe/sp500_membership_pit.parquet`
lists each company under its LAST ticker for its whole history (LB = L Brands since 1996 though it
was LTD until 2013 while LaBarge used "LB"; WM = Waste Management since 1998 though WaMu used "WM";
PTC 1997–2007 = Parametric, then PMTC; no ACE/NU/LTD/WPO intervals). Bankrupt names carry OTC
suffixes (ABKFQ, BTUUQ, EKDKQ). A symbol's historical user is NOT always the member.

**Identity rule that survived review (scripts/lazy_prices/b6_build_panel.py `decide_months`):**
candidates per (interval, month) = symbol users at t (Form 3/4/5 ISSUERTRADINGSYMBOL first..last,
earliest extended to interval start) + last chain user + live-map CIK, each only while a periodic
FILER (own submissions JSON); pick by insider activity over the whole interval (>=1.5x), tie ->
symbol user; uniqueness: one CIK per member per month, qstrip loses, share classes keep one.
Hard cases verified: CB Chubb Corp->Chubb Ltd 2016-05; MRK old Merck to 2009-08; SUNEQ != Sunoco.
Unresolvable (stay NOT_COVERED): FOXA pre-2019, DXC pre-2017 (CSC), KATE, ATGE, IAC 2006-08.

**Symbol-normalisation traps:** "N/A" split -> "A" (Agilent); "N O G" split on spaces -> "O"
(Realty Income); "M??????" (mis-encoded Japanese name) -> "M" (Macy's). Collapse spaces, reject
pieces with non [A-Z0-9.-], catch null markers before splitting.

**Price-FILE coverage of S&P member-months (file names only):** T-265 Alpaca TR 83.4% (2016) ->
96.5% (2025); data/processed 64.7% (2005), 86.8% (2016), 96.4%+ (2020+) — the canonical cache is
itself survivorship-truncated pre-2016, separately from the dividend-era HIGH. Missing names are
mostly acquired members (CELG, RHT, AET, TWX, MON).

**Text-panel census (COMPLETE S&P panel, 46,040 filings, 2026-11-12):** 6.7% of 10-Ks keep MD&A
only in an Exhibit-13 annual report (13.7% in the old-line low-CIK first sample — a CIK-ordered
partial fetch is NOT representative); 11.0% of 10-Qs have NO Part II Item 1A (Abbott — witnessed)
and where present it flips one-liner <-> full list -> rank 10-Qs on MD&A (98.1% carve, 91.7% pairs).
10-K risk OK 95.9%, both 90.3%, combo pairs 83.2% (2007–25). Usable ranking names per quarter-end
2016–25: 430–487 (86–97% of members; March lowest). Store ~7 MB per 1,000 filings (zstd).
**Fetch lessons:** 46k docs took ~9 h at ~1.3–1.7 docs/s serial (latency-bound); a local DNS blip
killed all 37 filings of one CIK (Cisco) past the backoff — always keep a `--retry-failed` path and
a reader that prefers the successful row; never accept a permanent drop for a transient error. The
Mac's free disk swings by GBs/hour (an Xcode build in /private/tmp, other agents' substrate
candidates, swap) — make every long fetch resumable with a per-batch disk floor.

**Phase-2 outcome (2026-11-12):** the frozen S&P gate HALTED at its own census before any return —
13 of 40 rebalances below the 80%-of-members floor (min 67.9%, 2016-Q1): text was fine (86–97%),
T-265 simply has no bars for acquired members. I had written that floor into the draft using each
coverage SEPARATELY (text 86%+, price files 83%+), never their JOINT rate at each rebalance. Lesson:
before a coverage floor is frozen, compute the JOINT census of every eligibility condition per
rebalance; a ticker join does not rescue missing bars. Never run the sensitivity first when the gate
halts — a sensitivity result seen before the gate ruling is a forking path.

**S&P arm RESULT (gate window (c) 2020-Q2→2025-Q4, 69 months; verdict
docs/Audit/b6_lazy_prices_verdict_2026-11-12.md):** H1 NOT MET — similarity Δlog wealth −0.027
(ci_low −0.116), Δtone −0.041; short-leg t_HAC −0.77 / −1.29 (changers did NOT underperform, wrong
sign). YoY filing similarity and LM tone change carry NO detectable return information in large caps
here (all variants: TF/TF-IDF/Jaccard, MD&A-only). Most of the satellite's shortfall was the EW-vs-cap
tilt in 2023–25, not the signal — any EW long leg gated vs SPY needs an EW-universe twin. Long-leg
turnover ~72%/qtr (similarity), ~94% (Δtone): the ranks are unstable. One of 8 diagnostics, the
ADJACENT-quarter 10-Q pairing, gave short-leg t_HAC +2.27 — multiplicity-exposed (Bonferroni over 8
needs ~2.7); a nomination for its own prereg only if T-265 agrees.

**Review (2026-11-12) of the S&P run — NOT READY until corrected:** my harness booked ANY price-file
end as an index exit (§7.7 required a recorded deletion or HALT): of 58 "exits" ~23 were TRUNCATED
data/processed files of live members (AVGO, NVDA 2024-06, ANET …) and 8 renames; BRK-B/BF-B never
matched BRK.B_1d.csv; FB/INFO files are other securities. Fix that held: resolve each name-quarter from
bar DATES + membership (processed if it covers; else T-265 by CIK; else exit only at a recorded
deletion −10/+45 d; else HALT), manifest every source/cause. Shared T-265 tickers fill only when the
date-aware holder (Form 3/4/5 symbol use ±90 d) is unique = this CIK (AMENDMENT 4; AVGO by date).
Corrected S&P (c): similarity −0.028 (ci_low −0.117), Δtone −0.037; short-leg t −0.72 under the
same-quarter pairing but +2.23 under the ADJACENT 10-Q pairing — the refutation half depends on the
pairing choice; a negative-screen candidate. **A file end is not an exit; reconcile before booking.**

**How to apply:** any S&P PIT study must map identity per month (never the live ticker map) and
census price coverage per year before choosing a window; a long-leg pass on these sources is an
upper bound; a short-leg null is biased toward zero. See [[t237-lazy-prices-parse-similarity]].
