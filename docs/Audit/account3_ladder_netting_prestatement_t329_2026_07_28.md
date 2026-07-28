---
title: "Account-3 stream ladder + netting policy — PRE-STATEMENT (write now, build at stage-2)"
task: T-2026-07-28-329
status: PRE-STATED — written BEFORE account-3 exists and BEFORE any stream can disagree
---

# T-329 — the account-3 stream ladder + netting policy

Account-3 is the reserved slot (per the 2026-07-09 fleet reallocation: **slots are
EARNED, not filled**). This doc is written **now, before the account exists**, so the
rules that decide "who gets to trade it and what happens when they disagree" cannot
be written after seeing which stream is winning. Build at stage-2.

---

## §1 — The stream-addition ladder

Streams join account-3 **one at a time**, each on its own pre-frozen bar. A stream
that has not cleared its bar does not trade the account — no exceptions, no
provisional allocations.

| # | Stream | Joins when | Bar (frozen elsewhere — cited, not re-set here) |
|---|---|---|---|
| 1 | **Constrained analyst** | at launch | G0 already cleared (stage-0 operational gate) — it is the *only* stream at launch |
| 2 | **Event desk** (D/T-304) | on its frozen T-304 bar | the event-call bar as frozen in T-304's pre-registration |
| 3 | **Thesis book** (D/T-324) | on `promotion_check` | `thesis_scoring.promotion_check` — the pre-stated per-theme bar (log-wealth ci_low > 0), NOT a pooled or story-based call |
| 4 | **Agentic analyst** (E/T-321) | only after the T-323 A/B | needs `B_WINS` in `ab_constrained_vs_agentic`; a tie **keeps the constrained stream** (T-323 §1.2) — a tie is not a reason to add surface |

**Ladder laws.**
- **One stream at a time.** Two streams joining together makes attribution
  impossible — and attribution is the entire point of the account.
- **A stream's bar is the one frozen in ITS OWN pre-registration.** This doc cites
  bars; it never re-states or relaxes them (that would be goalpost-moving by
  indirection).
- **Joining is reversible.** A stream that stops clearing its bar is removed from the
  account (its book keeps running on paper and keeps being scored). Removal is not a
  punishment; it is the ladder working.

## §2 — The netting policy (pre-stated before it can matter)

**The situation:** two streams take opposite positions on the same ticker — the
analyst is long AAPL, the thesis desk wants it short (or flat).

**PROPOSED RULE (for director/user ratification): streams are INDEPENDENT
SUB-BUDGETS. No netting. Disagreement is REPORTED as signal.**

- Each stream gets a fixed fraction of account-3's NAV as its own sub-budget and
  trades **only within it**. Stream A's long and stream B's short both exist; the
  account's net exposure is simply their sum.
- **Why no netting:** netting destroys attribution. If A's +100 shares and B's −100
  shares collapse to a 0-share order, then in six months neither stream has a record
  — you cannot score what was never expressed. **The account exists to produce
  scoreable per-stream records; netting is the one policy that guarantees it can't.**
- **Why not "loudest conviction wins":** it makes the account a conviction-weighting
  experiment (an untested mechanism) rather than a per-stream ledger, and it hands a
  systematic advantage to whichever model states higher confidence — a known LLM
  artifact, not a skill signal.
- **Disagreement is DATA.** Every cross-stream conflict is logged
  (`data/intel/stream_disagreements.jsonl`: date, ticker, streams, directions, sizes)
  and reported in the digest + fleet table. It feeds the same question as T-323 §2:
  *is disagreement itself informative?* Pre-stated there, measured here.
- **The one hard constraint:** the ACCOUNT-level risk limits (gross exposure,
  per-name cap, drawdown kill) apply to the SUM across streams and bind absolutely.
  If the sum breaches a limit, **all streams are scaled down pro-rata** — never one
  stream silenced in favor of another (that would be a discretionary override
  wearing a risk-limit costume). Engine B owns this; propose-first.
- **Wash-sale interaction:** cross-stream trades in the same account still route
  through the T-317 guard. Two streams disagreeing on a ticker can manufacture a
  wash sale between themselves; the guard is the authority and REFUSES loudly.

## §3 — Per-stream attribution from order #1

**`client_order_id` prefix carries the stream, from the very first order.**

```
coid := "<stream>-<account>-<YYYYMMDD>-<seq>"     e.g. "thesis-a3-20260901-001"
stream ∈ {analyst, agentic, event, thesis}
```

- Retrofitting attribution later is impossible — fills are immutable history. The
  prefix must be there from order #1 or the account's record is permanently
  ambiguous. (This is the cheapest possible insurance and it costs nothing now.)
- The existing `make_client_order_id` (`paper_trader/order_manager.py`) already
  builds a prefixed, ≤128-char, greppable id — **extend it with the stream token;
  do not invent a parallel scheme.**
- Every fill, journal line, tax lot, and digest row inherits the stream token, so
  per-stream P&L, per-stream twin comparison, and per-stream wash-sale state all fall
  out mechanically rather than being reconstructed by guesswork.

## §4 — What this does NOT do

- It does not authorize account-3, fund it, or set a date. **Slots are earned.**
- It does not re-state any stream's bar (each is frozen in its own pre-registration).
- It does not decide the sub-budget fractions — that is a director/user allocation
  call at stage-2. The *structure* (independent sub-budgets, no netting) is what's
  pre-stated here, so the allocation decision can't quietly become a netting decision.

**T-329 §2 pre-statement frozen: streams are independent sub-budgets; no netting;
disagreement reported as signal; account-level limits bind pro-rata.**
