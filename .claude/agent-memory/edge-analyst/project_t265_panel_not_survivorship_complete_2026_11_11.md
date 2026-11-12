---
name: t265-panel-not-survivorship-complete
description: The T-265 small-cap SIP panel (data/research/t265/) is survivorship-CORRECTED, not complete — ~20% of in-window dead firms priced vs ~79% of live ones; phantom zero-volume bars and ticker-reuse splices; remedy via Form 4 issuer symbols
metadata:
  type: project
---

Measured 2026-11-11 (B-2 / T-381 prereg census, `docs/Sources/prereg_b2_smallcap_t265_2026-11-11.md` §3):

- Of 8,244 EDGAR EPS-frame CIKs filing inside 2016–2026, 3,064 ceased by 2024Q4. **Priced: 19.8% of
  ceased vs 78.9% of continuing**; ceased 2016/17/18 priced only 6.7/3.8/9.6%. The cause is T-265's
  CIK→ticker map, which uses the LIVE SEC ticker list plus Alpaca name-matching.
- In the $1M–$200M dollar-ADV band, the observed death rate is 0.2–0.4%/yr in 2016–18 and 2023–25 and
  2.8–4.1% in 2020–22. A complete panel should show mid-to-high single digits.
- Price-file artefacts: 151 files carry trailing ZERO-VOLUME phantom bars forward-filled flat (45 run
  to 2025-03-21). 141 files have interior no-trade runs ≥ 63 days, which are ticker-reuse splices (EDR =
  Education Realty then Endeavor; MBLY). Always define a death as the last bar with volume > 0, and split
  files into segments at long gaps.
- Prices are Alpaca `adjustment='all'`, i.e. TR-consistent with the `tr_reconciled` twins (verified on
  AAPL and MO). The twins end 2026-05-22.

**Why:** the brief called it "survivorship-complete". Any small-cap PASS on it is an upper bound. A FAIL
stands a fortiori (in the literature's direction).

**How to apply:** pre-register the asymmetric interpretation for any test on T-265. The remedy:
`ISSUERTRADINGSYMBOL` in the SEC Form 345 zips recovers a ticker for 2,097 of 2,457 dead, unpriced CIKs
(1,993 are new symbols). That would need a one-time SIP fetch, which is a user/director call. See
[[form4-zips-are-the-cik-source]] and [[satellite-gate-low-power]].

Used by B-2 (T-381). Both arms FAILED on it, so under the asymmetric rule the FAILs stand. See
[[b2-smallcap-verdict]].
