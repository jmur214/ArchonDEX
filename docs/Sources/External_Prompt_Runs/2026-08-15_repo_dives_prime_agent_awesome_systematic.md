---
run_date: 2026-08-15
agent: two delegated deep-dive research agents (general-purpose, WebFetch/WebSearch), briefed
  with full ArchonDEX context incl. the refuted list
requested_by: user ("really dive into these repos... anything that will give us a leg up")
targets: github.com/PrimeIntellect-ai/prime-agent · github.com/paperswithbacktest/awesome-systematic-trading
status: triaged 2026-08-15 (director dispositions below); full verbatim reports in the session
  transcript (87b8cee4, task outputs a1112a85/a452d0f3)
---

# Repo dives — prime-agent + awesome-systematic-trading (2026-08-15)

## Consolidated director dispositions

### ADOPT / DISPATCH
1. **T-341 (B): validate the paperswithbacktest Hugging Face datasets** — free, claimed
   survivorship-aware daily stocks 1962→present (incl. delisted), ETFs 2000→, 1-min bars
   (huggingface.co/paperswithbacktest). If the dividend/delisting audit passes (the
   T-256/Stooq paranoia applies in full), this is a candidate [NN-MBL] substrate extension
   + free fuel for the queued Gao-momentum intraday probe. Validation FIRST; nothing
   canonical touches it before the audit.
2. **Gate-with-bounded-repair (E, POST-ignition; queued, not now)** — from prime-agent's
   `--autonomous-gate` pattern: a rejected analyst note / constructor output currently ends
   the stream's day; feed the firewall's EXACT rejection reason back for ≤2-3 capped repair
   attempts. The firewall stays authoritative and fail-closed — repair raises valid-artifact
   YIELD without weakening any safety property. Do NOT scope-creep into the account-3
   integration pass; it's a clean small unit after ignition.
3. **Per-cell idempotent campaign resume (B, before the next big campaign)** — from
   verifiers' `--resume`: completion manifests so a re-submitted Batch campaign re-runs
   only missing/errored cells; a cell is "done" only if its artifact exists and passes
   census. Low priority until a campaign is imminent.

### PROBE (pre-registered, queued on the science board)
4. **Overnight close→open EXECUTION-TIMING overlay** (SSRN 3829582) — not alpha (cost-dead
   standalone, per the paper itself); conditioning WHEN an already-decided rebalance
   executes. Zero incremental trades; paper-lab twin-able. Distinct from any refuted
   closure (those were overnight-as-strategy).
5. **OpEx-week effect** (Stivers & Sun; replication moderated-but-alive ~0.2%/wk) — ONE
   low-priority trial; structurally distinct from the refuted FOMC family (hedging-flow
   mechanics, not announcements); honest prior = straddle.

### BANK (doctrine/evidence, no build)
6. **Prime-agent's own Factorio reward-hacking admission** — they shipped unsupervised
   self-refinement and immediately observed the agent "optimized cheating rather than
   legitimate strategies." Independent empirical support for forward-only Brier promotion,
   pre-registration, and [NN-AI-GATE]. Quote whenever "let the analyst tune itself"
   resurfaces (T-305's contested strategy-learning thread).
7. **Provenance-stamped prompt edits** — if analyst prompts/skills ever evolve on Brier
   outcomes: every edit carries a machine-readable trigger (which resolved predictions
   motivated it) + outcome stamp + revert-by-ID; base prompts immutable. Pre-registration
   applied to prompt evolution.
8. **Coalesce missed ticks** — after an outage, a catch-up fires ONCE, never replays every
   missed invocation (ops note for E's scheduler docs).
9. **Filing-change score as a thesis-desk RISK FLAG only** — Lazy Prices sign-flips under
   survivorship cleaning (alpha in the short leg); zero-cost forward accrual off the
   existing EDGAR archive as a negative-attention marker for D's desk, never a tilt.

### SKIP (earned, with reasons)
- prime-agent's RLM code-execution architecture (trades our strongest injection defense —
  no-arbitrary-execution + schema-enforcement — for token efficiency we don't need at
  ~$0.03/call; their own docs: "not a security sandbox").
- GEPA/teacher-LLM prompt optimization on historical outcomes (a purpose-built overfitting
  machine; only admissible forward-window→next-forward-window, pre-registered).
- Their ops stack (interactive-session infrastructure; EventBridge + fail-closed +
  heartbeat + T-338 census is the stronger regime for scheduled batch — and their docs
  have no [NN-FIRST-ARTIFACT] counterpart at all).
- awesome-systematic-trading's libraries (nothing beats the in-house measurement stack;
  MlFinLab license-encumbered and redundant; Qlib/FinRL = AI-on-OHLCV, the exhausted
  shape), its seasonality family ex-OpEx (turn-of-month decayed to insignificance), its
  strategy table (point-estimate Sharpes that would fail [NN-SHARPE-CI] on arrival), and
  its commodity/FX papers as third-stream candidates (need futures books; the ETF-wrapped
  version IS DBMF, already the T-316 shadow).

## The meta-finding
Both dives independently confirmed the program's map: ~85% of the systematic-trading list
is territory already covered or refuted here, and the agent-tooling frontier's flagship
ships with the exact Goodharting failure our doctrine exists to prevent. The durable value
of these sweeps is one free dataset to validate, one yield-raising repair pattern, two
cheap probes, and third-party evidence that the fences are in the right places.
