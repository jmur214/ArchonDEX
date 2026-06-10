# RESULTS — blind-spots hunt, single pass WITHOUT research mode (2026-06-10)

> Provenance: user ran `PROMPT_blind_spots.md` without the deep-research feature.
> Output self-grades: Areas 2/3/4 = stable literature, "close to complete"; Areas
> 1.2/1.4 (injection incidents, post-cutoff agent tooling) = fast-moving → a
> dedicated research-mode sweep of AREA 1 ONLY is the optional follow-up. Director
> verdict: no full rerun. Time-sensitive items it DID verify with citations: OWASP
> LLM top-10 ranking, CVE-2025-54135 "CurXecute" (Cursor agent hijack via planted
> document text), FINRA prompt-injection resource (2026-03-06) + 2026 oversight
> report GenAI section, OAP (March 2026, 0% vs 74.6% attack success), NVIDIA
> NemoClaw, mutmut/cosmic-ray, Shumway −30/−55 conventions, Norgate delisted-symbol
> format, Carver Starter System parameters.
>
> DIRECTOR ACTIONS TAKEN ON THIS (2026-06-10): T-118b pre-registration committed
> pre-unblinding (docs/Audit/t118b_preregistration_2026_06_10.md, adapted from §2.3);
> Shumway −30/−55 + worst-case −100% sensitivity folded into A's staged T-136
> Part A; golden-master/property-suite/forbidden-lint bundle staged for B (T-138);
> quarantine + structured-extraction-only adopted as the standing design rule for
> any future free-text ingestion (T-137 is already structured-fields-only).

## AREA 1 — AI-agent-run codebase safety
Defense catalog ranked (effort/EV): 1. **Golden-master regression** on the numeric
pipeline (frozen hashed input window; replay; assert_frame_equal rtol=1e-9 on
positions/signals/P&L; any diff blocks merge + human-readable diff report) + a
**shadow-backtest-diff** job on every PR touching signal/risk code (ΔSharpe,
Δturnover, Δmax-position must be justified in the PR). 2. **Property-based tests
(hypothesis)** — the financial invariant set: NO-LOOKAHEAD (truncate-after-T must
not change signals ≤T), SIGN ANTISYMMETRY (negate forecast → negate position),
UNITS (decimals-vs-percents scale check), P&L CONSERVATION (Σ per-instrument = 
portfolio; cash+MV=NAV every bar), SCALE INVARIANCE, IDEMPOTENCY. 3. **Data
contracts (pandera) + forbidden-pattern lint** (CI fail on `.shift(-`,
`iloc[...+1]` in signal code, tz-naive timestamps, bare fillna on returns).
4. Differential testing of critical math. 5. **Mutation testing** scoped to
signal/risk/execution modules, WEEKLY not per-PR (mutmut fast path; cosmic-ray for
kill matrix); surviving sign-flip/arithmetic mutants = P0; use survivors to direct
agents to write the missing tests (Meta 2025 precedent).
CI gate stack verbatim: mypy --strict → pandera → unit+property → golden master →
forbidden-pattern lint → shadow backtest diff → human approval on any nonzero diff.

**Injection/poisoning (1.2):** EDGAR text is attacker-writable at near-zero cost;
GDELT aggregates the open web. Indirect prompt injection = OWASP LLM #1; CurXecute
(CVE-2025-54135) is the structural precedent (planted document text → agent
silently writes malicious config). No documented filings→trading-agent incident =
"not yet public," not "not possible." MITIGATION ARCHITECTURE (standing design
rule, adopted): (1) QUARANTINE — external text never enters the context of any
agent holding write/execute/trade privileges, period; (2) STRUCTURED-EXTRACTION-
ONLY — a privilege-less extractor may output ONLY a constrained JSON schema
(numerics/enums/bounded strings) validated by an allowlist parser; (3) only
numeric/categorical features cross into the trading system; (4) spotlighting as
defense-in-depth only (classifiers leak ~7%); (5) anomaly tripwire on
imperative-voice strings in filings → human review.
**Multi-agent failure modes (1.3):** state divergence → single source of truth in
versioned files, no unwritten session-state; assumption drift → contract tests at
agent boundaries + halt-on-un-ADR'd-assumption; verification debt → mutation
testing + test-writer-never-sees-implementation. No public AI-trading post-mortems;
Knight Capital 2012 remains the canonical automation lesson (deploy verification,
kill switches + position limits OUTSIDE strategy code). FINRA: tech-neutral rules;
human-accountable supervision of AI output is the right internal standard.
**Post-cutoff tooling (1.4):** OAP (Mar 2026) — pre-action policy authorization
outside the agent process, signed audit records, 0% vs 74.6% attack success,
~53ms; NemoClaw (Mar 2026) — kernel-level allowlisting, principle: policy
enforcement must live OUTSIDE the agent process; Inspect AI v0.3.225 actively
maintained; OpenAI acquired Promptfoo (Mar 2026). CI pattern: baseline on a golden
set, block on regression not absolute threshold.

## AREA 2 — Rare-event overlay validation
Conditional event-study evaluation, NOT unconditional Sharpe differencing
(Kaminski crisis-alpha; Israelov "Pathetic Protection"; Ilmanen tail-risk work).
Episode definition must be MECHANICAL: S&P 500 TR peak-to-trough DD ≥15%, window =
peak→trough +20td (better than worst-month ranking for a transition-triggered
mechanism). Small-N stats: the EPISODE is the observation unit — exact binomial
sign test across episodes + within-episode block bootstrap (5-10d blocks, never
across the full sample) + Bayesian credible interval reported descriptively. ONE
hypothesis with 6 observations → no multiplicity correction UNLESS per-episode
claims are made (don't). CALM-DRAG CEILING is co-equal and carries the actual
statistical power (calm periods are long): pre-register conditional drag bound
(common framing: drag ≤ ~25-33% of episode-frequency-annualized crisis benefit).
What survives scrutiny: SG-index-style full-period + pre-defined crisis windows on
the same page. What doesn't: Universa-style sleeve-return accounting (the +3,612%
March-2020 number was return on premium-at-risk, not portfolio capital — Weinstein/
Brown critiques; CalPERS case study). AQR's put-drag literature: always-on
convexity loses to trend-style CONDITIONAL de-risking net of bleed — our overlay's
design family. → T-118b template ADOPTED + COMMITTED (see Audit/).

## AREA 3 — Survivor-bias repair (delisting returns)
Conventions (verified): impute **−30%** (NYSE/AMEX) / **−55%** (Nasdaq) for
performance-related delists with missing returns (Shumway 1997; Shumway-Warther
1999; BMP 2007). CRSP codes: performance = 500, 520-584; mergers 200-299 (~51% of
delistings) need NO imputation (terminal price embeds deal terms). Nasdaq bias
~4.7× NYSE/AMEX; correcting it erased the Nasdaq size effect (the canonical
magnitude demonstration). Delist rates: ~1.2%/yr NYSE/AMEX vs ~5.6%/yr Nasdaq
(performance-related). Modern replications just use −30/−55.
**How close does free get us:** survivorship damage = (A) wrong universe + (B)
missing terminal decline path + (C) missing delisting return. Free PIT membership
fixes (A) = the dominant term; imputation fixes (C) on average. Residual biases
(direction: optimistic): truncated final-decline paths; strategies selecting INTO
distress realize worse-than-average delists. For an S&P large/mid universe with
exit rules, residual after (A)+(C) is small; material for small-cap/hold-to-zero.
Free delist dates/reasons: EDGAR Form 25/25-NSE (reliable ~2002/2006+); a cheap
curated 36k-filing dataset exists (apify blackfalcondata). THE REAL GAP: pre-2002
delist metadata — likely no clean free source; strongest single argument for
Norgate IF early-window fidelity proves load-bearing.
**Decision rule (ADOPTED into T-136):** run membership-correct retest WITH −30/−55
imputation + a worst-case (−100% on performance delists) sensitivity band. Buy
Norgate ($630/yr; delisted symbols suffixed e.g. JAVA-201001) iff: survivor
inflation proves load-bearing (flips a decision), OR the worst-case band changes
any go/no-go, OR we go below Russell-1000 / add shorts. Cloud-license: email
Norgate before any purchase; the workable pattern is a licensed Windows VM as a
data station exporting snapshots — compliance for an agent pipeline is a VENDOR
question.

## AREA 4 — Factor-premia deployment blueprint
Verified Carver anchors: Starter System = 16/64 MAC, stop 0.5× annual σ from HWM,
12% vol target (= half-Kelly on SR≈0.24 single-rule), ~5.4 trades/yr; fast:slow
2-6 acceptable. Parameter table (ETF translation): $5K = 2-3 ETFs (SPY + TLT/IEF +
GLD), EWMAC 16/64 core (+8/32, 64/256 as capital allows), forecasts scaled to
avg-abs-10 capped ±20, vol target 12% (≤15% this account), EWMA ~32d vol estimate,
weekly check + ~10% buffering, cost speed-limit ≤ ~⅓ expected SR. Expected:
single rule/instrument SR ≈0.24 pre-cost; diversified 8+ instruments × 3 speeds
≈0.5-0.8 pre-cost / **0.4-0.7 net (RANGE, not audited)**; MDD 15-25% at 12-15% vol.
Staircase: $5K = 2-3 ETFs, IDM capped ~1.2-1.4 by instrument count (fractional
shares at Alpaca remove the whole-share bind at THIS tier); $25K = 6-10 ETFs, 2-3
speeds, IDM ~1.7-2.0; $50K = first micro-futures viable + Carver dynamic
optimization designed for exactly this; $100K = 4-6 micros + ETF satellite, 60/40
§1256 tax treatment. After-tax: trend (ST-gain-heavy) → Roth; slow tilts →
taxable; IL flat 4.95% on top of federal ST. PLAIN STATEMENT: at $5K and a
generous 0.6 net Sharpe/12% vol ≈ ~$430/yr pre-tax — "below ~$25-50K this is
education with positive expected tuition rebate, not income"; the real ROI at
current size is the validated infrastructure + falsification discipline.
Critiques adopted with eyes open: 2018-2020 quant winter (multi-year premia
drawdowns arrive when conviction is newest); trend crisis-alpha is crash-SPEED
dependent (2020 muted, 2008/2022 strong) — exactly why T-118b includes fast AND
slow episodes, and the argument FOR a transition-trigger over slow trend; the
paper-to-realized gap is mostly the operator.

## TOP-8 ADOPT (researcher's, with director routing)
1. Golden-master + shadow-backtest-diff CI gate → staged T-138 (B).
2. Hypothesis property suite (no-lookahead/sign/units/P&L) → T-138.
3. Quarantine + structured-extraction-only JSON boundary BEFORE any free-text
   ingestion → standing design rule (T-137 already structured-only).
4. OAP-style pre-action authorization outside the agent process → evaluate after
   T-138 (the approval-gate formalization).
5. T-118b pre-registration → DONE, committed pre-unblinding.
6. Calm-drag ceiling as co-equal criterion → in T-118b §4.
7. Membership-correct retest + Shumway imputation + worst-case band → T-136 Part A
   (updated); Norgate deferred until that number exists.
8. Sleeve-to-account tax mapping (trend→Roth) → fork input.

## DO-NOT-BOTHER (adopted)
Whole-repo/per-PR mutation testing (scope+weekly); injection-detection classifiers
as primary defense; full-window Sharpe-diff CIs for the overlay ("stop
relitigating"); buying Norgate before the survivor-inflation number exists;
futures/options/>15%-vol below $50K; Universa-style sleeve accounting in any
internal report, ever.

## COULDN'T VERIFY
No public filings→trading-agent injection incident (absence of evidence only);
Norgate cloud/VM/agent licensing (vendor email required); AFTS ch.25 dynamic-opt
minimum-capital tables + exact buffering fractions (training knowledge — verify
before coding); SG Trend exact Q1-2020/2022 figures + AQR retrospective URLs;
BMP code-level refinements beyond −30/−55 (paywalled); pre-2002 free delist
metadata (likely doesn't exist cleanly).
