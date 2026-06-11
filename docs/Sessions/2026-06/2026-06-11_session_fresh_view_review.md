# Session Summary: 2026-06-11 (fresh-view full-system review)

## What was worked on

- **Fresh-view full-system review** at the user's request ("months of
  work, no significant progress — what can really be improved?").
  Director session + three parallel read-only subagent audits
  (architect, code-health, edge-analyst). Synthesis written to
  `docs/Audit/fresh_view_full_system_review_2026_06_11.md` and pushed
  to branch `claude/project-review-improvements-e0gy45`.
- **Safe follow-through items** from the review: governor.py engine
  mislabel fixed; capability_ledger Engine E staleness corrected + new
  crisis-HMM-mismatch row; health_check HIGH row added (production
  loads legacy `hmm_3state_v1.pkl`, not the validated crisis model) and
  the factor-α gate next-step re-scoped; dead twin `research/promote.py`
  and `config/backtest_settings.json.bak` archived; `sync_docs.py` run.

## What was decided

- **The review's three diagnoses** (each with file:line evidence in the
  audit doc): (1) the measured system runs ~25-30% of built engine code
  — the −59% MDD baseline is a nearly defenseless mean-variance
  rebalancer; (2) `policy.py` normalization is scale-invariant in
  signal level, so the timing/regime class — the only class that has
  ever validated — was killed by architecture, not evidence, and has no
  first-class validation machinery; (3) apparatus has inverted over the
  product (scripts+tests+docs ≈ 4× engine LOC; live path 64 LOC; never
  traded). Pivot recommendation: regime-aware risk-managed multi-asset
  allocator on cheap betas, Roth-first.
- **Factor-α gate wiring re-scoped USER-GATED, not autonomous**:
  although health_check called it "autonomous-allowed," wiring
  `factors=` would direct-mutate edges.yml (prod `lifecycle_enabled=
  true`, `lifecycle_readonly=false`, `journal=None` on the
  `update_from_trades` path) and T-043 measured 6/7 edges firing —
  shifting arm0 canon mid-T-140/T-118. Sequenced after the wave.

## What was learned

- The recurring flag-true-but-path-dead bug class has a fourth axis:
  even a "one-argument autonomous fix" can be a canon-stability hazard
  when campaigns are in flight. Capability claims need the 3-way join
  (config-flag × call-site-args × branch-reachability) **plus** a
  campaign-sequencing check before any enable.
- `git mv` pre-stages renames — a subsequent selective `git add` +
  commit absorbs them (commit 24ea5d6 contains the archive moves
  alongside the docstring fix; content correct, boundary off).

## Continuation (same session, later): P2 burndown executed

- **Remote-container test environment restored**: the cloud session had
  ZERO Python deps installed (no numpy/pandas/pytest — no test had ever
  been runnable in this environment). Installed the stack (numpy,
  pandas, scipy, sklearn, statsmodels, hmmlearn, scikit-optimize, dash,
  plotly, lxml, ta via --use-pep517, alpaca-py, yfinance, hypothesis).
  Result: 2,363 tests collect cleanly; **2,270 pass; 15 known-red**, all
  data-dependent (need gitignored data/ artifacts: FRED panels,
  cointegration manifests, minimal_c model features). A SessionStart
  dep-bootstrap hook for cloud sessions would make this permanent —
  candidate for the session-start-hook skill.
- **health_check triage** (subagent, lossless): 21 genuinely status-less
  entries → 17 moved to Resolved/Superseded with evidence pointers
  (several presented refuted verdicts as active — the T-055e
  "DEFENSIBLE" entry was the headline supersession violation), 2
  still-active, 2 needs-verification. Two stale Status lines
  contradicting their own RESOLVED/HISTORICAL titles corrected.
- **Scripts archive sweep** (subagent, verified): 32 closed-task
  one-offs → Archive/scripts/ (full T-055 + T-057 chapters, T-036/066/
  089/100 scripts, closed pre-task one-offs, two 0-byte files). 151
  kept under a protected set (test imports incl. the bare
  `from scripts import X` form, living-doc refs, transitive imports,
  all T-116+ in-flight era). Post-sweep full suite == baseline
  bit-for-bit (15 known-red, no new failures). index.md regenerated.

## Pick up next time

- The review's P1 list awaits user decisions: (1) retire the
  factor-negative edge book via T-043 gate post-T-140/T-118; (2) Engine
  B Path A/B consolidation (propose-first); (3) crisis-HMM repoint +
  YZ vol estimator (both propose-first, judged on MDD/crisis hit-rate
  criteria); (4) overlay gauntlet; (5) the 26-yr pivot measurement vs
  SPY/60-40; (6) paper trading. P2 debt burndown list is in the audit
  doc §Prioritized plan (scripts archive sweep, measurement-math
  consolidation, fill/SL-TP parity extraction, health_check triage of
  53 status-less entries, live_trader/ fate decision).

## Files touched

```
docs/Audit/fresh_view_full_system_review_2026_06_11.md (new)
engines/engine_f_governance/governor.py
docs/State/capability_ledger.md
docs/State/health_check.md
Archive/research/promote.py (moved from research/)
Archive/config/backtest_settings.json.bak (moved from config/)
engines/engine_f_governance/index.md (sync_docs)
engines/data_manager/index.md (sync_docs)
scripts/index.md (sync_docs)
docs/Sessions/2026-06/2026-06-11_session_fresh_view_review.md (this file)
```

## Subagents invoked

- **architect** — built-vs-running audit: ~25-30% of engine LOC
  influences a trade; 2.5/10 Engine B defenses live; crisis HMM never
  loaded; vol_target true-but-unreachable; 5 structural problems.
- **code-health** — debt scan: 185 scripts (~122 one-offs), 18
  hand-rolled bootstraps outside MetricsEngine, god functions in every
  hot path, ~6.3K LOC unreachable, health_check 53 status-less entries,
  live_trader 64 LOC / run_live.py 0 bytes.
- **edge-analyst** — washout mechanism confirmed in `policy.py`
  (~264-304); cross-sectional lane dead at this tier; validated-asset
  parts list assembles into the cheap-beta allocator; 6 false-negative
  channels in the falsification machine ranked.
