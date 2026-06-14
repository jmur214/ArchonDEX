---
name: engine-b-doc-buried-defensive-capabilities
description: Engine B (Risk) ships ≥4 crisis/de-gross capabilities that the living docs do not surface — the "refuted-but-present" doc-gap pattern
metadata:
  type: project
---

Engine B (Risk) carries multiple shipped DEFENSIVE capabilities that the living docs (CURRENT_STATE.md, engine_charters.md, index.md, high_level_engine_function.md) do not make discoverable. Found during the 2026-06-04 Path-B (crisis-regime robustness) audit.

The buried capabilities, by current state:
- **Crisis-floor on suggested_max_positions** — `engine_e_regime/advisory.py:228-235` (crisis→5, stressed→7 via `AdvisoryConfig.crisis_max_positions`/`stressed_max_positions`). Consumed ACTIVE in `risk_engine.py:729-731` (`risk_advisory_enabled` defaults True + present in prod). HIGH Path-B relevance, ACTIVE, in NO living doc.
- **Regime-conditional vol-target multiplier** incl. `portfolio_vol_target_crisis_multiplier=0.40` (`risk_engine.py:112-116`, `vol_target.py:90-94`). GATED-OFF (needs `portfolio_vol_target_enabled` AND `portfolio_vol_target_regime_aware`) AND refuted on 12-yr (T-055h). refuted-but-present.
- **Drawdown-gated kill switch** (`risk_engine.py:83-87,940-979`, 5/10/15% thresholds). INERT default-OFF. Only a RESOLVED line in health_check.md:524.
- **FactorRiskModel** (`factor_analysis.py`) — ORPHANED, zero importers repo-wide.

**Why:** The thing that buries a capability here is the negative VERDICT. When a measurement campaign (T-055 vol-target) is REFUTED, MEMORY records the refutation but the SHIPPED CODE that was touched stays in the tree, default-off, with no doc pointer. Future planners searching the docs cannot find the tool.

**How to apply:** When auditing ANY engine for "what defensive tools already exist," do NOT trust the charter or CURRENT_STATE alone — they enumerate intent and validated findings, not the inert/gated/refuted code surface. Always read the dataclass fields + their defaults directly, and grep prod config to classify each flag as active / inert-default-off / gated-off / refuted-but-present. A refuted finding ≠ removed code. See [[doc-gap-pattern-refuted-verdict-buries-shipped-capability]].
