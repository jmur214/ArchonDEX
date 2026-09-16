# T-350 Act 2 — the ARRIVAL EVENT: pre-stated, before it happens

**Written 2026-09-11 00:2x CDT, BEFORE the transition executes and before the
first deploy-candidate firing.** The point of writing it now is that an artifact
you predicted is a verification; an artifact you explain afterwards is a story.

## Why this event matters

The arrival event is the lump-sum deployment of a tier into the allocation — the
single highest-stakes execution moment any future real transition would face, and
the one thing no amount of daily rebalancing rehearses. It happens **once**, and
it is deliberately NOT run from the migration script: it belongs to the first
SCHEDULED firing under `deploy_candidate`, observed as its own artifact per
`[NN-FIRST-ARTIFACT]`.

## Pre-flight state, verified tonight (not assumed)

| item | verified |
|---|---|
| transition dry-run | script runs end-to-end, exit 0 |
| broker snapshot | `positions_before={"SSO": 149}` — the legacy offense position |
| dry-run restraint | `TRANSITION DRY-RUN would_sell qty=149 SSO` — read the broker, sold nothing |
| state to archive | 6 objects (orders/ledger/recon/tracker/heartbeat/alerts) |
| notional cap | live `ARCHONDEX_SLEEVE_NOTIONAL_CAP=10000` → MATCHES the arrival tier |
| rev34 image | `paper-sha-c288c42` built from merged main, verified IN-CONTAINER |
| in-container config | VOO 0.85 / MTUM 0.15 / cash SGOV; bands buy 1.5q > sell 1.0q; max_drift 0.10 |
| in-container wash classes | VOO → `US_LARGE_BLEND` (the acct-1 coupling), SGOV → `TBILL_ULTRASHORT` |
| contributions month-0 | $10,000 — the lump sum is NOT double-counted as a contribution |

## THE PRE-STATED ARRIVAL PLAN

Constructed in-container at indicative prices (VOO 600 / MTUM 230 / SGOV 100) on a
$10k tier, from flat:

```
BUY 14 VOO   (10000 × 0.85 / 600 = 14.16 → 14, conservative truncation)
BUY  6 MTUM  (10000 × 0.15 / 230 =  6.52 →  6)
BUY  2 SGOV  (the cash leg sweeping the whole-share residue — no idle dollar)
```

**Real fills will differ in QUANTITY** because real prices differ from these
indicative ones — that is expected and is NOT a discrepancy. What must hold is the
SHAPE:

1. **Three buys, no sells.** From flat, every leg is an add; a sell on arrival day
   would mean the constructor mis-sized something.
2. **The core is ~85% and the satellite ~15%** of the $10k tier, each rounded DOWN
   (truncation toward zero, never up — the T-329d3 invariant: realized ≤ requested).
3. **SGOV absorbs the residue**, leaving less than one SGOV share uninvested.
4. **The run is canonical**, and the banner states the allocation and bands.
5. **The contribution line reads +$0** (month 0).

## What would mean the fix is WRONG, not merely surprising

- Any **sell** on arrival day.
- Realized weight **above** target on either leg (truncation failed).
- Sizing off raw equity (~$100k) instead of the $10k tier — the notional-cap bypass
  I caught yesterday; if it reappears, the cap wiring regressed.
- The wash guard **refusing** the VOO buy: that would be a *correct* refusal, not a
  bug — acct-1 holds SPY and shares `US_LARGE_BLEND` — but it means the arrival
  event cannot complete as planned and becomes drill 12's artifact instead. Journal
  it with the typed reason; do not route around it.
- The guard failing to BUILD: the run refuses to trade. That refusal is also a
  correct artifact — journal it as such.

## Order of operations (in-window)

1. `--dry-run` again (state may have moved overnight) → 2. `--execute` the
transition → 3. provision rev34 (strategy + image together — the live rev33 image
has no `deploy_candidate` code, so the strategy swap and the image MUST land in the
same jobdef revision) → 4. account-3 right-size, `$10k` sub-budget pinned in
EFFECT through the equity change → 5. arm (the drill-3 protocol: prove
ALARM→OK→ALARM before trusting the alarm) → 6. observe the arrival event.

**Deliberately NOT done tonight:** provisioning. It would bump account-3 — live and
enabled — to a new image on the same morning as the first `price_fed` verify,
adding a variable to the observation that matters most, for no benefit. The
provision takes seconds in-window.

---

## 2026-09-14 — the arrival event was POSTPONED, not corrupted

The first scheduled firing under `deploy_candidate` **failed closed** at 13:51Z
with a `NameError: name 'sleeve_cap' is not defined`, before any order. No broker
contact, no partial fill, no state to unwind. **The pre-statement above stands
completely untouched** and is still the thing to check when the event fires.

**This is a THIRD kind of outcome**, distinct from both correct-looking failures
I listed above: not a wash-guard refusal, not a guard that failed to build, but
**an honest crash in my own wiring**. `sub_budget=float(sleeve_cap)` was a
leftover from the constructor's original dollars-based design that survived the
refactor to the fleet's FRACTION idiom — I changed the semantics and never
updated this call site.

**Why 53 green tests missed it, which is the durable part:** they exercised the
constructor directly, and the wiring tests read `main()` as *text*. Nothing ever
RAN this branch. **A text assertion cannot catch an undefined name; only
execution can.** `tests/test_deploy_candidate_driver_t350f.py` now drives
`main()` through the real branch with an injected client, and the lock is proven
by reversion — restore `sleeve_cap` and three of its four tests fail. The same
drive verifies the pre-stated shape locally: from flat, BUY 14 VOO / 6 MTUM, no
sells.

**Alarm reading:** account-2's alarm staying in ALARM today is the alarm system
**correctly reporting a failed run**, not a defect. The arming proof's second
half now closes on the first SUCCESSFUL firing.

**Why the event was not recovered by a manual submit today**, despite the window
being open and a same-day path being offered: the pre-statement above — endorsed
as a ruling — says the arrival event *belongs to the first SCHEDULED firing* and
is "not run from here". A manual catch-up would have bought back one paper day by
making the arrival event a manual artifact, which is the one property it must not
have. **The fix was deployed today so that tomorrow's 9:50 ET scheduled firing is
the arrival event**; the deploy deadline was never the market close.

Deployed for it: `paper-sha-20b6f1f`, account-2 jobdef `:17` (infra-only retry
preserved), schedule ENABLED and revision-pinned, drift gate clean.

---

## 2026-09-15 — ✅ THE ARRIVAL EVENT FIRED, AND THE SHAPE HELD

The 09:50 ET scheduled firing ran with no hands on it. Read off the live order
journal (`s3://…/paper_state_offense_sso/data/paper_state/orders.jsonl`), the full
lifecycle is present for all three legs — `stage → submitting → submit_acked →
broker_update → broker_poll → broker_update(filled)`:

| leg  | qty | fill px | notional | % of $10k tier |
|------|----:|--------:|---------:|---------------:|
| VOO  |  12 |  698.04 | 8,376.48 |         83.76% |
| MTUM |   5 |  300.28 | 1,501.40 |         15.01% |
| SGOV |   1 |  100.54 |   100.54 |          1.01% |
|      |     |         | **9,978.42** |     **99.78%** |

Against the five pre-stated criteria:

1. **Three buys, no sells** — ✅ exactly three orders, all `buy`.
2. **Core ~85% / satellite ~15%, each rounded DOWN** — ✅, *and this one needed
   checking rather than eyeballing* (see below).
3. **SGOV absorbs the residue** — ✅ $21.58 left uninvested, less than one SGOV
   share ($100.54).
4. **Canonical, with the allocation and bands stated** — ✅ `VOO 85% / MTUM 15% /
   cash→SGOV | bands buy 1.5q > sell 1.0q (stricter to add), max_drift 10%`,
   `notional cap $10,000 (equity $100,382)` — the cap binding on the tier, not on
   equity, exactly as the sub_budget catch required.
5. **Contribution +$0** — ✅ `+$0 = 0 whole month(s) x $583/mo since 2026-09-11
   (SIMULATED via the notional cap; no broker money moves)`.

Neither correct-looking failure fired. The wash guard built and enforced, and did
not refuse the VOO buy — account-1 evidently carries no SPY loss inside the 61-day
window, so **drill 12 stays latent, which is the correct outcome, not a skipped
test.** The 09-16 run then submitted 0 (holds inside the bands) and the silent-stop
alarm cleared: the arming proof closed its own second half.

### ⚠️ Criterion 2 nearly fired as a FALSE positive — the falsifier was underspecified

At the FILL price, MTUM's 5 shares are **15.01%** of the tier — *above* the 15%
target, which the falsifier list calls "truncation failed." It did not. The
constructor sizes off the prior close, and the arithmetic on its actual input is:

```
MTUM  10000 × 0.15 / 299.097 (09-14 close) = 5.0151 → 5   ✓ truncated DOWN
      realized at the sizing price: 14.95%  ≤ 15%         ✓
VOO   10000 × 0.85 / 699.300 (09-14 close) = 12.1550 → 12 ✓ truncated DOWN
      realized at the sizing price: 83.92%  ≤ 85%         ✓
```

MTUM simply opened 0.40% above its close. **A falsifier that is evaluated at the
fill price fires on ordinary overnight market movement** — it would have cried
"truncation failed" on a day truncation worked perfectly, and the next reader would
have spent the morning debugging a working invariant. Same wolf-crier class as the
orphan check fixed in T-350g, arriving from the opposite direction.

**The criterion is hereby sharpened for all future arrival/rebalance events:**
truncation is judged against the **sizing input** (the close the constructor
actually divided by), never against the realized fill. Slippage between the two is
a separate, already-measured channel (`exec_cost`: VOO 1.65 bps, SGOV 0.99 bps,
MTUM 0.00 bps on this event).

**Verdict: the pre-statement is CONFIRMED.** The structural stack is live and
accruing, and the dollars-vs-SPY line has its t=0.
