---
task_id: T-2026-07-30-336-C5
title: C5 — the ICE BofA OAS deep-history RECOVERY + the BAA−AAA proxy receipt (shelf entry REOPENS)
date: 2026-07-30
worker: Agent B
branch: feature/t336-honestn-oas
status: DONE. Recovery: 7,723 obs preserved (N+=0). Proxy check: GATE 1 FAILED → conditional_shelf.md:370 REOPENS. A receipt either way.
---

# C5 — recovery first, then the receipt

## 1. The deadline was real, and the window is now closed behind us
| source | what it serves TODAY (verified 2026-07-30) |
|---|---|
| FRED `BAMLH0A0HYM2` (HY OAS) | **786 obs, 2023-07-31 →** — a ~3yr ROLLING window |
| FRED `BAMLC0A4CBBB` (BBB OAS) | 786 obs, 2023-07-31 → |
| FRED `BAA10Y` / `AAA10Y` (the proxy) | full: 1986 / 1983 → (unaffected) |

**The truncation is at SOURCE, not a default-range artifact:** `&cosd=1996-12-31` still
returns only 786 obs. ALFRED `vintage_date` 404s for these IDs — consistent with an ICE
BofA **licensing** change (vintages purged too), which is why no FRED-side route recovers it.

## 2. RECOVERED — 7,723 obs, 1996-12-31 → 2026-07-28
Route: a **pre-truncation Wayback capture of the CSV endpoint** (`20251104204105`,
gzip-encoded) → 1996-12-31 … 2025-11-03 (7,530 obs), spliced with the live rolling tail.
**Independently corroborated:** a 2017 Wayback capture of `/data/BAMLH0A0HYM2.txt` returns
5,250 obs from the *same* 1996-12-31 start with the *same* first value (3.13) — two
independent snapshots agreeing on the deep tail.

Now archived by us, daily and idempotently: `pull_credit_spread_oas()` in the T-136
archiver → `data/macro_data/alt/credit_spread_oas.parquet`, registered in `main()` and
therefore in the shared orchestrator (both the launchd path and the cloud pulse). **The
deep rows are written once and preserved; only the live tail accrues.** Per T-335 the feed
must also be gated — see §5.

**Honest gap:** `BAMLC0A4CBBB` (BBB OAS) deep history was **NOT** recovered — its only
Wayback captures (2026-04, 2026-07) are already post-truncation. It holds the live 2023+
tail only. Not claimed as recovered.

## 3. The receipt — the pre-registered proxy-robustness gate
Tests the shelf claim at `conditional_shelf.md:370`: *"HY OAS deep history unobtainable →
BAA−AAA proxy; conclusion robust to the proxy."* Overlap: 1996-12-31 … 2026-07-28 (7,384 obs).

| gate | bar | measured | verdict |
|---|---|---|---|
| **1. corr of 21d changes** | ≥ 0.90 | **0.6358** | **FAIL** |
| 2. crisis-window sign divergence | none | none in 6/6 | PASS |

*(context: level corr 0.8575; 1-day-change corr 0.1528)*

| crisis window | HY OAS Δ | proxy Δ | sign |
|---|---|---|---|
| 1998 LTCM | +2.97 | +0.22 | same |
| 2000-02 dotcom | +4.11 | +0.70 | same |
| **2007-09 GFC** | **+14.62** | **+2.13** | same |
| 2011 EU debt | +1.73 | +0.56 | same |
| 2020 COVID | +4.80 | +1.06 | same |
| 2022 bear | +1.58 | +0.54 | same |

## 4. ⇒ VERDICT: **the shelf entry at `conditional_shelf.md:370` REOPENS**
The gate required corr ≥0.90 **AND** no sign divergence. Correlation of 21-day changes is
**0.636** — decisively below the bar. So the recorded "conclusion robust to the proxy"
does not survive its own pre-registered test.

**What specifically is now uncertain (not more, not less):** the proxy tracks crisis
**DIRECTION** reliably — 6/6 same-sign, which is why a purely directional reading survived
casual inspection — but it does **not** track **MAGNITUDE or short-horizon variation**. The
GFC is the clean illustration: HY OAS widened **+14.62 pp** while BAA−AAA widened **+2.13
pp**, a ~7× magnitude gap. **Any conclusion depending on the SIZE of credit stress
(thresholds, z-scores, sizing) is unsupported on the proxy; a sign-only conclusion is
weaker but not refuted here.**

**And the caveat's premise is now simply false:** "HY OAS deep history unobtainable" was
true when written and is **not true now** — we hold 7,723 obs back to 1996. So the reopened
question is **directly answerable on the real series**, no proxy required. Reopening is
therefore an upgrade in what can be tested, not a loss.

**N accounting:** recovery **N+=0** (preservation). The proxy check is a **verification, not
a trial** — no hypothesis was fitted, the gate was pre-registered by the dispatch.

## 5. Feed-gate follow-through (T-335 rule: no archiver outside the gate)
`credit_spread_oas` is a new live feed, so it must join `_FEED_HEALTH`. Added with a
**7-day** budget (the live FRED tail is daily). Its deep rows are historical by design, so
the gate ages the **newest** observation — which the live tail keeps current.
