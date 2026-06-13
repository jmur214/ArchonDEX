---
task_id: T-2026-06-13-164
title: P0 — current main makes ZERO cloud trades (hermetic fundamentals-fetch abort)
date: 2026-06-13
author: Agent D (alpha/edge lane)
outcome: FIXED + PROVEN. Root cause = the LIVE yfinance fall-through in
  fetch_historical_fundamentals was the one network path T-155's hermetic-pin
  sweep missed; under hermetic any value-edge candidate without a baked
  fundamentals parquet (75 of 654 resolved names) hit it → abort/hang → zero
  trades. Fix = hermetic_block guard (mirrors _fetch_yfinance). PROOF: a local
  ARCHONDEX_HERMETIC=1 arm0 run (the cloud no-network condition) now COMPLETES
  with 14,492 trades (was zero), the guard firing 63× as graceful skips.
  + sp500_membership.parquet pinned & baked (manifest + Dockerfile) to close
  the gitignored-data-drift hazard. Unblocks B's re-anchor + all cloud work.
status: CURRENT
reproduce: |
  python -m pytest tests/test_fundamentals_hermetic_t164.py -q     (3 pass)
  ARCHONDEX_HERMETIC=1 arm0 backtest -> completes, trades>0 (see §proof)
  python -m scripts.gen_substrate_manifest verify                  (OK, membership pinned)
---

# T-164 — the zero-cloud-trades P0

## Root cause (pinned with evidence — and an honest divergence from the brief)

**Structural cause (CERTAIN, tested):** `DataManager.fetch_historical_fundamentals`
falls through cache → SYNTH → `fundamentals_static.csv` (only **2 tickers**) →
a **LIVE `yf.Ticker(...)` fetch at data_manager.py:226**. That fetch had **no
`hermetic_block` guard** — the single network path the T-155 pin sweep missed
(cf. `_fetch_yfinance`, which IS guarded, and the earnings pin). Under
hermetic/cloud (no network) the live call aborts/hangs the run → zero trades.
`fundamental_value.py:65` ("Fetching fundamentals…") is the last line before it,
matching B's observation. **75 of 654 resolved-universe names lack a baked
fundamentals parquet** (585 exist) — each is a candidate that reaches the
unguarded fetch.

**Trigger attribution — I diverge from the brief, honestly.** The brief
hypothesised T-154's `sp500_membership.parquet` regeneration changed the baked
universe. The evidence does not support that as the mechanism:
- `data/universe` was **NOT** in `Dockerfile.backtest` (only processed/raw/
  governor) → the membership file was never baked → the cloud resolver hits the
  `fallback_to_static` path (universe_resolver.py:192), so my T-154 regen could
  not have changed the cloud universe.
- The fundamentals parquets ARE baked (data/processed) and **already
  manifest-pinned (1315 entries)** → drift-protected.
- T-154's code changes (PIT hook) are default-OFF and inert (T-161 proved the
  OFF path returns the identical slice object).

So the precise first-trigger ("why current-main when 5323a3c traded") is **not
cleanly attributable to T-154**. What is certain and load-bearing: the
unguarded fetch is a latent hermetic-safety gap that aborts for ANY uncovered
value-edge name, on ANY build/universe. The fix closes it permanently;
chasing the exact historical trigger is not worth gating the P0 on.

## The fix (Engine-A / data_manager lane — the T-155 hermetic pattern)

`data_manager.py`: a `hermetic_block("data_manager.fetch_historical_fundamentals",
ticker)` gate immediately BEFORE the live-fetch `try` (so strict mode isn't
swallowed). Under hermetic it returns empty → `fundamental_value` scores 0 and
continues (the no-data outcome it already handles) → **run COMPLETES**. Local
(hermetic off) behaviour is byte-unchanged; cache/static hits return before the
guard. This is exactly the `_fetch_yfinance` / earnings-pin pattern, applied to
the one site that was missed.

## Membership pin + bake (closes the gitignored-drift hazard)

`sp500_membership.parquet` is gitignored and was neither baked nor pinned — its
silent T-154 regeneration broke historical-universe runs repo-wide (the hazard
the brief rightly wants closed). Fix:
- `scripts/gen_substrate_manifest.py`: new curated `SUBSTRATE_FILES` mechanism
  pins **the file only** (NOT `data/universe/`, which holds the bulky rebuildable
  scrape cache). Regenerated manifest diff = **+1 line, nothing else** (14,092
  other files bitwise-unchanged — no unrelated drift folded in). `verify` passes.
- `Dockerfile.backtest`: `COPY data/universe/sp500_membership.parquet` so the
  cloud resolver uses the **real historical universe** instead of the static
  fallback it silently hit when the file was absent.

**FLAG for B (universe behaviour change):** baking the membership panel means a
fresh image's resolver returns the historical-S&P union, not the static
fallback. That is a deliberate, now-pinned correctness fix — but it CHANGES the
cloud universe vs prior builds. B must fold this into the re-anchor and
re-validate the anchor canons against it (the guard guarantees it trades; the
canon will reflect the corrected universe).

## Proof — cloud condition reproduced + unblocked (acceptance #4)

A local `ARCHONDEX_HERMETIC=1` arm0 run on 2024 (510 tickers, 30 edges) — the
exact cloud no-network gate, run locally so no cloud build is needed and the
network-hang cannot occur:
- **COMPLETED with 14,492 trades** (current main = ZERO). VERDICT: unblocked.
- The guard fired **63×** (`[HERMETIC] BLOCKED … fetch_historical_fundamentals
  ticker=ANSS/BF.B/BRK.B/…`) — the uncovered names that previously aborted, now
  graceful skips.

I am handing B the **green current-main source + pinned manifest** on this
branch to fold into the re-anchor image build (per the brief's offered path);
the local hermetic completion is the equivalent controlled proof.

## Tests (3, fast, deterministic, no real network)
`tests/test_fundamentals_hermetic_t164.py`: uncovered+hermetic → empty via guard
(no network touched, BLOCKED logged); without-guard demonstration that the live
call IS reached (the cloud hang point); cached ticker served from parquet
regardless (common path byte-unchanged).

## Files
- `engines/data_manager/data_manager.py` (hermetic guard on the fundamentals fetch)
- `scripts/gen_substrate_manifest.py` (curated SUBSTRATE_FILES) + `config/substrate_manifest.sha256` (regenerated, +membership)
- `Dockerfile.backtest` (bake membership file)
- `tests/test_fundamentals_hermetic_t164.py` (NEW), this audit.

## Follow-ups
- **B:** rebuild current-main image with this source+manifest → confirm the
  cloud cell trades + re-anchor against the corrected (historical-union)
  universe.
- The 75 uncovered names score 0 on the value edge (graceful). Building a
  vintage-stamped fundamentals parquet covering them would PRESERVE value-edge
  behaviour rather than skip it — a coverage enhancement (the value edge is
  factor-negative per T-117, so low priority), not the unblock.

## NOT included
No Engine B / live_trader. No fetch-logic rewrite (guard only). No TASK_LEDGER
write (T-114). Branch only; director merges.
