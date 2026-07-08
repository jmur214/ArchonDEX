# Session Summary: 2026-07-08/09 — The machine goes autonomous; the offense arc opens and resolves in a day

## What was worked on

- **Account 1's first fully self-triggered run** — CLEAN on every axis (held-book adopt, the ensemble's
  first real fractional rebalance executed and filled in-run, gate-b first slippage sample 0.51 bps PASS,
  news append n_new=163, canonical). The paper machine is genuinely autonomous.
- **The offense arc, opened and closed in ~24 hours** (T-294 → 294b → 297 → 298): vehicle bake-off,
  taxable-futures arm, turnover reduction, asymmetric damping — plus the T-294 calendar-bug correction
  and `core/calendar_guard.py`.
- **T-289 closed** (all four news tests null; the tilt family closed 3/3) and **T-296 closed**
  (double-trend interference). The fleet was provisioned, broke (S3 policy scoping), was fixed, and then
  REALLOCATED by user decision. T-292 (the LLM analyst) unblocked early; T-299/T-300 dispatched as
  idle-window work.

## What was decided

- **The offense config is EXECUTION-BOUND** (T-294, corrected): the undamped-2× charter config's edge
  over buy-hold SPY is +0.25%/yr pretax with a slippage breakeven of **1.55 bps** — E's one genuine SSO
  fill says >5, so as measured it loses. Real money HELD.
- **Deferral beats §1256 60/40** (T-294b): the taxable-futures arm's tax drag equalled its pretax edge
  to the basis point. Permanently closes annually-marked instruments under a never-sell benchmark.
- **T-298 asymmetric damping is the first config to clear the SPY bar** ($89,672 vs $74,104, at every
  slippage grid point; exit-lag ≡ 0) — held EARNED-BUT-DIRECTIONAL because the gain is a path shift to
  ~1.1× mean exposure (a better, calmer strategy — not "2× cheaper") and the CI straddles. Opens the
  user's charter question: was 2× ever the right target?
- **Fleet reallocation (user):** account 1 unchanged (highest confidence, deepest validation);
  account 2 = Option-2 sequencing (undamped armed run → slippage number → damped flip → enable);
  **account 3 DORMANT, its slot RESERVED for the LLM analyst's Stage 2** (the cap is THREE accounts —
  the program plan's "4th account" was a director error, amended). Principle recorded as user feedback:
  **a paper slot is earned by settled science + open execution questions, never filled because capacity
  exists.** The user's confidence ranking (defensive most, BTC least) matched evidence depth exactly.
- **Recovery of the state-lost armed runs:** Option 1, flatten + re-fire on a fresh trade date (same-date
  coids are burned by design — idempotency is a safety property, not a bug).
- Freezes/amendments: T-289c F1 re-frozen to cross-calendar-day materiality (the >30% HALT was timestamp
  granularity); T-298 frozen no-amendments; the external-research triage table updated with the split
  verdict on its #1 finding (decay mechanism CONFIRMED; NTSX/RSSB-as-vehicle REFUTED).

## What was learned

- **The silent-wrongness doctrine crystallized at five instances in two days** (pyarrow no-op, news-universe
  collapse, config-not-outcome S3 push, stale-fill slippage fabrication, calendar-hole reindexing):
  report OUTCOME never config; fail-closed on measurement (no sample beats a fabricated sample); the
  cheapest bug detector is the SIBLING-NUMBER TELL. Prevention shipped for the newest instance
  (`calendar_guard.py`, named regression).
- **Trend layers don't stack, they interfere** (T-296): a gate must read the price of the thing whose
  risk it manages. Internally-overlaid funds are always-long-core candidates, never the gated leg.
- **Six harness defects sat before T-289's first number; two would have lied confidently** — a lone
  significant result in a fresh harness is a bug hypothesis first (a1's fake t=−5.27 look-ahead).
- Agent conduct worth keeping: D's HALT-and-report on F1, D flagging its own pre-registration flaw in
  the arm's favor, E's retraction-before-it-traveled, B's control-run self-correction. The culture is
  the product.
- Data constraints: Yahoo 429s ALL cloud IPs by policy (yfinance = residential-only forever); stooq
  bot-walled; aggressive retries reset volume bans — patience IS the fix.

## State at session end

- **LIVE:** account 1 autonomous on rev16 (guard image); archivers capturing on schedule (verified);
  KXFED/FRED rate-path + news forward-accrual clocks running.
- **IN FLIGHT:** E building T-292's key-free slices + econ-health alerts (the Anthropic key ask is with
  the user); B on T-299 (contribution-vs-gate draft) while the Yahoo quiet window runs; D on T-300
  (advisor-surface consolidation); C deliberately idle (no question currently worth a trial).
- **TOMORROW (market-gated):** account-2 armed run — the persistence-fix proof + the REAL SSO slippage
  number vs the 1.55 bps breakeven → the damped flip → the enable decision (needs the user's
  scheduler:CreateSchedule IAM grant).
- **USER items:** the IAM grant; the dashboard-v2 verdict (redesign still uncommitted); optionally a
  30-second phone-hotspot assist to close T-295; the Anthropic API key when E asks.
- **Next session's first checks:** the armed-run result + slippage number; B's T-295 close; the T-299
  draft freeze; whether the analyst skeleton landed.
