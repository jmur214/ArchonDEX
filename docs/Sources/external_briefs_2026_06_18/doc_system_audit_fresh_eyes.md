# Fresh-Eyes Documentation-System Audit — Prompt for an External Developer (2026-06-18)

**Hand to a capable AI developer / engineer with FULL repo access but NO prior context.** The point is
an independent, unbiased view of how this project's documentation and knowledge system actually works —
its strengths, its failure modes, and the no-context onboarding experience. **Reach your own
conclusions; nothing here tells you what to find.**

---

You are an experienced engineer and technical writer. You've just been given a large, actively-developed
codebase — an autonomous algorithmic trading system, built over many months by a human director plus AI
agents — and asked to audit its **documentation and knowledge system.** Not the trading logic, not the
code quality — the *docs*: how they're organized, how they're written, how they're kept current, how
they're used in the actual work, how someone picks them up cold, and where they can mislead, decay, or
fail.

You have no prior involvement and no stake in any conclusion. Everything below is for you to discover and
judge for yourself.

## Your task — explore the system and form your own view

1. **Onboard cold.** Start exactly where a newcomer (human or AI) would. Using only the docs, figure out:
   what is this system, what is true *right now*, and what would you do next? Keep a running log of where
   you become oriented versus where you get lost, confused, double back, or are led to believe something
   that turns out to be wrong. How long until you'd actually trust your own understanding — and should you?

2. **Map the system.** What documentation/knowledge artifacts exist (the docs tree, root instruction
   files, any agent or AI "memory," automation/hooks, task logs, session notes, audits)? How do they
   relate? Is there an intended reading order? For each major artifact: who/what is it for, how is it meant
   to be created, updated, and consumed, and does that actually happen?

3. **Stress it — where can it go wrong?** Find the full range of failure modes that actually bite *here*.
   Documentation systems fail in many ways — staleness, drift from the code, internal contradiction,
   ambiguous authority (which doc wins when two disagree?), bloat/over-growth, update steps that silently
   don't fire, knowledge that lives in only one place, things that *read* as settled when they aren't, and
   subtler ones. Find which are real in this repo, plus any others you spot. For each: how exactly would
   someone be misled, and does the system have any way to catch it?

4. **The doc ↔ code ↔ work relationship.** How do the docs interact with the actual code and the
   development workflow? Do they reliably reflect what the code does? Is maintaining them *helping* the
   work or *competing* with it? What is the working relationship between the people/agents doing the work
   and the documentation — healthy, performative, neglected, overgrown? Verify doc claims against the code
   where you can; don't take a doc's self-description at face value.

5. **Verdict.** Independently: what does this documentation system genuinely do well, where is it fragile
   or failure-prone, and what are the highest-leverage changes you'd make? Is it serving its purpose — and
   what *is* its purpose, as far as you can tell?

## Ground rules
- **Form your own view.** No conclusion is prescribed. Read critically and skeptically.
- **Be comprehensive and brutally honest.** The owner wants the real picture of how the doc system
  behaves and where it can fail — *anywhere*, not just the obvious or the recent — over reassurance.
- **Verify, don't trust.** Where a doc asserts something, check it against the code/reality.
- **Cite** specific files/paths/locations so every finding is checkable.

## Deliverable
A structured independent assessment: (1) the cold-onboarding experience (where you got oriented vs
misled), (2) the system map, (3) the failure modes you found — each with *how it misleads* and *whether
the system self-corrects*, (4) the doc/code/workflow relationship, (5) your honest verdict + the
highest-leverage improvements. Whatever you conclude is yours; we want the unguided view.
