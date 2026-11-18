---
name: feedback-paper-probe-taker-only
description: Paper/forward probes can honestly test only TAKER rules (fill at a displayed quote and size); maker edges need real money. Also check the source paper's own latest-year slice for decay.
metadata:
  type: feedback
---

A paper record can honestly test only taker rules. A taker fills at a displayed ask, up to the displayed size. A maker or limit rule's paper fills are invented: queue position and adverse selection are invisible. The T-379 CEF lesson says the same: "paper fills at the quote". If a maker view is recorded at all, use trade-through fills (a later public trade at a worse price proves the resting order would have filled). Those fills are a pessimistic lower bound, and the view is exploratory and never gating.

**Why:** in T-403 the literature's only positive-net cell was the maker side (Bürgi–Deng–Whelan: makers buying ≥ 50c earned +2.6 %; takers lost). The tempting design was to paper-test the maker form, which would have produced an optimistic synthetic number.

**How to apply:**
- For any forward or paper probe design (prediction markets, CEF discounts, passive-order execution ideas), pick the taker form for the gate, or route the maker form to a pre-registered small real-money pilot.
- Before trusting a published anomaly, read the paper's OWN most-recent-year slice. BDW's 2025 coefficient was less than half its 2024 value, and the paper was public Sept 2025 – Mar 2026, so decay after publication is the default expectation.
- See [[project-t403-prediction-markets-2026-11-17]].
