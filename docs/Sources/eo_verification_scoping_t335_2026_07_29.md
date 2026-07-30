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
