# Papers Ledger — append-only, one row per triaged paper

Convention: `| date | paper (link) | claim (one line) | evidence class | verdict | receipt |`
Verdicts: ADOPT / PROBE / BANK / SKIP (reason). See README.md for the pipeline.
Seeded retroactively with the papers already triaged through the external-review and
repo-dive waves, so the ledger starts complete rather than empty.

| date | paper | claim | class | verdict | receipt |
|---|---|---|---|---|---|
| 2026-08-06 | Fulkerson-Jordan-Riley-Yan, FAJ 2026 (SSRN 4904652) | Poor timing costs fund investors ~0.10%/yr, not the 1.2pp Morningstar gap | OOS-REPL | BANK — automation scored ~10-20bps, memory corrected | memory: research-run entry superseded |
| 2026-08-06 | Rogoff-Rossi-Schmelzing, AER 2024 (700yr real rates) | Real rates trend-stationary around a DECLINING trend; high-yield eras are the deviation | BACKTEST (7 centuries) | BANK — the sleeve's macro bet stated on its label | forward_plan + option package |
| 2026-08-06 | Profit Mirage (arXiv 2510.07920) | LLM trading agents lose 51-62% of Sharpe past knowledge cutoff | OOS-REPL | BANK — vindicates the LLM-history ban | ban amendment preamble |
| 2026-08-06 | Glasserman-Lin (JFDS 2024) + Kim-Muhn-Nikolaev (2407.17866) | Entity anonymization controls memorization; anonymized can OUTPERFORM (distraction effect) | BACKTEST w/ controls | ADOPT — the gated-exception protocol; T-339 prereg frozen | amendment + T-339 doc |
| 2026-08-06 | ChronoBERT/ChronoGPT (arXiv 2502.21206) | Chronologically-trained LLMs enable look-ahead-clean historical text evaluation | BACKTEST | ADOPT (conditional) — named in the exception protocol | ban amendment |
| 2026-07-30 | Novy-Marx & Velikov, RFS 2016 | Buy/hold spread is the single most effective simple cost mitigation | BACKTEST | ADOPT — momentum-satellite construction; T-298 family retest queued | momentum spec (Q5 triage) |
| 2026-07-30 | Ben-David-Franzoni-Kim-Moussawi, RFS 2023 | Thematic ETFs lose ~4%/yr for 5yrs — driven by launch-at-peak overvaluation | BACKTEST (peer-reviewed) | ADOPT — the v2 valuation-embedding requirement + ETF-existence prior | thesis_contract_v2 FREEZE |
| 2026-07-30 | Daniel & Moskowitz, JFE 2016 (Momentum Crashes) | Momentum crashes live in the SHORT leg; long-only largely exempt | BACKTEST + LIVE (MTUM DD) | BANK — no crash overlay on the long-only satellite | momentum spec |
| 2026-08-15 | Stivers & Sun 2010 + replications (OpEx week) | Option-expiration week +~0.2%/wk in large caps, moderated not dead | OOS-REPL | PROBE (low priority, one trial, straddle prior) | repo-dive triage |
| 2026-08-15 | Overnight anomaly (SSRN 3829582) | Close→open effect cost-dead standalone; usable as execution-timing overlay | BACKTEST | PROBE — narrowed to open-vs-close cost arm, frozen (C) | overnight prereg + ruling |
| 2026-08-15 | Cohen-Malloy-Nguyen (Lazy Prices, JF 2020) | 10-K language change predicts returns (188bp/mo L/S) | BACKTEST; failed clean replication | SKIP as alpha (short-leg + survivorship sign-flip); spec'd as thesis-desk risk FLAG | T-341-D spec |
| 2026-08-15 | Cohen-Malloy-Pomorski (JF 2012, opportunistic insiders) | Opportunistic insider buys ~9.8%/yr; routine ≈ 0 | BACKTEST (2012, decay prior) | BANK — the Form 4 archive accrues the classification prerequisite | T-334 |
