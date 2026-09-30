# Referee repair proposal — RR-7: record and reproducibility hygiene

**Brief:** `docs/Sources/alpha_frontier_program_2026_09_30.md` §3.1 RR-7, fired unchanged, plus one
director-added line (`[NN-AI-GATE]`, §2.6). **Branch:** `chore/referee-rr7-record-hygiene`, based on
`origin/research/alpha-frontier-2026-09-30` (99153df) — the commit carrying the xfail tests, where the
sibling RR branches also start. **N_trials: 0.** **Status: PROPOSAL.** Nothing here merges: Agent R
reviews, then the director, then the USER rules.

**Anchor rule (09-18 design note):** every record change below cites `file:line` plus the exact text
it expects to find, so a reviewer can confirm each claim mechanically and a later reader can tell
whether it has gone stale. Every anchor was re-read against the branch on 2026-09-30, not transcribed.

---

## §0 A rail conflict, stated rather than resolved silently
Deliverable 1 edits `config/alpha_settings.prod.json`; the common hard constraints forbid touching
`config/*.prod.json`. The brief names this as its one exception ("docs only + one config key"). I made
the edit only after establishing it is **behavior-neutral in production** (§1). **The reviewer should
rule on the rail explicitly** rather than inherit my reading of it.

## §1 Edge-weight key — DONE on the branch (commit 1/6, `022f270`)
| | |
|---|---|
| anchor | `config/alpha_settings.prod.json:37` — was `"news_sentiment_edge": 0.5` |
| EDGE_ID | `engines/engine_a_alpha/edges/news_sentiment_edge.py:32` — `EDGE_ID = "news_sentiment_v2"` |
| change | key renamed to `news_sentiment_v2`; value 0.5 unchanged |
| xfail | `test_prod_edge_weight_keys_match_edge_ids` → PASS (marker removed there only; 15 others untouched) |

**Why it is behavior-neutral:** `news_sentiment` appears in `data/governor/edges.yml` **zero** times,
and `orchestration/mode_controller.py` loads edges only by iterating `registry.get_all_specs()`. The
edge never loads in production, so its weight is consulted under neither key.

**The xfail's own comment was inaccurate** — it said the 0.5 "is never applied (defaults to 1.0)". No
weight is misapplied today; the edge does not run. The real risk is forward: register it and
`edge_weights.get(edge_name, 1.0)` (`signal_processor.py:657`) silently uses 1.0. Corrected in place,
same intent.

**The generic test had to be widened**, found by auditing all 25 keys first. `growth_sales_v1` and
`value_deep_v1` have no class `EDGE_ID` anywhere — they are parametrised instances of the generic
`fundamental_ratio` module whose identity lives only in the registry. A class-attribute check falsely
flags them; a registry check falsely flags the declared-but-unregistered `news_sentiment_v2`. Only the
**union** is correct (`tests/test_edge_weight_keys_rr7.py`). After the fix, zero invalid keys: the
brief's one named mismatch was the only real one.

---

## §2 Record text — PROPOSALS ONLY (no edits to these files)

### §2.1 `health_check.md` — two HMM rows still describe work merged 2026-08-26
| anchor | current text | proposed |
|---|---|---|
| `docs/State/health_check.md:137-140` | `### [HIGH] Engine E: production loads the legacy HMM…` / `- Status: not started (repoint is propose-first; sequenced behind T-118 verdict)` | `- Status: **RESOLVED 2026-08-26** (`20f6fc6`). config/regime_settings.json and the HMMConfig default both name hmm_3state_crisis_v1.pkl. Residual: multires_hmm.py MultiResHMMArtifacts.default() still names the legacy model behind an `artifacts or default()` fallback — unreachable in production, see docs/Sources/design_referee_repairs_2026_09_18.md §2(a).` |
| `docs/State/health_check.md:41,60` | `### [HIGH] The HMM is structurally BLIND before 2020-05-08…` / `- Status: **OPEN — proposed, not applied.**` | `- Status: **RESOLVED 2026-08-26** (`068afba`): panel 5,041/8,361 complete rows back to 2006-04-04; tlt_ret_20d NaN 36.6% (was 82.1%). Residual: the partial-backfill guard recommended here was never built (design note §2(b)).` |

Verified live on 2026-09-18: both config pointers name the crisis model; the panel figures above were
re-measured, not quoted.

### §2.2 `CURRENT_STATE.md` — one stale claim and one misattributed number
| anchor | current text | proposed |
|---|---|---|
| `docs/State/CURRENT_STATE.md:21` | `**Engine E hmm_p_crisis is predictive (AUC 0.887)** — but production loads the legacy HMM and the panel is blind pre-2020…` | `**Engine E's validated signal is the COMBINED posterior (p_crisis + p_stressed), OOS AUC@5d 0.914–0.919, ci_low 0.880 (T-103/T-105).** Production loads the crisis model and the panel reaches 2006 (both fixed 2026-08-26). p_crisis ALONE on this model is OOS 0.497 — a coin flip; gate on the combined posterior.` |
| `docs/State/CURRENT_STATE.md:37` | `Referee repairs (B, after the director pass's first artifact): HMM backfill repoint; legacy-HMM production load.` | remove — both done; replace with a pointer to design note §2(a)/(b) for the two residuals |

**The 0.887 is a live misattribution, not just a stale status.** It is the **legacy** model's `p_crisis`
AUC (T-087). Production runs the crisis model, on which `p_crisis` by itself is 0.497. Anyone gating on
`hmm_p_crisis` from this line would be gating on a coin flip — the exact error T-103 pre-stated and the
08-26 repoint note recorded.

### §2.3 CLAUDE.md `[NN-SHARPE-CI]` — the block-length method is misnamed
| anchor | current text | proposed |
|---|---|---|
| `CLAUDE.md:123-124` | `Block-bootstrap (Künsch 1989, default 1000 iter, auto block length per Politis-White) is the project standard.` | `Moving-block bootstrap (Künsch 1989), default 1000 iterations, block length max(5, round(n^(1/3))) — core/metrics_engine.py:923. This is a fixed rule of thumb, NOT the data-adaptive Politis-White selector; strongly autocorrelated series may warrant a longer block.` |

Verified: `core/metrics_engine.py:923` reads `block_length = max(5, int(round(n ** (1.0 / 3.0))))`.
Politis-White (2004) chooses the block from the sample's autocorrelation; the code does not. Nothing is
computed differently by correcting the sentence — but a reader citing "Politis-White" to defend a CI
width is citing a method that was never run.

### §2.4 CLAUDE.md `[NN-MBL]` — "~75" is stale, and the paragraph's two numbers disagree with its own formula
| anchor | current text | proposed |
|---|---|---|
| `CLAUDE.md:135-136` | `At our current ~75 accumulated N_trials, the 5-year substrate-honest window requires SR ≥ 1.55 to clear DSR` | `N_effective is COMPUTED, never quoted: core.measurement.mbl_gate.compute_n_effective() (231 on 2026-09-30). Under T_years ≥ 2·ln(N)/SR², a 5-year window at N=231 requires SR ≥ 1.48.` |

**A sibling-number tell inside the rule itself.** The paragraph states `T_years ≥ 2·ln(N_effective)/SR²`
and then pairs "~75" with "SR ≥ 1.55". Under that formula, N=75 gives **SR ≥ 1.31**, and SR ≥ 1.55 at
T=5 corresponds to **N ≈ 405**. The two numbers were never mutually consistent with the rule printed
beside them. Live N_effective is **231 → SR ≥ 1.48**.

Proposing *computed, not quoted* rather than swapping 75 for 231: a hardcoded N goes stale again the
moment another trial is logged — which is how this one went stale. **Note for the reviewer:** RR-3
proposes replacing the upper-bound formula with the exact E[max]; if that merges, the 1.48 in the
proposed text changes too, which is a further argument for the sentence to point at the function.

### §2.5 `TASK_LEDGER.md:143` — T-196's two survivors are mislabeled
| anchor | current text | proposed |
|---|---|---|
| `docs/State/TASK_LEDGER.md:143` | `33 died at gate_1, 2 at gate_3.` | `33 died at gate_1; 2 cleared Gates 1–2 and were killed by a FORCED Gate 4 fail (mislabeled "gate_3"; see alpha_frontier_review 01_gap_report.md §1A.1 and §2 N-2).` |

Source: `docs/Sources/alpha_frontier_review_2026_09_30/01_gap_report.md:45-46` — *"Two T-196 features
that cleared Gates 1–2 were then killed by a forced Gate 4 fail (§2 N-2), mislabeled 'gate_3'."* I
could not find a persisted per-candidate gate record for T-196 under `data/research/` to confirm this
independently, so the correction rests on the gap report's reading; the reviewer may want that
confirmed before the ledger line is changed.

### §2.6 CLAUDE.md `[NN-AI-GATE]` — the premise, restated as pending B-1 (director-added)
| anchor | current text |
|---|---|
| `CLAUDE.md:247-251` | `The prior on any "AI finds alpha" hypothesis is LOW until proven on the honest bar: the price-vocabulary is H0-exhausted (foundry, conjunctive), so value — if any — is in NEW DATA modalities (text/news/filings the price vocabulary can't see), NOT a richer model of the exhausted price data (a foundation model on OHLCV is the same exhausted source).` |

**Proposed:**
> The prior on any "AI finds alpha" hypothesis is LOW until proven on the honest bar. That prior does
> not depend on any single verdict: it is the default for every alpha claim, and the gate below applies
> in full regardless. **The price-vocabulary H0 (T-196 foundry; conjunctive) was produced under the
> RR-1 frozen-capital sizing defect with Gate 4 forced false, and is UNTESTED pending B-1** (the
> raw-signal decile re-evaluation). Until B-1 reports, do not cite price data as *exhausted* — but do
> not read its demotion as evidence *for* price-data alpha either: an unproven vocabulary is not a
> promising one. New data modalities (text/news/filings the price vocabulary cannot see) remain the
> better prior on general grounds — price is the most heavily mined input in markets — and a richer
> model of price data carries no exemption from the gauntlet, DSR, or the beat-the-robo bar.

**How this avoids weakening the gate**, which the director made the constraint:
- the **gate** is untouched — no AI integration until the system without AI beats the robo; AI is held
  to the same falsification gates; no special pleading. None of that text changes;
- the **prior stays LOW**, and the proposal says *why* it does not rest on T-196, so withdrawing T-196
  cannot be read as lowering it;
- it closes the obvious misreading explicitly — *"an unproven vocabulary is not a promising one"* —
  because "demoted to untested" is exactly the phrase a motivated reader turns into "maybe it works";
- the new-data preference survives, re-grounded on a reason that does not depend on the demoted verdict.

What it withdraws is one **evidentiary claim** — "H0-exhausted" as established fact — because the
measurement it rested on is no longer valid. That is the whole change.

