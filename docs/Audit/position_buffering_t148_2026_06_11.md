---
task_id: T-2026-06-11-148
title: Carver position buffering (10% inertia) — Engine C post-processor, default-OFF
date: 2026-06-11
substrate: n/a (wiring + run-pair ACCOUNTING; no performance comparison; zero N_trials)
scope: Engine C autonomous (position_buffering.py + policy fields + compute_target_allocations branch); no prod flip — enable rides a pre-registered A/B (T-098 precedent)
outcome: **Delivered.** Trade-to-edge buffering behind `position_buffering_enabled: false` (+ `buffer_fraction: 0.10`), composing AFTER T-139 dynamic optimization. OFF canon-bitwise (`5d88e1a0…` ×3, det 3/3); ON fires (`9a2e804f…`). 43 tests green. **THE COUPLED HEADLINE: turnover ↓11% (26.0×→22.5× equity/yr) ⇒ exec cost ↓$46/yr (4.5 bps/yr) + tax ↓$1,341/yr (130 bps of equity/yr) — the tax channel is ~29× the cost channel** at the book's 100%-ST realization (T-141 coupling). TE price: realized ON-vs-OFF 3.05% annualized (band bound ≤10%/position). Honest T-098 echo: turnover fell 11%, NOT the predicted 60-70% — the vol-target-dominance failure mechanism partially carries even under trade-to-edge.
---

# T-148 — Position buffering (Carver 10% inertia)

## The coupled headline (accounting on the 2024 run pair, zero N_trials)

`python -m scripts.demo_position_buffering_t148 <off_dir> <on_dir>`:

| | OFF | ON (buffer 10%) | Δ |
|---|---:|---:|---:|
| fills | 1,297 | 1,225 | −72 (−5.6%) |
| turnover $ | $2,669,722 | $2,369,364 | **−$300,358 (−11%)** |
| turnover ×equity/yr | 26.0 | 22.5 | −3.5 |
| exec cost (realistic model) | $571 | $525 | −$46/yr = **4.5 bps/yr** |
| tax owed (taxable-IL, T-141 module) | $18,934 | $17,598 | −$1,341/yr = **130 bps of equity/yr** |

**The coupling is the finding: at this book's tax posture (100% ST
lots, wash-sale-heavy — T-141), a turnover lever is worth ~29× more
through the tax channel than through execution costs.** Cost-only
valuation of turnover reduction understates it by an order of
magnitude in the taxable account (and by exactly that much LESS in the
Roth — buffering's value is account-dependent, which feeds the T-141
router's allocation logic).

**The price, shown honestly:** positions drift inside the band —
band-implied bound ≤10% of each position; the REALIZED on-vs-off
tracking error this cell is **3.05% annualized**. (Single-cell Sharpe
deltas exist in the artifacts and are deliberately NOT quoted — a real
enable decision rides a pre-registered deep-window A/B; the T-098
precedent demands it.)

## How this differs from T-098's refuted no-trade band (required)

| | T-098 (REFUTED 2026-05-31) | T-148 (this) |
|---|---|---|
| Level | WEIGHT-space proportional band on `max(\|target\|,\|curr\|)`, 20–25% | POSITION-space band, `0.10 × \|optimal shares\|` (Carver convention) |
| Outside the band | trade ALL THE WAY to the center (full rebalance) | trade to the band EDGE (every executing trade is shrunk by the band width) |
| Measured failure | trade COUNT −17–19% but dollar turnover ~flat: small rebalances got suppressed, the DOMINANT daily vol-target moves passed through at full size | the haircut applies to every passing move too — both margins attacked |
| Did the failure carry? | — | **Partially, honestly: turnover ↓11%, not 60–70%.** The vol-target moves still dominate; trade-to-edge takes `band/move` off each (a 30%-of-position move still executes ~2/3+). The economics survive anyway because the TAX channel multiplies the modest turnover cut ×29. |

T-098's verdict ("band model assumes concentrated long-hold; our book
is diversified daily-vol-target") stands as a SHARPE claim — nothing
here contradicts it, and no Sharpe claim is made. What T-098 didn't
price was the tax channel: it predates T-141's after-tax machinery.

## What was built

- `engines/engine_c_portfolio/position_buffering.py` — pure
  trade-to-edge module: band `[N*−f|N*|, N*+f|N*|]`; inside → hold;
  outside → integer edge rounded INTO the band (no-integer bands fall
  back to `round(N*)`); zero target collapses the band → full close;
  output weights carry the T-139 ±1e-6-share nudge (Engine B truncation
  parity tested). Fail-open per ticker; sorted-ticker determinism.
- `PortfolioPolicyConfig.position_buffering_enabled = False` +
  `buffer_fraction = 0.10`; mirrored in portfolio_settings.json.
- **Composition order (documented + tested):** `allocate → dynamic
  optimization (T-139) → position buffering (THIS) → Engine B`. When
  dyn-opt is ON, buffering bands around its integer-implied book (the
  end-to-end test asserts every buffered target sits within the band of
  dyn-opt's positions); when OFF, around the unrounded optimal shares.
- OFF path: branch short-circuits, module never imported (asserted).

## Proofs

- **OFF inertness:** post-change OFF canon `5d88e1a0f70f0cd052a7813a6e40b1a9`
  ×3 bitwise, Sharpe 0.991 — the standing baseline chain (T-139 → T-146
  → T-147 → now), det 3/3.
- **ON fires (the T-146 standing step):** `position_buffering_enabled:
  true` for one 2024 run → canon `9a2e804fb8e92b9b79d6274a7bfdca56` ≠
  baseline; config reverted (working-tree diff = the feature keys only).
- **Tests: 43 green** (`tests/test_position_buffering_t148.py`): band
  semantics (inside-hold incl. exact edges; outside → edge NOT center,
  incl. flat-entry edge-sizing), short-side symmetry, zero-target
  close, no-integer-band fallback, buffered < full-rebalance trade
  sizes, Engine-B truncation parity, scale invariance ×20 seeds (≤1
  share of rounding granularity at 2×), dyn-opt composition (unit +
  end-to-end through PortfolioEngine), determinism, input-order
  invariance, fail-open (unpriceable ticker / invalid equity), zero
  buffer = full rebalance-to-integer, wiring inertness. Full suite:
  2265 passed, the standing pre-existing 5 only (one transient
  concurrent-window extra appeared while the proof ran — T-147's
  documented residual class; quiet re-run = known-5 exactly).

## What a pre-registered enable-A/B would test (the T-098-grade gate)

Pre-registration BEFORE any cells: hypothesis = buffering at f=0.10
improves AFTER-TAX portfolio-level economics without degrading pre-tax
Sharpe beyond noise. Cells: 12-yr + 26-yr, OFF vs ON {0.05, 0.10}
(primary = 0.10, named in advance; 0.05 sensitivity). Criteria (all
ci_low-aware): (i) pre-tax Sharpe Δ ci_low > −0.10 (non-degradation,
NOT improvement — the lever isn't a Sharpe claim); (ii) after-tax
Sharpe (T-141 module) Δ ci_low > 0 on the taxable account; (iii)
realized turnover ↓ ≥ 8%/yr sustained across years; (iv) tracking
error vs OFF ≤ 4% annualized. N_trials consumed: 2 primary. Enable
decision = user-gated on those numbers; Roth account may rationally
stay unbuffered (no tax channel — only the 4.5bps cost channel vs the
TE price).

## Files

- `engines/engine_c_portfolio/position_buffering.py` — NEW
- `engines/engine_c_portfolio/policy.py`, `portfolio_engine.py` — fields + branch + `_apply_position_buffering`
- `config/portfolio_settings.json` — keys (false / 0.10)
- `tests/test_position_buffering_t148.py` — NEW; 43 tests
- `scripts/demo_position_buffering_t148.py` — NEW; the coupled accounting
- this audit

## NOT done

- Any prod flip / Sharpe claim (pre-registered A/B required — above)
- Buffering inside live_trader (follows the backtest convention at the paper milestone)
- f-sweep beyond the demo's 0.10 (the A/B's sensitivity arm)
