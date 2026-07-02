---
task_id: T-2026-07-02-257
title: Wave-0 measurement corrections — integer-share reality + CI-machinery coverage
date: 2026-07-02
worker: Agent B
branch: feature/integer-share-ci-audit-t257
status: DONE — two corrections (0 N_trials; read-only, simulation scripts only)
---

# T-257 — integer-share reality check + CI-machinery coverage audit

Two measurement corrections from the gap audit (Part 5 holes 2 + 4). Read-only on
production code (no `metrics_engine`/sizing change). doc_lint green.

## Part 1 — integer-share discretization of the T-236 sleeve
`scripts/integer_share_sleeve_t257.py`. Simulates the T-236 trend sleeve (105d
long/flat absolute momentum on SPY/AGG/GLD, EW) held in WHOLE shares (the paper
`sleeve_constructor` floor logic: qty = floor(equity·w / price)) at $5K/$10K/$15K
vs the continuous backtest, net 5bps.

**Data caveat (honest):** `data/processed` GLD starts 2020-04-09, so the
SPY∩AGG∩GLD window is **2020-2026** here (the full-cycle T-236 used a longer gold
series not in `data/processed`). This recent HIGH-PRICE regime (SPY ~$710) is the
**conservative / binding "deploy $5K today" granularity test** — pre-2020's lower
prices would discretize FINER, so this understates viability, not overstates it.

| window | class | $ | tracking err | MaxDD drift | CAGR drift |
|---|---|---|---|---|---|
| 2020-2026 | SPY/AGG/GLD | 5K | 1.48%/yr | −0.11pp | −1.10pp |
| 2020-2026 | SPY/AGG/GLD | 10K | 1.37%/yr | −0.25pp | −0.42pp |
| 2020-2026 | SPY/AGG/GLD | 15K | 1.35%/yr | −0.48pp | −0.36pp |
| 2024-2026 (deploy-today) | SPY/AGG/GLD | 5K | 1.46%/yr | +0.13pp | −2.40pp |
| 2020-2026 | **SPLG/AGG/GLDM** | 5K | 1.34%/yr | −0.68pp | **−0.14pp** |
| 2024-2026 (deploy-today) | **SPLG/AGG/GLDM** | 5K | 1.22%/yr | −0.79pp | **−1.32pp** |

**Verdict:**
- The sleeve's **TAIL PROTECTION SURVIVES integer discretization at every size** —
  MaxDD drift < 1pp everywhere. Since the sleeve's entire value is the tail cut
  (T-236), this is the key result: it is intact at $5K.
- **Return give-up is the cost:** tracking error ~1.25–1.5%/yr; CAGR drift at $5K
  is −1.1 to −2.4pp with SPY/AGG/GLD — material vs the sleeve's ~1%/yr edge over
  the robo. At $10K+ the drift is milder.
- **Cheap share classes fix it:** SPLG (≈SPY/9) + GLDM (≈GLD/5) — same index,
  finer granularity — cut TE + CAGR drift ~40–90% (2020-2026 $5K CAGR drift
  −1.10 → −0.14pp).
- **Recommendation: viable at $10K+ with SPY/AGG/GLD; at $5K substitute SPLG/GLDM.**
  The paper deployment should use the low-price share classes for sub-$10K accounts.

## Part 2 — CI-machinery coverage audit (the yardstick's validity)
`scripts/ci_coverage_audit_t257.py`. Monte-Carlo coverage of
`MetricsEngine.bootstrap_distribution` on a GARCH(1,1)-t DGP (fat tails + vol
clustering — the serial dependence block-bootstrap exists for), T=1512, 300
samples, nominal 90%. Read-only (calls the production bootstrap).

**Sortino `ci_low` — TRUSTWORTHY.** Coverage of the population Sortino (0.745):
| block_length | coverage |
|---|---|
| 1 (iid) | 90.3% |
| 5 | 90.7% |
| **auto (~12 = n^⅓)** | **92.0%** |
| 21 | 90.7% |
| 63 | 88.3% |

The auto block-length is well-chosen — coverage ≈ nominal, mildly conservative
(CI slightly wide → safe for a kill-gate; it will not falsely clear). Only
over-long blocks (63) mildly under-cover. **The Sortino ci_low the whole program
gates on is validated.** (Sortino coverage is robust to block-length here because
the CI width dominates; even iid was ~90%.)

**MaxDD bootstrap — mildly optimistic, LESS biased than feared; do NOT hard-gate.**
Bootstrap MaxDD median −27.0% vs the true across-path median −27.4% → shortening
of only **+0.38pp (ratio 0.986)**; the CI over-covers the true median (94.3%). The
structural shortening (resampling breaks the worst contiguous run) is REAL but
small at these params. **However**, MaxDD's danger is the DEEP TAIL — the true
across-path p05 is **−47%** vs the −27% median — and a central-CI block-bootstrap
does not represent that tail. **Recommendation:** report the MaxDD **point estimate
+ the bootstrap CI as a descriptive band**, but do NOT hard-GATE kill decisions on
the bootstrap MaxDD ci — it is directionally optimistic and blind to the deep tail;
prefer the point MaxDD + the empirical across-window worst case for kills. (This is
consistent with the program already gating primarily on Sortino/Sharpe ci_low, not
MaxDD ci.)

## Net
- **Integer shares:** sleeve viable at $10K+ (SPY/AGG/GLD) or $5K (SPLG/GLDM); the
  tail protection survives — the return drag is the only cost, and share-class
  substitution largely removes it.
- **CI machinery:** Sortino ci_low is **trustworthy** (validated ~90% coverage);
  MaxDD bootstrap is **mildly optimistic** → keep it descriptive, don't hard-gate.
