---
task_id: T-2026-07-29-335
title: Earth-observation as a thesis-verification layer — scoping probe
date: 2026-07-29
author: Agent D
type: SCOPING PROBE (research only; nothing built, no new deps; N_trials = 0)
status: DONE — recommendation: **PARK the EO substrate, ADOPT the sub-claim class it was proposed for, on a
        different (free, daily, earlier) substrate.** Propose-first gate NOT requested.
---

# T-335 — EO as a verification layer for the thesis contract

The director's frame — *EO is not a signal source for us; the candidate fit is a **verification layer** for
v2 sub-claims* — was the right frame. This probe tested it rather than assuming it, and the frame survives:
**verification of physical build-out IS the right sub-claim class.** What does not survive is **EO as its
substrate**. The findings below are, in order: a fatal latency finding for AlphaEarth, a fatal licensing/cost
finding for Earth Engine, and a decisive survival-test finding that a **free, daily, PIT-stamped
public-records substrate already delivers the same verification EARLIER** — because in this domain the
paper trail structurally *precedes* the concrete.

---

## Q1 — LATENCY: the honest freshness of each free tier

| tier | freshness | resolver-viable? |
|---|---|---|
| **AlphaEarth annual embeddings** (64-dim, 10m, 2017-2025) | **The 2025 annual layer was announced 2026-03-09** ⇒ ~2-3 months after year-end. But it is an **ANNUAL** layer, so at any moment the freshest picture is **7-19 months stale** (today, late Jul-2026: the 2025 layer, ~7 months old; by Dec-2026 it is ~12; the 2026 layer arrives ~Mar-2027). | **NO.** Cannot resolve a quarterly sub-claim. A 2-quarter claim filed today would resolve against a picture that predates the filing. |
| **Copernicus Sentinel-2** (10m optical) | **~hours after acquisition**; **5-day revisit** at the equator (better at mid-latitudes with S2A/S2B). | **YES** — this is the only free tier fast enough. |
| **USGS EarthExplorer / Landsat** (30m, 1970s+) | days; 16-day revisit; 30m is coarse for building-scale change | historical baseline only |
| **Umbra open SAR** | opportunistic open-data grants, not a guaranteed cadence over a chosen site; night/cloud-proof | **NO** for a *pre-registered site* — you cannot commit at filing time to imagery you can't guarantee will be collected |

**Q1 verdict:** the dispatch's hypothesis is **confirmed and sharpened**. AlphaEarth is a **historical-baseline
layer only** — annual granularity is a structural disqualification for quarterly resolution, independent of
its lag. If EO were used at all, the resolver substrate is **Sentinel-2 direct**.

## Q2 — LICENSING + COST: Earth Engine is the landmine, not the imagery

| source | licence | cost to us |
|---|---|---|
| **Copernicus Sentinel-2 (direct)** | Free, full and open; **explicitly permits commercial use**; attribution "Contains modified Copernicus Sentinel data [YEAR]" | **$0** |
| USGS Landsat | US public domain | $0 |
| **Google Earth Engine — NONCOMMERCIAL tier** | Free for academic/research/nonprofit. **Explicitly excludes operational/commercial use**; a private entity using it operationally violates ToS. | **not available to us** |
| **Google Earth Engine — COMMERCIAL** | required for our use | **$500/mo (Basic)** or **$2,000/mo (Professional)**; on-demand **$1.33/Online EECU-hr**, **$0.40/Batch EECU-hr** |
| AlphaEarth paid 5-day custom product | commercial | **not publicly priced** — quote-only. Flagged as un-pricable from open sources; I did not guess a number. |

**Q2 verdict — two findings, one of them decisive:**
1. **Our use is COMMERCIAL.** A private individual running EO to inform real investment decisions is
   operational use, not academic research. **The free GEE tier is not available to us** — and using it anyway
   would be a ToS violation, which is not a cost trade-off, it is off the table.
2. **GEE commercial is $500-2,000/mo against a desk that runs at ~$2-3/mo** (the whole LLM layer is under the
   $30/mo governor and actually spends single dollars). That is **2-3 orders of magnitude** off the desk's cost
   class. The dispatch's own bar — *"a verification layer must run at ~$0-class like the rest of the desk"* — is
   failed by Earth Engine by a wide margin.
3. **But the imagery itself is free.** Sentinel-2 direct from Copernicus is $0 **including commercial use**. So
   the cost objection is an *Earth Engine* objection, not an *EO* objection. If EO is ever pursued, it must go
   **direct to Copernicus and never through Earth Engine.** That is the single most useful operational fact in
   this probe.

## Q3 — THE RESOLVER DESIGN: one spec, end to end

Drafted in full because it is reusable **whatever the EO verdict** — the same skeleton is what a records-based
resolver needs (see Q5). Proposed resolver type for the v2 contract: **`eo_area_change`**.

```
{ "type": "eo_area_change",
  "aoi_geojson":     {...},          # polygon FROZEN AT FILING TIME (the pre-registration)
  "aoi_sha256":      "<hex>",        # hash of the canonicalized polygon — prevents post-hoc AOI shopping
  "metric":          "built_area_m2",# one of a CLOSED metric set
  "baseline_window": ["2026-06-01","2026-07-31"],   # pre-filing imagery -> the baseline
  "resolve_window":  ["2027-01-01","2027-02-28"],   # post-claim imagery -> the comparison
  "threshold":       {"op": "gt", "value": 0.15},   # +15% built area
  "source":          "sentinel2_l2a",
  "cloud_max_pct":   20,
  "min_scenes":      3,              # per window, else UNRESOLVED (never a guess)
  "method_version":  "eo_area_v1"    # the classifier is pinned; changing it is a new resolver type
}
```
**Resolution procedure (mechanical, no analyst-looks-at-a-picture):**
1. Fetch all S2-L2A scenes intersecting the AOI in each window with scene cloud ≤ `cloud_max_pct`.
2. If either window has `< min_scenes` usable scenes → **`UNRESOLVED` (fail-closed)**, never a judgement call.
3. Per window, compute a cloud/shadow-masked **median composite** (kills transient cloud + illumination noise).
4. Compute `built_area_m2` by a **pinned** rule under `method_version` (e.g. a fixed NDBI/NDVI threshold pair,
   or a fixed-weights classifier) — deterministic, same inputs → same output.
5. Outcome = `1` if `(resolve − baseline)/baseline` satisfies `threshold`, else `0`.
6. Record scene IDs + acquisition timestamps in the resolution record.

**PIT honesty (the load-bearing property):** every scene used carries an acquisition timestamp, and the
resolver **must reject any scene acquired after the resolve-window close** — so a resolution can never see
imagery from beyond its own horizon. The AOI hash prevents the subtler cheat: quietly redrawing the polygon
around whatever got built.

**Where this spec is honestly weak (stated, not hidden):**
- **`built_area_m2` is the whole ballgame and it is not trivial.** At 10m, a datacenter shell is tens of pixels;
  a threshold-based built-area classifier confuses fresh concrete, cleared earth, gravel laydown and parking.
  A pinned classifier makes it *reproducible*, not *accurate* — and a reproducible-but-biased metric resolves
  claims wrongly with perfect consistency.
- **Cloud cover is a correlated failure**, not random: a persistently cloudy region yields systematic
  `UNRESOLVED`, so the resolved subset is not a random subset of filed claims — a selection effect on the
  scoreboard, which is exactly the class of defect this program keeps catching.
- **Seasonality** (snow, vegetation flush, sun angle) contaminates a 2-quarter comparison; the honest fix is
  year-over-year same-season windows, which pushes the minimum horizon to ~12 months — colliding directly with
  v2's *quarterly*-cadence requirement.

## Q4 — THE WORKED EXAMPLE: the machine's own datacenter/power theme

**Could "visible construction footprint at named hyperscaler sites expands over the next 2 quarters" be filed
today and resolved on free Sentinel-2?** **Mechanically yes; usefully no.**

*What filing would take:* name the sites (hyperscaler campus locations are largely public), draw and hash an
AOI per site, fix baseline (Jun-Jul 2026) and resolve (Jan-Feb 2027) windows, fix the threshold and
`method_version`. All feasible today, at $0 for imagery.

*What resolving would take:* ~6-12 S2 scenes per site per window, a masked median composite, the pinned
built-area rule. Compute is small — this runs on a laptop, no GEE needed.

*Where it breaks — four ways, in increasing severity:*
1. **The claim is near-certain, so it carries almost no information.** With ~$635-670bn of 2026 hyperscaler
   capex guidance already disclosed, "construction footprint at named sites expands" resolves `1` almost
   regardless of skill. A sub-claim whose prior is ~0.95 contributes nearly nothing to a calibration or
   discrimination estimate — it pads the count (exactly the padding failure mode the v2 spec warns about).
2. **10m resolution + 2 quarters is marginal** for distinguishing "expanded" from "graded the next pad."
3. **Seasonality forces YoY windows** (Q3 above) which breaks the quarterly cadence v2 needs.
4. **It is the LAST link in the causal chain** (see Q5) — by the time concrete is visible, the market has had
   the permit, the interconnection filing, the power-offtake announcement and a capex guide.

**Sharper EO-shaped claim that would actually be informative:** *"a site with an announced completion date of
Q1-2027 shows NO built-area change over two consecutive windows"* — i.e. **detecting the announcement that
didn't happen.** That inverts the prior to something genuinely uncertain and is the one thing imagery does
that a press release cannot. Recorded as the strongest form of the idea; it still fails Q5.

## Q5 — THE SURVIVAL TEST (the pre-stated kill criterion)

**Does the news tape / EDGAR / earnings-call text already deliver the same verification earlier or cheaper?**
**Yes — earlier AND cheaper, and the reason is structural, not incidental.**

**The build-out paper trail PRECEDES the concrete, in a fixed order:**
> land control → zoning/planning submission → **building permit** → power offtake agreement →
> **utility interconnection-queue request** → MEP procurement → *then* a foundation visible from orbit

Every step before the last is a public text/records event. So **EO is structurally the last-arriving signal in
this domain** — it can only confirm what the record already said months earlier. And the records substrate is
richer than expected: public trackers already aggregate **proposed / under-construction / operational US
datacenters from public records with daily updates**, interconnection-queue requests across US ISOs are
tracked daily, permit filings are compiled into running lists, and hyperscaler capex is guided quarterly.
Multiple efforts already **fuse imagery with permits and open sources** for exactly this purpose — meaning even
the differentiated version of the idea is not uncrowded.

**Per-candidate survival table:**
| candidate EO use | does text/records deliver it earlier or cheaper? | survives? |
|---|---|---|
| datacenter build-out progress | **Yes** — permits + interconnection queue + capex guides, daily, free, months earlier | ✗ |
| transmission / power infrastructure | **Yes** — interconnection queues, FERC/state filings, utility IRPs | ✗ |
| mine / port / factory expansion (US-listed) | **Yes** — 8-K/10-K capex, permits, earnings calls | ✗ |
| **"the announced thing did NOT get built"** | **Partly** — cancellations do surface in permit withdrawals, queue exits and capex revisions, but with a lag and less completely | ~ (the only near-miss) |
| non-disclosing / foreign / private entities | **No** — genuinely differentiated | ✗ *for us*: our theses trade **US-listed** names that must disclose |

**Q5 verdict: the kill criterion is MET for every candidate that is in scope for our desk.** The one
near-miss ("verify the non-event") is differentiated but (a) still substantially covered by permit
withdrawals/queue exits, (b) needs YoY windows that break the quarterly cadence, and (c) is exactly the case
the already-existing imagery+permit fusion efforts target. **Per the pre-stated criterion, the verdict is
PARK, and I am saying it plainly as the dispatch invited.**

## Q6 — PRIOR ART: what the decade mined, and what is actually uncrowded

**Mined to death** (institutional, decade-old, latency- and capital-advantaged): oil-storage **tank-shadow**
gauging, **NDVI** crop-yield nowcasting, retail **car-counts**, port container/ship counts, mine stockpiles.
These lose to institutions on every axis that matters — tasking priority, sub-meter resolution, labeled
history, and the ability to trade the result within hours. This is the same structure as our own T-289/T-265
findings: a signal whose value decays in days cannot be harvested by a daily-cadence retail machine.

**Structurally un-servable at our scale:** anything requiring *tasked* collection (you pay for a satellite to
look where you choose, when you choose) or sub-meter resolution. Free tiers are opportunistic, not tasked.

**Genuinely uncrowded in the slow-verification niche?** The honest answer is **thin, and shrinking**: the
plausible gap is multi-quarter *physical-progress-vs-announcement* verification on capex-class projects — and
that is precisely the gap public-records trackers and imagery+permit fusion projects are already filling, for
free, with daily updates. **I found no genuinely uncrowded slow-verification niche that our substrate access
could exploit.**

---

# RECOMMENDATION — **PARK the EO substrate; ADOPT the sub-claim class on a better substrate**

**PARK EO**, on three independent grounds, any one of which would be sufficient:
1. **Latency/granularity:** AlphaEarth is annual and 7-19 months stale — structurally unable to resolve a
   quarterly sub-claim. Only Sentinel-2 is fast enough, and its 10m/seasonality constraints push honest
   comparisons to YoY windows, which break v2's quarterly cadence.
2. **Licensing/cost:** our use is commercial; the free GEE tier is unavailable to us and GEE commercial is
   $500-2,000/mo against a ~$2-3/mo desk. (Sentinel-2 direct is $0 — so this kills *Earth Engine*, not EO.)
3. **The survival test (decisive):** text/records deliver the same verification **earlier**, because the
   paper trail structurally precedes the concrete — and free daily trackers already aggregate it.

### The constructive half — the director's instinct was right about the CLASS
The valuable idea in this dispatch is not the satellite; it is *"resolve sub-claims against physical reality
rather than only prices and filings."* That idea should be **kept and pointed at the right substrate**:

**Proposed v2 optional resolver type `records_progress` — the EO idea done on records:**
free, **daily** (not annual), PIT-stamped by filing date, mechanically resolvable, and **earlier in the causal
chain**. Same skeleton as the Q3 spec — pre-registered target (site/project/docket ID + hash), a closed metric
set (`permit_filed`, `permit_withdrawn`, `interconnection_mw_queued`, `queue_exit`, `capex_guide_delta`), a
frozen threshold and window, fail-closed `UNRESOLVED` when the record is absent. It satisfies every property
the EO resolver was wanted for **and** clears the desk's cost class.

**The gate EO would have to pass to be revisited (pre-stated):** a named sub-claim class where **(a)** the
subject has no disclosure obligation covering it (so text genuinely cannot serve), **(b)** a *pre-registerable*
free-tier collection cadence covers the AOI (no tasking), **(c)** the metric is deterministic at 10m with a
YoY-clean comparison, and **(d)** it clears the desk's ~$0 cost class end-to-end. If a future thesis names
such a claim, this doc is the design already drafted — the resolver spec in Q3 stands ready.

**Scope discipline:** nothing was built, no dependency added, no Earth Engine account created, and no
propose-first gate is being requested. N_trials = 0.

---
## Sources
- [AlphaEarth Foundations Satellite Embeddings: A Look at Our Planet in 2025 (Google Earth, Medium — dated 2026-03-09)](https://medium.com/google-earth/alphaearth-foundations-satellite-embeddings-a-look-at-our-planet-in-2025-f23349370399)
- [Introduction to the Satellite Embedding Dataset (Google Earth Engine docs)](https://developers.google.com/earth-engine/tutorials/community/satellite-embedding-01-introduction)
- [Earth Engine Noncommercial Tiers](https://developers.google.com/earth-engine/guides/noncommercial_tiers)
- [Google Earth Engine pricing (Google Cloud)](https://cloud.google.com/earth-engine/pricing)
- [The Economics of Earth Engine (EECU / plan rates)](https://christopherren.substack.com/p/the-economics-of-earth-engine)
- [Sentinel-2 — Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2)
- [Copernicus Sentinel data licence (rev. 1)](https://cds.climate.copernicus.eu/licences/ec-sentinel)
- [Sentinel-2 — Registry of Open Data on AWS (latency)](https://registry.opendata.aws/sentinel-2/)
- [U.S. Data Center Records — proposed / under construction / operational (interconnection.fyi)](https://www.interconnection.fyi/data-center)
- [Tracking Every Data Center Permit Filed in 2026 (Buildermuse)](https://buildermuse.com/commercial/tracking-every-data-center-permit-filed-in/)
- [Tracking Hyperscale AI Data Center Growth with Satellite Imagery (FAS)](https://fas.org/publication/tracking-hyperscale/)
- [Data center permits and decisions (Shovels.ai)](https://www.shovels.ai/blog/data-center-permits-decisions/)

---
---
# T-335b ADDENDUM (2026-07-29) — the probe broadens: **cheapest honest resolver per sub-claim CLASS**

Per the rider, the question is no longer "can EO verify?" but **"what is the cheapest honest resolver for each
sub-claim class?"** — with EO earning a place only for claims nothing cheaper resolves. Also banked here: the
PIT scrutiny checklist as a standing test, the GDELT probe answer, and the park's reversibility.

## PARK STATUS — recorded as **reversible**
**EO is parked AT THE SUBSTRATE, not refuted AT THE IDEA.** The verification-layer *idea* was adopted (it
became `records_progress`); only the satellite substrate lost. Two of the three PARK grounds are
**constraint-dependent and could move**: cadence (a sub-annual AlphaEarth product, or a free tier with
pre-registerable tasking) and licensing/cost. The third (text arrives earlier) is structural but **domain-
specific** — it holds for US-listed capex build-out, not necessarily for a future non-disclosing subject.
**This is the CEF pattern:** a park revived when its constraint moves. The Q3 resolver spec is the design
already drafted; the 4-condition gate is the trigger.

**Licensing footnote (user's challenge, resolved):** the user fairly pushed back on "our use is commercial" —
a private individual trading their own account fits no enumerated GEE noncommercial category but is not
obviously a business either. **Resolution adopted:** the conservative read stands **as policy** (a system that
may someday touch real money takes the strict reading, and at real-money time it becomes unambiguous), and the
question is **moot for the surviving substrate** — Copernicus direct is $0 including commercial use.

## THE RESOLVER TAXONOMY — one spec per class, cheapest-first
All four share the Q3 skeleton (**target hashed at filing**, frozen window + threshold, pinned
`method_version`, **fail-closed `UNRESOLVED`** when the record is absent, and rejection of any datum
timestamped after the resolve window). What differs is the substrate and the failure modes.

| class | substrate | cost | freshness | verdict |
|---|---|---|---|---|
| **power / grid** | **EIA Open Data API v2** | **$0** (free, API-key registration) | **hourly** electric-power operations (demand, net generation, interchange) | **PRIMARY** |
| **government contract** | **USASpending** (T-334 archiving) | $0 | award-posting cadence (days) | **PRIMARY** |
| **filings / disclosure** | **EDGAR** (already ours) | $0 | minutes-hours | **PRIMARY** |
| **records-progress** (permits, interconnection queue, capex guides) | public trackers + ISO queues + EDGAR | $0 | **daily** | **PRIMARY** (approved for the freeze) |
| **physical build-out** | Sentinel-2 (direct, never GEE) | $0 imagery | 5-day revisit, YoY-clean only | **LAST RESORT** — only where nothing above serves |

### 1. `eia_series_change` — the power/grid resolver (tested BEFORE imagery, per the rider)
```
{ "type": "eia_series_change",
  "series_id":      "<EIA v2 route + facets>",   # e.g. hourly net generation for a named BA/region
  "series_sha256":  "<hex>",                     # the route+facet set hashed at filing (no post-hoc reshaping)
  "agg":            "monthly_mean" | "monthly_sum",
  "baseline_window":["2026-Q2"], "resolve_window":["2027-Q1"],
  "threshold":      {"op":"gt","value":0.10},    # +10%
  "min_obs":        60,                          # else UNRESOLVED, fail-closed
  "method_version": "eia_v1" }
```
**Why it beats imagery for the same underlying claim:** a datacenter build-out thesis's *economic* content is
**load growth**, and EIA measures load **directly, hourly, free** — where Sentinel-2 measures a *proxy* (roof
pixels) at 5-day revisit with cloud gaps and seasonality. **Directly-measured hourly beats proxy-measured
seasonal, at the same price.**
**Honest limits:** EIA reports at balancing-authority/region granularity, **not per-facility** — so it cannot
attribute load to a *named company's* site (that attribution is the imagery/permit job). Revisions occur, so
the resolver must pin the **vintage** it read, or a later revision silently changes a settled outcome.

### 2. `usaspending_award` — the government-contract resolver
```
{ "type":"usaspending_award", "recipient_uei":"<UEI>", "naics"|"psc":"<code>",
  "target_sha256":"<hex>", "window":["2026-10-01","2027-03-31"],
  "metric":"obligated_usd_sum", "threshold":{"op":"gt","value":50000000},
  "min_records":1, "method_version":"usasp_v1" }
```
**Key**: key on **UEI**, not company name — names change, subsidiaries proliferate, and a name-matched resolver
silently resolves the wrong entity. Fail-closed if the UEI can't be resolved at filing time.

### 3. `edgar_fact_change` — the filings resolver
```
{ "type":"edgar_fact_change", "cik":"<10-digit>", "xbrl_tag":"<us-gaap concept>",
  "target_sha256":"<hex>", "baseline_period":"CY2026Q2", "resolve_period":"CY2027Q1",
  "threshold":{"op":"gt","value":0.20}, "use":"first_reported",   # NOT the restated value
  "method_version":"edgar_v1" }
```
**`use: "first_reported"` is load-bearing** — the same PIT rule as T-265's `companyconcept` work: scoring
against a *restated* figure is hindsight. Reuses machinery we already have.

### 4. `eo_area_change` — physical build-out (the Q3 spec), **LAST RESORT**
Unchanged from Q3, now explicitly demoted: **use only for a claim that (a) no records/EIA/EDGAR route serves
and (b) clears the 4-condition gate.** Its weaknesses (reproducible≠accurate; cloud cover as a *correlated*
selection bias on which claims resolve; seasonality forcing YoY) are the reason it sits last.

**The taxonomy's own rule, stated for the freeze:** *a sub-claim must use the cheapest substrate that can
resolve it.* A thesis proposing an EO resolver where an EIA/records/EDGAR route exists should be **rejected at
validation** — not because EO is bad, but because the cheaper route resolves earlier and with fewer failure
modes. That is a contract rule, not a preference.

## GDELT — the probe answer, and **three findings the rider didn't anticipate**
1. **GDELT is ALREADY archived.** `paper_trader/altdata_archive.py:90` maps `("gdelt", pull_gdelt_timelines)`
   via the T-136 archivers. So "no archiver until a named consumer exists" is **already violated** — not
   prospectively, retroactively.
2. **What is archived is NOT what the rider proposes.** On disk:
   `data/macro_data/alt/gdelt_tone_timelines.parquet` — **345 daily rows, aggregate TONE by bucket**. The
   rider describes the **15-min global EVENT tape**. Aggregate daily tone is a *macro sentiment series*, not
   tape breadth; it cannot add per-name coverage to the thesis desk no matter how it's consumed.
3. **⚠️ The archive is STALE — last row `2026-06-11`, ~7 weeks ago** (span 2025-07-02 → 2026-06-11, 345
   distinct days). The module's own docstring warns GDELT "already 503s intermittently," and a dedup'd parquet
   leaves the file the *same size* on a zero-snapshot day — **the documented silent-stop failure mode, now
   apparently realized.** This is the same class as the 2-week paper outage: a collector that stopped without
   anyone noticing. **Flagging for whoever owns the archivers (B's lane) — I did not touch it.**

**GDELT verdict: NOT a thesis-tape breadth candidate as archived** (wrong object), and the correct next action
is not "add a consumer" but **fix-or-retire the stale collector**. If tape breadth is genuinely wanted later,
that is a *new* proposal for the 15-min event API — which must answer the PIT checklist below first.

## BANKED — the PIT scrutiny checklist (standing provider-evaluation test)
**Any future data-provider proposal — paid or free — answers all five BEFORE it reaches the director:**
1. **Delisted coverage** — are dead names present, or is the panel survivor-biased? (T-265: 36% CIK↔ticker join
   loss was exactly this.)
2. **No silent backfill** — does the provider retroactively insert history into past vintages?
3. **Correction history preserved** — can you read what was *known then*, not just what is true now? (The
   T-265 `first_reported` rule and the `edgar_fact_change` `use` field both exist for this.)
4. **Recycled-ticker symbology** — is identity keyed on a stable id (CIK/UEI/PERMNO) or on a reusable ticker?
   (T-271: BBBY/CBL returned *phantom* bars past delisting on a recycled symbol.)
5. **PIT-constituent mapping quality** — is index/sector membership as-of-date, or today's membership projected
   backwards?

Each of these has already burned this project at least once, which is why it is a checklist and not advice.

## Addendum recommendation
- **`records_progress` + `eia_series_change` are the freeze additions**; `usaspending_award` and
  `edgar_fact_change` are drafted and ready behind them (both on substrates we already hold).
- **EO stays parked, reversibly**, and demoted to last-resort within the taxonomy rather than removed.
- **GDELT: no consumer; fix-or-retire the stale collector** (B's lane) — flagged, not touched.
- Nothing built here either. **N_trials = 0.**

## Sources (addendum)
- [EIA's API Technical Documentation](https://www.eia.gov/opendata/documentation.php)
- [EIA Open Data (registration / free API key)](https://www.eia.gov/opendata/)
