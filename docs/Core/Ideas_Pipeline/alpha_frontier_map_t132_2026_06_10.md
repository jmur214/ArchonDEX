# Alpha-Frontier Map — every untested category, scored and ranked

**Task:** T-2026-06-10-132 Part A · **Date:** 2026-06-10 · **Author:** Agent D (alpha lane)
**Status:** living document — owned by the Ideas Pipeline; update scores as categories get tested.

## Why this doc exists

T-117→T-122→T-123→T-129 closed a space that was narrower than the original
"substrate-empty" framing claimed. What is actually closed:

> **{our 13 artisanal edges + equity-proxy VRP + BAB-class low-beta}**
> on **{daily bars × S&P-survivor large/mid-caps × the cross-sectional harness}**.

Two structural reasons the closed space is small:

1. **FF5-span circularity.** Our t>2 gate demands alpha *orthogonal to FF5+Mom*.
   Characteristic factors (QMJ≈RMW, value≈HML, investment≈CMA, plain
   momentum≈Mom) cannot clear it **by construction** — they ARE the factors.
   BAB was the designated exception and failed (T-129: FF5 spans it via CMA/RMW
   on our universe). That closes the *characteristic-factor door*, not alpha.
2. **We have run exactly 2 literature implementations.** The research docs list
   dozens. Alpha that CAN clear the gate lives in: different **DATA**
   (events/filings/positioning), different **RESOLUTION** (intraday-derived),
   different **FUNCTIONAL FORM** (non-linear/conditional), different
   **INSTRUMENTS**, different **UNIVERSES**.

This map enumerates that frontier. **Bottom line up front: 16 categories are
materially untested; 4 are testable for free with data already on disk.**

## Scoring rubric

Each category gets six scores:

| dimension | meaning |
|---|---|
| **Data** | free + on disk (A) / free, needs fetch or build (B) / paid or hard (C) |
| **Lookahead risk** | how easy it is to keep point-in-time clean (L=low/M/H) |
| **Harness fit** | XS = expressible in the cross-sectional edge bus today; OVL = timing-shaped, needs the gross-exposure overlay path that does NOT exist (T-122); SLV = needs a capital-partition sleeve (mechanism exists post-T-112/T-115/T-120 but each new sleeve is director-gated) |
| **FF5-span risk** | can it even clear t>2 in principle? (L = structurally outside FF5+Mom / M / H = spanned by construction) |
| **Cost** | engineer-days-equivalent to first gauntlet-ready test (S <2d, M 2-7d, L >7d) |
| **N-trials** | est. backtest configs the first honest test consumes |

**Rank score = gate-viability × literature-evidence ÷ cost** (qualitative;
the ordering, not the arithmetic, is the deliverable).

---

## TIER 1 — testable now, free, data on disk

### 1. Overnight/intraday return composition ("tug of war", Lou-Polk-Skouras 2019) — *category the brief missed; added*
Rank stocks by the share of their return that accrues overnight vs intraday
(persistent, investor-clientele-driven; not an FF factor). **Computable TODAY
from existing daily OHLC — Open and Close are both on disk** for the full deep
panel. Cross-sectional, lookahead-trivial.
**Data A · Lookahead L · XS · FF5-span L · Cost S · N-trials ~2.**
*Honest caveat:* open prints in the Stooq-extended deep history may be less
reliable than closes (auction noise); validate opens vs Alpaca overlap window
(2020+) first.

### 2. VIX-term-structure / vol-of-vol as **per-ticker conditioner** (not a timing signal)
`vix_term_structure_slope`, `vvix_or_proxy`, `vol_regime_5_60` are **already
built in the Foundry** (29 features exist). T-122's lesson: as uniform timing
tilts they wash out. The XS-compatible use: **condition existing per-ticker
signals on vol-state** (e.g., mean-reversion edges only when term structure in
contango) — a conditional-form change, not a new factor.
**Data A (VIXCLS 2000-2026; CBOE term structure 2020+ only — flag) · Lookahead L
· XS (as conditioner) · FF5-span L-M · Cost S · N-trials ~2-4.**
*Cannot do:* standalone market-timing through the edge bus (washes out, T-122).

### 3. Non-linear / conditional combination (metalearner + meta-labeling)
The MetaLearner is **built, never trained** (full fit/save/load in
`engines/engine_a_alpha/metalearner.py`; no trained model in `data/brain/`).
T-117 closed only LINEAR recombination. **Part B of this task ran the
go/no-go diagnostic** (MI + Friedman-Popescu H vs block-bootstrap nulls on the
1.85M-row signal panel) — see `docs/Audit/alpha_frontier_t132_2026_06_10.md`
for the verdict; this row is GATED on it. Meta-labeling (López de Prado;
train a filter on whether an edge's trades win, not a new signal) is the
sibling and survives even if pure combination fails.
**Data A (panel exists) · Lookahead M (label construction discipline) · XS ·
FF5-span L (form, not factor) · Cost M · N-trials ~3-5.**

### 4. Residual momentum (Blitz-Huij-Martens 2011)
Momentum on FF-residual returns rather than raw returns — lower vol, less
crash-prone, claims alpha beyond UMD. Computable from prices + cached FF
factors today. *Honest span-flag:* Mom is in our gate's RHS, so only the
residual-construction premium can clear — literature says it's there, but this
is the same class of claim BAB just failed on; treat as a cheap falsification.
**Data A · Lookahead L · XS · FF5-span M-H · Cost S · N-trials ~2.**

---

## TIER 2 — free data, needs a fetch/build step (the event/data class — strongest gate-viability)

### 5. 8-K filing-type event reactions
Different DATA = structurally outside FF5 span. EDGAR is free; the **T-041b
fetcher pattern (rate-limited, cached parquet) already exists**
(`_helpers/spinoff_detector.py` → `data/spinoff_events_edgar.parquet`).
Item-type taxonomy (1.01 M&A, 2.02 results, 5.02 departures, 7.01/8.01…) with
acceptance-datetime timestamps = lookahead-clean event panel.
**Data B · Lookahead L (acceptance ts) · XS (per-ticker events) · FF5-span L ·
Cost M · N-trials ~2-3.**

### 6. Form-4 insider-cluster depth
`insider_cluster_v1` exists but its feed is **EMPTY — `data/insider/` is 0 B**
(the edge is all-zero in every signal log; it has never actually traded on
data). So this is a *repoint/feed* job, not a new edge: build the Form-4
pipeline (EDGAR free, same fetcher pattern), the edge logic already exists.
Cluster-purchase depth (multiple distinct insiders buying) is the
literature-strong variant.
**Data B · Lookahead L · XS · FF5-span L · Cost M · N-trials ~2.**

### 7. Intraday-derived FEATURES for daily signals (the user's idea)
Opening-range stats, intraday vol shape, volume profile, first-half-hour
return, close-auction imbalance proxies — **precomputed ONCE from Alpaca
minute bars and joined to the daily panel**, side-stepping the 78-390×
intraday-backtest cost (standing memory). Feeds both edges and the Foundry.
**Data B (free via Alpaca REST; *flag: free tier = IEX feed, thin pre-2017 and
thin-volume — validate coverage first*) · Lookahead L (features from completed
sessions) · XS · FF5-span L · Cost M (bulk fetch + feature build) · N-trials ~2-4.**
*Separate, bigger line:* GHLZ first-half-hour→last-half-hour SPY momentum — the
one research-endorsed intraday *strategy*; needs intraday fills → gated on an
intraday execution path (L cost), not this item.

### 8. 13F crowding / connected-stocks (Antón-Polk 2014)
Quarterly holdings, free bulk from EDGAR. Crowding/connectedness predicts
comovement and unwind risk — different DATA, strong literature.
**Data B (bulk parse is the cost) · Lookahead M (45-day filing lag must be
respected) · XS · FF5-span L · Cost L · N-trials ~2-3.**

### 9. Cross-asset carry + rotation (we only ever tested TREND)
Stocks-vs-bonds on yield-curve state; defensive-vs-cyclical on credit spreads
(`hyg_lqd_spread`, `anfci_z_60d` foundry features exist); HYG-IEF carry;
term-structure tilts. Research Q3: documented net 0.6-0.9.
**Honest harness problem:** rotation is timing-shaped between a handful of
ETFs → washes out in the stock cross-section (T-122); the viable path is a
**capital-partition sleeve** (mechanism exists: T-112 KMLM, T-115/T-120 spot
sleeve — but T-120 found capital-coupling surprises; each sleeve is
director-gated). ETF history on disk only 2020+ (HYG absent) → needs Stooq
extension fetch (cheap, fetcher exists).
**Data B · Lookahead L · SLV (not XS) · FF5-span L (cross-asset) · Cost M-L ·
N-trials ~3-6.**

### 10. Earnings-guidance direction from press-release text (8-K Ex-99.1)
Timestamped, lookahead-clean. Non-LLM first pass (structured guidance
language: raise/lower/affirm keyword grammar) keeps it inside the
plateau-before-AI directive; LLM upgrade later.
**Data B · Lookahead L · XS · FF5-span L · Cost M-L · N-trials ~2.**

### 11. Index add/delete events
Free-ish (S&P press releases / curated lists). *Honest decay note:* the
add/delete premium has shrunk substantially post-2010 in the literature —
mid-rank at best.
**Data B · Lookahead M · XS · FF5-span L · Cost M · N-trials ~2.**

### 12. DHS FIN (long-horizon financing: net issuance/repurchase composite)
The one characteristic-class factor with a serious claim to live PARTIALLY
outside FF5 (Daniel-Hirshleifer-Sun 2020 build it to complement, not
duplicate, FF). SimFin (on disk) covers shares outstanding/buybacks **2020-2025
only** → fails MBL alone; EDGAR 10-K/10-Q parse to extend = the real cost.
**Data B/C · Lookahead M (PIT fundamentals discipline) · XS · FF5-span M ·
Cost L · N-trials ~2-3.**

---

## TIER 3 — fork-gated (real money/architecture decisions; listed so the space is honest)

| # | category | why gated | cost sketch |
|---|---|---|---|
| 13 | **Options-class VRP** (sell index puts / short variance when IV≫RV — the REAL premium T-122's equity proxy couldn't reach) | options data + a non-XS gross-exposure sleeve + new risk surface (Engine B, propose-first) | data $0-$$ (CBOE/ORATS tiers), build L |
| 14 | **Futures carry/trend multi-asset** (the managed-futures premium beyond the KMLM ETF wrapper T-112 already added) | new instruments, new broker capabilities | data B-C, build L |
| 15 | **Micro-cap / international universes** (where BAB & friends actually live per the literature — T-129's loadings argument) | paid data (Norgate ~$80/mo discussed), capacity/liquidity limits at retail size | data C, build M |
| 16 | **LLM/news sentiment lane** (`data/news/` is 0 B; news_sentiment edge has no feed) | plateau-before-AI directive (standing memory) — explicitly deferred until non-LLM capability plateaus | data B-C, build L |

---

## Closed doors (do not re-test without new structure)

- **Characteristic factors on this universe** (value/quality/accruals/low-vol/
  plain & 12-1/6-1 momentum, BAB-class): T-117 + T-123 + T-129. FF5-span by
  construction or empirically spanned.
- **Uniform timing/overlay signals through the cross-sectional edge bus**
  (macro_* tilts, VRP-style vol-managed overlays): structurally wash out
  (T-122, Gate-1 ≡ 0). Needs an overlay path that doesn't exist.
- **LINEAR recombination of existing edges** (T-117). Non-linear = Part B's
  verdict, see audit.
- **Aggregator-topology iteration** on the existing signal set (HRP slices,
  weighted-sum variants, Bayesian opt — Phase-0 + research: signal diversity,
  not aggregation, is binding).

## The ranked shortlist (gate-viability × evidence ÷ cost)

1. **Overnight/intraday composition** — free TODAY, XS-native, span-L, lit-strong. *Next dispatch.*
2. **8-K event reactions** — strongest *class* (different data), infra half-built.
3. **Form-4 insider feed repoint** — edge exists, feed is 0 B; cheapest event win.
4. **Intraday-derived daily features** — the user's idea; one-time precompute, feeds everything; validate IEX coverage first.
5. **Metalearner/meta-labeling** — conditional on Part B's GO/NO-GO (see audit).
6. 13F crowding → 7. Vol-state conditioners → 8. Residual momentum (cheap falsification) → 9. Cross-asset carry sleeve (needs sleeve gate) → 10. guidance-text → 11. DHS FIN → 12. index events → fork-gated 13-16.

## The honest bottom line

- **Untested categories: 16** (4 free-now, 8 free-with-build, 4 fork-gated).
- What we had actually tested before this map: **2** literature implementations
  + 13 artisanal edges, all in ONE cell of the (data × resolution × form ×
  instrument × universe) grid.
- The narrow closure (T-117→129) was real and worth having — it killed the
  cheapest-looking lane decisively. But "the substrate" was never tested as a
  whole, and the strongest gate-viability class (event/data edges) has zero
  tests to date.
