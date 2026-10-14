---
task_id: edges.yml wipe (found in RR-6a §5.3; ruled its own unit 2026-10-14)
title: Discovery never wipes edges.yml — fail-closed read, atomic write
date: 2026-10-14
author: Agent D
branch: fix/engine-d-registry-write-fail-closed (off main 16c000f)
type: PROPOSAL — propose-first; R reviews, the director merges
n_trials: 0
---

# Discovery never wipes edges.yml

**The defect.** `DiscoveryEngine.save_candidates` read `data/governor/edges.yml` inside
`except Exception: existing = {"edges": []}` and then wrote back only `existing + candidates`. A registry it could
not read was therefore **replaced by the candidates being saved**, deleting every other edge from the sole
edge-status authority. Unreadable here means: a merge-conflict marker, a half-written file, a stray character, or
an empty file (`safe_load("") or {"edges": []}`).

It also opened the file with `open("w")`, which truncates, **before** `yaml.dump` ran. A serialisation error left
the registry empty. `get_queued_candidates` swallowed the same read failure into `[]`, so the cycle silently
found "nothing queued".

**The fix** (`engines/engine_d_discovery/discovery.py`):
- `_read_registry()`: an absent file is an empty registry. A file that exists but is unparseable, empty, or not
  an edge registry raises `RegistryUnreadableError` and is left byte-untouched. The legacy list-root format is
  still accepted.
- `_write_registry()`: serialise first, write a sibling `.edges.yml.tmp-<pid>`, fsync, then `os.replace` it over
  the registry. Nothing touches `edges.yml` until a complete file exists. A failed attempt leaves the temp file
  in place as evidence; nothing is deleted.
- `save_candidates` keeps any other top-level keys; the old code dropped them. `get_queued_candidates` raises
  instead of returning `[]`.

**Locks** (`tests/test_engine_d_registry_write_fail_closed.py`, 12 tests). Each plants a file and asserts its
bytes afterwards:
- six unreadable shapes (unparseable, merge-conflict markers, empty, scalar root, dict without `edges`, `edges`
  not a list): each refuses, and the bytes are unchanged;
- `get_queued_candidates` refuses an unreadable registry;
- an absent registry is an empty one;
- a serialisation failure never truncates;
- a failed rename leaves the old file whole;
- **positive control:** a healthy save merges, is byte-identical to the old `yaml.dump({"edges": …},
  sort_keys=False)` output, and leaves no temp file;
- the legacy list root is still read.

**Reversion proof** (`scripts/registry_fail_closed_reversion_proof.py`): 4 of 4 cases bite.
- With the old read restored, the six refusal tests fail with `DID NOT RAISE`.
- With the old write restored, the registry's sha after a dump error is `e3b0c442…`, the sha256 of an **empty
  file**. That is the wipe, observed directly.

**First artifact, read-only.** The real `edges.yml` (218 edges, 20 queued) reads cleanly, a save's serialisation
round-trips it **byte-identically**, and the file was not modified.

**Tests:** all 59 files touching Discovery or its callers pass: 722 passed / 1 skipped / 3 deselected / 12 xfailed
/ 0 failed.

**Composes with RR-6a.** RR-6a's cycle fails loudly on any exception, so a `RegistryUnreadableError` there ends the
cycle at stage `save new candidates` or `write-back <id>` with a `cycle_failure` row. Without RR-6a, the old outer
handler only WARNs, but the file is still untouched. The constraint stands: no promotion cycle until both are on
main.

## Seen, NOT changed — the same class in Engine F, for its own unit

`engines/engine_f_governance/lifecycle_manager.py:1108` (`_save_registry`) and
`engines/engine_f_governance/evolution_controller.py:97` (`save_edges`) both write `edges.yml` with a
non-atomic `open("w")` + `yaml.dump`, inside an `except Exception: log` that swallows the failure. A dump
error or crash mid-write truncates the registry, and the caller is never told. Their **read** failures do not
wipe it: both return early on an empty load. LifecycleManager is ACTIVE in production, with
`lifecycle_enabled=true` and `lifecycle_readonly=false`. Engine F is outside this unit; the shared fix would be
one atomic registry writer that both engines use.
