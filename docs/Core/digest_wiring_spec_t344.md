# Digest wiring spec — Friday pulse step + census clock (T-344)

**Why this exists:** `performance_digest.py` was built 2026-07-28 (T-329) and extended
through v1.3, and had **zero production callers** for a month. The committed digest sat
frozen at its build date while the machine ran. The content was always right; only the
plumbing was missing. *The surface built to watch everything was the last unwatched clock.*

This spec is the fix, in two halves: **E** wires the step (rev30), **C** registers the
clock. It is deliberately small — the generator already enforces its own design laws
(banned pressure words, the 60-day gate, verdicts-off-the-raw-record, missing-streams-
reported), and none of them change here.

---

## Part 1 — the Friday pulse step (owner: E, rev30)

**Placement:** in `intel_pulse` / the account-1 branch, **after** the trackers and books
have recorded the day (the digest reads their persisted state, so it must run last).

**Cadence:** fire when `as_of.weekday() == 4` (Friday). On a Friday holiday the pulse
does not run at all, so the week is simply skipped — the clock below is what makes that
skip **visible** rather than silent. Do not "catch up" a missed Friday on Monday: a
digest is a weekly snapshot, and back-dating one would date-stamp Monday's state as
Friday's.

**Contract:**
```python
from intelligence.analyst.performance_digest import generate
res = generate(streams, as_of=str(today), notes=notes)   # returns {"ok": bool, ...}
```
* **REPORT-ONLY and FAIL-OPEN.** Wrap in `try/except … non-fatal`, exactly like the
  T-308 eval step. A digest failure must never fail the pulse or touch trading.
* **Heartbeat line:** `DIGEST streams=<n> ok=<bool> path=<...>` so the run log shows it
  fired.
* **Durability:** `docs/State/performance_digest.md` is COMMITTED (it is a doc, not
  state), and the dated archive lands in `docs/Measurements/<YYYY-MM>/`. If the pulse
  container cannot commit, it must still **push the rendered markdown to S3** so the
  render is recoverable — a digest that renders and evaporates is the same failure class
  this task exists to close.

**★ Building `streams` — the unit trap, stated so it cannot be re-introduced:**
the live books publish **dollar NAVs against different notionals** (`sleeve_tier_50k` is
a **$50k book vs a $10k twin**). Differencing raw NAVs prints a spectacular false number.
**Pass each book's own normalized `book_growth`/`twin_growth`** (or `excess_growth`); the
generator now prefers those and falls back to NAVs only for index-at-1.0 streams. Same
for `cash_adj`: pass `excess_growth_cash_adj`, not the dollar `*_cash_adj` navs.

**Streams to include** (all eight in the first real render): the four `ALL_BOOKS` live
books via `LiveBook(spec).summary()`, `sleeve_tracking` (account-1), `btc_shadow_tracking`,
`dbmf_shadow_tracking`, `llm_shadow_book`. A stream with no NAV pair is passed as `{}` —
the generator lists it under **Not reporting** rather than dropping it.

## Part 2 — the census clock (owner: C)

Register the digest as a clock so a **missed digest ALARMS** instead of passing quietly:

| field | value |
|---|---|
| `clock` | `weekly_performance_digest` |
| `artifact` | `docs/State/performance_digest.md` (+ the dated archive) |
| `expected_cadence` | weekly, Fridays |
| `staleness_alarm` | **> 10 days** since the artifact's `as_of` (one missed Friday plus slack) |
| `derivation` | **artifact-derived** — read the `as_of` in the rendered file, never a "we ran it" flag. A run-flag would have shown green for the entire month this thing was dead |
| `NOT_DUE` | a Friday holiday is `NOT_DUE`, not `MISSED` |

**The clock must key off the ARTIFACT, not the caller.** The whole failure being fixed
here is that the caller never existed while everything else looked fine; a clock that
trusts a caller's self-report would have reproduced it exactly.

## Verification (before this is called done)

1. **First-artifact proof — DONE:** the first production render is committed
   (`docs/State/performance_digest.md`, as-of 2026-08-26, 8 streams) and archived. It
   was produced from live S3 state through the real generator.
2. **E:** one pulse run on a Friday shows the `DIGEST` heartbeat line and a refreshed
   `as_of` in the artifact.
3. **C:** the clock reports `NOT_DUE` mid-week, `OK` after a Friday render, and **MISSED**
   when the artifact is artificially aged past 10 days.
