# Fresh-Eyes Gap Analysis — Prompt for an External Developer (2026-06-18)

**Hand this to a capable AI developer / engineer with FULL access to this repository but NO
prior context about it.** The whole point is independence: the team that built this has deep
accumulated context, and we want an outside assessment that is NOT anchored to the builders'
own framing. Read critically; form your own view.

---

You are an elite quantitative-systems engineer and trading-system architect. You have just been
given full read access to this codebase and asked for an **independent,
brutally honest capability and gap assessment**. You have no prior involvement and no stake in
its conclusions.

**What the system is supposed to be (the goal, stated by its owner):** an autonomous algorithmic
trading system, organized as 6 engines (A: Alpha/signals, B: Risk, C: Portfolio, D: Discovery,
E: Regime, F: Governance). Its goals, in the owner's words, are to **"perform like a quant
desk"** and to **"significantly outperform the market."**

**Hard real-world constraints (facts, not opinions):** it trades a **retail Alpaca account,
equities only** (no native options/futures/bonds/FX), small AUM (**$5–50K**), **daily bars**.
Real capital currently sits in a Schwab robo-advisor, and the bar for deploying real money is
"beat that robo net-of-cost/after-tax, paper-confirmed."

## Your task

Explore the repository on your own terms and answer, with evidence (cite files/functions):

1. **What does this system actually do?** Trace the real data → signal → portfolio → risk →
   execution path. What is genuinely implemented and wired vs aspirational/stubbed/dormant?
   Distinguish "exists in a file" from "actually runs in the production path."
2. **Capability gaps vs the stated goal.** Where does this fall short of a market-beating
   systematic-equity operation? Be specific about architecture, signal breadth, risk modeling,
   portfolio construction, execution realism, validation rigor, and anything else. What's
   *missing* that a competent quant system would have?
3. **What's overbuilt / misdirected.** Where has effort gone that doesn't serve the goal?
   Complexity that isn't earning its keep? Dead or duplicated machinery?
4. **Blind spots.** What would the builders likely NOT see because they're too close to it?
   Structural assumptions baked in so deep they've stopped being questioned. (For example —
   without treating this as the answer — is everything evaluated "universally" across the whole
   universe, or can edges be conditional? Is the system equity-only by necessity or by habit?
   Is the measured performance actually *alpha*, or beta/survivorship?)
5. **The honest path.** Given the real constraints (retail, equity-only, daily-bar, small AUM),
   is "significantly outperform the market" even achievable here? If yes, what's the
   highest-leverage path? If the honest answer is "risk-managed beta is the realistic ceiling
   and the money should stay in the robo," say so plainly.

## Ground rules
- **Form your own view.** The repo contains extensive docs (`docs/`), task ledgers, audits, and
  memory files written by the builders. **Read them critically as evidence of intent and
  history — do NOT adopt their conclusions as your own.** We are paying for fresh eyes precisely
  because the existing narrative may contain blind spots.
- **Verify, don't trust.** If a doc claims something works, check whether the code actually does
  it. The builders have a known history of "capabilities that exist in code but were never
  wired, fed, or validated" — look for that pattern, but confirm each case yourself.
- **Be brutal.** Flattery is useless here. Name what's broken, missing, or misguided plainly.
  The owner explicitly wants honest assessment over reassurance.
- **Cite everything** in `path/file.py:line` form so claims are checkable.

## Deliverable
A structured gap-assessment report: (1) what it really does, (2) the prioritized capability
gaps, (3) overbuilt/misdirected areas, (4) the blind spots you found, (5) your honest verdict
on whether/how this can reach the goal — and the 3–5 highest-leverage changes you'd make.
