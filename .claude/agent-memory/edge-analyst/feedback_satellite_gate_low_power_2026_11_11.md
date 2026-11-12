---
name: satellite-gate-low-power
description: Statistical trap — the 25%-satellite Δ log wealth paired ci_low > 0 gate over ~10 years only detects an arm beating SPY TR by ~10–16%/yr; state the MDE in every prereg that uses it
metadata:
  type: feedback
---

Arithmetic (B-2 prereg §8.1, 2026-11-11): Δ log wealth ≈ Σ 0.25·(r_arm − r_SPY). At 20%/yr tracking
error, sd(monthly Δ) ≈ 1.44% and SE over 111 months ≈ 15%. ci_low > 0 needs a point of about +30% total,
which means the arm must beat SPY by roughly 10–16%/yr net. 2016–2025 makes this worse for small-cap
sleeves: IWM TR trailed SPY TR in 8 of 10 years.

**Why:** a null on this gate means "not demonstrable at this length", not "no edge". An event-study
t_HAC on hundreds of events is far more powerful. Reporting the satellite null as a refutation of the
anomaly overstates it.

**How to apply:** put a minimum-detectable-effect line in every prereg that gates on the satellite
ci_low. Keep the event or IC statistic as the informative instrument, and word refutations by which
instrument failed. See [[t265-panel-not-survivorship-complete]].
