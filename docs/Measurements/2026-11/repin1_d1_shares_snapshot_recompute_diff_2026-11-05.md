# Re-pin #1, D1 — the T-219 shares snapshot and the hermetic recompute's whole-file diff (2026-11-05)

Point-in-time artifact of the re-pin #1 record (`docs/Sources/proposal_repin_1_drip_substrate_2026-11-05.md` §3 D1;
ledger T-375). Nothing in `data/universe/market_cap_tiers.json` was rewritten: it is pinned as-is (sha256 f12933ce…
before and after). The recompute went to a scratch file; this is its diff against the pinned file, whole, as the
execution reviewer's F1 required.

## The fetch (`--write-snapshot`, network, once)

| cohort (left the index) | with a price file | fetched | empty | failed | rows |
|---|---|---|---|---|---|
| 367 | 219 | 199 | 20 | 0 | 111,236 |

The 20 empty names (yfinance `get_shares_full` returned None — the free-data wall, pre-~2015 delistings): ABS, BMC,
CBE, CCE, CFC, COL, ESRX, EVHC, GENZ, GR, GRN, HAR, MHS, NSM, PCS, RX, SVU, TEG, TIE, USL. Every reason is in
`data/universe/delist_shares_snapshot.meta.json`, pinned beside the parquet.

## The recompute (`--from-snapshot`, hermetic, scratch output)

Stats line: snapshot_names 199 · resolved 191 · wall 8 · changed_vs_current 63 · new_vs_current 0. The file holds
**193** `delist_shares` entries (130 identical to the pinned file + 63 changed) — the stats counter reads 191, two
short of the file's content: a NOTE for the C4 selection-rule follow-up, not a defect in any pinned file.

**The 138 pinned `delist_shares` entries: 130 reproduced EXACTLY from the snapshot; 8 differ** — all eight are
still-trading names whose `asof` moved to 2026-04-24 (the price cache's last bar) because the shares series now
extends past the date that bounded June's window; ratios 0.9898 – 1.0148 (JEF, KBH, KMX, LW, NWL, RRC, SE, SUN).
The snapshot reproduces June's live fetch for every name whose window June's shares data already covered.

**The 55 cohort names carrying a current-snapshot cap today would be REPLACED by the recompute** (the reviewer's F1):
for a still-trading name `cap_at_delist` keys its 12-month window on the price file's last bar, so it is a trailing
median, not a cap at leaving the index; ratios 0.19 (CIEN) – 3.20 (ADCT), spot-vs-median differences plus share
revisions. **Ruling (director, 2026-11-05):** none of these is written at re-pin #1. Before re-pin #2 the recompute
gains a SELECTION rule — write cap-at-delist only for names whose price file ENDS before the recompute date; a
still-trading name keeps its current-snapshot cap — locked, and this diff is the evidence that sizes it (55 + 8).

## Every difference (ticker · kind · current cap/tier/asof → recomputed cap/tier/asof · ratio)

```
  AA      replaced current-snapshot -> delist_shares       1.567e+10/large/-                -> 9.482e+09/mid/2026-04-24         ratio 0.6052
  AAL     replaced current-snapshot -> delist_shares       1.058e+10/large/-                -> 8.137e+09/mid/2026-04-24         ratio 0.7694
  AAP     replaced current-snapshot -> delist_shares       3.626e+09/mid/-                  -> 3.104e+09/mid/2026-04-24         ratio 0.8561
  ADCT    replaced current-snapshot -> delist_shares       1.386e+08/micro/-                -> 4.435e+08/small/2026-04-24       ratio 3.1988
  ADT     replaced current-snapshot -> delist_shares       5.004e+09/mid/-                  -> 6.684e+09/mid/2026-04-24         ratio 1.3356
  AIV     replaced current-snapshot -> delist_shares       4.172e+08/small/-                -> 6.109e+08/small/2026-04-24       ratio 1.4643
  ALK     replaced current-snapshot -> delist_shares       5.489e+09/mid/-                  -> 5.919e+09/mid/2026-04-24         ratio 1.0783
  AMD     replaced current-snapshot -> delist_shares       8.762e+11/mega/-                 -> 3.205e+11/mega/2026-04-15        ratio 0.3658
  AMG     replaced current-snapshot -> delist_shares       9.321e+09/mid/-                  -> 6.903e+09/mid/2026-04-24         ratio 0.7406
  AN      replaced current-snapshot -> delist_shares       6.316e+09/mid/-                  -> 7.491e+09/mid/2026-04-24         ratio 1.1861
  ANF     replaced current-snapshot -> delist_shares       3.876e+09/mid/-                  -> 3.648e+09/mid/2026-04-24         ratio 0.9410
  APC     replaced current-snapshot -> delist_shares       8.748e+08/small/-                -> 1.496e+09/small/2026-04-24       ratio 1.7098
  ATI     replaced current-snapshot -> delist_shares       2.748e+10/large/-                -> 8.361e+09/mid/2025-10-22         ratio 0.3043
  AYI     replaced current-snapshot -> delist_shares       9.629e+09/mid/-                  -> 9.582e+09/mid/2026-04-24         ratio 0.9951
  BBBY    replaced current-snapshot -> delist_shares       4.385e+08/small/-                -> 5.175e+08/small/2026-04-24       ratio 1.1803
  BBWI    replaced current-snapshot -> delist_shares       4.144e+09/mid/-                  -> 5.19e+09/mid/2026-04-24          ratio 1.2523
  BC      replaced current-snapshot -> delist_shares       5.43e+09/mid/-                   -> 4.218e+09/mid/2026-04-24         ratio 0.7768
  BEAM    replaced current-snapshot -> delist_shares       3.512e+09/mid/-                  -> 2.423e+09/mid/2026-04-24         ratio 0.6899
  BHF     replaced current-snapshot -> delist_shares       3.633e+09/mid/-                  -> 3.396e+09/mid/2026-04-24         ratio 0.9346
  BIO     replaced current-snapshot -> delist_shares       7.559e+09/mid/-                  -> 7.59e+09/mid/2026-04-24          ratio 1.0042
  BTU     replaced current-snapshot -> delist_shares       3.021e+09/mid/-                  -> 3.34e+09/mid/2026-04-24          ratio 1.1054
  BWA     replaced current-snapshot -> delist_shares       1.474e+10/large/-                -> 9.369e+09/mid/2026-04-24         ratio 0.6358
  CCK     replaced current-snapshot -> delist_shares       1.135e+10/large/-                -> 1.161e+10/large/2026-04-24       ratio 1.0233
  CE      replaced current-snapshot -> delist_shares       5.61e+09/mid/-                   -> 5.246e+09/mid/2026-04-24         ratio 0.9350
  CEG     replaced current-snapshot -> delist_shares       9.787e+10/large/-                -> 1.045e+11/large/2026-04-24       ratio 1.0681
  CIEN    replaced current-snapshot -> delist_shares       6.062e+10/large/-                -> 1.133e+10/large/2025-09-30       ratio 0.1869
  CLF     replaced current-snapshot -> delist_shares       7.005e+09/mid/-                  -> 5.592e+09/mid/2026-04-24         ratio 0.7984
  CNX     replaced current-snapshot -> delist_shares       4.622e+09/mid/-                  -> 4.882e+09/mid/2026-04-24         ratio 1.0563
  COTY    replaced current-snapshot -> delist_shares       1.717e+09/small/-                -> 3.447e+09/mid/2026-04-24         ratio 2.0079
  CPB     replaced current-snapshot -> delist_shares       6.307e+09/mid/-                  -> 8.847e+09/mid/2026-04-24         ratio 1.4027
  CPRI    replaced current-snapshot -> delist_shares       2.34e+09/mid/-                   -> 2.43e+09/mid/2026-04-24          ratio 1.0382
  CPWR    replaced current-snapshot -> delist_shares       1.197e+06/micro/-                -> 1.9e+06/micro/2026-03-31         ratio 1.5873
  CTRA    replaced current-snapshot -> delist_shares       2.472e+10/large/-                -> 1.92e+10/large/2026-04-24        ratio 0.7767
  CZR     replaced current-snapshot -> delist_shares       5.952e+09/mid/-                  -> 5.336e+09/mid/2026-04-24         ratio 0.8965
  DD      replaced current-snapshot -> delist_shares       1.933e+10/large/-                -> 1.411e+10/large/2026-04-24       ratio 0.7303
  DELL    replaced current-snapshot -> delist_shares       2.654e+11/mega/-                 -> 7.779e+10/large/2026-02-26       ratio 0.2931
  DOW     replaced current-snapshot -> delist_shares       2.287e+10/large/-                -> 1.865e+10/large/2026-04-24       ratio 0.8154
  DV      replaced current-snapshot -> delist_shares       1.585e+09/small/-                -> 1.855e+09/small/2026-04-24       ratio 1.1700
  DXC     replaced current-snapshot -> delist_shares       1.394e+09/small/-                -> 2.521e+09/mid/2026-04-24         ratio 1.8087
  DYN     replaced current-snapshot -> delist_shares       3.273e+09/mid/-                  -> 2.396e+09/mid/2026-04-24         ratio 0.7321
  EMN     replaced current-snapshot -> delist_shares       8.289e+09/mid/-                  -> 7.83e+09/mid/2026-04-24          ratio 0.9446
  ENPH    replaced current-snapshot -> delist_shares       6.89e+09/mid/-                   -> 4.898e+09/mid/2026-04-24         ratio 0.7108
  EP      replaced current-snapshot -> delist_shares       1.186e+08/micro/-                -> 1.258e+08/micro/2026-04-24       ratio 1.0608
  EPAM    replaced current-snapshot -> delist_shares       4.004e+09/mid/-                  -> 9.369e+09/mid/2026-04-24         ratio 2.3399
  EQT     replaced current-snapshot -> delist_shares       3.172e+10/large/-                -> 3.384e+10/large/2026-04-24       ratio 1.0668
  ETSY    replaced current-snapshot -> delist_shares       7.018e+09/mid/-                  -> 5.602e+09/mid/2026-04-24         ratio 0.7982
  FHN     replaced current-snapshot -> delist_shares       1.178e+10/large/-                -> 1.114e+10/large/2026-04-24       ratio 0.9459
  FLR     replaced current-snapshot -> delist_shares       7.495e+09/mid/-                  -> 7.031e+09/mid/2026-04-24         ratio 0.9381
  FLS     replaced current-snapshot -> delist_shares       1.044e+10/large/-                -> 7.327e+09/mid/2026-04-24         ratio 0.7017
  FMC     replaced current-snapshot -> delist_shares       1.444e+09/small/-                -> 3.659e+09/mid/2026-04-24         ratio 2.5333
  FOSL    replaced current-snapshot -> delist_shares       2.535e+08/micro/-                -> 1.592e+08/micro/2026-04-24       ratio 0.6279
  FOX     replaced current-snapshot -> delist_shares       1.971e+10/large/-                -> 2.479e+10/large/2026-04-24       ratio 1.2572
  FOXA    replaced current-snapshot -> delist_shares       2.193e+10/large/-                -> 2.489e+10/large/2026-04-24       ratio 1.1349
  FSLR    replaced current-snapshot -> delist_shares       2.769e+10/large/-                -> 2.159e+10/large/2026-04-24       ratio 0.7797
  FTI     replaced current-snapshot -> delist_shares       2.598e+10/large/-                -> 1.439e+10/large/2026-01-07       ratio 0.5537
  JEF     replaced delist_shares -> delist_shares          1.128e+10/large/2026-04-23       -> 1.128e+10/large/2026-04-24       ratio 1.0000
  KBH     replaced delist_shares -> delist_shares          3.897e+09/mid/2026-03-26         -> 3.871e+09/mid/2026-04-24         ratio 0.9932
  KMX     replaced delist_shares -> delist_shares          6.817e+09/mid/2026-04-17         -> 6.747e+09/mid/2026-04-24         ratio 0.9898
  LW      replaced delist_shares -> delist_shares          7.296e+09/mid/2026-04-23         -> 7.296e+09/mid/2026-04-24         ratio 1.0000
  NWL     replaced delist_shares -> delist_shares          1.971e+09/small/2026-03-28       -> 1.96e+09/small/2026-04-24        ratio 0.9941
  RRC     replaced delist_shares -> delist_shares          8.921e+09/mid/2026-04-23         -> 8.924e+09/mid/2026-04-24         ratio 1.0004
  SE      replaced delist_shares -> delist_shares          8.657e+10/large/2026-04-20       -> 8.646e+10/large/2026-04-24       ratio 0.9987
  SUN     replaced delist_shares -> delist_shares          7.174e+09/mid/2026-02-26         -> 7.28e+09/mid/2026-04-24          ratio 1.0148
```
