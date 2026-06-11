# Research prompt — AREA-1 EXHAUSTIVE SWEEP: AI-agent safety for a trading codebase (run in RESEARCH MODE)

> The just-in-time follow-up the blind-spots pass itself recommended ("Areas 1.2/1.4
> are the genuinely fast-moving ones... a good candidate for a dedicated Research
> run"). Trigger: our agents are about to wire SEC-filing and news-derived data, and
> we are formalizing per-PR safety gates. Paste below the line; file results here.

---

You are a security/AI-systems researcher with live web access. Training-cutoff-stale
knowledge is the enemy: VERIFY everything on live pages, cite URL + date-checked.
Context: a retail systematic-trading codebase written and operated by LLM agents
(Python/pandas; AWS Batch backtests; Alpaca brokerage planned; one human approver).
We already adopted: golden-master P&L regression + property-based invariants +
forbidden-pattern lint (in build), and the design rule that external text NEVER
enters a privileged agent's context (structured-extraction-only quarantine).
Deliver actionable specs/checklists with citations — no reading lists. **You have NO access to our codebase** — everything you know about us is in this prompt; mark any us-specific inference explicitly as INFERENCE (we verify locally before adopting).

## 1. EXHAUSTIVE incident + technique sweep (the fast-moving half)
- Every documented prompt-injection / data-poisoning incident or demonstration
  involving: financial documents (SEC filings, earnings releases), news/RSS
  aggregation, agentic coding tools (the CurXecute/CVE-2025-54135 class), MCP/tool
  ecosystems — anything 2025→today. For each: vector, what the agent did, the
  mitigation that would have stopped it.
- Adversarial-text techniques relevant to a STRUCTURED-extraction boundary: can
  injection survive into JSON-constrained outputs (schema-smuggling, enum abuse,
  numeric-field manipulation)? Published evaluations of structured-output defenses.
- Data-poisoning of public datasets we consume (GDELT, Wikipedia-derived constituent
  lists, EDGAR): documented cases + integrity-check practices.

## 2. Tooling verification (the claims we're about to build on)
- Open Agent Passport: current state, real adoptions, criticisms, integration cost
  for a Python multi-agent shop. Same for NemoClaw-class kernel-level sandboxing.
- Inspect AI / promptfoo-successor landscape for CI-gated agent evals TODAY; what do
  teams actually run per-PR vs nightly?
- Mutation-testing-for-LLM-tests (the Meta line): anything newer/practical.

## 3. The trading-specific layer
- Any regulatory movement (SEC/FINRA/CFTC 2025-2026) on AI agents in trading
  operations relevant to a retail account that might later manage outside money.
- Broker-API-level kill-switch / circuit-breaker best practices for automated retail
  (position limits OUTSIDE strategy code — the Knight lesson, modern form; what does
  Alpaca natively support?).

## OUTPUT: ranked adopt-list (effort/EV/evidence + citations), a "we are already
covered" list (vs our adopted controls above), a do-not-bother list, couldn't-verify
section. Flag anything that should change our quarantine design BEFORE we ship
filing-text ingestion.
