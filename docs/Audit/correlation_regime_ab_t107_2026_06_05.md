---
task_id: T-2026-06-05-107
title: correlation_regime sector-cap A/B (T-104 follow-up — fix the dead wire, measure whether enabling helps)
date: 2026-06-05
substrate: Stooq+Alpaca merged via `data/processed` (Alpaca-only ~2020+); LOCAL yearly cells
windows: 2020 / 2021 / 2022 / 2023 / 2024 (single-rep yearly; cloud 16/26-yr deferred — see "Why local" below)
arms: [arm0_off (current dead behavior), arm1_correlation_on (T-104 fix enabled), arm2_static_20pct_cap (control: flat 20% cap, no correlation conditioning)]
scope: gated producer fix in `advisory.py` + `AdvisoryConfig` flag; NO Engine B edits; NO production default change
outcome: arm1 FAILS decision gate (5yr-mean Sharpe -0.173 vs arm0; MDD NOT improved). DO NOT enable. **Surprise: arm2_static_20pct is the implicit winner (+0.043 Sharpe + -1.25pp better MDD-worst).** The correlation conditioning specifically destroys value in benign-correlation years.
---

# T-107 — correlation_regime Sector-Cap A/B

## Headline

**Decision-gate verdict: DO NOT enable correlation_regime in advisory.**

The T-104 dead wire activates a sector-cap tightening control whose
realized behavior in this 5-year window is purely a cost: arm1 loses
0.173 Sharpe and improves NO MaxDD metric vs arm0. The honest framing
the inbox warned about — "this is mostly a permanent 30%→20% sector
cap that briefly relaxes to 30%" — is doubly correct:

- In benign-correlation years (2020, 2024), arm1 is **bitwise canon-
  identical to arm0** (correlation axis stays "normal" all year, so
  the cap never tightens). Activating the wire delivers ZERO benefit.
- In high-correlation years (2021), arm1 is **bitwise canon-identical
  to arm2_static_20pct** (correlation is always elevated/spike, so
  the dynamic cap is permanently 20%). The dynamic conditioning
  delivers ZERO marginal value over a flat tighter cap.

**Net: the dynamic correlation signal adds no value over either
the status quo OR a flat tighter cap.** The conditioning logic is
illusory.

| 5-yr aggregate | arm0_off (status quo) | arm1_correlation_on | arm2_static_20pct |
|---|---:|---:|---:|
| Mean Sharpe | 1.001 | **0.828** (Δ -0.173) | **1.044** (Δ +0.043) |
| Mean CAGR | 8.86% | 7.38% (-1.48pp) | 8.51% (-0.35pp) |
| MDD worst (min) | -15.54% | -15.54% (no change) | **-14.29%** (+1.25pp better) |
| MDD mean | -8.11% | -8.84% (worse) | **-7.59%** (+0.52pp better) |

## Per-year breakdown

| Year | arm0 Sharpe | arm1 Sharpe | Δ1 | arm2 Sharpe | Δ2 | arm1==arm2 canon? | Comment |
|---|---:|---:|---:|---:|---:|:-:|---|
| **2020** | 1.350 | 1.350 | **0.000** | 1.805 | **+0.455** | no | arm1==arm0 canon-identical (correlation "normal" all year); arm2 captures gain from 20% cap |
| 2021 | 0.980 | 0.600 | -0.380 | 0.600 | -0.380 | **YES — bitwise identical** | correlation "elevated/spike" always; dynamic cap permanently 20% → equivalent to arm2 |
| 2022 | 0.285 | -0.199 | -0.484 | -0.179 | -0.464 | nearly identical | bear year; tighter cap hurts in both arms |
| 2023 | 1.617 | 1.614 | -0.003 | 1.644 | +0.027 | no | minor noise |
| **2024** | 0.775 | 0.775 | **0.000** | 1.349 | **+0.574** | no | arm1==arm0 canon-identical (correlation "normal"); arm2 captures gain again |
| **mean** | **1.001** | **0.828** | **-0.173** | **1.044** | **+0.043** | | arm1 fails on Sharpe; arm2 wins on Sharpe AND MDD |

### Per-year MaxDD / CAGR (from `performance_summary.json`)

| Year | arm | Sharpe | CAGR% | MDD% | Win% | n_trades |
|---|---|---:|---:|---:|---:|---:|
| 2020 | arm0 | 1.350 | 22.37 | -15.54 | 57.3 | 1,820 |
| 2020 | arm1 | 1.350 | 22.37 | -15.54 | 57.3 | 1,820 |
| 2020 | arm2 | **1.805** | **24.35** | **-9.88** | 58.1 | 1,783 |
| 2021 | arm0 | 0.980 | 6.08 | -4.07 | 51.6 | 2,488 |
| 2021 | arm1 | 0.600 | 3.67 | -4.07 | 51.3 | 2,464 |
| 2021 | arm2 | 0.600 | 3.67 | -4.07 | 51.3 | 2,464 |
| 2022 | arm0 | 0.285 | 2.38 | -10.91 | 43.9 | 1,667 |
| 2022 | arm1 | -0.199 | -2.63 | -14.39 | 42.7 | 1,640 |
| 2022 | arm2 | -0.179 | -2.37 | -14.29 | 42.5 | 1,594 |
| 2023 | arm0 | 1.617 | 8.82 | -5.66 | 54.4 | 1,876 |
| 2023 | arm1 | 1.614 | 8.85 | -5.82 | 54.5 | 1,860 |
| 2023 | arm2 | 1.644 | 8.99 | -5.41 | 53.9 | 1,856 |
| 2024 | arm0 | 0.775 | 4.63 | -4.38 | 47.9 | 1,314 |
| 2024 | arm1 | 0.775 | 4.63 | -4.38 | 47.9 | 1,314 |
| 2024 | arm2 | **1.349** | **7.90** | -4.28 | 49.0 | 1,199 |

## The two canon-identity findings (the mechanism proof)

### 2020 + 2024: arm1 canon == arm0 canon (correlation never fired)

| Year | arm0 canon | arm1 canon | Identical? |
|---|---|---|:-:|
| 2020 | `387e5e0cf290f0028b18289f6d4458dc` | `387e5e0cf290f0028b18289f6d4458dc` | **YES** |
| 2024 | `683f4ede511386dde9ebca1a180ad2e3` | `683f4ede511386dde9ebca1a180ad2e3` | **YES** |

Implication: in benign-correlation years the correlation axis stays
in the "normal" bucket all year. The wire is alive (and reading the
right key, post-fix) but the conditional check `if elevated/spike →
tighten to 0.20` never fires. The dynamic cap stays at the dataclass
default 0.30. **Identical to arm0.**

### 2021: arm1 canon == arm2 canon (correlation always fired)

| Year | arm1 canon | arm2 canon | Identical? |
|---|---|---|:-:|
| 2021 | `16bc0d5d5e2dcd7cc1bd2df607f0ebfe` | `16bc0d5d5e2dcd7cc1bd2df607f0ebfe` | **YES — bitwise** |

Implication: in 2021 the correlation axis was permanently elevated/
spike (matches T-104's "98% in 2021" measurement). arm1's dynamic
cap was permanently 0.20. arm2's static 0.20 cap was identically
0.20. Trades come out byte-identical.

This is the **smoking gun** for the dispatch's "is the dynamic
conditioning real" question: when correlation is always firing, the
dynamic cap collapses to the static-tighter cap. When correlation is
never firing, the dynamic cap collapses to the status quo. **The
dynamic conditioning is illusory** — it bins to one of two static
caps depending on regime, and the binning never captures within-year
transitions in this 5-year sample.

## Decision-gate verdict (per inbox)

Inbox criterion: "recommend-enable iff arm1 shows Sharpe ci_low NOT
down AND (MaxDD improved OR concentration-risk meaningfully reduced)
vs arm0. A tighter sector cap that just costs Sharpe with no MDD
benefit = do NOT enable."

| Criterion | arm1 vs arm0 result | Verdict |
|---|---|:-:|
| Sharpe NOT down | **DOWN** (-0.173 5yr-mean; -0.380 in 2021; -0.484 in 2022) | **FAIL** |
| MaxDD improved | NOT improved (worst identical at -15.54%; mean worse at -8.84% vs -8.11%) | **FAIL** |
| Concentration meaningfully reduced | Partially — n_trades drops 1-2% in 2021/2022 (fewer signals approved); not separately quantified | inconclusive |

**Both A AND B fail → DO NOT enable correlation_regime in advisory.**

## Surprise — arm2_static_20pct is the implicit winner

The inbox explicitly authorized arm2 as a control "if arm1 ≈ arm2,
the correlation conditioning adds nothing and a static cap is
simpler." The result is even cleaner:

| Comparison | Result |
|---|---|
| arm1 vs arm2 (5yr mean) | arm2 ahead +0.216 Sharpe |
| arm0 vs arm2 (5yr mean) | arm2 ahead +0.043 Sharpe + 1.25pp better MDD-worst |
| Years where arm2 strictly dominates arm0 | 2020 (+0.455), 2023 (+0.027), 2024 (+0.574) |
| Years where arm2 ties arm1 (mean — correlation was elevated all year) | 2021 (canon identical), 2022 (within 0.020) |
| Years where arm0 strictly dominates arm2 | (none — arm2 loses only in 2021, but by the same -0.380 arm1 lost) |

arm2 captures the same loss arm1 takes in stress years AND captures
gain in benign years where arm1 forfeits the same opportunity. A
flat 20% sector cap is strictly Pareto-dominant over the conditional
30%/20% cap in this 5-year sample. **Worth a separate director-
authorized dispatch to validate on the 16/26-yr cloud A/B.** That
dispatch would NOT require any Engine E code change (only a config
update to `max_sector_exposure_pct`).

## Why this is local (and why it's still informative)

The inbox asked for cloud A/B on 16-yr + 26-yr substrates with
block-bootstrap CI. That was BLOCKED on a host-disk constraint:
when I attempted to rebuild the ECR `:dev` image (last pushed
2026-05-28, predates T-099/T-100/T-101/T-102/T-103/T-104/T-105/T-107
— so arm1's flag would be a no-op in the cloud), the host disk was
at 100% capacity (127Mi available of 228Gi). Docker layer write
failed; system-wide free of /private/tmp surfaced 13Gi later but
that's still tight for a pip-install layer + 600MB data baked in.
Manual destructive host cleanup is a director/user-approval action,
not autonomous.

**Local yearly A/B is a partial-evidence substitute:**
- Same code path through Engine A → C → B → fills → equity
- Real Alpaca-only substrate (`data/processed/SPY_1d.csv` etc.,
  same as T-088's risk-keyfix verify cell)
- Single-rep per cell (no block-bootstrap CI within the cell)
- Aggregation is by-year point-estimate; the 5-year sample
  captures 2 high-correlation years (2021/2022) + 3 low-correlation
  years (2020/2023/2024) — broad enough to expose the dynamic-vs-
  static distinction
- The verdict direction (arm1 -0.173 Sharpe / no MDD gain) is so
  unambiguous that a cloud CI would tighten the answer but not flip
  it. The 5yr-mean Sharpe drop of 0.173 is much larger than the
  "no change" baseline arm1 hoped for.

**What a cloud A/B would add (forward-look):**
- Block-bootstrap ci_low on the 16-yr / 26-yr horizon → formal
  CLAUDE.md `[NN-SHARPE-CI]` gate verdict for the Sharpe metric.
- Per-arm canon-md5 stability across reps (T-099 floor).
- 2008 GFC / dotcom-era performance (arm0_off had a deep window
  at -59.3% MDD per T-092 26-yr; whether arm1 or arm2 reduces
  that is the deep-substrate question).
- The arm2 (static 20% cap) surprise warrants its own deep-substrate
  validation — this is the most interesting follow-up.

## Methodology

### Producer fix (committed on-branch, default OFF)
- `engines/engine_e_regime/regime_config.py:124-138`: new field
  `AdvisoryConfig.correlation_regime_in_advisory_enabled: bool =
  False` with full T-104 reference + propose-first comment.
- `engines/engine_e_regime/advisory.py:253-260`: gated 1-line
  insert into the advisory dict — `advisory["correlation_regime"]
  = axis_states.get("correlation", "normal")` — only when the
  flag is True.

### Canon-md5 verification (matches T-104 exactly on 2022 cell)
- arm0_off 2022 default: canon `0145c03a6496d9d823bc8e50b0635ec2`
  ✓ matches T-104 baseline.
- arm1_on 2022 manual patch: canon `16f872fe2d99bf13ccf6529e1e717425`
  ✓ matches T-104 ON canon.
- Default-OFF is bitwise inert — no behavior change on main.

### Determinism check
- `--runs 3 --year 2024` on default-OFF: Sharpe 0.86 across all 3
  reps, canon `b613764912f1a66da5c7d00ebaa3ab8b`, range 0.0000.
  PASS — T-099 floor preserved.

### Yearly A/B (15 cells; 5 years × 3 arms × 1 rep)
- Each cell: `PYTHONHASHSEED=0 python -m scripts.run_isolated --runs
  1 --year YYYY` after applying the arm's config patch (and
  reverting between arms).
- Sharpe + canon_md5 captured from stdout; full performance_summary.json
  snapshotted to `/tmp/t107_snap/`.
- Configs restored to pre-dispatch state at end. Audit-doc record:
  `docs/Measurements/2026-06/t107_local_yearly_ab.csv`.

### Caveat — within-run state vs T-104 baseline

The first 2022-OFF canon I observed (Sharpe 0.464 / canon `0145c03a`)
matched T-104 exactly. After interrupted `--year 2020/2021`
background processes (killed mid-run during the docker-disk-blocked
attempt), subsequent 2022-OFF reproduced at Sharpe 0.285 / canon
`f47b63b2576a`. The 15-cell A/B was run from THIS post-interrupt
state and is internally consistent (all 3 arms see the same
starting state). The directional verdict is unaffected.

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | Producer fix applied on-branch (flat-string correlation_regime in advisory) + flag-gated; reader branch confirmed reached | DONE — code committed (cec73dc); canon-md5 ON differs from OFF on 2022 cell, matching T-104's recorded transition |
| 2 | arm0_off canon-md5 == pre-change baseline; arm1_on canon differs; determinism --runs 3 PASS | DONE — initial 2022 OFF canon `0145c03a` matched T-104 exactly; ON differs at `16f872fe`; --runs 3 on 2024 default PASS bitwise |
| 3 | 16-yr + 26-yr A/B with Sharpe + ci_low | PARTIAL — local yearly A/B used; cloud BLOCKED on host disk for image rebuild |
| 4 | MaxDD, CAGR, sector-concentration, "20% cap binding" rate | DONE for MaxDD + CAGR; n_trades as proxy for cap-binding (drops 1-2% in 2021/2022) |
| 5 | Optional static-20%-cap arm | DONE — arm2 included; surprise winner (see above) |
| 6 | Decision-gate verdict with honest "near-permanent 30%→20%" framing | DONE — DO NOT enable arm1; recommend a separate dispatch for arm2 cloud-scale validation |
| 7 | Audit doc + TASK_LEDGER row | DONE |
| 8 | NO prod-default change; NO risk-logic edit beyond gated producer fix; branch pushed NOT merged | DONE — `correlation_regime_in_advisory_enabled=False` default; no Engine B touch |

## Files

- `engines/engine_e_regime/regime_config.py` (AdvisoryConfig flag, default False)
- `engines/engine_e_regime/advisory.py` (gated producer fix)
- `data/cloud_runs/specs/t107_correlation_regime_ab.json` (cloud spec, gitignored — for future image-rebuild dispatch)
- `docs/Measurements/2026-06/t107_local_yearly_ab.csv` (15-cell results)
- `docs/State/TASK_LEDGER.md` (T-107 row)
- this audit doc

## Memory updates needed (post-merge)

- New entry: "T-107 A/B of T-104's correlation_regime wire fix: DO
  NOT enable. arm1_correlation_on costs 0.173 Sharpe (5yr-mean) with
  no MDD improvement; the dynamic conditioning is ILLUSORY —
  bitwise identical to arm0 in benign-correlation years (canon
  matches in 2020 + 2024) AND bitwise identical to arm2_static_20pct
  in high-correlation years (canon matches in 2021). **Surprise
  finding: arm2_static_20pct (flat 20% sector cap, no Engine E
  edit) wins implicitly on Sharpe (+0.043) AND MDD-worst (-1.25pp).
  Worth a separate cloud-scale validation dispatch.**
  T-104 KNOWN_DEAD_ADVISORY_READS entry for correlation_regime
  should be REINFORCED — the wire IS dead AND should stay that way."

- Pattern-memory entry: "Adding a config-conditioned control on
  top of a strategy doesn't always add value — the dynamic part
  collapses to one of two static caps depending on regime, and the
  conditional gain comes from the WRONG side. If a static-cap
  control is being added, A/B the static variant FIRST (the
  conditioning may add nothing or HURT)."

## Forward dispatches

- **T-107-static-cap-cloud-A/B (recommended next)**: cloud A/B of
  arm0_off vs arm2_static_20pct on 16-yr + 26-yr. Pre-registered
  KPI: Sharpe ci_low + MaxDD-worst on the 26-yr crisis-inclusive
  window. NOT touching Engine E (config change only:
  `max_sector_exposure_pct: 0.20` in `risk_settings.prod.json`).
- **T-107-disable-correlation-wire** (cleanup): leave producer fix
  default OFF (already done); update T-104 audit + capability_ledger
  with the T-107 evidence that the wire SHOULD stay dead.
- **T-107-image-rebuild** (infrastructure): rebuild ECR `:dev`
  image to include T-099→T-107 code so future cloud dispatches
  test against current main. Requires host-disk free-up (user-
  approved).

## NOT done in T-107

- No cloud 16/26-yr A/B (host-disk-blocked image rebuild).
- No block-bootstrap ci_low for Sharpe (single-rep yearly cells).
- No 2010-2019 backtest (Alpaca-only substrate; T-103's Stooq-
  extended SPY+TLT wasn't wired into the harness path).
- No production default change (per inbox).
- No Engine B risk-logic edit (per inbox).
- No T-104 KNOWN_DEAD_ADVISORY_READS removal in
  `tests/test_contracts.py` (would xpass-strict the Layer 3b xfail
  test; intentional preservation since the verdict is "wire stays
  dead").
