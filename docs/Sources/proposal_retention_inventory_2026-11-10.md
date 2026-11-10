# Proposal: retention inventory (read-only) — what may never be deleted, what is expensive, what is regenerable

**For:** the user. **Status:** PROPOSAL, read-only. Nothing was moved, deleted, or uploaded to produce it.
**Measured:** 2026-11-10, Data volume 228 GB, **1.5 GB free**. **N_trials: 0.**

## 0. The finding that changes the plan

The project is not what fills the disk. Everything under `~/Dev` is about 22 GB of 199 GB used.
The disk filled for the FOURTH time (09-30, 10-15, 11-04, 11-10) from the same source each time:

| Consumer | Size | Class |
|---|---|---|
| iOS Simulator runtimes, `/System/Library/AssetsV2/com_apple_MobileAsset_iOSSimulatorRuntime` (18.3.1 + 26.5; re-downloaded 2026-11-06 22:03) | 16.3 GB | regenerable (Xcode re-downloads) |
| Simulator dyld cache, `/Library/Developer/CoreSimulator/Caches/dyld` | 5.6 GB | regenerable (rebuilt on first boot) |
| Claude desktop `vm_bundles` | 8.9 GB | regenerable per the 10-08 note; the user's call |
| Office group container | 7.0 GB | UNCLASSIFIED (may hold the only copy of mail/files) |

**Rule proposed:** project data is never the space lever. A session that is short of disk measures
the four rows above first and may not propose a project deletion while any of them is non-empty.
The durable fix is Xcode → Settings → Components: remove the runtimes there and turn OFF automatic
downloads, or the 16 GB returns (it has, three times).

## 1. Classes

- **IRREPLACEABLE** — cannot be recreated. Never removed locally without a hash-proven second copy AND the user's word.
- **EXPENSIVE** — recreatable in hours/days or at provider cost. Same protection.
- **REGENERABLE** — one named command recreates it. Removable by quarantine-rename, never `rm`.
- **UNCLASSIFIED** — anything not listed. Protected by default.

## 2. Inventory (everything over 100 MB, plus small irreplaceables)

### IRREPLACEABLE
| Path | Size | Second copy today |
|---|---|---|
| `data/raw`, `data/processed`, `data/governor`, `data/macro`, `data/external/base_curve`, the pinned `data/universe` + `data/observability` files (the pinned substrate, 14,259 files) | 2.7 GB | YES — S3 `substrate/44d3be53…/`, 14,260 objects, sha256-proven 11-05. Local copy is the working canon: keep. |
| `data/state/` (autonomy ledger, verify stamp) | <1 MB | ledger: S3 `ops/phase6/` nightly; stamp: none |
| `data/intel/news_panel` (the daily news tape; a missed day cannot be re-fetched) | 0.52 GB | S3 `news_panel/` exists; parity UNVERIFIED |
| `~/.claude/projects/` (memory + every session transcript) | 1.23 GB | NONE |
| `~/Dev/_director_tools/` (merge gate, publish scripts, logs) | <10 MB | NONE — not in git |
| `.env` | — | NONE |
| `_substrate_candidates/*.jsonl, *.log, *.tsv, *.json` (provider responses and measure records, 10-15 and 10-22) | ~6 MB | NONE |
| Unmerged work: worktrees `agent-a06a…` (dashboard-v2-redesign, 3 commits), `agent-a62b…` (review-l4, 1), `trading_machine-agent-e` (t364, 1); uncommitted files in `agent-a5e8…` (6), `agent-b` (1), `agent-c` (1); 2 stashes; 82 local branches not on origin/main | small | NONE — local git only |

### EXPENSIVE
| Path | Size | Why |
|---|---|---|
| `_substrate_candidates/cutover_copy_2026_10_22` | 1.0 GB | cutover step-1 output; a lock reads it; needed until cutover day |
| `data/edgar` (sections.parquet 1.1 GB, insider_zips, 8k, raw) | 2.66 GB | SEC re-fetch is rate-limited, days; 11 scripts read it; S3 `altdata/` parity UNVERIFIED |
| `data/processed_alpaca_backup_2026_05_23` | 0.79 GB | looks like a stale backup, but `tests/test_processed_cache_adjustment_class_2026_10_15.py` READS it — removing it breaks a lock. The exact trap this document exists for. |
| `data/trade_logs` (145 runs), `data/research`, `data/logs` | 1.3 GB | some are receipts cited by ledger rows; not yet mapped run-by-run → protected |

### REGENERABLE (candidates; none acted on)
| Path | Apparent size | Real space freed | Recreate / evidence |
|---|---|---|---|
| `_substrate_candidates/repin1_stage_44d3be53…` | 2.7 GB | **~0** — all 14,259 files are hard links to the canon | `repin1_s3_publish.sh stage`; published and proven. Removing it frees nothing: `du` overstated it. |
| 25 merged, clean worktrees in `.claude/worktrees/` | 1.5 GB | ~1.5 GB | `git worktree add`; each verified MERGED into origin/main, dirty=0 |
| `data/observability/rr3b_s3_mirror_2026-10-13` | 0.61 GB | 0.61 GB | a download of S3 prefixes that still exist; `scripts/rr3b_population_pass.py` reads it |
| `.venv` | 0.79 GB | — | `pip install -r requirements.lock.txt`; in use, keep |

### SUPERSEDED — archive to S3 first, then removable on your word
| Path | Size | Evidence |
|---|---|---|
| `_substrate_candidates/cutover_copy_2026_10_22_pass1_no_close_unadj` | 0.94 GB | pass 1 of the cutover copy; 0 code refs |
| `_substrate_candidates/processed_exact_tr_2026-10-15` + `_replay` | 1.07 GB | the 10-15 candidate, replaced by the 10-22 copy; provider-fetched, so archive not discard |
| `data/Archive_wfo_runs_2026_08_26` | 1.08 GB | archived 08-26 with a README; 0 refs |

### UNCLASSIFIED (protected until inspected)
`trading_machine-agent-a` (1.5 GB) and `-agent-d` (1.6 GB): branches merged and clean, but they hold
real data copies of unknown provenance. `/private/tmp/sb-dd` (0.93 GB) belongs to another project.

**Project-side ceiling: about 5 GB, and only after an S3 archive step. The simulator rows alone are 22 GB.**

## 3. What made earlier recommendations wrong, and the guard for each
1. **Judged by name** (`*_backup_*` read by a live test) → a path is regenerable only with a named recreate command AND zero readers by grep.
2. **Judged by `du`** (2.7 GB of hard links frees nothing) → measure real freed bytes (`find -links 1`) before proposing.
3. **Judged under pressure** → the class is decided in this file, in advance; an unlisted path is protected.
4. **Wrong lever** → the simulator rows are measured first, every time.

## 4. Proposed build (after your corrections to §2)
1. `config/retention_manifest.yml` — §2 as data; unlisted = protected.
2. `scripts/retention.py audit|archive|quarantine` — `archive` uploads and proves by sha256; `quarantine` renames into `~/Dev/_quarantine/<date>/` only for REGENERABLE paths, refuses unmerged/dirty worktrees, never deletes. Emptying the quarantine stays yours.
3. Janitor check `disk_floor` (alert under 15 GB) naming the four §0 rows with their sizes.
4. Close the second-copy gaps marked NONE: `_director_tools` into a private git repo; `~/.claude/projects` and the candidate logs to S3 (a few cents a month; needs your approval).

## 5. Decisions requested
1. Corrections to any class in §2.
2. S3 as the second-copy home (cost approval).
3. Xcode: are both simulator runtimes needed for your iPhone work, one, or none?
