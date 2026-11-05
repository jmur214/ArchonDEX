---
name: whitelist-defeated-by-passthrough
description: Command whitelists with a free-form extra-args passthrough are defeated by argparse last-flag-wins; the exclusion lives in comments/memory, never in a behavior test
metadata:
  type: project
---

A registry-style command whitelist that appends a free-form "extra args" field to the spawned argv is NOT a whitelist for flags — Python argparse takes the LAST occurrence of a repeated option, so a base_cmd-pinned safe flag (`--strategy reconcile_only`) is silently overridden by typing the excluded one in the passthrough box.

First seen: `feature/dashboard-v2-redesign-2026-09` (banked b2284b2, audited 2026-09-29). `cockpit/dashboard_v2/callbacks/command_callbacks.py` (~:94) appends `cmd-param-extra` to every command; the branch's new `sleeve_reconcile` registration in `utils/command_runner.py` brags in-comment that `--strategy trend_sleeve` (order-arming) is "DELIBERATELY NOT registered" — and the ux-engineer memory file repeats the claim — but no code strips flag overrides and NO test drives `run_command` with hostile extra args. This is the [[pattern_product_moved_charters_stayed]] sibling of the documentation-test defect (2026-09-17): the safety claim exists in a comment + a memory file, i.e. "we said it," not "it holds."

**Why:** the passthrough field predated the branch harmlessly (legacy research commands only); the risk appeared the moment a command touching production paper-account state joined the registry. Composition created the hole — neither piece alone was wrong.

**How to apply:** when auditing any UI/agent-facing command registry, (1) trace every user-controlled string into the argv; (2) check whether pinned safe flags can be repeated/overridden; (3) treat any "deliberately excluded" comment without a behavior test as an unverified claim; (4) re-audit the registry whenever a NEW command class (state-mutating) is added, not just when the passthrough is added.
