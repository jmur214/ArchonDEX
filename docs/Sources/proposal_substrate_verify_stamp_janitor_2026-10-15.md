# Proposal: the nightly substrate VERIFY STAMP (janitor side), the half that makes D's submit gate true

**For:** Agent D (the gate's owner) to agree the interface, then Agent R (review), then the director.
**Owner of this half:** Agent B (the janitor and the manifest). **Status:** PROPOSAL ONLY; nothing
built. **Sequencing (director, 2026-10-15):** build after D's anchor-registry build, so the two units
land together.

## 0. Why the stamp exists

The submit gate's HIGH row (health_check, "the campaign submit gate checks only that the anchor KEYS
exist") was ruled with this design: the gate checks a verify **stamp** by digest. It does NOT hash
14,000 files per submit. A stamp is only as true as whatever writes it. This half makes it true: the
nightly janitor runs the FULL data-hashing verify, writes the stamp on success, and turns it stale on
failure, so every submit refuses until the re-pin.

**Its first nightly will be RED.** `verify` exits 1 today: MISSING 0, EXTRA 134, CHANGED 5, the known
B-7 blocker (health_check's MEDIUM manifest row). That is the honest state, the same way the
relay_gap row was for the push: a red row that names its fix (re-pin #1, the honest-N re-bake).

## 1. The stamp

**Where:** `CANON/data/state/substrate_verify_stamp.json`, beside the autonomy ledger. It is a runtime
artifact in the gitignored canonical tree (`janitor_nightly.py:73-77`), never in a commit.

**Shape:** keyed by the digest of the manifest it verified, so a verdict about one manifest can never
stand in for another:

```json
{"schema": 1,
 "stamps": {
   "<sha256 of config/substrate_manifest.sha256>": {
     "result": "PASS | FAIL | ERROR",
     "verified_at": "2026-10-16T07:05:12Z",
     "writer": "janitor_nightly | repin",
     "tree_head": "<the commit whose manifest was verified>",
     "counts": {"pinned": 14120, "host": 14254, "missing": 0, "extra": 134, "changed": 5},
     "first_paths": ["CHANGED data/macro/VIX.parquet", "..."]
   }}}
```

- **PASS only on an exact match:** missing = extra = changed = 0, from a COMPLETE run of the
  generator's own `build_manifest()`. Never from `verify`'s printed footer, which misreports its own
  totals (RR-7 D3).
- **FAIL** on any drift, with the true counts.
- **ERROR** when the verify could not run (a crash, an unreadable file, a timeout). ERROR is never
  PASS. A verify that did not finish says nothing about the substrate.
- **Exactly two writers:** the nightly, and the re-pin step (`generate`, then a full verify, which
  stamps the NEW digest). A submit never writes the stamp. A verify of manifest X never touches the
  entry for manifest Y.
- **Written atomically:** a temp file plus `os.replace`, as the cache writer does. A torn stamp must
  read as absent, never as PASS.

## 2. The janitor check

A new `check_substrate_verify()` in `scripts/janitor_nightly.py`, run in the same nightly as the
others:

1. compute the manifest's digest at the runner's tree (it certifies `origin/main`, by design:
   `check_relay_gap`, :221-262);
2. run the full verify with `build_manifest()` against the canonical data;
3. write the stamp for THAT digest: PASS, FAIL or ERROR;
4. the Check is GREEN only on PASS. On FAIL it is red and names the true counts, the first paths and
   the fix ("re-pin: `scripts/gen_substrate_manifest.py generate`, committed in the same PR"). On
   ERROR it is red and names the error.

**Cost:** one full hash of about 14,250 files a night, a minute or two. The host is idle at that
hour.

## 3. The interaction to agree with D: origin/main vs local main

The nightly certifies **published** truth. After a LOCAL re-pin that has not been pushed:

- the re-pin step stamps the NEW digest PASS;
- that night, the runner (at `origin/main`) verifies the OLD manifest, finds drift, and stamps the
  OLD digest FAIL. The new entry is untouched (§1);
- the gate reads the LOCAL manifest's digest, so the re-pin's PASS stands, but only until its
  freshness bound (§4) expires. After that every submit refuses until the push lands and a nightly
  verifies the new manifest.

That is honest: an unpushed re-pin is not the published substrate. The gate's refusal should name the
fix: "stamp expired; is the re-pin pushed? (the relay_gap row)".

## 4. Freshness: a dead nightly must not leave a PASS standing

Without a bound, a nightly that stops running (the T-338 clock class) leaves the last PASS valid
forever, even after the data drifts. **Proposed:** the gate refuses a stamp older than **48 h**. That
is two nightlies, so one missed night does not block a submit and two do. The stamp file should also
join the clock census as a durable path. `clock_census.py` is on the janitor guard's denylist, so
that registration is a separate one-line edit by the census's owner, not the janitor.

## 5. Locks (reversion-proven; each DRIVES the real check function on a planted tree)

1. **Drift:** one byte changed in a planted substrate → FAIL stamp for that digest, true counts, red
   Check naming the fix.
2. **Clean:** an exact match → PASS for that digest.
3. **Fail-closed:** `build_manifest()` raises → ERROR stamp, red Check, and NEVER PASS. A positive
   control first, so the lock is shown able to fail.
4. **Isolation:** an existing stamp for another digest survives byte-identical.
5. **Atomicity:** an interrupted write leaves the previous stamp intact and no temp file.
6. **(D's side)** the gate refuses an absent stamp, a FAIL or ERROR stamp, a stale stamp, and a
   stamp for a different digest, naming which.

## 6. Interface questions for D

1. **The digest:** sha256 of the manifest file (proposed), or the md5 the workflow uses for the S3
   prefix? One digest for both would let the stamp name the S3 snapshot too.
2. **The freshness bound:** 48 h (proposed)?
3. **The stamp path:** `CANON/data/state/substrate_verify_stamp.json` (proposed). Does the submit
   path resolve CANON the same way the janitor does?
4. **The re-pin step's stamp:** D's design names "the re-pin step's full-hash verify result". Is
   that a new `gen_substrate_manifest.py` subcommand (proposed: `generate` stamps PASS after its own
   full verify), or a separate script?
