# Proposal: cut the canonical substrate over from the T-082b drip to EXACT total return

**For:** Agent R (review), then the director, then **the USER**. A change of the canonical
substrate is the user's decision. **Status:** PROPOSAL ONLY. The drip stays canonical until the user
rules. Nothing in the real `data/processed/` has been written. **N_trials: 0.**

**Direction already ruled** (director, 2026-10-15): exact ex-date total return is the honest form of
the TOTAL RETURN convention. But it is a **planned cutover**, not a refresh. The convention guard
switches on **on cutover day, all files at once, never before**, because its
`RESCALED → full re-fetch` path would otherwise adopt exact total return file by file, leaving a mixed
universe.

**Evidence base:** the writer `engines/data_manager/tr_writer.py` (branch
`feature/price-cache-tr-writer`), run against a copy of the cache at
`/Users/jacksonmurphy/Dev/_substrate_candidates/processed_exact_tr_2026-10-15/`:
- real cache aggregate md5 BEFORE: `8ead63bc2271b38fc7adf56a0aa2918c` (2,172 files);
- the measure-only inventory: `/Users/jacksonmurphy/Dev/_substrate_candidates/measure_2026-10-15.jsonl`.

---

## 1. Finding one: the cutover changes RETURNS, not just levels

T-082b's `apply_dividend_strip` gave pre-seam history a smooth constant-yield drip. Replacing it with
exact ex-date total return does not just move price levels. **The drip under-counted dividends.** On
the XOM trial, the exact pre-seam history earns **+1.98%/yr** more than the drip (annualised log
return, 1970 to the 2020 seam).

**Consequence: every pre-2018 equity-book number is a RE-QUALIFICATION, not a relabel.** The
distribution across the universe is in §4. *(PENDING: the full measure pass.)*

## 2. Finding two: delisted names cannot be re-fetched, so a naive cutover splits the universe on SURVIVORSHIP

yfinance returns **nothing** for delisted tickers. The trial hit ABMD, ABS, ALXN and ANSS in its
first 64 files. Count: *(PENDING: the full measure pass)*.

A naive cutover would therefore move live names to exact total return and leave delisted names on the
drip. The survivorship-corrected universe would be split into two conventions **exactly along
survivor status**. Given finding one, that is not a cosmetic split: it converts the existing upward
survivorship bias into an upward bias whose SHAPE differs by survivor status.

**This proposal rules nothing on it.** The three candidate treatments, with their consequences:

| option | what it does | consequences |
|---|---|---|
| **(a) One convention everywhere: keep the drip, labelled universally** | No cutover of deep history until a delisted-capable total-return source exists. Every deep history is labelled "drip (constant-yield approximation)", everywhere. | Homogeneous and survivorship-consistent. **Knowingly keeps** the dividend under-count (finding one) in every pre-seam number, labelled rather than fixed. Post-seam is already exact. Cheapest; no re-qualification beyond the label. |
| **(b) Exact where available, drip where not, with a per-name convention field** | Live names cut over; delisted names stay on the drip. Each file carries a `convention` field (`exact_tr` / `drip`); the **census reads it**, and every equity-book measurement reports the split (share of names, share of weight, on each convention). | The most exact per name. The universe is **mixed by construction**, and the mix correlates with survivor status, so a long/short or cross-sectional result can partly reflect the convention split. That is visible because it is reported, but it is a confound. A census field becomes a referee change. |
| **(c) Buy a survivorship-complete total-return source** | Acquire a source that covers delisted names with exact total return (the B-1 prereg's re-verification clause already names this path). One provider, one convention, the whole universe. | The only option that is exact AND homogeneous. Costs money and is a new external dependency (a propose-first gate under CLAUDE.md), plus provider evaluation and a manifest of its own. Until it lands, (a) or (b) must hold. |

## 3. The re-pin list (every pinned artifact the cutover moves)

| artifact | why it moves |
|---|---|
| the backtester golden master | its fixture reads the processed closes |
| the 26-yr anchor `158fe678` | the canonical-window equity book |
| B-1's panel md5 `d9d449d17f8f` | built from the processed closes (R's lock 7: it must move VISIBLY) |
| `config/substrate_manifest.sha256` | exact-match verify of `data/processed/` |
| the exact-TR candidate's own manifest | pinned now, so the candidate is a fixed object |
| *(PENDING)* | any other pin whose inputs read `data/processed/`, enumerated by grep before the user's gate |

## 4. Measured deltas per file *(PENDING: the full measure-only pass)*

Per file: provider by span, span coverage, measured basis, overlap class, pre-seam and post-seam level
ratio, and pre-seam and post-seam annualised return delta. A distribution summary goes here; the full
per-file inventory is the jsonl above.

## 5. Per-verdict re-qualification plan under `[NN-SUBSTRATE-REVERIFY]` *(to be completed)*

Verdict by verdict: **re-run** (the verdict's own measurement crosses pre-seam history on equity
names, so finding one can move it) or **re-label** (post-seam only, or ETF sleeves on `tr_reconciled/`,
which this cutover does not touch). The scope authority for which verdicts ran on this substrate is
the RR-1 proposal's verdict list, per `CURRENT_STATE`, not a paraphrase. *(PENDING: the enumeration.)*

## 6. Sequence, if the user approves

1. The user's choice among (a), (b) and (c).
2. The write pass completes on the copy; the candidate manifest is pinned.
3. Re-qualification runs per §5.
4. Cutover day: the copy replaces the canonical substrate in one step; every §3 pin is re-pinned
   together; the guard switches on at every writer in the §4 inventory of the guard proposal, all at
   once.
5. First artifact: the next canonical run's census reports the convention, and, under (b), the split.
