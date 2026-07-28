# T-322 — the EVENT-DESK shadow book: SPEC + FROZEN GATE (report-only)

**Date:** 2026-07-28 · **Agent:** C · Branch `feature/event-shadow-t322` · **0 N_trials** (infra)
Gives D's typed event calls a **trading record**, not just a Brier record. Per the user directive that the machine should "act like a trader": a trader's core desk is event-driven — a filing drops, you size a position on it. **Report-only, zero order effect.** Fourth instance of the shadow machinery (after T-276 BTC, T-302 LLM book, T-316 DBMF).

## The gate is NOT new — it is D's own pre-registered bar (ONE shared standard)
T-304's bar #5 reads verbatim: *"Net-of-cost tradability (only if 1-4 clear): **a paper sleeve acting on the calls must beat its sector/market benchmark net of honest small/mid-cap costs**."* **This module IS that sleeve.** So rather than invent a promotion bar, the book imports D's:
- **`GATE_MIN_CLOSED_PER_TYPE = 30`** — D bar #1 (≥30 resolved calls **per event_type**; routine/other excluded from any skill claim).
- **`GATE_REQUIRE_CI_LOW_GT_0`** — D bar #3 (block-bootstrap **`diff_ci_low > 0`**; a point improvement whose CI straddles zero does NOT clear).
- The measured quantity is **excess vs the twin, net of costs** — D bar #5.
By construction the desk record and the Brier record can never disagree about what "good enough" means.

## Construction (frozen at t=0)
- **Qualification:** `materiality ≥ 0.50` **AND** `direction ∈ {bullish, bearish}`. Neutral/uncertain never open a position — **an opinion is not a trade.**
- **Sizing:** `w = 0.20 × materiality`, signed by direction. The analyst firewall bounds (**≤20%/name, gross ≤2.0**) are **re-enforced at this layer** (defense in depth) and a violation is **REJECTED + logged, never silently clamped**.
- **No look-ahead, structurally:** signal-t / **fill-t+1** — a call dated D fills at the *next* session's close (the btc_shadow construction).
- **Holding:** the call's **own stated horizon**, parsed from its `Prediction.horizon`, closed at that day's close.
- **Costs:** `ROUND_TRIP_BPS = 25 bps/side` — honest **single-name small/mid-cap**, deliberately *not* ETF-cheap, because D's bar #5 says "net of honest small/mid-cap costs."
- **The twin:** **SPY over the SAME holding windows** — the honest *"would doing nothing have won?"* comparison. Excess = net position return − twin return over the identical window.

## Fail-closed on measurement (never a fabricated trade)
| situation | behavior |
|---|---|
| horizon unparseable (`"when the dust settles"`, `"soon"`, >252d) | **PARK the call + log** — never guesses a holding window |
| no price for the name | park (no fabricated fill) |
| no price at horizon | position **holds**, day flagged degraded — never closed at an invented price |
| firewall breach (name/gross) | **reject + log**, never clamp |
| source feed absent | **dormant-but-armed** (the T-302 posture) |

## Two desks, ONE machinery (parameterized, not forked)
`DeskConfig` selects the call **source** + state file:
- **`EVENT_DESK`** → `data/intel/event_calls.jsonl` (D's live interpreter) → `data/state/event_shadow_book.json`
- **`ANALYST_DESK`** → E/T-321's agentic-analyst feed → `data/state/analyst_desk_book.json` — **ships dormant-but-armed** and wakes when that feed lands (point `source_path` at it; no code change).
Both are the same class; a test asserts `type(ev) is type(an)` with independent state, so the "no fork" constraint is enforced by the suite, not by discipline.

## Wiring + durability
Runs in the Account-1 pulse after the DBMF shadow. Prices are fetched **dynamically** for the union of {open-position symbols, today's call symbols, SPY} — the desk trades arbitrary tickers, not the sleeve universe. Both state files added to `DURABLE_PATHS`: **open positions carry ACROSS sessions until their horizon elapses**, so an ephemeral disk would silently drop live positions and the ≥30-per-type bar could never accrue. Heartbeat: `EVENT-DESK[<desk>] days=… open=… closed=… mean_excess_vs_twin=…`.

**21 unit tests** (43 across all four shadow books) green; doc_lint clean.

## Honest prior (carried from D's T-304)
**LOW-MEDIUM.** Post-2015 news/event alpha is small and decayed; the credible edge, if any, is in the **discrete high-materiality tail** (going-concern, tender, delisting, non-reliance), not routine flow — which is exactly why the bar is **per-event-type** and why routine/other are excluded from any skill claim. The desk existing is not evidence that it works; the record it accrues is.

**T-322 armed.**
