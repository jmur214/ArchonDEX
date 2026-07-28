# T-326 — the THESIS BOOK: SPEC + FROZEN GATE (report-only)

**Date:** 2026-07-28 · **Agent:** C · Branch `feature/thesis-book-t326` · **0 N_trials** (infra)
Gives D's thesis desk (T-324) a virtual **book**, so a thesis produces a *trading* record and not only a Brier record. Instance **#3** of the shadow-desk parameterization (after the event desk + agentic-analyst desk, T-322). **Report-only, zero order effect.**

## The three mechanics that differ from the fixed-horizon desks
D's handoff named them; each is implemented and tested:

1. **Hold-until-falsified-or-horizon.** A thesis runs months-to-years. A falsifier that fires closes the basket at the **NEXT close** and marks the thesis **FALSIFIED** — a falsifier is not an opinion, it is the pre-stated condition under which the thesis was wrong. **A thesis with no falsifier is PARKED as "a story, not a position"** (D's own rule, enforced at the book layer too).
2. **Twin = SPY over MATCHED windows.** D flagged this explicitly: a thesis is an **equity** bet, so a 60/40 twin would flatter it. Every outcome is scored against SPY over the *identical* holding window.
3. **Multi-instrument baskets.** A thesis names several legs (`primary` / `second_order` / `sector_etf` / `hedge`). The book holds the basket at the thesis's own `weight_hint` proportions, costing **every leg** at the honest **25 bps/side** single-name rate.

## Sizing: a rule, not a silent clamp — **and the applied scale is ON THE RECORD**
> **DIRECTOR RULING (2026-07-28):** the design stands — the clamp-ban protects the model's
> *expressed* intent, and absolute sizing was never the model's to express. **Addition, now
> implemented:** every position record carries the applied scale so a down-sizing is visible
> in the book's history, never discovered by archaeology. Reject stays for malformed input only.

Every open **and closed** record now carries:
`sizing_scale` (what was applied) · `binding_cap` (`per_name` | `gross_x_conviction`) ·
`unconstrained_scale` (what conviction alone would have given) · `downsized` (bool).
A down-sized basket is additionally **announced in the day's `reasons`** (`"sized to 0.3333
(cap=per_name, unconstrained 0.4800) — recorded, not silent"`). Three tests cover the
per-name-bound case, the gross-bound case, and **survival of the provenance onto the closed
record** — which is exactly where archaeology would otherwise bite.

### The rule itself
D's `weight_hint` is a **within-basket proportion** (schema: `[0,1]`, default 0), **not** an absolute portfolio weight. So the absolute size is *this book's* decision, constructed to satisfy both firewall caps up front:

    scale = min( MAX_THESIS_GROSS · conviction ,  MAX_WEIGHT / largest_share )

A concentrated basket is therefore **sized down to the per-name cap rather than rejected** — which is *not* the "reject, never clamp" violation the analyst firewall forbids, because **the model never requested an absolute weight**; nothing of its request is being quietly shrunk. Genuinely malformed input (no legs / no symbols) still **rejects with a logged reason**, and the constructed basket is re-asserted against both caps before use. (Caps: ≤20%/name, thesis basket gross ≤60% — a thesis is a satellite, not the book.)

## Scoring is D's, not mine — ONE standard
The book's job is to produce **`ThesisOutcome`** records (realized basket return + twin return over the SAME window). The verdict comes from **D's own `thesis_scoring.promotion_check`**:
- **≥20 RESOLVED theses per `theme_class`** (D's pre-stated bar #1), **AND**
- **bootstrap CI on the mean log-wealth ratio vs the twin EXCLUDES ZERO** (`ci_low > 0`) — **A's skew-aware metric**, the one that can say a 1-in-5 hit rate is *good*;
- **Brier/calibration reported alongside** — a profitable-but-miscalibrated record is flagged, never silently promoted.
Re-implementing any of that here would create a second standard, which the handoff forbids. `promotion_gates()` calls D's function directly.

## Channel firewall — two sub-books, records never blend
Two `DeskConfig` instances keyed on `origin`: **`MACHINE_DESK`** (`thesis_book_machine.json`) and **`USER_DESK`** (`thesis_book_user_seeded.json`). Each filters the shared feed to its **own** origin, so a user-seeded thesis can never inflate the machine's record (or vice versa) — **the bias-firewall directive applied to scoring attribution.** Tests assert both the loader-level filter and independent state.

## Fail-closed on measurement
| situation | behavior |
|---|---|
| falsifier past its `check_by` **unresolved** | **treated as FIRED** — an expired unresolved falsifier is never assumed benign |
| no falsifier at all | PARK ("a story, not a position") |
| missing leg **or** twin price at exit | position **HOLDS**, day flagged degraded — never an invented exit |
| missing price at entry | park (no fabricated fill) |
| `conviction < 0.50` / no `horizon_days` | park + log |
| feed absent | dormant-but-armed |

## Wiring + durability
Runs in the Account-1 pulse after the event desk; prices fetched **dynamically** for {open basket legs ∪ today's thesis legs ∪ SPY}. Both books added to `DURABLE_PATHS` — **theses hold for months**, so an ephemeral disk would drop live baskets long before their horizon and the ≥20-per-class bar could never accrue. Heartbeat: `THESIS-BOOK[<desk>] days=… open=… closed=… falsified=…`.

**17 unit tests; 84 green across all five books + D's T-324/T-324b suites** (my consumption of their scoring doesn't perturb it). doc_lint clean.

## Honest posture
The book existing is not evidence the thesis desk works — **the record it accrues is**, and it earns nothing until D's pre-stated bar clears per theme_class. Awaiting the first blind-scan filings.

**T-326 armed.**
