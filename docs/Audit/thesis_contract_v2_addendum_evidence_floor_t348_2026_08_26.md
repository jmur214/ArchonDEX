---
task_id: T-2026-08-26-348
title: thesis_call/v2 ADDENDUM — the EVIDENCE FLOOR + the DUPLICATE GUARD (from scan 6's zero-document filing)
date: 2026-08-26
author: Agent D
type: CONTRACT ADDENDUM to docs/Audit/thesis_contract_v2_FREEZE_t331b_2026_08_13.md — for the director's stamp. 0 N_trials.
status: FOR STAMP. Contract language only; E ships the mechanical n_documents floor on rev31.
---

# v2 addendum — §9 the evidence floor, §10 the duplicate guard

**What happened:** during drill 6's injected news fault the scan called the model on `n_documents = 0`, and it
**filed** — a near-duplicate of its own open power-buildout thesis, recited from priors. Contained same-day
(quarantined; the book mechanically could not open it). These two rules make the containment structural.

**Scope:** contract language for v2, deployable rev28/rev31-era. Extends the stamped freeze; **nothing in §§0-8
of the freeze changes.**

---

## §9 — THE EVIDENCE FLOOR

**The principle:** *a thesis is a reading of the world. A bundle with no world in it can only produce priors.*
And the consequence that makes this load-bearing rather than hygienic: **the null generator IS
priors-without-evidence (freeze §5). A desk that refiles its priors is indistinguishable from its own null,
which destroys the only comparison that could ever prove skill.** The evidence floor is therefore a
**precondition of measurability**, not a quality filter.

### 9.1 The rule
> **No thesis may be filed from a bundle below the stated evidence floor. The scan SKIPS, with a
> self-explaining reason, and the skip is CLEAN** — no model call, no spend, no `record_scan`; the scan stays
> due and retries when the tape returns. (The shape already exists in
> `intelligence/thesis_desk/thesis_scan_runner.py`, `MIN_SCAN_DOCUMENTS`, T-327 drill-6 collateral.)

### 9.2 ⭐ The floor is PER-CHANNEL, not a sum — the current guard does not close the drilled fault
The mechanical floor today tests `n_docs = len(news) + len(events)`. **That sum is satisfiable by events alone
while the news tape is dead — which is precisely the fault that was injected.** One stale event call and a
silent tape passes a sum-floor of 1 and the model gets called on no news at all.

> **BINDING: the floor is stated per channel, and the NEWS channel has its own minimum.** A theme scan reads
> the tape; events are corroboration, not substitute evidence. A bundle failing the news minimum is below the
> floor **regardless of how many events it carries**.

Recorded in the skip reason and the provenance stamp as counts per channel, never as one collapsed number —
the same discipline as T-346's finding that a single collapsed tell hid three mechanisms.

### 9.3 ⚠️ The floor VALUE — provisional, and honestly ungrounded until calibrated
`MIN_SCAN_DOCUMENTS = 1` is, as its own comment says, the *"refuse-literally-empty"* intent. **One document is
a floor against zero, not an evidence floor** — a theme is by definition a pattern across independent items,
and one item cannot establish one.

**I cannot ground the number from our own record:** the scan provenance log
(`thesis_scan_provenance.jsonl`) is not present locally — the canonical scans ran in-cloud. **Setting a
precise number without that distribution would be inventing a threshold and calling it a standard.** So:

- **Provisional floor, pre-registered:** `news ≥ 5` **and** `news + events ≥ 8`. Rationale is structural, not
  fitted: below ~5 independent items there is no cross-item pattern for a *theme* to be read from, only a
  single story to be paraphrased.
- **REQUIRED calibration step before the floor is final:** read the actual per-channel counts from the cloud
  provenance log across scans 1-6 and report the distribution. **If a healthy scan routinely sits near 5, the
  floor is too high and starves the record; if healthy scans sit at 40+, the floor is not doing any work.**
  Either way the number is then set on evidence and frozen.
- **The floor is revisable ONLY by a new pre-registration**, never tuned after a scan whose output someone
  disliked. It is stamped into each scan's provenance record so a change is visible in the artifact, not just
  in code.

**The honest cost, stated:** a floor that is too high means **weeks with no thesis filed**, and the forward
record accrues more slowly. That is the correct trade — *v1 was cheap and unmeasurable* (freeze §8), and a
prior-recitation is worse than a skip because it enters the record wearing the same clothes as a real thesis.
**A skip is legible; a fabricated thesis is not.**

### 9.4 ⭐ The floor changes the NULL COMPARISON — a selection effect that must be handled
If the desk files only on high-evidence days while the null generator files on all days, **the two are scored
on different populations** and the comparison silently becomes desk-on-good-days vs null-on-all-days.

> **BINDING: the null generator is evaluated on exactly the scan dates the DESK actually filed on** — never on
> all dates. Skipped scans are excluded from both arms, symmetrically, and the count of floor-skipped scans is
> reported alongside any skill estimate.

## §10 — THE DUPLICATE GUARD

> **A new thesis whose instruments majority-overlap an OPEN thesis is REJECTED as a duplicate, with a pointer
> to the open thesis.** Re-derivation of an open thesis is **CONFIRMATION** — worth a note on the open record,
> **never a second basket**.

### 10.1 🔴 THE FIREWALL TRAP — the guard runs against OPEN MACHINE THESES ONLY
This is the rule's most dangerous edge and it must be written down before anyone implements it.

> **BINDING: the duplicate check compares ONLY against theses with `origin == "machine"`. A machine thesis
> that duplicates a USER-SEEDED thesis MUST BE FILED.**

Two independent reasons, either sufficient:
1. **It would have destroyed the desk's best result.** In T-325 the machine, provably blind, independently
   converged on the user's own picks (the AI picks-and-shovels theme — VRT + ETN, NEE, XLU). **Under a
   duplicate guard scoped to include user-seeded theses, that convergence would have been rejected as a
   duplicate and never recorded.** The convergence *is* the evidence; suppressing it is the one outcome worse
   than not looking.
2. **It is a firewall breach by construction.** Rejecting a machine thesis because it matches a user seed
   lets user-seeded content **shape the machine's output**, which is exactly what `assert_bundle_is_blind`
   exists to prevent (T-324b). The existing `load_machine_theses` already filters to `origin == "machine"`;
   **the guard must use that path and no other.**

### 10.2 ⭐ Instrument overlap is PRIMARY; theme_class is NOT a necessary condition
The dispatched rule reads *"same theme_class AND majority-overlapping instruments."* **`theme_class` cannot be
a necessary condition**, for two reasons that both follow from the taxonomy being CLOSED and small (7 classes,
freeze-era `THEME_CLASSES`):

- **Collision is the norm, not a signal.** Two genuinely distinct `supply_demand` theses (lithium; natural gas)
  share a class every time. The class contributes almost no discriminating power — the overlap does the work.
- **Requiring it creates a one-word bypass.** The same power-buildout basket filed as `supply_demand` one week
  and `picks_and_shovels` the next evades the guard entirely. **The very recitation this rule exists to stop
  could relabel its way past it.**

> **BINDING: majority instrument overlap alone triggers the duplicate verdict. A theme_class MATCH is
> corroborating; a theme_class MISMATCH at high overlap is MORE suspicious, not exempt** — same basket, new
> story — and is filed as `duplicate:relabelled` with both classes recorded.

### 10.3 The overlap test, stated exactly
```
overlap = |symbols(new) ∩ symbols(open)| / |symbols(new)|     # denominator = the NEW thesis
duplicate  iff  overlap > 0.5   against ANY open machine thesis
```
- **The denominator is the NEW thesis, deliberately.** A new 3-name basket that is a subset of an open 12-name
  basket is a re-derivation (overlap 1.0) even though the open thesis is far broader. Using the union or the
  larger set would let a narrow recitation slip through.
- **Symbols compare across ALL instrument roles** (core and `second_order` alike). A basket re-derived with
  the roles permuted is the same basket.
- **`OPEN` is defined as:** filed, and NOT (a) closed by a fired falsifier, (b) past its stated horizon, or
  (c) carrying a quarantine row. All three are readable from the append-only ledger; **no new state is
  introduced** and no filed record is ever mutated.

### 10.4 The confirmation note — and the non-use that keeps it honest
A rejected duplicate is **not discarded**. An append-only `confirmation` row is written against the open
thesis: `{thesis_id, confirmed_on, scan_ordinal, overlap, theme_class_new, rejected_thesis_payload_hash}`.

> **NON-USE (binding): a confirmation note is PROVENANCE, never a scoring input.** It does not add to `n`, does
> not raise the open thesis's prior, conviction, size or standing, and never enters a promotion bar. A desk
> that could improve its own record by re-deriving its own theses would have found the cheapest possible way
> to manufacture evidence.

Nor does the rejection consume a `theme_class` slot or count as a filed thesis: **the scan reports
`filed`, `rejected:duplicate`, and `skipped:evidence_floor` as three distinct counts**, and the digest reports
them separately. Collapsing them would reintroduce exactly the "one number, three mechanisms" defect.

## §11 — Builder's delta (additions to freeze §7)
- `intelligence/thesis_desk/thesis_scan_runner.py` — replace the scalar `MIN_SCAN_DOCUMENTS` with the
  per-channel floor (§9.2); keep the existing clean-skip shape and the no-spend/no-`record_scan` semantics
  unchanged. Stamp per-channel counts into the provenance record. *(E, rev31.)*
- `intelligence/thesis_desk/thesis_scan.py` — the duplicate guard on the scan's filing path, sourcing open
  theses via `load_machine_theses` **only** (§10.1).
- `intelligence/thesis_desk/thesis_scoring.py` — the null generator restricted to the desk's filed scan dates
  (§9.4); confirmation rows excluded from every count and every bar (§10.4).
- **Tests that must exist:** a bundle with 0 news and many events is BELOW the floor (the named regression for
  the drilled fault); a floor skip spends nothing and leaves the scan due; a machine thesis duplicating a
  **user-seeded** thesis IS FILED (the T-325 regression); a relabelled high-overlap basket is caught; a
  confirmation row changes no score, count or bar; the three outcome counts stay distinct.

---
**ADDENDUM — for the director's stamp.** Contract language only; nothing built. **0 N_trials.** §9.3's floor
value is PROVISIONAL pending the calibration read, and is frozen once set.
