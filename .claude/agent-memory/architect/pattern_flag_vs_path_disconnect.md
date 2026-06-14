---
name: pattern-flag-vs-path-disconnect
description: Recurring ArchonDEX bug class — an enable-flag reads True (or a default-skip signature reads OFF) but the actual call site tells a different story; flag state lies about live behavior
metadata:
  type: project
---

A capability's enable-flag is NOT authoritative about whether it runs. Two
inverted forms keep recurring in this codebase, both verified:

1. **Flag-True-but-path-dead.** Engine F `factor_alpha_enabled` defaults True,
   but `governor.evaluate_lifecycle` never passes `factors=`, and the gate body
   short-circuits on `factors is None`. Permanent no-op despite True flag. Only
   `scripts/lifecycle_factor_alpha_reeval_t043.py` exercises it. (T-088 was the
   same shape: `risk_per_trade_pct` is a live-looking knob on a DEAD Path B.)

2. **Default-skip-signature-but-wired-ON.** Engine D Gates 7 (substrate
   transfer) and 8 (DSR) have default-skip signatures suggesting they're off,
   but `--discover` wires them ON in production.

3. **Mode-flip reachability.** Engine C prod config is `mode="mean_variance"`
   (overlays early-return, don't fire), BUT `_apply_regime_overrides` treats
   "mode" as a safe override key and `allocation_recommendations.json` on disk
   recommends `mode="adaptive"` for every regime — so the crisis overlays CAN
   silently activate at allocation time. Reachability depends on a per-bar flip
   that no doc describes.

**Why:** flags and call sites are edited in different tasks; nobody re-checks the
join. The codebase has lots of layered gating (config flag → wiring guard →
reachability branch) and any one layer can silently veto.

**How to apply:** to claim a capability is live OR dead, trace ALL THREE: config
flag value, the wiring guard at the call site, and any mode/branch reachability
condition. Never infer liveness from the flag alone. For Engine C specifically,
check whether the regime-override layer can flip `mode` before concluding an
overlay is dead.

Related: [[pattern-verdict-buries-capability]].
