---
task_id: T-2026-07-10-306
title: Scope — the multi-decade substrate (T-305 tripwire #1; ex-T-050)
date: 2026-07-10
worker: Agent B
branch: feature/multidecade-substrate-scope-t306
status: SCOPE (0 N_trials). Scope → director go → build. Nothing built yet.
---

# T-306 — Multi-decade substrate: scope

## Executive answer (read first — it revises the task's premise)
Three findings change the shape of this build:

1. **The Stooq wall is NOT the binding constraint.** The deep index-level legs come
   from FRED + Fama-French + Shiller — all **non-Stooq and refreshable**. The Stooq
   bot-wall only freezes the *ETF / single-stock* bundle, which is not what a deep
   *index-level* sleeve substrate is built from. So "banked before the walls went up"
   is true for equity but irrelevant for the depth path.

2. **The EQUITY+BOND core is extendable to the 1960s TODAY, from free refreshable
   sources, no new sourcing.** Verified on disk / live: FRED **DGS10 → 1962-01-02**
   (build the bond-TR synthetic exactly as `bond_synth_dgs10_t255.csv` does, just
   deeper); Fama-French **Mkt-RF+RF daily → 1926** (daily total-market equity + cash);
   Shiller **1871** (monthly, equity-only, for a pre-1926 extension). A **daily
   1962–2026 (~64yr) 2-asset equity+bond substrate is buildable with zero new data
   acquisition.**

3. **GOLD is the single hard blocker for the 3-ASSET sleeve.** On disk, gold floors at
   **2000-08-30** (`gold_gcf`) / 2005 (GLD) — the exact reason the current fair
   substrate stops at 2000. Deep gold is NOT on disk, and the two obvious FRED LBMA
   IDs (`GOLDAMGBD228NLBM`, `GOLDPMGBD228NLBM`) **404** (verified; other FRED series
   succeeded in the same call). Pre-1971 gold is a *fixed $35 peg* — no trend signal
   exists to backtest — so the honest 3-asset floor is **free-float ≈ 1968**, and
   reaching it requires **sourcing an LBMA daily gold-fix series (1968+) from outside
   FRED** (LBMA publishes it free at lbma.org.uk; World Gold Council is a fallback).

**Therefore the build splits into two honestly-different deliverables:**
- **D-A (immediate, free): the 2-asset equity+bond deep substrate, 1962–2026.** Clears
  MBL by itself (below) and is the substrate on which the T-305 tripwire-#1 rule
  meta-validation can run *now*.
- **D-B (gated on gold sourcing): the full 3-asset substrate to ~1968.** Blocked ONLY
  on the LBMA gold fetch; everything else (bond 1962, equity 1926) is ready.

## ⚠️ DIRECTOR CORRECTION (2026-07-27, from the adversarial holistic audit) — the MBL/DSR headline below is WRONG in the way that matters

The computation below holds **SR = 0.598** fixed — the SUPERSEDED, survivorship-inflated static-109 equity-book
baseline that `[NN-AUDITS-NOT-CURRENT]`/CURRENT_STATE explicitly say not to quote, describing a book nobody
deploys. "Clears DSR with 2.4-2.6× margin" is therefore a statement about a dead strategy's absolute Sharpe —
NOT about either deploy candidate. The deploy decisions ride on **difference metrics** (sleeve-minus-benchmark,
offense-minus-buy-hold), whose CIs straddle zero at 26yr; the deep window's honest value is that it can test
THOSE differences across 8-10 crises for the first time (T-311/T-312 do exactly this) — not that it "clears"
anything by holding a stale Sharpe. At the honest PIT-measured base (~0.119) the deep window does not clear at
all. The substrate remains the program's most valuable measurement asset; this headline framing is retracted.

## Why this is the decisive lever — the MBL/DSR number [SUPERSEDED — see the correction above]
`[NN-MBL]`: `T_years ≥ 2·ln(N_eff)/SR²`. At N≈75, SR=0.598 (the corrected baseline):
**T_required = 2·ln(75)/0.598² ≈ 24.1 years.** The current 2000–2026 substrate (26yr)
barely reaches it; the 5yr exploratory window needs SR≥1.55 (unreachable). A **64yr**
(2-asset) or **~58yr** (3-asset, 1968) substrate clears the 24.1yr requirement with a
**2.4–2.6× margin** — the 0.598 baseline would clear DSR for the first time. Even after
the re-verification runs each add to N (say N→~90 → T_required ≈ 24.9yr), the margin
holds. **This is why the multi-decade substrate is the program's biggest single unlock:
it is the only lever that moves the baseline from "cannot clear DSR on any honest
window" to "clears with room."**

## 1. On-disk inventory (depth, TR/price, frozen vs refreshable)
| Leg | Deepest on-disk | TR? | Deeper source (verified) | Frozen or refreshable |
|---|---|---|---|---|
| Equity | SPY_1d.csv **1993** (TR); tr_reconciled SPY **2005** | TR | **FF Mkt-RF+RF daily 1926**; Shiller **1871** (monthly, price+div) | SPY/ETF FROZEN (Stooq wall); FF + Shiller **refreshable** |
| Bond | bond_synth_dgs10 **2000** (TR); AGG **2005** | TR | **FRED DGS10 → 1962-01-02** (verified live) | **refreshable** (FRED) |
| Cash | DGS3MO **2000** on disk (FRED series → 1981); DFF **2000** | — | FF **RF 1926**; FRED **TB3MS 1934** | refreshable |
| **Gold** | **gold_gcf 2000-08-30**; GLD 2005 | price (≈TR) | **NONE on disk; FRED LBMA IDs 404** → LBMA web 1968+ | on-disk FROZEN; deep = **must source** |
| Trend ref | AQR TSMOM monthly **1985** | excess | — | refreshable (validation target only) |
| Overlay ctx | CBOE BXMD/PPUT **1986**, PUT 1991, BXM 2002 | TR idx | — | refreshable (CBOE CDN) |

Full per-file spans (39 tr_reconciled ETFs @ 2005/2007, Shiller fields, FF columns,
CBOE) are in the T-306 recon appendix; the table above is the load-bearing subset.

## 2. Per-leg proxy chains + splice rules + TR-honesty
Each chain is **oldest→newest**, spliced at overlaps with a **T-256-style basis check**
(reconcile returns on the overlap; require median |Δ| below a pre-set bound before the
splice is accepted — never a blind concat).

**EQUITY (broad total-market TR):**
`FF Mkt-RF+RF (daily, 1926)` → `SPY adj-close TR (1993)` → [modern: tr_reconciled SPY 2005].
- TR-honesty: FF `Mkt-RF+RF` **is** a daily total return (value-weight CRSP incl.
  dividends); SPY adj-close is TR. Both honest.
- **Basis caveat (must be measured, not assumed):** FF market = CRSP total-market;
  SPY = S&P 500. They are not identical (size/breadth tilt). The 1993–2026 overlap
  basis check quantifies the tracking gap; if material, the deep segment is labeled
  "broad-equity, not S&P-500" (the sleeve is a broad-equity leg by intent, so this is
  acceptable if disclosed). Optionally reconstruct S&P-500 TR from Shiller
  `price + dividend` (monthly) for a like-for-like deep index — but monthly (see §freq).

**BOND (10y-constant-maturity total return):**
`DGS10 → bond-TR synthetic (daily, 1962)` → `AGG TR (2005)`.
- Method: identical to `bond_synth_dgs10_t255.csv` (duration-return + coupon accrual
  from the 10y yield), just started at 1962 instead of 2000. **Reuse the existing
  builder**; do not invent a new method.
- Basis check: synthetic-10y vs AGG-TR on 2005–2026 (AGG is agg not pure-10y, so a
  known small duration/credit basis — quantify, disclose; the synthetic is the
  index-level bond leg by construction).

**GOLD (spot/fix total return ≈ price, no yield):**
`LBMA daily gold fix (1968, TO SOURCE)` → `gold_gcf GC-continuous (2000)` → [GLD 2005].
- Basis check: LBMA-fix vs gold_gcf on the 2000–~2022 overlap (spot vs front-future =
  a small roll/basis; quantify). Gold has no dividend → price return ≈ TR (ex the
  futures roll already handled by using spot).
- **This chain is BLOCKED until the LBMA fetch lands.** Everything downstream of it
  (the full 3-asset deep run) waits on that one file.

**CASH (short rate):** `FF RF (1926)` / `FRED TB3MS (1934)` → `DGS3MO (1981)` → the
flat-leg / cash return, per the T-255 convention (flat leg earns the short rate).

## 3. PIT / survivorship — the clean part
The sleeve is **index-level by construction** (S&P/broad-market, 10y-CMT, gold-fix are
*benchmark levels*, not stock baskets). None of the deep legs carry survivorship bias —
unlike the Stooq **single-stock** bundle, which the recon confirmed IS survivorship-biased
(183/202 misses are delisted SPX members: LEH, BSC, EK…). **That bundle is NOT used for
the sleeve substrate**, so its bias does not propagate here. The one PIT nuance: FF/Shiller
are academic index reconstructions (Shiller `dividend`/`earnings` go NaN in recent rows →
needs the modern splice anyway); index-level, no look-ahead in the return series.

## 4. Deliverable design — `data/research/substrate_multidecade/`
Versioned dir, one file per leg + provenance + a validation report:
- `equity_tr_daily.csv`, `bond_tr_daily.csv`, `gold_tr_daily.csv` (D-B only), `cash_daily.csv`
  — each a single `date,<leg>_tr` series on ONE benchmark trading calendar.
- `provenance.json` — per segment: `{source, url, span, tr_method, splice_date,
  basis_check:{overlap, median_abs_pct, max_pct, pass}}`. Every splice self-documents.
- **`core/calendar_guard` applied** — one benchmark calendar, zero holes asserted before
  emit (the T-294 48-day calendar-hole lesson: fail-closed, never silent-fill).
- `validation_report.md` — the T-256 basis battery: for each splice, the overlap
  reconciliation stats + PASS/FAIL against a pre-registered bound (propose ≤0.15%
  median |Δ| for TR-adjusted overlaps, wider for spot-vs-future gold; director sets the
  bound at freeze).
- **Frequency handling (freeze decision needed):** the daily 3-asset sleeve uses the
  `[42,105,210]`-DAY speeds. FF-daily equity (1926), DGS10-daily bond (1962), LBMA-daily
  gold (1968) are ALL daily → **the sleeve runs daily from ~1968 with no monthly variant
  needed.** The Shiller-monthly (1871) path is a SEPARATE optional equity-only artifact
  and would need month-scaled speeds — recommend deferring it (the 3-asset sleeve can't
  use pre-1968 anyway; gold floors it).

## 5. Honest cost + the `[NN-SUBSTRATE-REVERIFY]` blast radius
**Build effort:**
- D-A (2-asset, 1962–2026): **~0.5–1 day** — 1 FRED DGS10 refetch + FF parse + 1 bond-TR
  build (reuse T-255 code) + equity splice + basis battery + calendar_guard. No new data.
- D-B (3-asset, ~1968): D-A **+ the LBMA gold sourcing** (fetch + parse + 1 splice +
  basis check). Cost dominated by whether LBMA's free endpoint is scriptable (unknown
  until tried; WGC fallback). Estimate **+0.5–1 day** once the source is confirmed.

**N-implications — extending the substrate RE-OPENS, per `[NN-SUBSTRATE-REVERIFY]`,
every verdict measured on the 2000–2026 substrate.** Each demotes to "DEFENSIBLE (prior
substrate); re-verify required" until re-run on the deep substrate. Named list (each
re-run is +1 N_trial, pre-register before running):
- **T-255** fair sleeve (the beat-robo / tie-60_40 verdict) — the headline; re-run first.
- **T-260** multi-speed ensemble `[42,105,210]` selection (100–350 bps/yr was spec-selection
  — a deep substrate is the honest test of whether the speeds generalize).
- **T-282 / T-284** gated 2× leverage; **T-298** asymmetric damping (the offense arc — all
  measured on 2000–2026; a 58yr window with ~8–10 crises is the real test of the tail).
- **T-272** BTC leg (BTC has no deep history → stays exploratory regardless; note it).
- **T-296** return-stack; **T-299** contribution rule (re-run on the deep DCA path).
This is a FEATURE, not a cost: it is exactly the re-anchoring the director wants (8–10
independent crises vs 4). But it is real N-consumption and must be pre-registered per
verdict, not run as a batch.

**Two risks to flag at freeze:** (a) the LBMA gold source may not be cleanly scriptable
(the whole 3-asset depth hinges on one external fetch — D-A de-risks by not depending on
it); (b) the FF-market-vs-S&P-500 basis (broad-market vs S&P) — measured, not assumed;
disclose the deep equity leg as "broad-equity" if the basis is material.

## Recommendation
**Build D-A now** (2-asset equity+bond, 1962–2026) — it is free, immediate, decisively
relieves the MBL ceiling (64yr vs 24.1yr required), and is the substrate the T-305
tripwire-#1 rule meta-validation runs on. **Pursue LBMA gold sourcing in parallel as the
single gate to D-B** (the full 3-asset deep substrate to ~1968). Re-verifications
(T-255 first) are pre-registered per verdict as the deep substrate lands, not batched.

**T-306 scope ready** → awaiting director go on: (1) build D-A now / D-B on gold; (2) the
basis-check PASS bound; (3) the frequency ruling (daily-from-1968, defer Shiller-monthly);
(4) the re-verification order (propose T-255 → T-260 → T-298).

## DIRECTOR GO — 2026-07-10 (all four decisions ruled; BINDING)
1. **Build D-A NOW** (2-asset equity+bond, 1962-2026); pursue the LBMA gold source in parallel as the
   single gate to D-B (~1968 3-asset). D-A does not wait on gold.
2. **Basis-check PASS bound:** ≤0.15% median |Δ| on TR-adjusted overlaps; gold (spot-vs-futures class)
   ≤0.50% median |Δ|, disclosed per segment. A splice failing its bound ships as DISCLOSED-FAIL or not at
   all — never silently.
3. **Frequency:** daily throughout (the [42,105,210]-day speeds run natively from 1962/1968). The
   Shiller-monthly 1871 equity artifact is DEFERRED — out of scope until someone pre-registers a use.
4. **Re-verification order:** T-255 → T-260 → T-298, each individually pre-registered (+1 N_trial each),
   NEVER batched; every 2000-2026 verdict demotes to "DEFENSIBLE (prior substrate); re-verify required" the
   day D-A ships, per [NN-SUBSTRATE-REVERIFY]. T-272 stays exploratory regardless (BTC has no deep history).
Build authorized. calendar_guard mandatory before emit; provenance.json per splice as scoped.
