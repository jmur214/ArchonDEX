---
task_id: T-2026-06-16-178
title: Regime Step 2 — dynamic MF-sleeve SIZER A/B vs always-on 20% (OOS, net-of-cost) + canonical deep-window safe_f
date: 2026-06-16
substrate: 158fe678 26yr base curve + AQR TSMOM (1985-2025); HMM trained 2000-2012, OOS 2013-2025; measurement-only
scope: scripts/ + docs/ ; pre-registered (regime_sleeve_sizer_preregistration_t178_2026_06_16.md). No prod swap, no live path.
outcome: **HONEST CEILING — the dynamic sizer does NOT beat always-on 20% OOS net-of-cost.** Δsharpe +0.03 (raw AQR) / +0.00 (0.5× haircut), and the dynamic arm slightly WORSENS MDD (−0.4pp) and the 2022 grind. The detector's specificity is excellent (the required genuinely-held-out-calm check: p_crisis>0.5 in **0/84** calm 2013-2019 months — zero false alarms, with margin) — so the negative result is NOT a false-alarm problem; it's that the held-out OOS window (2013-2025) was bull-dominated with one brief V-shaped fast crisis (COVID), which is too little of the sizer's intended use case for it to add net value. **Verdict: always-on 20% is the deployable sleeve; the regime timer adds nothing net on the available honest OOS — do NOT deploy it.** Separately: the **canonical deep-window safe_f = 0.928** (live size cap min(1, safe_f) = 0.928; supersedes the benign-2024 1.602 and the 12yr-interim 1.104).
---

# T-178 — Regime Step 2 (sizer A/B) + canonical safe_f

## Canonical deep-window safe_f (the cheap deliverable)

On the canonical 26yr re-anchor base curve
(`data/external/base_curve/t118r_v1_26yr_arm0_3b403882.csv` = 158fe678
arm0, 2000-2025, MDD −32.6%):

| window | MDD | safe_f | live cap min(1,·) |
|---|---:|---:|---:|
| 2024 benign (T-151) | small | 1.602 | 1.000 |
| 12yr crisis-light (T-169 interim) | −16% | 1.104 | 1.000 |
| **26yr deep (the gate)** | **−33%** | **0.928** | **0.928** |

`mdd95@f1` = 21.3% (just over the 20% tolerance → P(DD>20%) = 6.2% > 5%
→ safe_f < 1). The book is **~7% OVERSIZED** at f=1 on the honest deep
window; the eventual live size cap is **0.928**. Monotone-down across
windows exactly as expected.

## The sizer A/B (the main deliverable)

**Design (pre-registered):** HMM trained 2000-2012, applied OOS to
2013-2025 (causal forward filter, crisis state = max-mean-vol, monthly,
lagged 1 month). 2013-2019 = genuinely held-out calm (the T-172
in-sample-FA caveat fixed). Monthly portfolio `(1−x)·base + x·MF − cost`;
**always-on** `x=0.20`, **dynamic** `x = clip(0.20 + 0.25·(p_lag −
0.20), 0.10, 0.40)` (lighter in bull, heavier in crisis). MF = AQR
TSMOM (raw + 0.5× haircut — AQR is optimistic per T-171). Net of 20bps
round-trip on re-sizing turnover.

**Held-out-calm specificity (the required check):** p_crisis > 0.5 in
**0 of 84** calm months (2013-2019). The detector is correctly silent
in genuinely-held-out calm — zero false alarms, with margin. The
operating point did not need to be loosened.

**Results (OOS 2013-2025):**

| sub-period | always-on (Sharpe / CAGR / MDD) | dynamic (Sharpe / CAGR / MDD) |
|---|---|---|
| full OOS (raw) | +1.59 / +10.7% / −6.5% | +1.62 / +11.1% / −6.8% |
| full OOS (0.5× haircut) | +1.64 / +10.2% / −6.4% | +1.64 / +10.7% / −6.8% |
| calm 2013-2019 | +1.65 / +11.3% / −6.5% | +1.67 / +11.6% / −6.8% |
| COVID 2020 | +2.82 / +24.2% / −1.0% | +2.84 / +25.6% / −1.0% |
| grind 2022 | +1.76 / +13.9% / −4.1% | +1.66 / +13.2% / −4.0% |

dynamic sleeve x: mean **0.153** (range 0.15–0.40) — it ran mostly at
the bull-light 0.15, lifting toward 0.40 only briefly in COVID.

**Δ full-OOS: Sharpe +0.031 (raw) / +0.000 (haircut); MDD −0.4pp
(worse).** The dynamic arm's lighter-in-bull weight bought a tiny CAGR
bump (+0.4pp) but cost a tiny MDD/grind degradation — a net wash. The
COVID-2020 benefit was negligible (Δsharpe +0.02) because the crash was
too brief/V-shaped for a monthly sizer to act.

## Decision (per the locked rule)

The dynamic sizer **does NOT beat always-on 20%** risk-adjusted
net-of-cost OOS (Δsharpe ≈ 0 and it worsens MDD), and the result is
weaker under the haircut. **Per the pre-registration, this is the honest
CEILING: always-on 20% is the deployable sleeve; the regime timer adds
nothing net. Do NOT deploy the dynamic sizer.**

## The honest caveat (why the result, and what it does/doesn't say)

The negative result is NOT a specificity failure (0/84 calm FA) and NOT
the detector being wrong (it correctly lifted in COVID). It is that the
**held-out OOS window (2013-2025) is bull-dominated with one brief
V-shaped fast crisis** — the sizer's entire thesis is "add value in
sustained fast risk-off," and the honest held-out window contained
almost none of that. So the A/B is **underpowered for the sizer's
intended use case** — which tempers "the timer is useless" to "the timer
did not beat always-on on the only honest OOS available, which lacked
the crisis type it is built for." That is still a deploy-NO: we do not
ship a timer that doesn't beat the simple always-on baseline on the
evidence we have. If a future deep-OOS window with a sustained fast
crisis becomes testable (it would need pre-2013 data the detector was
trained on, breaking OOS), the question could re-open under a fresh
pre-registration — but on today's honest evidence, **always-on 20% is
the ceiling.**

This is consistent with the T-172 verdict (regime-classification-grade,
not sharp-timing-grade) and the T-118r failure (the action couldn't
convert prediction → outcome): the detector sees regimes, but turning
that into a sleeve-sizing EDGE over a flat 20% requires crisis episodes
the honest OOS doesn't supply.

## Files

- `docs/Audit/regime_sleeve_sizer_preregistration_t178_2026_06_16.md` — locked pre-reg
- `scripts/regime_sleeve_sizer_t178.py` — the A/B harness
- `data/research/regime_sleeve_sizer_t178.json` — results
- this audit

## NOT done / caveats

- Measurement-only — no production regime/sleeve change, no live path.
- AQR TSMOM is the OPTIMISTIC MF proxy; the result is reported under
  raw AND a 0.5× haircut (the no-beat verdict holds, strengthens, under
  the haircut).
- The OOS window is bounded below by the train/test split (2013) and the
  underpowering is inherent to an honest OOS that excludes the
  trained-on deep crises.
