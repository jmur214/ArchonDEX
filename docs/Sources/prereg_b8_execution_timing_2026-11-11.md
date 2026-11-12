---
task_id: T-386 (B-8)
title: Pre-registration — execution timing for the monthly 85/15 VOO/MTUM rebalancer, {open, close} × {TOM −1, 0, +1} vs (close, day 0)
date: 2026-11-11
worker: edge-analyst (worktree agent-a387580a4ac70b709)
branch: research/execution-timing-b8
status: CLOSED — not run (power analysis)
---

# B-8 — does WHEN the monthly rebalancer trades change terminal wealth by more than it costs?

## 1. The question (H1 and refutation verbatim from the brief)

Source: `docs/Sources/alpha_frontier_program_2026_09_30.md` §3.2, "### B-8".

**Question (brief):** "for a monthly core+satellite rebalancer at Alpaca, does executing buys at the close
(capturing the overnight leg) vs at the open, and rebalancing on turn-of-month day −1 vs +1, change
terminal wealth by more than the measured cost?"

**H1 (brief, verbatim):** "one cell beats baseline by ci_low > 0 bps/yr."

**Refutation (brief, verbatim):** "none does ⇒ execution timing is noise at this turnover — record and stop."

**N (brief):** +1. **Brief prior:** 15%; "if positive, ≤ 20 bps/yr — free, compounding, and small."

B-8 runs in a **standalone harness** (the T-311 pattern). It does not use `BacktestController`.

## 2. Hard pre-commitments

1. **One gating configuration:** the primary flow model P (§5.1) on the native window W-13 (§4.3), at
   1.02 bps per side, with the project-standard block. No other flow model, window, cost, block or
   cell definition can become the headline.
2. **No tuning after any result.** Every sensitivity in §9 is named here. Each is reported beside the
   headline and never replaces it.
3. **Windows are set by input availability (§4.3), not by results.** The one data-quality rule that can
   move W-13's start is mechanical and declared now (§4.3, rule Q).
4. **Fetch once.** One yfinance call per ticker writes an md5-manifested snapshot. The harness reads only
   the snapshot and halts on any md5 mismatch. The fetch script refuses to overwrite a snapshot.
5. **Determinism ×2.** The results JSON must be bit-identical (md5) over two runs before any number is
   quoted.
6. **Smoke first.** The smoke covers the FIRST 12 months of each window. It checks mechanics only
   (event count, turnover > 0, cost charged, the identity locks). No smoke number is quoted.
7. **Outputs are worktree-local**, under `data/b8_local/` (a real directory). Nothing is written through
   the shared `data/research` symlink. `data/processed/` is not read (the drip HIGH, `d82f4b8`).
8. **Read-only everywhere else.** No edits to `engines/`, `paper_trader/`, `live_trader/`, `ops/`,
   `config/*`, `data/governor/*`, `backtester/` or `core/`. No registry write. No Alpaca call. Nothing is
   written to S3.

## 3. Input census (read-only; no returns computed)

### 3.1 What the deployed system actually does (it is not a monthly rebalancer)

Read from the code. Nothing is changed.

- **Weights:** `config/deploy_candidate.json` sets VOO 0.85 and MTUM 0.15. SGOV is the cash leg and holds
  only the residue that whole shares and the bands leave. Defaults are at
  `paper_trader/deploy_candidate_constructor.py:58-60`.
- **Bands in share quanta:** buy 1.5q, sell 1.0q, with a 0.10 max-drift backstop. At the $10k cap one VOO
  share is ≈ 6–7% of the book, so the core's buy band is ≈ 9–10%.
- **Cadence: DAILY, not monthly.** Account 2 (`offense-sso`, strategy `deploy_candidate`) fires at
  `cron(50 9 ? * MON-FRI *)` America/New_York (`scripts/provision_paper_fleet.py:53,305`). It places
  market DAY orders (`ARCHONDEX_SLEEVE_TIF=day`). The band check runs every session.
- **No close execution path.** The driver accepts TIF `day|opg` only (`scripts/run_paper_cloud_day.py:725-728`).
  A market-on-close order is not expressible today.
- **Contributions:** $583 per whole month since 2026-09-11, simulated by growing the notional cap. They
  arrive on the 11th, not at the turn of the month.

**Consequence.** The brief's "monthly rebalancer" is a stylized schedule, not the deployed mechanics.
B-8 answers: *if* the 85/15 were rebalanced once a month, does the execution time matter? Its relevance
to the daily band trigger is indirect, and the verdict will say so.

### 3.2 The prior evidence: T-341 (2026-08-15), and how B-8 differs

T-341 (`docs/Audit/exec_timing_verdict_t341_2026_08_15.md`, frozen at `85bf551`) found:
- **Arm A (open-vs-close COST):** NOT MEASURABLE. Daily bars carry no quotes, and Corwin-Schultz is wrong
  by 20–40× at SPY's liquidity.
- **Arm B (the close − open price gap on monthly dates, full notional):** SPY +6.8 bps per event,
  CI [−4.8, +17.7], n 316, MDE 16.2 bps. It was pre-registered with no verdict.
- **The real fills:** 0.26 / 0.51 / 1.02 bps vs arrival (n = 3). The ceiling on any cost saving is ≈ 1 bp.

**B-8 is not a re-run of T-341's Arm B.** That arm priced a full-notional trade. A held book captures
every overnight leg whatever time it trades, so execution timing touches only the **traded** dollars:
- for a closed 85/15 book, that is the monthly drift trade, ≈ 0.27% of the book per leg per month (§11);
- for a book with contributions, it also includes the new money.

B-8 measures the **terminal-wealth consequence at the deployed turnover**, which T-341 never did. It adds
the turn-of-month (TOM) axis.

### 3.3 The paper fleet's fill journal (S3, read-only)

Listed and copied OUT of the bucket with `aws s3 ls|cp --profile archondex`. Nothing was written to the
bucket.
- **Prefix:** `s3://archondex-results-407539788432/paper_state_offense_sso/data/`.
- **Files:** `paper_state/orders.jsonl` (82 lines, md5 `41b8389803ec45ccea5ef5c82455eb61`) and
  `state/exec_cost_ledger.jsonl` (12 rows, md5 `891da6b021547757c3f8b43a44c0a6f3`), both last pushed
  2026-11-11 08:51.

| | fills | instruments | slippage vs arrival (the ledger's own `slippage_bps`) |
|---|---|---|---|
| ≤ 2026-11-04 (used) | **10** | VOO 1, MTUM 1 (both the 2026-09-15 arrival), SGOV 8 (cash sweeps) | VOO 1.65; MTUM 0.00; SGOV 0.00–0.99. Notional-weighted 1.33 bps, simple mean 0.61, on $10,782.69 |
| 2026-11-05 (void, excluded) | 2 | the phantom MTUM 18-share buy (3.07 bps) and an SGOV sell | — |

**Every fill is a market DAY order submitted at ≈ 09:51 ET** (13:51 UTC under EDT, 14:51 UTC under EST).
There is **no fill at the open print and no fill at the close.** The journal therefore cannot measure
realized open-vs-close slippage.

> **The brief's journal cross-check is NOT AVAILABLE** (`[NN-FIRST-ARTIFACT]`). The artifact was opened
> and read, so this is not inferred from code. What it can supply is the 09:51 ET arrival-relative cost
> (n = 10; n = 1 each for VOO and MTUM). §6 uses it as a cost sensitivity.

A side observation: VOO and MTUM have not traded since the arrival event, in 36 clean sessions. The bands
did not bind once, which is consistent with the turnover bound in §11.

### 3.4 Prices: the planned fetches (Phase 2; nothing fetched yet)

- **Source:** free, keyless yfinance 1.2.0 (installed; pandas 3.0.1, numpy 2.4.3). One
  `Ticker(t).history(start="1999-11-01", end="2026-11-11", interval="1d", auto_adjust=False,
  back_adjust=False, actions=True, repair=False)` per ticker. `repair=False` keeps Yahoo's raw fields: the
  heuristic repair rewrites prices.
- **Tickers:**
  - **SPY:** the core and satellite proxy;
  - **VOO:** the core;
  - **MTUM:** the satellite;
  - **SGOV:** the cash leg (S1 only);
  - **^IRX:** the 13-week T-bill yield, the cash proxy before SGOV (S1 only).
- **Fields kept:** Open, High, Low, Close, Adj Close, Volume, Dividends and Stock Splits.
- **Snapshot:** `data/b8_local/snapshot/<ticker>.csv` plus `manifest.json`. The manifest holds each file's
  md5, the yfinance version, the exact call arguments and the UTC fetch time.

**How the legs get the same adjustment basis.** No adjusted open is needed. Yahoo's Open and Close are
split-adjusted but not dividend-adjusted. Its Dividends column is on the same split basis, and G4 (§10)
proves that. Each day splits into two legs:
- **overnight leg:** g_on(t) = (Open_t + D_t) / Close_{t−1}. The dividend D_t (ex-date t) belongs to the
  holder at close t−1, so it sits in the overnight leg;
- **intraday leg:** g_id(t) = Close_t / Open_t;
- **close-to-close total return:** g_on · g_id.

Each instrument gets a TR level at every open and close mark: L_C(t) = L_C(t−1) · g_on · g_id and
L_O(t) = L_C(t−1) · g_on.

**Cross-check (G5).** Yahoo's dividend factor is constant within a day: ex-date adjustments apply only to
bars strictly before the ex-date. So the equivalent adjusted open is AdjOpen_t = Open_t · AdjClose_t /
Close_t. G5 compares this TR with Yahoo's Adj Close path and halts on disagreement.

**Proxy rules (stated before any data):**
- **Core:** SPY until VOO's first full month (VOO incepted 2010-09-09), then VOO from 2010-10-01.
- **Satellite:** SPY until MTUM's first full month (MTUM incepted 2013-04-18), then MTUM from 2013-05-01.
- **Cash (S1 only):** ^IRX accrual, IRX_{t−1}/100 × calendar days/360, credited wholly to the overnight
  leg, until SGOV's first full month. SGOV TR from 2020-06-01. The proxy is approximate (discount vs
  investment yield) at a level that cannot move a bps/yr result.

**Consequence of the SPY proxy, stated now.** Before 2013-05 the satellite proxy is the same index as the
core, so the 85/15 has no drift and no rebalance trade.
- Before 2010-10, P's Δ is **identically zero** at zero cost. That becomes a positive-control lock (G10).
- From 2010-10 to 2013-04 (VOO vs SPY) it is ≈ 0.
- **So 2000–2013 carries no information about the rebalance timing.** That is why the gating window is
  W-13 (§4.3), and why W-00 runs only for the contribution arm S1, where SPY-timed new money is
  informative.

### 3.5 An independent Open-field validator (local Stooq raw; proposed, §18 ruling 5)

`data/raw/stooq/daily/us/nyse etfs/` holds Stooq OHLC for the four ETFs. It is a different vendor, and
it is not `data/processed/`.

| file | span | rows | md5 |
|---|---|---|---|
| `2/spy.us.txt` | 2005-02-25 → 2026-05-22 | 5,343 | `feafaef75ab078e9e24e73ace1561a3f` |
| `2/voo.us.txt` | 2010-09-14 → 2026-05-22 | 3,946 | `d574f6e21bff34701783a9f74ece5294` |
| `1/mtum.us.txt` | 2013-04-24 → 2026-05-22 | 3,288 | `e3f8e825b15bf9694246146f8ada255e` |
| `1/sgov.us.txt` | 2020-05-29 → 2026-05-22 | 1,504 | `f781fe1340b3dac27f3c652156944893` |

Stooq's levels are back-adjusted, and the project has open defect findings on its dividends (the
2026-11-11 health addendum to `d82f4b8`). So it is **never a return source here.** It is used for one
quantity that a per-day adjustment factor cannot touch: the intraday log ratio ln(Close/Open). If Yahoo's
Open field were stale or synthetic, the two vendors' intraday legs would disagree (G6).

### 3.6 Pinned read-only inputs (the harness records and checks these md5s)

| file | md5 |
|---|---|
| `config/deploy_candidate.json` | `f9969de4259a1cb2978872430a233892` |
| `paper_trader/deploy_candidate_constructor.py` | `494f30974a0134c7887a5c6677e8a547` |
| `core/metrics_engine.py` | `e8c5ecdef4c1d2380bc0b1f6766136df` |
| `core/measurement/mbl_gate.py` | `ab412ddca6e99e9594667ad9c0adb7ef` |

## 4. Cells, timing convention, windows

### 4.1 The turn-of-month day (proposed, §18 ruling 2)

On the NYSE trading calendar (SPY's native index):
- **day 0** of month m is the **last trading day of m**;
- **day −1** is the trading day before it;
- **day +1** is the first trading day of m+1.

With this definition the baseline (close, day 0) is the **month-end close**. That is the convention of
every standalone harness in this program (T-311 `robo_returns`, B-9, B-10), so B-8's baseline is the
book every other verdict assumed.

**Alternative (B):** day 0 = the first trading day of m+1. That is closer to a "first of the month"
schedule on the fleet's cron.

### 4.2 The six cells

| cell | executes at | relative to the baseline |
|---|---|---|
| (open, −1) | opening print, day −1 | ≈ 1.75 sessions earlier |
| (close, −1) | closing print, day −1 | 1 session earlier |
| (open, 0) | opening print, day 0 | day 0's intraday leg earlier |
| **(close, 0) — BASELINE** | closing print, day 0 (month-end close) | — |
| (open, +1) | opening print, day +1 | the overnight leg 0→+1 later |
| (close, +1) | closing print, day +1 | 1 session later |

- **"Open" means the official opening print** of the daily bar. The fleet actually fills at ≈ 09:51 ET.
  The 09:30→09:51 move cannot be observed in daily bars, so the open cells approximate the fleet's fill
  time with an error of about 20 minutes.
- **(open, +1)** is the cell nearest to what a monthly schedule on today's cron would do.

### 4.3 Windows (set by input availability)

| window | base (initial 85/15 at this close, identical in every cell) | events | terminal | years | role |
|---|---|---|---|---|---|
| **W-13 (gating)** | 2013-04-30 | the TOMs ending May-2013 … Nov-2025: **151** | 2025-12-31 close | 12.67 | P (gating), S1 |
| W-00 | 1999-12-31 | the TOMs ending Jan-2000 … Nov-2025: **311** | 2025-12-31 close | 26.00 | S1; P identity lock only |

- **The Dec-2025 TOM is excluded from every cell.** Its day +1 is 2026-01-02, after the terminal date, so
  every cell holds through the same terminal close.
- **Why the window ends 2025-12-31.** The brief says 2025. Data to 2026-11-10 will exist, but that period
  is not used. This also keeps the MTUM 4-for-1 split (2026-11-05) outside every window.
- **Rule Q (input quality, can only move W-13's start later; mechanical).**
  - A **suspect bar** is one with Open outside [Low, High] (relative tolerance 1e-6), High == Low, or any
    of O/H/L/C ≤ 0 or missing.
  - **The start moves later** to the end of the first month after which every calendar month has
    ≤ 1 suspect bar per instrument (VOO, MTUM).
  - **HALT** if a month after 2014-12 breaks the rule: the Open field would then be unusable mid-window.
  - Rule Q does not apply to SGOV, whose bars are often one cent wide by nature. SGOV gets G3 only.

## 5. Flow models (frozen)

### 5.1 P — the gating flow model: "monthly rebalance of the 85/15 at the deployed weights"

- **A closed book**, scale-free, with fractional units.
- At each event's execution mark, the book resets to exactly 85/15. With no contributions and no bands,
  it carries no SGOV.
- The drift trade every month is the **largest rebalance turnover any 85/15 monthly schedule can have.**
  The deployed bands only suppress trades. **P is therefore an upper bound on the rebalance component's
  timing exposure,** and a refutation under P covers the banded book too.

**Mechanics:**
- At mark τ, V = Σ uᵢ Lᵢ(τ), and the trade is tradeᵢ = wᵢ V − uᵢ Lᵢ(τ).
- The cost is κ Σ|tradeᵢ|. After the trade, V′ = V − cost and uᵢ = wᵢ V′ / Lᵢ(τ).
- Each cell's daily return is r_t = V(C_t)/V(C_{t−1}) − 1, on the identical trading-day index for every
  cell.

### 5.2 S1 — the deployed-scale contribution flow (pre-named, non-gating; §18 ruling 3)

S1 is P plus Rule-B contributions at the configured nominal scale:
- **Start:** $10,000 at the base close.
- **Contributions:** $583 per event, credited as cash at the close of the trading day before day −1, in
  every cell.
- **Cash:** earns the cash leg (§3.4) until the cell's execution mark. The whole book, cash included, then
  resets to 85/15.
- **Return series:** time-weighted daily returns r_t = V(C_t)/(V(C_{t−1}) + F_{t−1}) − 1. The
  money-weighted terminal ratio ln(W_T,cell / W_T,base) is reported as a point estimate only.

**Why S1 cannot meet H1.** In S1, executing earlier puts the new money in the market sooner. Its Δ is
mostly **time-in-market** (the equity premium per day of earlier exposure), not execution skill. Its sign
is known in advance: earlier cells win on average. That is the T-299 always-invest question, already
answered. S1 reports how large the timing stakes are for the money that actually moves. It is labelled
"includes time-in-market of new money".

### 5.3 S2 — the exact deployed mechanics (OFFERED; my recommendation is DROP, §18 ruling 4)

S2 is S1 plus the real `DeployCandidateConstructor.construct`, imported read-only and called once per
event at the cell's price:
- whole shares at nominal (split-reconstructed) prices;
- the 1.5q / 1.0q / 0.10 bands;
- cash-first funding;
- the SGOV sweep.

**Why I recommend dropping it.**
- **The noise is not timing.** At the $10k scale, one VOO share is ≈ 6% of the book. Two cells that trip a
  band one month apart hold a 6% VOO-vs-SGOV difference for a month, which is ≈ 25 bps of noise per
  divergence. That swamps any timing effect.
- **P already bounds S2's rebalance component from above.** S2's Δ would mostly measure rounding-path
  chaos.

## 6. Cost model (frozen)

- **Primary: κ = 1.02 bps per side** on every traded notional, in every cell, at the open and at the
  close. This is the top of the measured 0.26–1.02 range the brief names.
- **Why symmetric.** No instrument we hold distinguishes the cost at the open from the cost at the close.
  T-341 Arm A was NOT MEASURABLE, and every journal fill is at 09:51 ET (§3.3). B-8 therefore measures
  the **return-timing** component. Any open-vs-close **cost** difference is unmeasured and assumed zero.
- **Why the assumption barely matters.** Under P the baseline trades ≈ 6.4% of the book per year (§11).
  Even a 5 bps open-vs-close cost asymmetry would be worth ≈ 0.3 bps/yr.
- **Sensitivities (§9):**
  - κ = 0;
  - κ = 1.65 bps, the journal's lone VOO fill and the largest pre-void core/satellite fill;
  - the journal's notional-weighted 1.33 bps sits inside that range.
- **Inception is not charged to any cell.** The initial allocation at the base close is identical in all
  cells, so the convention is symmetric.

## 7. Metric and bootstrap (frozen)

- **Paired daily differential per non-baseline cell k:** d_k,t = ln(1 + r_k,t) − ln(1 + r_base,t), on the
  identical date index (asserted).
- **Headline:** Δ_k = Σ_t d_k,t = ln(TW_k / TW_base), reported in **bps/yr** = 10⁴ · Δ_k / years.
  - **Identity check:** Σ d = ln(TW_k/TW_base) from the two equity curves to 1e-9, or HALT.
- **Bootstrap (gating):**
  - The call is `MetricsEngine.bootstrap_distribution(d_k, metric_fn=sum, n_iterations=1000,
    block_length=None, seed=0)`. This is the project-standard moving-block bootstrap (Künsch 1989).
  - The auto block is max(5, round(n^⅓)): **15 days on W-13** (n ≈ 3,190) and **19 on W-00**.
  - The same seed, the same n and the same block give **identical resample indices for every cell.** The
    five cells are therefore paired with each other as well as with the baseline.
- **p-values from the bootstrap.**
  - From p_above_zero: p⁺_k = (1 + #{S* ≤ 0}) / 1001 and p⁻_k = (1 + #{S* ≥ 0}) / 1001.
  - Two-sided: p_k = min(1, 2 · min(p⁺_k, p⁻_k)).
  - The smallest attainable p_k is 2/1001 ≈ 0.002, below the first Holm threshold of 0.01.
- **Also reported per cell:** the unadjusted 95% interval (2.5th / 97.5th percentiles), which is the
  brief's literal "ci_low", and the 99% interval (0.5th / 99.5th), which is Holm's first-step bound.

## 8. Multiple comparisons, decision rule, pre-named outcomes

**Multiplicity: Holm step-down over the 5 non-baseline cells,** two-sided, family α = 0.05. That is
equivalent to a one-sided family α of 0.025 in each direction, the same level as a single 95%
`ci_low > 0`.
- **Why Holm and not BH.** H1 is "one cell beats the baseline", and acting on it would change the
  execution schedule. The error that matters is any false "this time is better", so FWER control is the
  right standard. FDR is not.
- **The cells are positively dependent.** Adjacent cells share interval legs. Holm is valid under any
  dependence.

| outcome | condition | what it means | what it does NOT mean |
|---|---|---|---|
| **H1 MET** | Holm rejects ≥ 1 cell with a positive Δ (P, W-13, κ 1.02, auto block) | That execution time beat the month-end close for the 85/15 rebalancer on 2013–2025, beyond multiplicity. | Not deployment evidence unless the MBL line (§12) clears. Not an operational change: a close/opening-auction order path is a `paper_trader/` change, propose-first. Not material unless the point exceeds the baseline's cost drag and ≈ 1 bp/yr (T-341's ceiling). Both are reported. |
| **NOT MET — does not survive multiplicity** | Holm rejects no cell positive, but ≥ 1 cell has unadjusted ci_low > 0 | The brief's literal reading would fire. The family-wise reading does not. Reported plainly, not quoted as a finding. The operational consequence is the same as REFUTED: record and stop. | Not H1. |
| **REFUTED** | no cell has unadjusted ci_low > 0, so Holm rejects none either | "Execution timing is noise at this turnover." Record and stop. The verdict prints each point and its CI, so "not demonstrated" and "demonstrably zero" stay distinguishable. | Not a claim that timing can never matter (§16). |
| **BASELINE DOMINATES cell k** (reported with either outcome above) | Holm rejects k with a negative Δ | Moving execution to k would have cost wealth. **Decision-relevant if k = (open, +1)**, the cell nearest the fleet's ≈ 09:51 practice. | Not H1. Same family and same test, so no extra N. Any order-path change is propose-first. |

**Labels that attach without changing the category:**
- "**not robust to monthly blocks**" if the 21-day block changes a Holm decision;
- "**not robust to cost**" if κ = 0 or κ = 1.65 changes one;
- "**not robust to the TOM definition**" if alternative-B dating (only if ruled in) changes one.

## 9. Pre-named secondary reporting (non-gating; consumes no N)

1. **Block sensitivities:** 21-day (one event period) and 252-day, on P.
   - **Why 21 matters.** Within a month the cells' weight differences persist, so if MTUM's active return
     has a nonzero mean, d_t carries a month-long persistent component.
2. **Cost sensitivities:** κ = 0 and κ = 1.65 bps, on P.
3. **S1** on W-13 and W-00, with the same Holm table, labelled "includes time-in-market of new money".
   Plus the money-weighted terminal ratio (point only).
4. **The oracle ceiling (not tradable).** Σ over events of the max over the six cells of the event-level
   Δ (one event's earliest mark to the next's), in bps/yr, on P/W-13. **It bounds what ANY timing rule
   could have extracted from this flow with perfect hindsight.**
5. **Decomposition per cell** (descriptive):
   - the traded-fraction term Σ Δw · r(interval);
   - the persistent-weight term (the rest-of-month carry);
   - the mean turnover per event, the baseline's cost drag in bps/yr, and the cell's own.
6. **The 09:51-ET journal costs** (§3.3): n = 10, by instrument.
7. **The Open-field validation** (§3.5 / G6): per instrument, the correlation and mean difference of the
   daily intraday log legs, Yahoo vs Stooq, on the overlap.
8. **Overnight vs intraday split per instrument on W-13** (descriptive): the mean overnight and intraday
   log legs, all days and TOM days. This is context for the "capture the overnight leg" premise. It is not
   a test.

## 10. Fail-closed guards (`[NN-FAIL-CLOSED]`) and the locks that prove them

| ID | guard | HALTS when |
|---|---|---|
| G1 | snapshot manifest md5s; the pinned read-only md5s (§3.6) | any mismatch |
| G2 | native index per instrument | non-monotonic, duplicate, or a NaN/≤ 0 in O/H/L/C/Adj Close inside a window |
| G3 | open sanity | any Open outside [Low, High] (rel. 1e-6) inside a window; rule Q (§4.3) for VOO and MTUM |
| G4 | dividend sanity (proves the split basis) | any D < 0; any single D / Close_{t−1} ≥ 3%; the trailing-12-month yield outside [0, 4%] for SPY/VOO/MTUM. An MTUM dividend left on the pre-2026-11-05 share basis would read ×4 and trip it. |
| G5 | own TR vs Yahoo Adj Close | on non-ex-dates, \|Δ ln\| > 1 bp on > 0.5% of days or > 10 bps on any day; on ex-dates, \|Δ ln\| > 5 bps; window-level gap > 3 bps/yr |
| G6 | Yahoo vs Stooq intraday legs (if ruled in) | correlation < 0.95 or mean \|difference\| > 10 bps per instrument over the in-window overlap |
| G7 | joint calendar | any instrument missing a day of SPY's calendar inside a window after its native start. Never forward-filled. |
| G8 | TOM events | the event count ≠ 151 (W-13) or 311 (W-00); any event without a distinct −1/0/+1; day 0 not the month's last trading day |
| G9 | Σd identity (§7) | violated |
| G10 | identity locks on the real data | (a) P on W-00 before 2010-10 at κ = 0: every cell's Δ is exactly 0 (both legs SPY) to 1e-12. (b) The general engine's baseline equals an independent vectorized month-end-close 85/15 reset to 1e-12. |
| G11 | cell distinctness (the re-exec lesson) | any non-baseline cell's return series equals the baseline's on every day of an event in which P trades; any post-2013 event with zero turnover in any cell |
| G12 | bootstrap input | length < 2 × 252, or < 2 × block |
| G13 | no secrets, no broker | an `APCA_*` variable becomes set during the run (checked by name, never printed); any network call other than the one fetch |

**Locks:** `tests/test_b8_execution_timing_guards.py`, synthetic data only, no `data/` dependence.
- G3, G4, G7 and G8 are proven by planting the defect: an Open above the High, an MTUM dividend ×4, a
  missing day, and a month with a duplicated day 0. Each must raise.
- **The sign convention gets a positive control.** In a synthetic two-asset market, the satellite earns
  +10 bps on every overnight leg and 0 intraday, and the core is flat. A rebalance that BUYS the satellite
  at (close, 0) must beat (open, +1) by exactly the analytic amount. Swapping the legs must flip the sign.
- G10(a) also gets a negative control: a 1-bp cost or a single perturbed price must break the zero.

## 11. Power, MDE, and the mechanical ceiling (literature assumptions; no data used)

**Assumptions:**
- MTUM − VOO active return: TE ≈ 9%/yr, so σ_a ≈ 0.57%/day and 2.6%/month;
- w(1 − w) = 0.1275.

**The rebalance trade:**
- The monthly drift trade per leg has RMS 0.1275 × 2.6% ≈ 0.33% of the book (mean |·| 0.27%).
- The baseline therefore trades ≈ 6.4% of the book per year, a cost drag of ≈ **0.07 bps/yr** at κ 1.02.

**How a cell differs from the baseline.** A cell executing one session away from the baseline differs in
two places:
1. the traded fraction over the interval: Δw · r_a(1 session), SD ≈ 1.9e-5;
2. a persistent weight gap, 0.1275 · r_a(1 session), carried through the rest of the month: SD ≈ 1.8e-5.

That gives ≈ 2.6e-5 per event (0.26 bps), ≈ 0.91 bps/yr, and **SE ≈ 0.26 bps/yr over 12.67 years.**

| quantity (P, W-13) | value |
|---|---|
| SE of Δ, one-session cells | ≈ 0.26 bps/yr (overnight-only ≈ 0.16; intraday-only ≈ 0.21; (open, −1) ≈ 0.33) |
| **MDE, 80% power, Holm first step** (one-sided 0.005) | **≈ 0.9 bps/yr** (range 0.55–1.1 across cells) |
| MDE, unadjusted 95% | ≈ 0.7 bps/yr |
| plausible true \|Δ\| | ≤ 0.3 bps/yr: \|corr\| ≤ 0.1 between the traded weight and the interval's active return |
| **oracle ceiling** (perfect hindsight, best of 6 cells every month) | ≈ 2–5 bps/yr |

**The brief's "≤ 20 bps/yr" is mechanically out of reach for the closed 85/15.** Even an oracle gets
about one tenth of it, because the book holds every overnight leg anyway and only ≈ 0.3% of it moves
each month. A 20 bps/yr effect needs traded fractions two orders of magnitude larger. That happens only
with large external flows, which is S1's territory.

**S1, for scale.** $10k growing with $583 per month gives a new-money share of 5.8% falling toward
≈ 0.2–0.5%. The expected time-in-market gain of one session earlier is ≈ +0.5–0.7 bps/yr, with
SE ≈ 1.3 bps/yr on both windows, so the MDE is ≈ 3.6 (unadjusted) to 4.4 (Holm) bps/yr. S1 is
underpowered for its own expected effect.

**So B-8 can resolve sub-basis-point effects for the rebalance**, because the traded fraction is small.
What it cannot do is find a large one, because none can exist at this turnover.

## 12. Honest-N context (read-only, never written)

The read went through `core/measurement/mbl_gate.py` (`compute_n_effective`,
`compute_n_effective_correlated`, `load_n_effective_artifact`), on the pinned inputs
(`config/honest_n_pin.json`).
- `data/observability/run_registry.sqlite` md5 `83e474412a37075db16d419ad3dea414`, identical before and
  after the read (the gate opens it `mode=ro`).
- **The gate's N:** N_raw = **231**; ρ̄ (ci_low) 0.4325; ONC compression 0.1598. **N_eff (conservative)
  = 36.92** (equicorrelated 33.51, ONC 36.92). **At N_raw + 1 (this trial): N_eff = 37.08.**
- **The hand count.** The registry omits standalone-harness trials (health MEDIUM `573fc62`), so the
  trials are counted by hand:
  - ≥ 282 at the B-10 verdict (267 from ruling 9.2, plus 13 standalone trials since, plus B-10's 2);
  - **+1, this trial = ≥ 283**;
  - ≈ 290 if the July T-306 standalone series is outside the 267.

**The MBL line for the differential's IR** uses the exact form E[max_N]/√T. It is a reported secondary,
not part of H1:

| window | T (yr) | IR needed @ N_eff 37.08 | IR needed @ hand N 283 (290) |
|---|---|---|---|
| W-13 | 12.67 | 0.607 | 0.808 (0.810) |
| W-00 | 26.00 | 0.423 | 0.564 (0.566) |

**What a pass below the line would mean.** If H1 is met with the differential's IR (annualized mean d /
annualized SD d) below the line, the verdict reads "**Holm clears, MBL does not**: exploratory, not
deployment evidence" (`[NN-MBL]`).

## 13. N_trials

**+1:** one configuration (P/W-13), one test family of five cells under Holm. The two-sided reading
(§8's baseline-dominates row) is the same family, so it adds nothing.

The following are characterization, not selection, and consume no N (the B-5 / B-9 / B-10 practice): S1,
the oracle ceiling, the block and cost sensitivities, the decomposition, the journal costs and the Stooq
validation.

**If the director wants S1 able to carry its own verdict, the count is +2.** If S2 is ruled in as a
quotable arm, it is +3. The smoke runs consume none.

## 14. Predictions (frozen here; the verdict compares against them)

| quantity | prediction |
|---|---|
| P/W-13, every cell's Δ | \|point\| < 1 bp/yr; every 95% CI contains 0; CI half-widths ≈ 0.3–0.7 bps/yr |
| P/W-13, Holm | rejects nothing in either direction |
| oracle ceiling | 2–5 bps/yr |
| baseline cost drag (P) | 0.05–0.10 bps/yr; mean one-way turnover per leg per event 0.2–0.35% |
| S1 | earlier cells ((open, −1), (close, −1), (open, 0)) positive points, later cells negative; \|Δ\| ≤ 2 bps/yr; no Holm rejection |
| 21-/252-day blocks; κ 0 / 1.65 | change no category |
| journal | open-vs-close NOT AVAILABLE (already established, §3.3) |
| overnight vs intraday (descriptive) | for SPY and VOO, the overnight leg carries most of the mean on 2013–2025 (Lou-Polk-Skouras); MTUM similar but noisier |
| **outcome** | **REFUTED** — execution timing is noise at this turnover |

## 15. Honest prior (before any data)

**P(H1 MET) ≈ 4%,** well below the brief's 15%.
- **There is no room for an effect.** A held 85/15 already earns every overnight leg. Only the ≈ 0.3% of
  the book that moves each month is timed, so the plausible effect (≤ 0.3 bps/yr) is about a third of the
  MDE.
- **What is left is mostly false positives.** About 2.5% is the Holm family's one-sided false-positive
  rate, and about 1.5% is a real sub-bp effect landing in the upper tail.
- **The deployed system confirms it.** VOO and MTUM have not traded since arrival (§3.3).
- **Where the brief's 15% / 20 bps could come from.** It implicitly priced the timing on the whole book,
  as T-341 Arm B's full-notional framing does. On the deployed turnover, the same idea is worth roughly
  100× less.
- **If H1 is met anyway, it is immaterial.** The effect will be below 1 bp/yr. The verdict would then
  read "statistically detectable, economically immaterial; no order-path change proposed" unless the point
  exceeds T-341's ≈ 1 bp ceiling.

**The three outcome rows of §8 are mutually exclusive:**
- P(H1 MET) ≈ 4%;
- P(NOT MET, unadjusted only) ≈ 8%. Under the null, five correlated one-sided 2.5% tests fire at least
  once ≈ 8–12% of the time;
- P(REFUTED) ≈ 88%.

P(baseline dominates some cell), which can co-occur with any of the three, is ≈ 3%.

## 16. Scope exclusions

- No intraday (minute-bar) execution times. T-341's director freeze declined that build. 09:51 ET is
  approximated by the open print (§4.2).
- No cost model by time of day: it is unmeasurable on held data (§6).
- No other weights, satellites or rebalance frequencies. No band search. No contribution-size search.
- **No claim about large flows.** A lump-sum arrival or a much larger contribution-to-book ratio re-opens
  the question. Its stakes then are time-in-market, which T-299 governs.
- No `paper_trader/` change. An order-path proposal, if any, is propose-first and outside B-8.
- No `BacktestController`, no network beyond the one fetch, no Alpaca, no registry write.

## 17. Computation performed before this draft (complete list)

1. **The S3 journal.** `aws s3 ls` of the account-2 prefix, then a read-only `cp` of `orders.jsonl` and
   `exec_cost_ledger.jsonl` OUT to a session scratch directory. Then field and row counts, fill times, and
   the ledger's own recorded `slippage_bps` summarized pre/post void (§3.3).
2. **The local Stooq files.** Header, span, row count and md5 for the four tickers. No price was read
   into a computation.
3. **The honest-N read** (§12), plus the MBL and MDE arithmetic on literature assumptions (§11, §12).
4. **md5s** of the pinned read-only files (§3.6).

**No price was fetched. No instrument, leg, cell, portfolio or differential return has been computed.**

## 18. Rulings requested before the run

1. **The gating window is W-13** (2013-04-30 → 2025-12-31, native VOO/MTUM), not 2000–2025. Under the
   SPY proxy, the 85/15 is degenerate before 2013-05 and P's Δ there is identically ≈ 0 (§3.4). W-00 runs
   for S1 and the G10(a) lock only. *(Alternative, not proposed: splice PDP, the Invesco DWA Momentum ETF
   from 2007-03, as a pre-2013 momentum proxy. That is one more fetch and a different methodology.)*
2. **TOM dating:** day 0 = the last trading day of the month (§4.1). The baseline is then the month-end
   close every other harness uses. Alternative B (day 0 = first trading day) only if the director prefers
   it.
3. **Flow model:** P (closed book) gates. S1 (Rule-B contributions at the deployed scale) is a labelled,
   non-gating secondary that cannot meet H1 (§5.2). N = +1.
4. **S2 (the exact constructor with whole shares and bands): DROP** (§5.3). If kept, it is non-gating.
5. **The Stooq raw Open-field validator (G6):** allowed as a validator only, never a return source
   (§3.5). It is not `data/processed/`.
6. **The cost model:** κ = 1.02 bps symmetric (primary), with 0 and 1.65 as sensitivities. Open-vs-close
   cost is assumed equal, because it is unmeasurable on held data (§6).
7. **Multiplicity:** two-sided Holm at family α = 0.05 over 5 cells (§8). The brief's unadjusted ci_low is
   reported beside it but does not decide H1.

## 19. Sequence

1. Draft (this commit), then **STOP for the director's acknowledgment and rulings**.
2. Freeze amendment.
3. Fetch once and snapshot (`scripts/b8_fetch_snapshot.py`).
4. Build the harness (`scripts/b8_execution_timing.py`) and the locks.
5. Smoke the first 12 months of W-13 and W-00.
6. The full run.
7. Determinism ×2 (md5).
8. The verdict, `docs/Audit/b8_execution_timing_verdict_2026-11-11.md`.
9. The full suite.
10. Commit on `research/execution-timing-b8` (`feat(research): B-8 execution-timing cells for the
    monthly rebalancer`), and add the CLI to `docs/Core/execution_manual.md`.

No push, no merge.

## Reproduce the pre-run census

```bash
# §3.3 the fill journal, read-only (copy OUT of the bucket only)
aws s3 ls --profile archondex --recursive s3://archondex-results-407539788432/paper_state_offense_sso/data/
D=$(mktemp -d); for f in paper_state/orders.jsonl state/exec_cost_ledger.jsonl; do
  aws s3 cp --profile archondex --only-show-errors \
    s3://archondex-results-407539788432/paper_state_offense_sso/data/$f $D/; done; md5 $D/*
# §3.5 / §3.6 md5s
md5 -q "data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt" "data/raw/stooq/daily/us/nyse etfs/2/voo.us.txt" \
  "data/raw/stooq/daily/us/nyse etfs/1/mtum.us.txt" "data/raw/stooq/daily/us/nyse etfs/1/sgov.us.txt"
md5 -q config/deploy_candidate.json paper_trader/deploy_candidate_constructor.py core/metrics_engine.py \
  core/measurement/mbl_gate.py
# §12 honest N, read-only
python -c "from core.measurement.mbl_gate import compute_n_effective_correlated as f; print(f(method='conservative'), f(method='equicorr'), f(method='onc'))"
```

---

## §20 DIRECTOR RULING 2026-11-11 — CLOSED WITHOUT RUNNING (N_trials 0)

**The director ruled on the Phase 1 draft (`54d0104`): B-8 is CLOSED WITHOUT RUNNING.** This section is
appended. Nothing above it was changed except the frontmatter `status:` line, which the ruling asked for.

### The ruling

**Verdict: "execution timing is noise at this turnover — closed by power analysis, not by measurement."**

- **No price was fetched.** No snapshot exists.
- **No return was computed.** That covers instrument, leg, cell, portfolio and differential returns.
- **N_trials consumed: 0.** Spending an honest-N trial on a question that arithmetic already settles would
  raise the bar for every later test and buy nothing. The honest-N count stays where B-10 left it: the gate's
  N_raw 231 / N_eff 36.92; the hand count ≥ 282 (≈ 289 if the July T-306 series is outside the 267).
- **The seven rulings requested in §18 are moot.**

### The arithmetic that closes it (from §11; literature assumptions, no data)

| quantity | value |
|---|---|
| turnover: the monthly drift trade of the 85/15 at an MTUM−VOO tracking error of ≈ 9%/yr | ≈ 0.27% of the book per leg per month (RMS 0.33%), ≈ **6.4% of the book per year**; cost drag ≈ 0.07 bps/yr at 1.02 bps per side |
| MDE (80% power, Holm first step, 12.67 years) | **≈ 0.9 bps/yr** (0.55–1.1 across cells; ≈ 0.7 unadjusted) |
| plausible true effect | **≤ 0.3 bps/yr** |
| perfect-hindsight ceiling (the best of the six cells, chosen every month) | **≈ 2–5 bps/yr** |
| the brief's "if positive, ≤ 20 bps/yr" | impossible at this turnover |

**The mechanism.** A held book earns every overnight leg whatever time it trades. Execution timing
touches only the dollars that move: about 0.3% of the book per month for a closed 85/15. Even an
oracle captures about a tenth of the brief's ceiling. The true effect is about a third of what the test
could detect.

### The durable output: census facts (each read from the artifact, not inferred)

1. **The deployed system is not a monthly rebalancer** (§3.1):
   - Account 2 (`offense-sso`, strategy `deploy_candidate`) checks its bands every trading day at 09:50 ET
     (`cron(50 9 ? * MON-FRI *)`, `scripts/provision_paper_fleet.py:53,305`).
   - It sends market DAY orders (`ARCHONDEX_SLEEVE_TIF=day`).
   - The driver accepts TIF `day|opg` only (`scripts/run_paper_cloud_day.py:725-728`), so **no
     market-on-close path exists.**
   - Rule-B contributions ($583) grow the notional cap on whole months since 2026-09-11, so they land on
     **the 11th**, not at the turn of the month.
2. **The fill journal cannot answer open-vs-close** (§3.3).
   - **Location:** `s3://archondex-results-407539788432/paper_state_offense_sso/data/`. I only listed it and
     copied files out; nothing was written to the bucket.
   - **Files:**
     - `paper_state/orders.jsonl`: 82 lines, md5 `41b8389803ec45ccea5ef5c82455eb61`;
     - `state/exec_cost_ledger.jsonl`: 12 rows, md5 `891da6b021547757c3f8b43a44c0a6f3`;
     - both pushed 2026-11-11 08:51.
   - **All 12 fills are market DAY orders at ≈ 09:51 ET.** No fill sits at the open print or at the close.
   - **The 10 fills ≤ 2026-11-04:**
     - VOO 1.65 bps and MTUM 0.00 bps, one fill each, both the 2026-09-15 arrival;
     - SGOV 0.00–0.99 bps, n 8, cash sweeps;
     - **1.33 bps notional-weighted, 0.61 bps simple mean**, on $10,782.69.
   - The two 2026-11-05 fills (the void, split-day record) are excluded.
   - VOO and MTUM have not traded since the arrival: the bands did not bind in 36 clean sessions.
3. **The prior close-vs-open read is T-341's** (`docs/Audit/exec_timing_verdict_t341_2026_08_15.md`).
   - Arm B, full-notional, on monthly dates 2000–2026: SPY close − open **+6.8 bps per event,
     CI [−4.8, +17.7]**, n 316, MDE 16.2 bps. It carried no verdict, by pre-registration.
   - Arm A (the cost of open vs close) was NOT MEASURABLE on held data.
   - The real fills then were 0.26 / 0.51 / 1.02 bps vs arrival (n 3).

### What WOULD re-open it

- **An order type the driver cannot send today.** A market-on-close or limit-on-close path (MOC/LOC; TIF
  `cls`) would make the close cells executable. The first thing to measure would then be its realized
  cost vs arrival, from that order type's own fills.
- **Turnover an order of magnitude higher.** That means ≳ 60% of the book per year: a large
  contribution-to-book ratio, a lump-sum arrival, or a tactical book. Re-run the §11 arithmetic at the
  new turnover before proposing any test. For new money, the stakes are mostly time-in-market (T-299),
  not execution skill.

Neither condition holds on 2026-11-11.
