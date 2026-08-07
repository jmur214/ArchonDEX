# T-338 — THE CLOCK CENSUS: spec + integration proof

**Date:** 2026-08-06 · **Agent:** C · Branch `feature/clock-census-t338` · **0 N_trials** (infra)
*"We can't keep having the silent failures when we should instead be gathering useful data that we missed because of said failures."* Every recent near-miss was **one disease**: a clock believed to be accruing that wasn't. The trading census guards the TRADE; nothing guarded the CLOCKS. This is that guard.

## The contract
- **Artifact-verified, never config-verified.** A config saying "enabled" is not evidence that anything moved; only the artifact's own last-advanced date is.
- **FAIL-CLOSED.** An unverifiable clock (missing artifact, unparseable date, a check that *raises*) is a **MISS**, never a skip. You cannot census what you cannot read.
- **`NOT_DUE` must itself be artifact-derived.** If we cannot establish whether a clock was due, that is a **MISS** too — *"probably not due"* is the same silence the census exists to eliminate.
- **READ-ONLY.** The census observes; it never repairs, backfills, or writes to a clock's artifact. A census that fixes what it measures cannot be trusted about what it found. (Test-locked: bytes and directory listing unchanged after a run over a stale artifact.)
- **ONE REGISTRY**, and a **tripwire test** asserting every `DURABLE_PATH` is either covered by a clock or **explicitly exempted with a reason** — so a new clock cannot be added silently.

## The clocks (19 registered)
| # | clock | how "advanced" is established |
|---|---|---|
| 1 | `analyst_note_written` | a note file exists for `as_of` — **constrained AND agentic** |
| 2 | `eval_scored_when_due` | due-ness from the ledger itself (matured + unscored); advanced = a row scored today |
| 3 | `news_month_pushed` | the current month's partition exists **and its mtime is today** |
| 4 | 12 × `*_rolled` | each book/shadow/tracker's newest state date **== `as_of`** |
| 5 | `scan_filed_when_due` | if `due`, a provenance row for `as_of` — **a self-explained zero (reason enum) COUNTS as advanced** |
| 6 | `stage2_clock_ticked` | last tick == `as_of` |
| 7 | `archive_feeds_in_budget` | **imports B's T-335 `assess_feed_health`** — a health standard is never duplicated |
| 8 | `exec_ledger_on_fill_days` | due-ness from the **orders journal** (fills today), advanced = ledger row today |

Exempted (each with a stated reason): the heartbeat itself (circular), the alerts log (silence is healthy), broker-truth mirrors, derived rollups, spend/tax ledgers that legitimately don't advance daily, and the two fleet files populated only in their own containers.

## Output + escalation
`clocks_advanced n/n` on the heartbeat, plus per-clock detail. **Any miss → `degraded` + the notify channel fires SAME-DAY, naming the failing clock** — a count alone is not actionable. Deliberately **orthogonal to the trading verdict** (like `altdata`): a stalled research clock must not flip `canonical` and fail the Batch job; it fires its own channel. Even a census that *itself* throws prints a loud `[CLOCK-CENSUS][ALERT] … clocks UNVERIFIED today` — a silent census is the disease.

## @E — the drill contract
- **Heartbeat key:** `clock_census`; miss list at **`clock_census.missed[].clock`**; the boolean is `clock_census.degraded`.
- Stall any clock you like during drill week — freezing a book's state date is the cleanest injection — and the census will name it in both the heartbeat block and the notify text.

## ✅ INTEGRATION BAR — met with a REAL injected miss, end-to-end
Not just unit tests. A realistic full-artifact day was built, then **one book was frozen at 2026-07-15** (file still present and well-formed — the exact disease):

```
baseline missed : ['archive_feeds_in_budget']                             (15/16)
after   missed : ['archive_feeds_in_budget', 'book_quality_sat_rolled']  (14/16)
DELTA (injected miss, isolated)      : ['book_quality_sat_rolled']
heartbeat clock_census key present   : True
heartbeat names the clock            : True
notify fired same-day                : True
notify NAMES the clock               : True
```
**PASS** — artifact → detection → heartbeat flag → notify, with the injected clock isolated as the *only* new miss. Locked as a regression test.

*Note on the baseline:* `archive_feeds_in_budget` misses in **both** runs because a synthetic root genuinely has no alt-data feeds — that is the census being **correct about a real absence**, which is precisely why the assertion is on the **delta** rather than on a "clean" baseline. Asserting a clean baseline would have forced me to weaken a true finding.

**19 tests green.** Read-only, fail-closed, tripwired.

## What this changes
**Silence becomes trustworthy.** After this, "no alarm" genuinely means every forward-accruing record advanced — which is the actual deliverable, and the precondition for trusting any of the nine live records the laboratory is accruing.

**T-338 done.**
