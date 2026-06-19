# T-203 — Phase 0: re-aim the gate + un-bias the measurement (three moves)

**Date:** 2026-06-18
**Agent:** C (branch `feature/phase0-robo-gate-reaim-t203`)
**Status:** DONE — three separate commits (surgical rollback), all measurement-integrity (my lane). Re-architecture Phase 0: the resolved goal is **beat the Schwab robo net-of-cost/after-tax on risk-adjusted/tail terms**, NOT academic factor-orthogonal alpha. We were gating on the wrong target with an upward-biased ruler; both fixed. The anti-self-deception machinery (MBL, DSR, census, pre-registration, walk-forward, block-bootstrap CI) is UNCHANGED — this re-aims the target, it does not relax rigor.

---

## Move 1 — the robo scorecard is the PRIMARY deploy gate (commit c81e194)
`core/combined_candidate_scorecard.py::evaluate_deploy_readiness(candidate_equity, account, robo, ...)`. Pass vs a proxy = **`ci_low(Sharpe_cand) > ci_low(Sharpe_robo)`** (block-bootstrap, NOT point estimate, CLAUDE.md #6) **OR** a ≥20% shallower MaxDD — **after-tax + net-of-cost**. Primary account = **Roth** (tax/turnover lever off → the bar is risk-adjusted + tail); **taxable** = secondary diagnostic. Factor-orthogonality (Gate-6) DEMOTED to diagnostic-only (`config/discovery_settings.json::factor_gate_mode="report"`, default) — still computed/recorded (with the HAC t-stat) but no longer KILLs; `robo_deploy_gate_enabled` flag added. 6 unit tests.

### Window-honesty (the un-biasing — the headline)
The candidate (base + 20% DBMF) is only measurable where DBMF exists (2019+, a post-COVID-mostly-bull window). Naively, that window flatters the tail: the candidate's MaxDD over 2020–2025 is ~−8% while the base's full-cycle MaxDD is ~−40%. **A tail "win" measured over a window that excludes dotcom/GFC/COVID is a window artifact, not evidence the sleeve cuts the real tail.** So the gate (a) DISCOUNTS a window-flattered MDD-improvement (verdict rests on `ci_low` only when `window_excludes_base_tail`), and (b) requires `full_cycle_tail_verified` to certify DEPLOY — you cannot deploy on an untested tail.

### THE GATE WORKING on the current base (26yr run, both accounts → DO NOT DEPLOY)
| account | beats on ci_low | window MaxDD | base full-cycle MaxDD | verdict |
|---|---|---|---|---|
| Roth | 60/40 ✓, schwab_like ✓ | −8.2% | **−39.7%** | **DO NOT DEPLOY** |
| taxable | 60/40 ✓, schwab_like ✗ | −8.2% | −39.7% | **DO NOT DEPLOY** |

The candidate beats the robo on `ci_low` over 2020–2025 — but the window excludes the base's −39.7% full-cycle drawdown, so the sleeve's tail-cut is UNVERIFIED and full-cycle deploy-readiness is NOT established → **DO NOT DEPLOY** (honest "not yet"). Note: this reaches the dispatch's expected verdict for a more honest reason than "base after-tax loses" — over the *available* window it actually *beats*; the binding problem is the untested tail. (Taxable also outright trails schwab_like on ci_low — the after-tax/turnover drag, the 3rd indictment.)

## Move 2 — Gate-6 OLS→HAC/Newey-West SEs (commit b687fd8)
`core/factor_decomposition.py` computed homoskedastic OLS SEs `σ²·(X'X)⁻¹` — no autocorrelation correction → understated alpha SE → inflated alpha t-stat on autocorrelated returns → Gate-6 more permissive than advertised (the silent-fail-open class, T-181/194/199). Replaced with **Newey-West HAC** (Bartlett kernel, auto lag `floor(4·(n/100)^(2/9))`, overridable). Identity on white-noise residuals (lag terms vanish → ≈OLS); strictly wider on autocorrelated residuals → t-stat DROPS (the honest direction). `FactorDecomp` gains `se_method`/`hac_lag`.

### DOCUMENTED OLS→HAC delta (26yr run 3d7bbcf9, real per-edge, FF5+Mom)
| edge | OLS t | HAC t | Δ |
|---|---|---|---|
| low_vol_factor_v1 | 3.628 | 3.199 | −12% |
| volume_anomaly_v1 | 4.975 | 4.228 | −15% |
| accruals_inv_sloan_v1 | 0.959 | 0.977 | ~flat |
| (near-zero edges) | … | … | ~flat |

The edges with **real autocorrelated alpha drop ~12–15%**; near-zero edges barely move. A PASS, not a fail — Gate-6 is now correctly less permissive (an OLS t of ~2.7 on autocorrelated returns could be ~2.3 under HAC, i.e., below the bar). 3 unit tests (white-noise identity, AR(1) wider, method/lag reported).

## Move 3 — Sharpe-reimpl CI guard (commit 4f88953)
**Audit FIRST** (the dispatch's discipline): the "14 private Sharpe reimpls" are NOT 14 naive duplicates. The 6 inline computes are **custom variants** — `run_benchmark` (log returns + 2% rf), `t154 madj_sharpe` (median-adjusted), `t117` (an appraisal ratio alpha/residual-std) — or **frozen T-xxx one-offs** (archive-track); plus several **consumers** that already read a pre-computed Sharpe. **A blanket consolidation would have SILENTLY CORRUPTED the custom variants** — the exact silent-drop this arc kills. So the durable win is PREVENTING NEW drift, not churning the frozen/custom set. `tests/test_no_private_sharpe_reimpl.py` flags any NEW `scripts/*.py` inline Sharpe (`mean()/std()*sqrt(252)`) not routed through `MetricsEngine.sharpe_ratio`; the 6 existing computes are allowlisted WITH classification; wired into `contract_tests.yml`. Non-destructive (no source files touched).

## Canon-unchanged proof
None of the changed files is in the backtest trade path: `combined_candidate_scorecard` + `factor_decomposition` are offline tools (factor_decomp's only non-script consumer, `tier_classifier`, is offline too — 0 trade-path imports); Discovery runs only under `--discover`, not a q1 backtest; the rest are config/tests/CI. **Empirical proof: 2022 `trades_canon_md5` = `80b501a8ab16206d74bdfc09a7f245aa` on BOTH origin/main and this branch (all three moves) — bitwise identical.** The HAC fix changes factor t-stats (by design) but not a single trade.

## Files / constraints
Move 1: `core/combined_candidate_scorecard.py`, `engines/engine_d_discovery/discovery.py`, `config/discovery_settings.json`, tests. Move 2: `core/factor_decomposition.py`, tests. Move 3: `tests/test_no_private_sharpe_reimpl.py`, `.github/workflows/contract_tests.yml`. No Engine-B-risk / live_trader / trade-path edits. Branch push; director merges + re-verifies canon. (The `Base-Clean-Ready` tag awaits the cleanup track too.)
