---
name: project-t403-prediction-markets-2026-11-17
description: T-403 prediction-market probe design — Kalshi venue, near-close FLB taker hypothesis, per-event power, wrapper/tax blocker, archive defects; DRAFT prereg not frozen
metadata:
  type: project
---

T-403 (2026-11-17): design note + DRAFT prereg for a forward PAPER probe, committed on the worktree branch as 4b4b588 (not merged). Files: `docs/Sources/design_note_prediction_markets_t403_2026-11-17.md`, `docs/Sources/prereg_t403_prediction_market_paper_probe_DRAFT_2026-11-17.md`. No trial count stated; the director rules it at freeze.

**Why:** the fresh-eyes audit (2026-11-14) said only per-event niches can clear honest-N ≈ 372 on ≤26-yr data, and suggested "one paper probe" on prediction markets (prior ~10 %).

**Key facts worth not re-deriving:**
- **Venues.** Kalshi direct is the venue: public orderbook and trades (`security: []`), signed Ed25519/RSA keys with no stated expiry, taker fee 0.07·C·P(1−P) rounded up (maker 0.0175 on some series). Polymarket international = close-only for US persons. Polymarket US (QCX) taker Θ = 0.095 below $10k of 30-day volume. ForecastEx/IBKR charges a flat 1c per contract, which is worse than Kalshi for favourites.
- **Wrapper — the biggest blocker.** No venue is confirmed for a Roth (tastytrade: Kalshi "not IRAs"; IBKR unknown). In a taxable account the treatment is unsettled, and the wagering reading is punitive: losses deductible only by itemizers, ≤ winnings, at 90 % under §165(d).
- **Literature.** Bürgi–Deng–Whelan (Jan 2026; Kalshi 2021–Apr 2025) document the FLB robustly, but TAKERS still lose on average at high prices. Makers buying ≥ 50c earn +2.6 % (SD 33 %) before maker fees. The 2025 ψ = 0.021 against 0.048 in 2024. My linear arithmetic: the taker's net edge is ≈ 0 pooled and ≈ −1.3 % on the 2025 coefficients.
- **Live census** (2026-11-18 03:19Z): about 23 qualifying events/day (42 markets). Median depth at the favourite's best ask is $42 (25th percentile $1.84); median spread 2c; 19 of 42 asks at 0.99.
- **Power** (σ_event 0.20, design effect 1.5, 20 events/day): MDE 0.71 % (z 1.645) / 1.09 % (z 2.96) at 12 months; 0.50 / 0.77 % at 24 months. The plausible true edge is 0–0.5 %, so the probe is a kill-test.
- **Priors:** effect exists 20 %; material 8 %; passes within 12 months ≈ 8 % (one-trial bar) / ≈ 2 % (N_eff 372 bar).
- **Archive defects found:**
  - the generic Kalshi snapshot has 100 % null prices for five months;
  - the Polymarket archive has no bid/ask and no resolution;
  - the CEF feed has failed since 2026-10-19;
  - the archiver UA sends the owner's contact address to non-SEC hosts (against the SEC-only ruling).

**How to apply:** if asked to build the recorder or freeze the prereg, start from the files above. Do not re-propose the maker form as a paper test (see [[feedback-paper-probe-taker-only]]). Do not use the alt-data archive to choose or check the rule.
