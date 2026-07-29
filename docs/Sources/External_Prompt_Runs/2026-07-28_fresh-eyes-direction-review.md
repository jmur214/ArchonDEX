---
run_date: 2026-07-28
agent: fresh-eyes codebase agent (full repo READ access, zero prior context, two-phase blind design)
model: Claude Fable 5 (claude-fable-5) — self-reported
executed_by: user (separate chat session; relayed verbatim to the director)
prompt_working_copy: data/coordination/prompt_fresh_eyes_codebase_2026_07_28.md (debiased v2)
status: findings VERIFIED + triaged by the director same day (see Director Triage at bottom)
contamination_note: the agent disclosed that its harness auto-injected CLAUDE.md, the memory
  index, and a CURRENT_STATE preview before exploration; Phase 1 was committed to disk before
  any docs/State file was opened, but headline verdicts had been seen. Anchor-plausible points
  were flagged ⚠ by the agent itself.
---

# External Prompt Run — Fresh-Eyes Direction Review (2026-07-28)

Permanent record of the findings VERBATIM, per the archive-every-run rule. The full verbatim
text as relayed is preserved below the triage. Director verification was performed IN CODE the
same day (grep/read, no trust of the review's own citations) before any finding was accepted.

---

# DIRECTOR TRIAGE (verified 2026-07-28)

## Verification verdicts on the review's factual claims

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Analyst eval filename joint: `intel_pulse.py:227` writes `note_{date}.json`; `eval_harness.py:305` globs `analyst_note_*.json` → analyst+agentic notes NEVER scored; G1 (≥150 resolved) cannot accrue; T-323 constrained-vs-agentic A/B can never populate | **CONFIRMED — CRITICAL** (broken-clock class, same as the July outage) | Both lines verified in code. Event calls ARE scored (event_service uses correct keys); only the analyst/agentic arms are dead. |
| 2 | LLM kill switch unreachable: `load_governor` has zero production callers; `config/llm_settings.json` has no `"llm"` block | **CONFIRMED** | grep: zero non-def/non-test callers; no llm block. |
| 3 | Special-sits/8-K feed fires on content-free docs (`terms=="{}"`) with `file_date` months back, could burn ~$24 of the $30 governor | **PARTIALLY MITIGATED** | A durable seen-ledger exists (`run_forward.py:74` + `event_calls.jsonl` IS in DURABLE_PATHS) → each doc fires at most once, ever, and the backlog was already absorbed at the 07-27 ignition without incident. Residual (real, bounded): `"{}"` is a truthy string so content-free docs pass the body check; no `file_date` lower bound. Small fix warranted, not urgent. |
| 4 | `corporate_action_tickers` never populated → reconcile CA-class dead; a split halts the laboratory; dividends silently absorbed into adopted cash | **CONFIRMED** | Only def + read exist; prod passes nothing → `or set()` at reconciliation.py:207. |
| 5 | Holiday calendar fallback is 2026-only → broker-calendar failure in Jan 2027 silently treats holidays as trading days | **CONFIRMED (latent)** | `_FALLBACK_HOLIDAYS_2026` verified; used when broker calendar unavailable. |
| 6 | CI runs ~6 of 257 test files; contract workflow doesn't trigger on `paper_trader/**`; two core test files are `assert True` | **CONFIRMED** | contract_tests.yml runs 7 named files. |
| 7 | Run-registry honest-N frozen since 2026-05-08; Gate-8 DSR deflates against `len(batch)`; T-200 dispatched-not-done; OOS lock built with no config + zero callers | **ACCEPTED** (matches ledger state; not re-verified line-by-line) | — |
| 8 | Dividend-strip: the 730-name deep panel is price-return (T-082 splice) while the benchmark side was TR-corrected → T-180-v2 value/accruals sub-verdict and the T-215 "0.1–0.3" number exposed | **ACCEPTED AS A LEGITIMATE CHALLENGE** — the review's own scoping is honest (headline H0 vs robo survives; the sub-verdicts need a TR receipt) | → C1 experiment adopted. |

## Retractions the review made itself (the debiased design working)
- Drawdown-shaped over-exposure → retracted against T-294/298/312/315 ("this arc is the strongest evidence the team's closures deserve deference").
- HMM-into-sizing → retracted against T-101/106/111/116/118/220/221; flags Engine E's ~3,400 LOC as consumer-less (archive-or-adopt call).
- Auction/cost engineering → retracted against T-146/157 + the live 0.51–2.2bps ledger.
- Its own blind #3 (news cross-sectional) self-demoted from growth pillar to kill-fast probe after reading T-289.

## Director dispositions

**ADOPTED — fix now (broken clocks; A's lane):** the eval filename joint (fix `_load_notes` glob, project `note_id`/`note_date`/`model_id` into AnalystNote, scan the agentic dir, backfill-score from the S3 raw-note archive) + wire `load_governor`/the `"llm"` config block + the special-sits residual (non-trivial-body requirement; `file_date` lower bound).

**ADOPTED — folded into T-327 Act 1 scope (E's drill week, already queued):** `PAPER_NOTIFY_WEBHOOK` + DLQ alarm + second alert channel (was already in Act 1); forced-split reconcile drill + populate `corporate_action_tickers` + dividend recognition in the ledger (extends the synthetic-dividend drill already in Act 1); 2027 calendar fix; LLM kill-switch drill.

**ADOPTED — cheap integrity fixes:** CI coverage of `paper_trader/**` + replace the two `assert True` files; registry honest-N refresh + Gate-8 `compute_n_effective` threading + OOS-lock activation (completes T-200).

**ADOPTED — pre-registered experiments (in priority order):** C1 dividend-strip TR-sensitivity audit of the equity-book closures (N+=1; `[NN-SUBSTRATE-REVERIFY]` cascade if it flips); C5 ALFRED OAS recovery (hours; preservation deadline); C2 vol-term-structure conditioning for conditional-leverage #3 (free tier on disk, $0); C4 cross-sectional news kill-fast probe (closes the last news branch).

**ADOPTED — process (the headline):** the **verification-asymmetry** finding — measurement claims face adversarial re-derivation while integration claims get marked done on code inspection, and every recent expensive failure is of the integration class. New rule: **no integration claim is "done" until its first output artifact has been observed and checked end-to-end** (first scored prediction in the jsonl, first delivered webhook, a forced-split drill, a firing on the real scheduled principal). To be codified.

**REJECTED / not adopted:** none outright; the "archive most of Engine E" call is DEFERRED pending conditional-leverage #3 (which would be the HMM's first real consumer).

---

# THE FINDINGS (verbatim, as relayed)

[The full verbatim review as relayed by the user on 2026-07-28 follows. Highlights preserved
here; the complete text is retained in the conversation record and in the agent's own
`direction_review_full.md` in its worktree.]

**Reviewer model:** Claude Fable 5 (claude-fable-5). Contamination disclosure as noted in frontmatter.

**Phase 1 headline:** "This is a measurement-and-governance system with a nearly-inert trading
system inside it. ~30 engineered, tested capabilities ship default-OFF; at least 12 have no
consumer at all. The rigor is applied more strictly to candidates than to the default baseline
they're measured against."

**Subsystem grades:** measurement toolkit A− toolkit / C+ applied; census+determinism A;
Engine D gauntlet A−; Engine F B+; cost modeling B+; paper execution B+/C (idempotency A,
reconcile wiring C+, observability C); Engine A B; Engine E B−; data substrate B (dividend-strip
flagged); Engine B C+ (documented-unfixed 1.7× gross bug); Engine C C (MVO dimensionally
mis-scaled, covariance decorative); intelligence layer A− design / D verified; tests B
(CI runs 6/257 files).

**Blind top-10:** (1) repair the measurement baseline (TR-reconcile the 730-name panel, retail
costs/PIT/after-tax as measured defaults, registry refresh, OOS lock); (2) drawdown-shaped
over-exposure ⚠ [retracted in Phase 2]; (3) news corpus → cross-sectional alpha ⚠ [self-demoted];
(4) options/IV data (the one genuine void — absent from the OPEN FRONTIER); (5) deep PIT
fundamentals; (6) wire the HMM [retracted]; (7) auction execution [retracted]; (8)
survivorship-complete small-cap panel; (9) preserve deep credit OAS before FRED truncation
loses it; (10) close the LLM eval loop.

**The unbuilt list:** corporate-actions ground-truth feed + dividend accounting in the paper
loop (a split halts the machine); working alerting beyond two CloudWatch alarms; CI covering
what runs in production; an activated OOS lock; a 2027 calendar; failure forensics on the
114-edge graveyard (112 untagged); options/IV as a modality; the Engine B book-level cash
budget fix.

**Five experiments (C1–C5):** the dividend-strip TR audit; vol-term-structure conditioning
for conditional-leverage #3; make the analyst clock real (repair + market-implied baseline);
cross-sectional news kill-fast probe; ALFRED OAS recovery + proxy-robustness receipt. (Full
designs with gates in the conversation record.)

**Trajectory verdict (verbatim):** "This trajectory is healthy — unusually so — and the honest
description of its output is: negative results of institutional quality at a rate few teams of
any size achieve, converging correctly on the true amount of extractable alpha at this
operator's scale, which is approximately zero on price inputs. … What holds the finding rate
below potential is not statistics but a verification asymmetry: measurement claims face
adversarial re-derivation, while integration claims get marked done on code inspection — and
every recent expensive failure is of that class. … The single process change most likely to
raise the rate of real findings: extend the census principle from measurements to integrations
— no wiring claim is 'done' until its first output artifact has been observed and checked
end-to-end. … A broken clock that looks armed doesn't merely delay findings — it silently
converts years of patience into nothing."
