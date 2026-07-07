---
task_id: T-2026-07-06-286
title: TR canonical curves — VERIFICATION (the curves are ALREADY total-return; re-emission would double-count)
date: 2026-07-06
author: Agent D (fair-harness lane)
type: verification / escalation (0 N_trials)
status: DONE — ESCALATE: no re-emission needed; the curves are already TR (verified 3 ways). Branch feature/tr-canonical-curves-t286
---

# T-286 — the canonical curves are already total-return

The task (from B/T-283c) was to re-emit `data/research/t284/daily_curves.parquet` as dividend-inclusive TR,
on the premise that the curves are price-only and understate user-facing wealth ~1.5-1.7× over 26yr. **Before
executing, I verified the premise — and it does not hold. The curves are ALREADY total-return.** Re-emitting
them "with TR" would double-count dividends and inflate every dollar figure by ~1.6×. Escalating rather than
executing (relay-before-deciding).

## Three independent verifications that `data/processed/SPY_1d.csv` is total-return
1. **vs yfinance both ways (2005-01-03):** ours = **81.38**; yfinance `auto_adjust=True` (TR) = **81.17**;
   yfinance raw price = **120.30**. Ours matches the TR value, NOT the raw price → dividend-adjusted.
2. **vs the `tr_reconciled` substrate:** `data/processed/SPY_1d.csv` grew **8.851×** over 2005-02→2026-04;
   `data/processed/tr_reconciled/SPY_1d.csv` grew **8.851×** over the same window → **ratio 1.0000, identical
   growth.** The processed SPY is already the TR-reconciled series (no dividend gap).
3. **vs the CAGR sniff test:** the `bh_spy` curve in `daily_curves.parquet` compounds at **7.61%/yr**
   (2000-10→2025-12, $10k→$63,335) — SPY TR over that window is ~7.5-8%/yr; price-only would be ~5.5%/yr
   ($10k→~$40k). The curve is TR.

## All three legs of the curves are TR
- **SPY leg:** `data/processed/SPY_1d.csv` — dividend-adjusted (proven above).
- **BOND leg:** `data/research/bond_synth_dgs10_t255.csv` — a synthetic DGS10 constant-maturity **total-return**
  bond (carry `y_{t-1}/252` + duration), CAGR **3.74%/yr** (a coupon-inclusive TR bond; a price-only bond
  would be ~0-1%/yr). Coupon income is included by construction.
- **GOLD leg:** `data/research/gold_gcf_t255.csv` (GC=F) — gold pays no dividend, so price = total return.
- **Levered arm:** the SSO-synthetic is `2·spy_tr_gross − borrow − ER`, and `spy_tr_gross` is the TOTAL return
  → the 2× arm already captures **2× the dividend** (the "2× the dividend in the levered arm" the task asks
  for is already present, because doubling a total-return series doubles its dividend component).

## Verdict — NO re-emission; the T-282/284/285 dollar figures already reflect reinvested dividends
`daily_curves.parquet` and every wealth figure in the T-282/T-284/T-285 audits are already total-return with
dividends reinvested. There is nothing to relabel as "price-only" — those audits quote TR numbers. **Applying
a 1.5-1.7× dividend uplift to these curves would be a double-count.**

## ⚠️ Downstream risk to reconcile (for the director)
B's T-283c premise was that my curves are price-only. **If B's T-283/T-283b accumulation overlay applied a
dividend uplift (×1.5-1.7) to these already-TR curves, the published accumulation figures (e.g. the gated-2×
"$1.94M" vs buy-hold "$1.45M") would be OVERSTATED by that factor.** The director should reconcile which
inputs T-283 used: if it consumed `daily_curves.parquet` as-is (TR), the accumulation numbers are correct and
no dividend uplift should be added; if it added an uplift on top, those numbers need to be divided back down.
I did not touch T-283's artifacts (out of my lane) — flagging for reconciliation. `[NN-FAIL-CLOSED]`-adjacent:
a plausible-looking ×1.6 wealth inflation that isn't real is exactly the kind of silent error to catch before
it reaches the user. Reproducible checks: the one-liners in this session's transcript / `scripts` are trivial
to re-run against `data/processed/{SPY_1d,tr_reconciled/SPY_1d}.csv`.
