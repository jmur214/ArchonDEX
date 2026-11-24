# T-409 freeze record — the real-money home study (2026-11-24)

**Status: FROZEN by the director on 2026-11-24.** This file freezes the pre-registration by naming the exact files. The prereg cannot hold its own hash, so the freeze lives here.

## What is frozen (at main `6450533`)

| File | SHA-256 |
|---|---|
| `docs/Sources/prereg_real_money_home_t409_DRAFT_2026-11-19.md` (revision 5) | `ae71e99c1c5706b0a15adbbccadfa31e41667d162706db4a33392cd91b0721ea` |
| `scripts/t409_real_money_home.py` | `8bc74b97540d43fb22b50c2ea65a9346aeec983b6c268e26996e17e1e5eef252` |
| `tests/test_t409_real_money_home.py` | `f8c589507aeea10353c2bbc3d1eb44ce0f447e604dc8877eb1093d25f2c57e7c` |
| `core/metrics_engine.py` | `fda5341be63601c396be3d52850dfb44cbe90f33ff9f4accbf30cbcf11668316` |

The prereg's "DRAFT — NOT FROZEN" status line is superseded by this record. Its text is unchanged.

## Frozen inputs

Held at `/Users/jacksonmurphy/Dev/_research_snapshots/t409_real_money_home_2026-11-20/inputs/` and md5-pinned in the code (`INPUT_MD5`).

| File | SHA-256 |
|---|---|
| `F-F_Research_Data_Factors_daily_CSV.zip` | `96c23b88e651cbfff3740a53f8225e59ee39893371e96385a1d8125ec2cd9c89` |
| `fred_CPIAUCNS.csv` | `30ae6c271b6ea2319a1fb132562848042738adf058dfc853abdbd3a46f36004c` |
| `shiller_ie_data.csv` | `230c0272bd650596ed8f1a4e918ffa1bbb37b39190ee235a251b435cc689630d` |
| `JSTdatasetR6.xlsx` | `c1bb91fe56ea50d4f27af5c0fc897d481e89ae38ce41eaecab62134c9354981d` |
| `manifest.json` | `6de01bbc618cd7c222b3caade0893acda62afa56b3aa8cd6324a837abe1ab33b` |

## Director's rulings at freeze

1. **Decision rule: the pair rule of prereg §3.1** (`--decision-row pair`). Each decision is read in `param:h=+0.00` and `param:h=-0.02`. Agreement is the choice; disagreement resolves to K1 and is flagged.
2. **Owner override: none.** The owner was asked on 2026-11-20 and 2026-11-24 and stated no view on the forward equity premium.
3. **Trial count: 17, counted raw** (5 primary arms, 7 sensitivity arms, 3 JST analogs, 2 gate mixes). Recorded in `config/honest_n_trials.json` at this freeze.
4. **What this study is.** A decision study of ordinary manual choices at an institutional broker. It involves no strategy, account or code path of the trading machine. Its outcome licenses no deployment of the machine.
5. **Disclosed before the run.** A smoke on 10-year 1990s cohorts showed decision B flipping between belief rows before the pair rule was chosen (prereg §3.1).

## The run

Two full runs with the documented command (`run --jst --decision-row pair --progress`), whose `results.md5` must match. Only then are the results read.
