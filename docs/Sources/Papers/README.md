# The Papers Pipeline — intake → triage → verdict → action

The standing route by which papers the user (or anyone) finds become system knowledge,
probes, or doctrine — instead of ad-hoc pastes that evaporate. Adopted 2026-08-20 at the
user's direction.

## How to submit (user side — deliberately cheap)
Drop a line in `data/coordination/papers_inbox.md`:
`- <link or title> — <one line: why it caught your eye>`
That's it. The director takes it from there. Batch as many as you like.

## Triage (director side)
Every submission gets a verdict within one session of being relayed — either a quick-kill
inline or a deep-dive (delegated background research agent, the repo-dive pattern). The
triage template, applied to each paper:

1. **The claim** — one sentence, with the effect size the paper actually reports.
2. **Evidence class** — [BACKTEST] / [OOS-REPL] (out-of-sample or post-publication
   replication) / [LIVE]. Replications and live records outrank originals.
3. **Dedupe** — against the refuted/closed ledger AND the papers ledger. A paper
   re-proposing a closed door is SKIP-with-pointer unless it carries genuinely new
   evidence, in which case it's a reopening case and says so.
4. **Fit** — our constraints (long-only, retail scale, daily+ bars, no margin, Roth/
   taxable wrappers) and the McLean-Pontiff decay prior for anything published.
5. **Data feasibility** — is the required data PIT-honest and obtainable at our cost
   class? (The five-point PIT checklist applies to any vendor claim.)
6. **Verdict** — one of:
   - **ADOPT** — a technique/design improvement we implement (no trial consumed).
   - **PROBE** — becomes a pre-registered test candidate (drafts through the normal
     freeze machinery; consumes honest N when run).
   - **BANK** — doctrine/evidence recorded (a durable memory + ledger row; no build).
   - **SKIP** — with the reason written down, so it is never re-litigated silently.

Verdicts land as one row each in `PAPERS_LEDGER.md` (append-only, greppable). Deep-dive
triages get their own doc in this directory; the row links it.

## The two consumption paths — and the firewall rule
**(a) System development** (the primary path, per the user): ADOPT items become tasks;
PROBE items enter the science queue through pre-registration like everything else.
**(b) Feeding the AI:** triaged summaries MAY join the analysts' reference material and
resolver/scoring design. **They must NEVER enter the blind thesis generator's bundle.**
A paper the user selected is user-seeded content by definition — feeding it to the
generator would break provable blindness exactly the way the seed firewall exists to
prevent. Strategy-recipe papers additionally never feed any generator (the analyst
parroting a published anomaly is the refuted-vocabulary trap wearing a citation).
Mechanism knowledge (how power markets work, how AUKUS contracting flows) is the safe
and valuable feed; recipes are not.

## What this is not
Not a reading list. Every entry ends in a verdict, and SKIP is a first-class verdict —
the pipeline's job is to make the system's knowledge monotonically better, which mostly
means killing things cheaply and keeping the receipts.
