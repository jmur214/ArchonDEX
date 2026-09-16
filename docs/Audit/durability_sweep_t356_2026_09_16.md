---
task_id: T-2026-09-16-356
title: THE DURABILITY SWEEP — every writer of a forward record, durable-or-exempted, with the reason on the record
date: 2026-09-16
author: Agent D
type: AUDIT + TRIPWIRE — 0 N_trials. Audit and guard only; fixes route to the owning lanes.
status: FOR REVIEW — 5 gaps reported with owners, none fixed here (boundary respected)
---

# The durability sweep

**Trigger, verified before acting:** C found `deploy_candidate_tracking.json` written to the ephemeral disk and
discarded nightly — account-2 traded canonically and green while its decision-relevant record evaporated
(T-351, merge `04ba1c4`; 09-15/16 are permanent holes). I checked the cited merge record: it says what the
dispatch says it says. T-337 is the same class one venue over.

---

## 0. ⭐ THE CORRECTION THE SWEEP FORCED: "is it in `DURABLE_PATHS`?" is the WRONG QUESTION

`DURABLE_PATHS` is the **paper loop's** registry and defends against exactly **one** failure mode — container
exit. A record written in another venue was never in its scope, so its absence there is **not** evidence of a
defect, and a sweep that treated it that way would have reported ~15 false gaps. The question that generalises:

> **Does this record have a durability mechanism IN ITS OWN VENUE?**

| venue | what it is | mechanism | sweep result |
|---|---|---|---|
| `cloud_paper` | the ephemeral per-day container | `DURABLE_PATHS` / `DURABLE_DIRS` → S3 | ✅ **COMPLETE** — every `paper_trader/*` writer is covered |
| `cloud_batch` | a campaign cell | the entrypoint's per-run S3 upload of `<CELL_ID>/<RUN_ID>` | scoped to run artifacts; `data/governor/` is **not** uploaded |
| `local` | launchd / hand-run on one machine | **git, or nothing** | ⚠️ **where every gap is** |

**`local` is the venue with no default.** A gitignored file on one laptop has no mechanism at all — and that is
not a smaller problem than the ephemeral one, it is a **slower** one. C's failure loses a row per night, loudly
enough to be found in two days. This one loses everything at once, years later, and only when it is needed.

## 1. THE HEADLINE — the record that governs autonomous authority is the least durable record in the system

**`data/state/autonomy_ledger.jsonl`** — the Phase-6 constitutional record, the append-only evidence base on
which autonomous authority is **granted and symmetrically demoted**.

- **Actively accruing:** 18 rows, last written **the day of this audit**.
- **Gitignored. Not in git. Not in `DURABLE_PATHS`. In no S3 sync.** One copy, one machine.
- **Its exposure is NOT C's.** The janitor runs *locally*, so no run loses a row — this is **T-337's** class:
  single-copy loss, unreconstructable, silent. Stating the mechanism precisely matters; calling it "the same
  nightly evaporation" would send the fixer to the wrong place.

The janitor has already solved the *adjacent* problem — `_canonical_root()` resolves the ledger via
`--git-common-dir` so a run from any worktree writes **one** record (it previously split in two and cost a
hand-merge of ten stranded rows). **That fix guarantees the ledger is single. Nothing guarantees it survives.**

**Owner: B (janitor lane).** Not fixed here, per the dispatch boundary.

## 2. ⭐ THE INVERSE DEFECT — a record that is saved and can never accrue

**`data/intel/agentic_analyst_calls.jsonl`** is the `source_path` of `ANALYST_DESK`
(`paper_trader/event_shadow_book.py:104`), whose book `analyst_desk_book.json` **is durable**.

**Nothing in the tree writes that source, and the file does not exist.** It is a **NEVER_ALIVE channel**
(T-342's liveness taxonomy). The module says so honestly — *"ships dormant-but-armed until the feed exists"* —
but the consequence is worth naming:

> C found a record that **accrued and was not saved**. This is one that is **saved and can never accrue**.
> **Both read "too early to say" in every digest, forever.** Durability of a book whose feed does not exist is
> a null guarantee — **and no durability check can catch it. Only a liveness check can.**

That is the boundary of this sweep, stated so nobody mistakes a green durability census for "the records are
accruing." **Owner: E (agentic analyst lane).**

## 3. THE AUDIT TABLE

34 written accruing paths across `paper_trader/`, `engines/`, `core/`, `intelligence/`. Every one is now
DURABLE, EXEMPT-with-reason, an OWNED KNOWN_GAP, or a verified INPUT.

### Gaps (5) — reported, owned, none fixed here
| path | venue | state | owner | note |
|---|---|---|---|---|
| `data/state/autonomy_ledger.jsonl` | local | 🔴 **LIVE** (18 rows, today) | **B** | §1 — the authority record |
| `data/intel/agentic_analyst_calls.jsonl` | cloud_paper | 🔴 **NEVER_ALIVE** | **E** | §2 — no writer exists |
| `data/governor/lifecycle_history.csv` | local | 🟡 dormant (33 rows, 06-13) | F | latent; matters when lifecycle resumes |
| `data/governor/feedback_history.log` | local | 🟡 dormant (488 rows, 04-23) | F | latent |
| `data/research/discovery_log.jsonl` | local | 🟡 dormant (88 rows, 06-17) | **D (mine)** | latent; mine when Discovery next runs |

**Dormant is reported as dormant, not as bleeding.** Three of these have lost nothing in three-to-five months
because nothing is writing them. Calling them active losses would be crying wolf, and the next reader would
discount the two that are real.

### Exempt (with the reason on the record)
`janitor_report.md` (rendered surface, replaced whole) · `janitor_merge_requests.md` (a queue, consumed) ·
`lifecycle_journal.jsonl` (absent — nothing accruing) · `edge_weights.json` (**state, not history** —
regenerable from the lifecycle; sits under `[NN-NO-MANUAL-EDGES]`) · `edge_recommendations.json` ·
`edge_results.csv` (measurement artifacts, regenerable).

**`allocation_recommendations.json` is exempt for an unusual reason worth reading:** it is **absent, and that
is the healthy state.** T-158 found this learned artifact silently overriding `mode→adaptive` on every local
`allocate()`, so **local and cloud ran different trading systems.** Making it durable would preserve a hazard,
not a record.

### Verified INPUTS (flagged by the scan, confirmed read-only)
`data/trade_logs/trades.csv` and `snapshots.csv` are the default arguments of
`governor.update_from_trade_log` (`governor.py:493-494`) — **read, not written.** Recorded so a future reader
does not inherit the scanner's mis-attribution as fact.

## 4. THE TRIPWIRE — `core/durability_census.py`

T-338 idiom: **read-only, artifact/code-derived, fail-closed.** 14 tests.

- **BIDIRECTIONAL, per B's launchd sweep.** An unregistered writer is a fault **and** a registry entry naming
  a writer that no longer exists is a fault. *A one-directional check catches the zombies and misses the
  outage.*
- **A reason is mandatory**, and an owner is mandatory on a gap. *"It exists" is what kept a dead launchd job
  alive for six weeks; an unowned gap is the supersession-dependents failure one layer over.*
- **`KNOWN_GAP` passes the census but is reported loudly** by `open_gaps()`. Deliberate: failing the suite over
  another lane's writer would be hostile and outside this unit's boundary, while an unrecorded gap goes quiet.
  The owner + date + finding-number make it traceable, and a test locks the gap **set** so a later edit cannot
  silently drop one.

**On the scan being deliberately over-inclusive — and why that is not crying wolf.** It joins *"this module
writes something"* × *"this module names a data path"*, which cannot prove that path is the one written (hence
the two verified INPUTs above). **This is a GATE, not an alarm:** it fires **once per unclassified path** and
then never again, so the cost is a one-time classification with the verified nature recorded. The failure mode
worth refusing is a *recurring* alarm on a healthy state; a one-time "classify this" is exactly what stops a
new writer shipping undurable in silence.

**Proven by reversion, not by reading source text** (the 2026-09-14 lesson — 53 green tests passed on a broken
line because they asserted on source rather than executing it): a synthetic new writer in a temp tree **fails**
the census; stripping a reason fails it; removing an owner fails it; a stale writer reference fails it.

## 5. What this sweep did NOT do
- **Fixed nothing.** Five gaps, four owners, all reported with evidence — per the dispatch boundary.
- **Did not sweep `scripts/` or `research/`.** Their outputs are measurement artifacts and one-shot research,
  not accruing records; sweeping them would produce an alarm nobody can action. The janitor's three records are
  carried in the registry by hand instead, and a test asserts that arrangement so it cannot drift unnoticed.
- **Cannot see liveness.** §2 is the proof: a durable book with no feed passes every durability check there is.

---
**AUDIT + TRIPWIRE — 0 N_trials.** 34 paths classified, 5 gaps owned, 14 tests, census green.
