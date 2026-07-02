---
name: pattern-archive-verification-string-vs-import
description: When verifying a script is safe-to-archive, a live module's reference may be a docstring/error-string/comment, NOT a real python import — these don't break archiving but flag a doc smell
metadata:
  type: feedback
---

When producing a safe-to-archive manifest, "module X is referenced by live module Y"
is NOT automatically a KEEP. In this codebase the reference is frequently a
**docstring, an error-message string, or a code comment** that names the script
(often `python -m scripts.foo` build instructions), not a Python `import`.

**Why:** `engines/data_manager/membership.py` names `build_membership_panel_t136`
only in a docstring + an error string (a "build via" instruction). `cockpit/
dashboard_v2/utils/paper_loader.py` names `run_paper_day_t163` only in a docstring.
`scripts/run_isolated.py` lists `path_c_synthetic_compounder` in a defensive
module-global reset registry that is a **proven no-op** (`_reset_one_global` does
`sys.modules.get(path)` then `return`s if absent — never force-imports). `quality_
roic_edge.py` names `path_c_synthetic_compounder` in a comment about a shared
constant. None of these break if the script is archived.

**How to apply:** grep -rEl for ACTUAL import forms (`import scripts.X`, `from
scripts.X import`, `from scripts import ...X`), not bare name matches. A bare-name
match in live code → open the file and classify: import (KEEP) vs docstring/string/
comment (SAFE-with-note: archiving is safe but the director should null the stale
pointer in the same change so it doesn't dangle). Distinct from the execution_manual
tie (a documented current CLI command → genuine KEEP per the audit rules) and from
operational tools in active use this week (e.g. `land_held_position_t201.py` for the
6/22 CLS landing while T-202 is in-flight → KEEP even though imported-by-nothing).
See also [[pattern-orphan-script-accumulation]].
