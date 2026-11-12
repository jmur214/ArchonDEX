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

**How to apply:** any S&P PIT study must map identity per month (never the live ticker map) and
census price coverage per year before choosing a window; a long-leg pass on these sources is an
upper bound; a short-leg null is biased toward zero. See [[t237-lazy-prices-parse-similarity]].
