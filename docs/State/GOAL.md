# ArchonDEX: Master Orchestrator

## AI Alignment & Objective
You are an Advanced Agentic AI working on **ArchonDEX**, an institutional-grade, autonomous trading system. Your overarching objective is to help architect, refine, and maintain it. 

When beginning a new large-scale project or if you ever feel context is drifting, use this document and its referenced files to anchor your understanding.

> **First time here?** Start with `docs/Core/README.md` — it explains the reading order, file purposes, and how to navigate this folder.

Here is the reference map:
- **Architecture:** Review `docs/Core/PROJECT_CONTEXT.md` to understand the fundamental structure and the system's philosophy.
- **Codebase Navigation:** Consult `docs/Core/files.md` for a quick directory map. For deep module-level details, see the `index.md` file inside each engine or component directory (e.g., `engines/engine_a_alpha/index.md`).
- **Execution Manual:** Reference `docs/Core/execution_manual.md` for the exact CLI commands required to operate the system's various engines, scripts, and workflows.
- **Progress & Trajectory:** `docs/State/ROADMAP.md` dictates forward-looking goals, while `docs/State/lessons_learned.md` logs what has historically worked or failed, and `docs/Sessions/` contains timestamped summaries of completed phases.
- **Operational Rules:** `docs/Core/agent_instructions.md` holds operating protocols and coding standards.
- **Cognitive Lenses:** `docs/Core/roles.md` outlines specific parameter focuses and mindsets based on the problem at hand (Risk, Quant, UI/UX, etc.) - adopt the corresponding cognitive lens dynamically.

## The concrete success bar (USER-SET 2026-06-15) — read this FIRST
**Real capital lives in a Schwab robo portfolio (a low-cost index+satellite proxy) and is NOT deployed into this system until the system is (1) PAPER-VALIDATED (the machine works on the live paper API) AND (2) demonstrably OUTPERFORMING the robo benchmark net of costs and after-tax.** This is the deploy gate — concrete and real-world, not an abstract Sharpe threshold. Until it clears: the system is in **capability-build + edge-hunt** mode, paper-only, no real money. The honest near-term truth (2026-06-15): the borderline, bull-conditional, beta-driven base (26yr Sharpe 0.751/ci_low 0.382, Roth-only, −33% MDD, no working crisis-defense) likely does NOT beat a robo net-of-costs today — so the edge-hunt is real, and "the system remains a rigorous capability/falsification platform while the money stays in the robo" is an acceptable, honest outcome. Both in-house crisis defenses (de-gross overlay, capital-partitioned sleeve) are conclusively refuted; the live levers are a *bought* managed-futures sleeve + new alpha. See `docs/State/CURRENT_STATE.md` for live state.

## Current Mode
When needed, route your capabilities through these core documents before initiating research or execution. You are not just writing scripts; you are building an institutional-grade, self-evolving portfolio manager. Operate with caution, scalability, and modularity in mind. Every component must fit into the larger machine. 

