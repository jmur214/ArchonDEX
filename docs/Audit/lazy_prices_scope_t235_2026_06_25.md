# T-235 — SCOPE: the EDGAR "Lazy Prices" hypothesis (pre-registered design, NOT a build)

**Date:** 2026-06-25 · **Agent:** A (edge-analyst lens) · **Branch:** `feature/lazy-prices-scope-t235` (docs only)
**Governing rules:** `[NN-AI-GATE]` (gated exploration, no live integration, same falsification bar, LOW prior) · `[NN-MBL]` (pre-register N_trials + window) · `[NN-SHARPE-CI]` (ci_low, block-bootstrap) · metric reframe → Sortino/tail ([[feedback_measure_sortino_tail_not_sharpe_2026_06_25]]).
**This is SCOPE + a proposed pre-registered experiment for the user's go. No ingestion built, nothing run.**

## 0. The hypothesis (one paragraph)

Cohen, Malloy & Nguyen ("Lazy Prices", *J. Finance* 2020): when a firm **changes**
its 10-K/10-Q language YoY — especially Risk Factors (Item 1A) and MD&A (Item 7)
— it predicts **negative** forward returns; firms that leave language unchanged
("non-changers") modestly outperform. The retail-tradeable residual is a
**long-only tilt toward high-similarity non-changers** (the short "changers" leg
is borrow-expensive and small-cap-heavy → out of scope for a $5–15K cash Roth).
This is the one fresh **return-signal frontier the price vocabulary can't see**
(text), so it is exactly the kind of new-data modality `[NN-AI-GATE]` points at —
held to the same bar, LOW prior.

## 1. Data feasibility — GOOD (the hard plumbing already exists)

**Search-before-scope ([[feedback_search_existing_infra_before_scoping_2026_05_22]]):**
`scripts/fetch_8k_edgar_t137.py` ALREADY implements the entire EDGAR access layer
we need, for 8-Ks — and it generalizes to 10-K/10-Q with minimal change:

| Capability needed | Already in `fetch_8k_edgar_t137.py` | New work |
|---|---|---|
| ticker → CIK map | ✅ `company_tickers.json` | — |
| per-company filing history | ✅ `data.sec.gov/submissions/CIK##########.json` (`filings.recent` + paged `filings.files`) | — |
| **PIT acceptance timestamp** | ✅ extracts `acceptanceDateTime` per filing | — |
| SEC fair-access etiquette | ✅ UA-with-contact, ~7.7 req/s (`RATE_SLEEP=0.13`) | — |
| offline raw cache, OUTSIDE pinned substrate | ✅ `data/edgar/…/raw/` (not in `processed/raw/governor` manifest → no canon regen) | — |
| amendment exclusion | ✅ excludes `8-K/A` ("not the market's first sight") | mirror for `10-K/A`, `10-Q/A` |
| **filing DOCUMENT text** (Item 1A / Item 7) | ❌ 8-K builder pulls STRUCTURED fields only | **the genuinely-new build** |
| section parse + YoY similarity | ❌ | **new** |

**No new dependency.** `requests`, `beautifulsoup4`, `lxml`, and **`scikit-learn`**
(TF-IDF + cosine) are all already in `requirements.lock.txt`. `finagg` is NOT
needed (it does XBRL/structured EDGAR; text-similarity needs the raw filing
documents, which the submissions→Archives path already reaches). Loughran-McDonald
stop/sentiment word lists (Notre Dame, free, public) are a small static asset to
vendor under `data/edgar/lm/`. So no `[NN-AUTONOMOUS]` "new dependency" gate is tripped.

**The new ingest, concretely:** from each 10-K/10-Q row's accession, fetch the
primary document from `https://www.sec.gov/Archives/edgar/data/{cik}/{accNo}/…`,
strip HTML (bs4/lxml), regex-segment Item 1A / Item 7, cache raw. Same rate-limit
+ cache discipline as the 8-K builder.

**Coverage / history limits (be honest):**
- Our universe is **PIT-691** (survivorship-free, large/mid-cap US) → essentially all file 10-Ks; coverage is good.
- **Item 1A (Risk Factors) was only MANDATED in 2005** (SEC FRR-75). The headline Risk-Factors-diff leg therefore has **~20 years** of usable history (2005→2025). MD&A (Item 7) reaches further back (~1996) but is the weaker leg in CMN.
- EDGAR full-text (EFTS) is 2001+; the submissions/Archives document path reaches mid-1990s, but pre-2001 parsing is messier (plain-text vs HTML). **Pre-register the window as 2005–2025** for the Risk-Factors signal.

## 2. Signal design (ONE pre-registered design — no sweep)

- **Document similarity, YoY, per filing:** for each 10-K (annual) compare its
  Item 1A + Item 7 text to the **same firm's prior-year same-form** filing.
  Primary metric: **cosine similarity of TF-IDF vectors** (LM stop-word list,
  L2-normalized). Secondary (reported, not gated): Jaccard on the word-set and a
  raw section-length-delta — for mechanism/robustness only, NOT extra trials.
- **Cross-sectional rank → long-only tilt:** each rebalance, rank the universe by
  similarity; **tilt long-only toward the top tercile (non-changers)**, weight =
  cap-aware within the existing portfolio engine; no shorts.
- **Rebalance cadence:** **annual** at each name's 10-K acceptance (signal is
  annual; a 10-Q quarterly variant is a SEPARATE pre-registered trial, NOT bundled).
- **Composition, not standalone (per `[NN-AI-GATE]`):** the deliverable test is
  whether adding this tilt makes the **WHOLE system beat the robo by MORE** — so
  it is measured both standalone (diagnostic) AND as an overlay on the T-215 base,
  net-of-cost / after-tax Roth.

## 3. The PIT trap (explicit — this is where text signals die)

1. **Key every signal to `acceptanceDateTime`** (already extracted), NEVER the
   period-end / cover date / `filingDate`. Decision usable only on the **first
   trading day AFTER acceptance** (filings are often accepted post-close → same-day
   use is look-ahead).
2. **YoY baseline only from filings accepted as-of the decision date** — compare to
   the prior filing that was *already public* at t, never a later vintage.
3. **Exclude 10-K/A, 10-Q/A (amendments/restatements)** — a restated doc is not the
   market's first sight (the 8-K builder already does this for 8-K/A; mirror it).
   Never use a restated 10-K's text as the "original."
4. **PIT universe membership** — tilt only into names in the survivorship-free
   PIT-691 set as-of t (no delisted/not-yet-public leakage). The PIT universe
   already enforces this.

## 4. Falsification gates (pre-registered, BEFORE any run)

| Gate | Threshold | Rule |
|---|---|---|
| **CI-aware Sharpe** | `ci_low(Sharpe) ≥ 0.4` net-of-retail-cost; block-bootstrap (block≈7 / Politis-White auto, n_iter=1000, seed=42) | `[NN-SHARPE-CI]` — point-estimate is not evidence |
| **MBL / honest-N** | pre-register **N_trials += 1**; the window must clear `T_years ≥ 2·ln(N_eff)/SR²` | `[NN-MBL]` — at **N_eff ~260+** (run_registry 125 rows + cloud cells) a 20yr window needs a **high SR** the decayed long-only residual is unlikely to reach. State this up front. |
| **Beat-robo** | `evaluate_deploy_readiness(equity, account="roth", w_dbmf=0.0)` → must beat 60/40 AND schwab_like on `ci_low(Sharpe)` OR ≥20% MDD improvement | the FIXED goal |
| **Sortino / tail reframe** | report Sortino, Calmar, MaxDD, tail-capture; classify: adds RETURN, TAIL, or both? | the new metric directive; per `[NN-AI-GATE]` judged on the WHOLE system |
| **Beta-or-edge** | `FactorRiskModel().decompose(returns).is_it_beta_or_edge()` → must be "edge-candidate", not "beta" | the non-changers tilt is a **likely quality/low-vol beta** — this gate is the prime suspect for failure |
| **Tradeability / micro-cap** | if lift survives ONLY in untradeable micro-caps → **FAIL** | our PIT-691 is large/mid; if the effect needs small-caps it's outside our investable set |

**Pre-registration artifact (to commit BEFORE running, if greenlit):** hypothesis
+ the single design above + threshold table + `N_trials_consumed` + the exact
window — one immutable doc, no post-hoc metric swaps.

## 5. Honest prior — LOW (~10–15%)

- Published 2020 → **post-publication decay** (~50% is the McLean-Pontiff base rate;
  CMN's own later work shows attenuation).
- The **long-only non-changers residual is a fraction** of the long-short headline;
  most of the alpha was in the short "changers" leg we're dropping.
- CMN's effect concentrates in **smaller, less-covered** firms; our PIT-691 is
  **large/mid-cap** (the most-arbitraged, weakest-effect cohort).
- At **N_eff ~260+** the MBL bar is steep; a decayed, liquid-universe, long-only
  text residual clearing `ci_low(Sharpe) ≥ 0.4` AND the robo bar is unlikely.
- **Most probable outcome = H0** — it joins the price vocabulary in the exhausted
  bin. A clean H0 here is still **valuable** (it bounds the "new data will save us"
  hope with evidence, cheaply).

## 6. Build-effort estimate (IF greenlit — quant-dev / ml-architect)

- **Phase A — 10-K/10-Q doc ingest** (~1–2 d, quant-dev): extend `fetch_8k_edgar`
  to pull 10-K/10-Q rows + fetch & cache primary documents from Archives. Reuses
  CIK map, rate-limit, cache, amendment-exclusion.
- **Phase B — section parse + similarity** (~2–3 d, ml-architect): Item 1A / Item 7
  extraction (bs4/lxml + regex), TF-IDF cosine (sklearn) + LM stop-words, YoY
  pairing keyed to `acceptanceDateTime`. Output a PIT similarity panel (parquet).
- **Phase C — signal panel → backtest** (~2–3 d): cross-sectional ranks → long-only
  tilt through the existing portfolio engine + backtester + scorecard + bootstrap;
  cloud cell for the multi-year run.
- **Total ≈ 1–1.5 weeks** + one cloud campaign. The **ingest is cheap** (plumbing
  exists, no new deps); the cost is the parse-and-validate, not the access layer.

## 7. Go / No-Go recommendation

**QUALIFIED GO — propose the pilot, eyes open.** Rationale:

- **For:** it is the *correct* `[NN-AI-GATE]` move (a new data modality the price
  book can't see; the apparatus is now trustworthy enough to CATCH an overfit —
  T-181 census + T-199); the **ingest is cheap and reuses existing plumbing with
  zero new deps**; and a clean H0 is high-information (it tests the "new data will
  save us" thesis for the price of ~1 week of build, not a research program).
- **Against (honest):** the **prior is LOW (~10–15%)**, the most likely result is
  H0, and it consumes a scarce N_trial against an already-steep MBL bar. The
  beta-or-edge gate will probably catch the non-changers tilt as a **quality/low-vol
  beta** rather than a text edge.

**Recommended shape if the user greenlights:** run the **single pre-registered
design only** (cosine-TF-IDF, Item 1A+7, long-only top-tercile, annual, 2005–2025),
judged on the full gate table **including Sortino/tail and beta-or-edge**, as a
**falsification pilot** — explicitly NOT a production-build commitment. Decide
continuation strictly on the gates. Do **not** sweep similarity variants (each is
a new trial). If it fails the robo/DSR/edge bar — which is the modal outcome —
**archive it as a clean H0** and do not integrate (per `[NN-AI-GATE]`: no live
integration until the whole system beats the robo, which it currently does NOT,
T-215).

**My lean:** worth proposing because it's cheap and the *right* test, but I'd set
the user's expectation at "this most likely refutes — and that refutation is the
deliverable," not "this is our edge."

## 8. Status / N_trials

- SCOPE only. **0 N_trials consumed** (nothing run). The pilot, if greenlit,
  pre-registers as **N_trials += 1**.
- Nothing wired, no ingestion built, no dependency added. Branch is docs-only.
