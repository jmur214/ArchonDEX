---
name: Unused-def scan false-positive classes
description: Two classes of false positive dominate the unused-defs scan in this codebase — pytest fixtures and same-file script helpers — both must be excluded before reporting candidates
type: project
---

When scanning this codebase for "function defined but never called":

**False-positive class 1: pytest fixtures.** Any `def name(...)` in `tests/` decorated with `@pytest.fixture` is auto-injected by name into test functions that list it as a parameter. A literal name match in test bodies will exist but is also at the def site, so naive scanners miss it. ALWAYS check for `@pytest.fixture` (or `@pytest.fixture(autouse=True)`) above the def before flagging a tests/* function as unused. Tests confirmed as fixtures in this scan: `isolated_data`, `golden_data`, `tmp_worktree`, `chdir_repo_root`, `isolate_dividends_cache`, `isolated_registry`, `synthetic_snapshot_csv`, `synthetic_trades_dir`, plus several universe fixtures in `test_ws_c_*` and `test_ws_e_*`. Roughly 20 of 90 raw findings in 2026-05-23 sweep were of this class.

**False-positive class 2: same-file helpers in `scripts/`.** Every `scripts/*.py` is a self-contained command. Its top-level helper functions are typically called only from the same file's `main()`. A scanner that excludes the def-file from the search (to avoid matching the def line) will flag all helpers as unused. The right test for scripts is not "is this helper unused?" but "is the SCRIPT itself referenced by anything active?" — a separate, file-level check. Roughly 50 of 90 findings in 2026-05-23 sweep were of this class.

**Why:** A scan that reports these as unused will cause confident deletion of working code. False positives are MUCH worse than false negatives in a delete-based workflow.

**How to apply:** Two-phase verification for any candidate unused def:
1. Same-file ref count (excluding the def line) — if > 0, it's an internal helper, not dead.
2. Whole-repo string grep (excluding def file) — if > 0 in any active doc/code, it's not dead.
Only flag candidates that score 0 on BOTH. For test files, additionally require absence of `@pytest.fixture` decorator. For `scripts/*.py` top-level helpers, default to "in-script use" assumption — only flag the SCRIPT if no caller exists anywhere.

**True-positive rate after filtering:** 2026-05-23 sweep started with 90 raw candidates, filtered to 6 true unused functions + 13 truly unread constants/dataclass fields + 1 orphan script. Filter ratio ~22%.
