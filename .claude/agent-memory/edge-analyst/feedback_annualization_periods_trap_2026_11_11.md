---
name: annualization-periods-trap
description: Statistical trap found in T-249 — MetricsEngine.sharpe_ratio/sortino_ratio default periods=252; passing MONTHLY returns with 252 inflates Sharpe/Sortino and their CIs by √21 = 4.58x
metadata:
  type: feedback
---

`MetricsEngine.sharpe_ratio(r, rf, periods=252)` and `sortino_ratio` multiply by √periods.
`scripts/smallcap_momentum_gauntlet_t249.py` set `TD=252` and fed month-end returns. Its published
"gross Sharpe 3.21 / net 2.47 / Sortino ci_low 0.49" are really 0.70 / 0.54 / 0.11. Its audit then
blamed the implausibly high Sharpe on survivorship, so the prose verdict was built on an arithmetic
error.

**Why:** an implausible Sharpe (above 2 for a diversified long-only equity book) is the tell. Check the
annualization before inventing a cause for it.

**How to apply:**
- In any harness, pass `periods = 12` for monthly series and 252 for daily, explicitly.
- When quoting a prior audit's Sharpe, grep its script for the `periods` argument against its return
  frequency.
- Bootstrap CIs scale the same way, so they are inflated identically and do not reveal the error.
- See [[b2-smallcap-verdict]].
