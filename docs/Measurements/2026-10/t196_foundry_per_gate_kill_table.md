---
task_id: T-196 records — per-gate kill table (input to the gap report's §2g reconciliation)
date: 2026-10-14
author: Agent D
type: MEASUREMENT RECORD — read-only tabulation of 36 existing result records. No backtest run.
n_trials: 0
---

# T-196 foundry records — what each gate actually rendered

**Why this exists.** The gap report's "93/93 died at Gate 1" mixes three populations: the 2026-05-01 diagnostic
(30/30), the T-193 sweep (35/35, an artifact of a zero baseline), and T-196's 36 records, two of which did NOT die
at Gate 1. This file covers **T-196's population only**. The director writes the reconciliation from it.

**Not evidence about alpha.** Every number below was produced before RR-1 (frozen-capital sizing) and before RR-2
(Gate 4 forced to FAIL). T-196's H0 was demoted to UNTESTED on 2026-09-30. This table says what the records
**say**, and which of their gate fields are verdicts versus defaults. It says nothing about whether any feature
has an edge.

## Provenance

- **36 records**, one per file, from the S3 `foundry-t196/` prefix. Local mirror (RR-3B, 2026-10-13):
  `data/observability/rr3b_foundry_t196_2026-10-13/`. Full sha256 per file in the appendix.
- **Harness:** `scripts/run_foundry_eval_t195.py` at `55568b1` (2026-06-17), the version current until RR-2.
  Verified in that source:
  - `significance_threshold=None` → `validate_candidate` set `gate_4_passed=False` for every candidate.
    **Gate 4 was forced; it never tested anything.**
  - `n_trials_for_dsr=len(feats)`. Each file holds exactly one record, so each container swept one feature:
    N = 1. **Gate 8 was skipped** (N ≤ 1), and Gate 0 at N = 1 passes any window.
  - No `data_map_substrate_b` is passed. **Gate 7 never ran.**
  - Kill attribution (`:114`): the first gate with `gate_{g}_evaluated` (default **True**) and not
    `gate_{g}_passed` (default **False**). Gate 3 has no `gate_3_passed` key, so whenever WFO ran, Gate 3 was named.
- **After a Gate-1 failure** `validate_candidate` returned early. The recorded `g2–g6 = false` are initialiser
  defaults (never ran), `g7 = g8 = true` are skip defaults (never ran), and `g3 = null`.

## Counts

| | records | distinct features |
|---|---|---|
| total | 36 | 35 (`mom_12_1` twice: `cand/` and `probe/`, every result field bit-identical — determinism PASS) |
| recorded `first_failed_gate = gate_1` | 34 | 33 |
| — of which contribution **exactly 0.0** (with-candidate Sharpe = baseline to full precision) | 4 | 4 |
| — of which a **rendered** Gate-1 FAIL (contribution ≤ 0.10, non-zero) | 30 | 29 |
| recorded `first_failed_gate = gate_3` (cleared Gates 1 and 2) | 2 | 2 |
| passed all gates | 0 | 0 |
| harness errors | 0 | 0 |

**The four exact-zero records are not Gate-1 verdicts.** They are `anfci_z_60d`, `correlation_average_60d`,
`cot_commercial_net_long` and `earnings_proximity_5d`. Both the contribution and the attribution Sharpe are
exactly 0.0, which is T-346's class: a blind or absorbed candidate. Under the T-347 census (2026-08-26, after
these runs), a candidate that emits no signal, or whose attribution stream is identically zero, raises
`DiscoveryCandidateCensusError` instead of recording a Gate-1 FAIL. The record carries neither the signal counts
nor the stream, so this is the class the numbers fit, not a re-run. Under RR-6a's reading, Gate 1 would be
NOT_EVALUATED for these four.

**Observation, no mechanism asserted:** four distinct features produced a **bit-identical** result:
`dispersion_60d`, `month_of_year_dummy`, `vvix_or_proxy`, `weekday_dummy`. Each has contribution
−0.2847130218221805 and with-candidate Sharpe 0.976897111828005. Four different features producing the same
book to full precision suggests their positions did not depend on the feature. Whoever re-runs T-196 under
RR-1/RR-6a should check this. It is not a verdict either way.

The baseline Sharpe is 1.2616101336501855 in every record. This is the T-195 harness fix working, and not T-193's
zero baseline.

## The two that cleared Gates 1–2

| gate | `triple_witching_premium` | `january_effect` |
|---|---|---|
| 1 contribution > 0.10 | **PASS** (+0.1805) | **PASS** (+0.1629) |
| 2 PBO survival ≥ 0.60 | **PASS** (0.795) | **PASS** (0.745) |
| 3 WFO consistency | recorded only; `g3 = null`. **The harness named it the killer** | recorded only; `g3 = null`. **The harness named it the killer** |
| 4 permutation p | **forced FALSE** (threshold `None`; recorded p 0.980 from the pre-RR-2 degenerate null). Not a test | **forced FALSE** (recorded p 1.000). Not a test |
| 5 universe-B > 0 | recorded `true` | recorded `false`. The record cannot tell a real ≤ 0 from an unmeasurable NaN: pre-RR-6a, NaN was recorded False, and the record carries no `universe_b_sharpe` |
| 6 factor α (report mode) | recorded `true`. Cannot tell evaluated from the skip-as-pass paths (missing cache, `decomp is None`) | recorded `true`. Same caveat |
| 7 substrate transfer | **never ran** (recorded `true`) | **never ran** (recorded `true`) |
| 8 DSR | **never ran** (N = 1; recorded `true`) | **never ran** (N = 1; recorded `true`) |
| recorded killer | `gate_3` | `gate_3` |
| RR-7's ledger correction | "killed by forced Gate 4" | "killed by forced Gate 4" |
| **what was actually rendered** | **No gate FAILED it.** It cleared every gate that rendered a verdict (1, 2, 5; 6 unknown). It is *untested at Gates 4, 7 and 8*, not killed | Its only possible rendered failure is **Gate 5**, and the record cannot say whether Gate 5 was evaluated. *Untested at 4, 7 and 8; possibly failed at 5* |

RR-7 corrected the ledger from "Gate 3" to "forced Gate 4". That is right about the mechanism that stopped both
candidates, but a forced gate is not a verdict either. The precise statement is the last row.

## Per-record table

Vector `g1…g8` as recorded: `T` true, `F` false, `·` null. Read the "after a Gate-1 failure" note above before
reading any position past `g1` on a Gate-1 row.

| record | feature | ticker-indep. | recorded killer | contribution | attribution Sharpe | survival | p | g1…g8 | sha256[:12] |
|---|---|---|---|---|---|---|---|---|---|
| `cand/anfci_z_60d` | anfci_z_60d | False | gate_1 | +0.0000 | +0.000 | 0.000 | 1.000 | FF·FFFTT | d0933fe9ac0e |
| `cand/beta_252d` | beta_252d | False | gate_1 | -0.2840 | +0.097 | 0.000 | 1.000 | FF·FFFTT | a13c23f16ae1 |
| `cand/correlation_average_60d` | correlation_average_60d | True | gate_1 | +0.0000 | +0.000 | 0.000 | 1.000 | FF·FFFTT | 81e495429c64 |
| `cand/cot_commercial_net_long` | cot_commercial_net_long | False | gate_1 | +0.0000 | +0.000 | 0.000 | 1.000 | FF·FFFTT | 5ebd494dbf1c |
| `cand/days_to_quarter_end` | days_to_quarter_end | True | gate_1 | -0.2971 | -0.139 | 0.000 | 1.000 | FF·FFFTT | bb4ed9ea0ec3 |
| `cand/dispersion_60d` | dispersion_60d | True | gate_1 | -0.2847 | -0.128 | 0.000 | 1.000 | FF·FFFTT | 508d098f84a3 |
| `cand/dist_52w_high` | dist_52w_high | False | gate_1 | -0.3026 | -0.204 | 0.000 | 1.000 | FF·FFFTT | 12f43dec7f80 |
| `cand/drawdown_60d` | drawdown_60d | False | gate_1 | -0.1205 | +0.005 | 0.000 | 1.000 | FF·FFFTT | e9d26536d802 |
| `cand/dxy_change_20d` | dxy_change_20d | True | gate_1 | -0.2960 | -0.168 | 0.000 | 1.000 | FF·FFFTT | b89a8530529d |
| `cand/earnings_proximity_5d` | earnings_proximity_5d | False | gate_1 | +0.0000 | +0.000 | 0.000 | 1.000 | FF·FFFTT | 110c9595e58f |
| `cand/faber_multi_asset_trend_above_10mo_sma` | faber_multi_asset_trend_above_10mo_sma | True | gate_1 | -0.1773 | -0.029 | 0.000 | 1.000 | FF·FFFTT | a77b7ecd91b1 |
| `cand/fomc_drift` | fomc_drift | True | gate_1 | -0.0596 | -0.126 | 0.000 | 1.000 | FF·FFFTT | ea94c28835ac |
| `cand/high_minus_low_60d` | high_minus_low_60d | False | gate_1 | -0.3036 | +0.085 | 0.000 | 1.000 | FF·FFFTT | f50a69101e78 |
| `cand/hy_oas_change_20d` | hy_oas_change_20d | True | gate_1 | +0.0476 | +0.160 | 0.000 | 1.000 | FF·FFFTT | e34db77d1c2c |
| `cand/hyg_lqd_spread` | hyg_lqd_spread | True | gate_1 | +0.0206 | +0.081 | 0.000 | 1.000 | FF·FFFTT | 7decba599306 |
| `cand/january_effect` | january_effect | True | gate_3 | +0.1629 | +0.260 | 0.745 | 1.000 | TT·FFTTT | 6f4d6e843915 |
| `cand/ma_cross_50_200` | ma_cross_50_200 | False | gate_1 | -0.3273 | -0.146 | 0.000 | 1.000 | FF·FFFTT | aefc825c7621 |
| `cand/mom_12_1` | mom_12_1 | False | gate_1 | -0.4321 | -0.189 | 0.000 | 1.000 | FF·FFFTT | 41a9c836131b |
| `cand/mom_6_1` | mom_6_1 | False | gate_1 | -0.0156 | +0.250 | 0.000 | 1.000 | FF·FFFTT | 52f07c3b8f02 |
| `cand/month_of_year_dummy` | month_of_year_dummy | True | gate_1 | -0.2847 | -0.128 | 0.000 | 1.000 | FF·FFFTT | e47fed75a58f |
| `cand/moving_avg_distance_50d` | moving_avg_distance_50d | False | gate_1 | -0.3092 | -0.069 | 0.000 | 1.000 | FF·FFFTT | 8512735f47e9 |
| `cand/pair_zscore_60d` | pair_zscore_60d | False | gate_1 | +0.0587 | +0.216 | 0.000 | 1.000 | FF·FFFTT | b2c4d7cb3c4d |
| `cand/pre_fomc_reduce` | pre_fomc_reduce | True | gate_1 | +0.0802 | +0.167 | 0.000 | 1.000 | FF·FFFTT | 6f44eb8f1fe8 |
| `cand/pre_holiday` | pre_holiday | True | gate_1 | -0.0386 | +0.009 | 0.000 | 1.000 | FF·FFFTT | 40ba8a8314b1 |
| `cand/realized_vol_60d` | realized_vol_60d | False | gate_1 | -0.2440 | +0.177 | 0.000 | 1.000 | FF·FFFTT | 857c97063978 |
| `cand/reversal_1m` | reversal_1m | False | gate_1 | -0.1254 | +0.116 | 0.000 | 1.000 | FF·FFFTT | cdacf2e4db6a |
| `cand/sell_in_may_halloween` | sell_in_may_halloween | True | gate_1 | -0.3069 | -0.235 | 0.000 | 1.000 | FF·FFFTT | efd346d009f6 |
| `cand/skew_60d` | skew_60d | False | gate_1 | -0.4576 | -0.327 | 0.000 | 1.000 | FF·FFFTT | 71ccd72c5060 |
| `cand/tax_loss_season` | tax_loss_season | True | gate_1 | -0.0113 | -0.074 | 0.000 | 1.000 | FF·FFFTT | f6b9cfd5505b |
| `cand/triple_witching_premium` | triple_witching_premium | True | gate_3 | +0.1805 | +0.250 | 0.795 | 0.980 | TT·FTTTT | ab26f474b641 |
| `cand/vix_change_5d` | vix_change_5d | True | gate_1 | -0.3305 | -0.178 | 0.000 | 1.000 | FF·FFFTT | c7a6f544cfc5 |
| `cand/vix_term_structure_slope` | vix_term_structure_slope | True | gate_1 | -0.4195 | -0.271 | 0.000 | 1.000 | FF·FFFTT | baa420b98a25 |
| `cand/vol_regime_5_60` | vol_regime_5_60 | False | gate_1 | -0.3382 | -0.155 | 0.000 | 1.000 | FF·FFFTT | 5f91de42ec00 |
| `cand/vvix_or_proxy` | vvix_or_proxy | True | gate_1 | -0.2847 | -0.128 | 0.000 | 1.000 | FF·FFFTT | 184f0f646cfb |
| `cand/weekday_dummy` | weekday_dummy | True | gate_1 | -0.2847 | -0.128 | 0.000 | 1.000 | FF·FFFTT | fc9b87467596 |
| `probe` | mom_12_1 | False | gate_1 | -0.4321 | -0.189 | 0.000 | 1.000 | FF·FFFTT | c35056170b38 |

On Gate-1 rows, `survival 0.000` and `p 1.000` are the result-dict initialisers: Gates 2 and 4 never ran.

## Records: annotate, never rewrite

None of the 36 records is edited. RR-6a will add a sidecar note beside them on S3 that points here.

## Appendix — full sha256 (relative to the mirror root)

```
d0933fe9ac0e462dbf3131d001df63a2d4f49525e7e55184a636a0b2ba29b435  cand/anfci_z_60d/t195_foundry_eval.jsonl
a13c23f16ae14a8bbeb33fb663af341d03f45ffc7de0bd2b4256db5216b222b4  cand/beta_252d/t195_foundry_eval.jsonl
81e495429c64d10b20335004a0a12688467f3023e70e186d81a927b2bc2df6a6  cand/correlation_average_60d/t195_foundry_eval.jsonl
5ebd494dbf1ca2d5de3372e6553aa26e4be12e84d63f68f94ae068f13d73dc18  cand/cot_commercial_net_long/t195_foundry_eval.jsonl
bb4ed9ea0ec3c0e55fc587a91323ddd1236540551f79b062299b7555b6f07a7f  cand/days_to_quarter_end/t195_foundry_eval.jsonl
508d098f84a366260e6b6476a9926006dd4b87ddc319884347594a4c6684f718  cand/dispersion_60d/t195_foundry_eval.jsonl
12f43dec7f80c6e794c8264f3028fdd70df846edc020477ddc175bdc4052e89b  cand/dist_52w_high/t195_foundry_eval.jsonl
e9d26536d80283865243e335641716149fdde38b372774b2f425cfc503cf4505  cand/drawdown_60d/t195_foundry_eval.jsonl
b89a8530529d33c14f69aa8a355b18bae03dbb515064ed3469e55f1d0b6e9f00  cand/dxy_change_20d/t195_foundry_eval.jsonl
110c9595e58f119b186454e690f6aa5471b129357527a45085e646e849a91776  cand/earnings_proximity_5d/t195_foundry_eval.jsonl
a77b7ecd91b19b45c1e2410bb6870ce3776ccc3b930d8bbe064741b427774b58  cand/faber_multi_asset_trend_above_10mo_sma/t195_foundry_eval.jsonl
ea94c28835aceefa9917ea8cf222196f5cf62b53aa8a8c3d37787c114769c89e  cand/fomc_drift/t195_foundry_eval.jsonl
f50a69101e78057120c86689e634e45cc3b19d9805d66ab90cb07c91ce807820  cand/high_minus_low_60d/t195_foundry_eval.jsonl
e34db77d1c2c68b02c3b43a76cb1650ad6064a604f27fcd202acf8977bb2b76d  cand/hy_oas_change_20d/t195_foundry_eval.jsonl
7decba59930672d139946506ab7adce270a9c5f6afd73b95076e080fbb0eda57  cand/hyg_lqd_spread/t195_foundry_eval.jsonl
6f4d6e84391508bb84e3972a445dcadd91b9dbad318e7f3e244ac8c2d1b9e8e1  cand/january_effect/t195_foundry_eval.jsonl
aefc825c7621a2cc076d57359a51e77444d027dc60f57dfa6067688c63e597cc  cand/ma_cross_50_200/t195_foundry_eval.jsonl
41a9c836131b05c728986f11394772661ca4127186f13ae36b115c89f9504c6f  cand/mom_12_1/t195_foundry_eval.jsonl
52f07c3b8f02d012ae5387bd12fefdd1c6e66e6b5b15f25f80feee8e9d64bad1  cand/mom_6_1/t195_foundry_eval.jsonl
e47fed75a58f8ed45ca72bdec693b16072c67afb95b1f15aba8f78e037ee635a  cand/month_of_year_dummy/t195_foundry_eval.jsonl
8512735f47e9888a40b0c7f206be76a9d1d6868208255a4ab72e1e9f9fd75367  cand/moving_avg_distance_50d/t195_foundry_eval.jsonl
b2c4d7cb3c4db5715093ff4622e9c06801e81fea194e7a31f144b9ae24ee6325  cand/pair_zscore_60d/t195_foundry_eval.jsonl
6f44eb8f1fe8e548fcb6bee05018c238a50360f3d12ddf151659ba2254c18e58  cand/pre_fomc_reduce/t195_foundry_eval.jsonl
40ba8a8314b1d4b57f4a9a1f1f0edd140bea8f63c1514dcccaa36331bca58553  cand/pre_holiday/t195_foundry_eval.jsonl
857c97063978f27f89b3dfc2b5441c62de394468e941aff47096e06bc3940de5  cand/realized_vol_60d/t195_foundry_eval.jsonl
cdacf2e4db6a2eac3facaa2589425eaedc2276e41b76354f1128c67bce317a4b  cand/reversal_1m/t195_foundry_eval.jsonl
efd346d009f6838f2fd3a42a39f9b6ecf9521b9d6d013565cc819112ec2fa94f  cand/sell_in_may_halloween/t195_foundry_eval.jsonl
71ccd72c50609356f4b6c89cdeb718f967f27ad77df94378283b953d29f88a13  cand/skew_60d/t195_foundry_eval.jsonl
f6b9cfd5505b1a47aac27d9bd3de5bd8d81d090263e92657529abd66f5412e61  cand/tax_loss_season/t195_foundry_eval.jsonl
ab26f474b641eac90cd7db8769b7b32632ee84d120a4c6db284131944f3140b2  cand/triple_witching_premium/t195_foundry_eval.jsonl
c7a6f544cfc567d189fdc91a27997bd64948b814c1a59ce91a26f218ad950699  cand/vix_change_5d/t195_foundry_eval.jsonl
baa420b98a2500e57fb542403a9a6e3546ef658b0a0c0d1de72c8b593bd3f042  cand/vix_term_structure_slope/t195_foundry_eval.jsonl
5f91de42ec0040ef7317395db323c8e206e70a959edf8f4f194901d573445e1c  cand/vol_regime_5_60/t195_foundry_eval.jsonl
184f0f646cfbc85d9d2cc63d9229be040b123999ec8ccbd6424be662ef23d815  cand/vvix_or_proxy/t195_foundry_eval.jsonl
fc9b874675966c1bfdf29aac8d7116ff4c7947cf9be5985b3b04d3b417b78e2d  cand/weekday_dummy/t195_foundry_eval.jsonl
c35056170b38d95592376dc7a826ba6287436f0a25e4607fe60e37e9d31072ea  probe/t195_foundry_eval.jsonl
```
