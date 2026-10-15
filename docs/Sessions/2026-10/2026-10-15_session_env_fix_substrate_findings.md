# Session Summary: 2026-10-15 — director: the .env fix lands, the substrate's conventions measured, the cutover becomes a decision

## What was worked on

- **The main-tree suite hang, closed.** Root cause (B, 10-14 night): `data_manager.py:34` loaded `.env` with override at IMPORT, so collection in the main tree armed the API key and the agentic pulse test called the real provider. Merged: pytest scoped to `tests/` (`c1229b8`), the hermetic `tests/conftest.py` (`9b1be4a`), and the engine-side unit (`c215408`: four import-time loads removed; one explicit no-override load at the 64 true process entries; provider call sites refuse under pytest; canonical runs refuse the yfinance fallback; the census records `data_feed`). **First artifact: the full suite ran green in the main tree — 4226 passed in 2:43, no sockets — where it had always hung.**
- **The price cache's conventions, measured.** The cache is total-return (exact post-seam, T-082b's constant-yield drip pre-seam) while every stated intent said split-only (B's R-5 unit `0f7a013`; R's measured correction `8ead52c`). A total-return WRITER now exists on a copy; a full pass would rewrite ~2000–2018 for ~626 files and changes RETURNS (the drip under-counted dividends: XOM +1.98%/yr); delisted names cannot be re-fetched. The cutover is a planned decision: proposal → R → the user. Three more substrate hazards found and recorded as HIGH rows: the reader DELETES an unparseable cache file; the ÷10 auto-scale masks a stitched-identity DAL; dollar-ADV computed on the TR close is a yield-correlated bias in every equity-book measurement.
- Also merged: B's testpaths unit, B's adjustment-class unit, the D1-reverted RR-7 follow-ups' remainder; the Engine A EdgeRegistry row anchored (the lint's first real catch, of the director).

## What was decided

- The substrate convention is **total return — exact post-seam, a constant-yield approximation pre-seam** (overridable by the user). Refresh paths will write the cache's MEASURED class and refuse a mixed convention (B's guard, R: BUILD IT with four corrections — writer first, provider-per-file, the cadence in numbers, two rails, measure-at-first-write, floor tolerance, atomic pair). The guard switches on **on cutover day**, all files at once.
- **Dollar-ADV, slippage and borrow buckets use split-only price × volume**; the unadjusted column ships with the cutover writer; recorded, not re-run, until then.
- **DAL:** pre-2007 bars withheld at load by a declared, census-recorded exclusion; DAL_OLD at cutover if a source exists.
- **Four decisions at the user's gate:** the push (181 commits, record green in the main tree); the three-engine registry design (R: BUILD IT); archive vs register the three never-registered, ledger-refuted edges; the audit-only image-listing Batch job (the permission layer correctly refused the director's attempt to authorise an AWS resource).

## What was learned

- **Quote heredoc delimiters; confirm merges by ancestry; never let a chained check continue past a failing step** — two director commits landed with doc_lint failing for one commit (an anchor at the wrong line, then an unreadable note); one merge's pre-check was void because a grep swept a fixture JSON into pytest's file list. Each stated in its fix commit. Band-runners restrict to `*.py` and abort on exit ≠ 0.
- **The lint's first real catches were of the director** (an unanchored new HIGH row; an anchor note the parser rejects). That is the design working.
- **A loader that "protects" is a loader that masks:** the ÷10 auto-scale fired on exactly one series and it was corrupt. The dollar-ADV bias lived in the one product nobody looks at (Close × Volume on a back-adjusted close).
- **Test-hygiene facts (B):** `monkeypatch.delenv` after a real setter RESTORES at teardown; `delenv(raising=False)` on an absent var records nothing; a reversion that passes for the wrong reason (the old load hid behind `if env_path.exists()`); AST locks on CALLS, never text; Discovery's Gate-1 candidate census is a separate producer.

## What was worked on (afternoon)

- **Three more merges on R's approval, each checked by the FULL suite on the staged merge in the main tree** (possible since the .env fix removed the hang): item (d) (`e733a94`, 4239/0 — the ÷10 auto-scale gone, DAL withheld by a declared exclusion carried by both census producers, the dollar-ADV row anchored, the two-producer rule in the contract); the price-cache guard branch (`23a5ef7`, 4260/0 — the total-return writer and guard NOT wired, the never-delete reader WIRED, the proposals as docs); D's census fail-closed unit (`032569d`, 4273/0 — the census fails closed on its own errors; three more fail-open shapes found by executing every except branch; no silent zero; the candidate census declares its kind). A 91-file "touching band" showed 8 order-dependent failures identical on clean main — a band artifact — which is why the full suite became the check.
- **B's measure pass over the whole cache copy (730/730, the real cache untouched):** the pre-seam exact-TR vs drip delta is per-name DISPERSION (median −0.10%/yr, p10 −1.33, p90 +0.59), not the uplift XOM suggested; R's "one provider per file by span" overturned — Alpaca's IEX history starts 2020-07-27 and disagrees with the cache's convention wherever chosen, yfinance agrees everywhere → one provider for the whole universe; 69 "empty" results were Alpaca fetches, not delistings — the true unfetchable count is being re-measured (172 files via yfinance); AGG is split-only in the canonical cache; BBBY is a ticker-reuse hazard the span check caught.
- **R reproduced B's writer gap with a planted mismatch:** `classify_overlap` existed but `full_refetch` never called it — a split-only provider series replaced a total-return cache with a clean write record. A blocker for switch-on (the writer is unwired, nothing exposed); the fix + lock and the Alpaca path/constant are B's next writer unit; the write pass on the copy is HELD until it merges.

## What was learned (afternoon)

- **A primitive that exists is not a guard until the write path calls it.** Prove a guard by a planted mismatch that reaches the write, never by the primitive's own unit test.
- **A "touching band" is not a check**: subsets can fail on order; the full suite in under three minutes is now cheaper than attributing a band's artifacts.
- **The lint's exits are a workflow, not a nuisance:** two rows resolved themselves on merge because their witness lines vanished; one anchor moved by reading the line. The director's own unanchored rows were the lint's first catches.
- **Measure before ruling on a provider:** the "per file by span" rule was reasonable and wrong; one measurement over 730 files settled it.

## What was worked on (evening)

- **The writer unit merged (`8616f93`, 4279/0 on the staged merge):** the Alpaca path dropped (one provider for the whole universe — its IEX history starts 2020-07-27 and disagreed with the cache wherever chosen), the overlap refusal in `full_refetch` over a measured 252-bar window (a 40-bar tail passed two conventions as a rescale), R's planted mismatch as the lock. **The Yahoo symbol table merged alone (`47aca8a`, 4292/0)**; the BK → BNY rename HELD out of code until the cutover's declared class (R: an identity claim does not enter code ahead of the ruling).
- **The write pass on the copy, complete; the real cache untouched (md5 identical):** 630 of 730 written; every refusal classed (the split-only trio AGG/EFA/VNQ from one writer; AMCR a mixed cache; CPWR/NFX/CA/BBBY/PSKY reused tickers; DAL the stitch; eight names with Stooq history deeper than the provider's; five with start leads); **the true unfetchable count 75 of 730 (10.3%)**, measured by a slow serial retry keeping the provider's own reasons — the survivorship number the cutover must rule on. §4 final: pre-seam delta median −0.10 %/yr (p10 −1.34, p90 +0.58), post-seam exact TR everywhere but the four refused.
- **The cutover proposal is COMPLETE and with R** (`docs/cutover-proposal-numbers` @ ec3385b). §3 settled by artifact: **the cutover changes NO live trading input** (trading closes come from Alpaca at run time; the paper image bakes tr_reconciled, outside the cutover; one report-only read is 'unverified: needs the image listing'); the re-pin list; corrections by evidence (the four tests the director named do not move; the T-306 family reads SPY_1d.csv but a constant ratio cancels). Two findings of their own, now HIGH rows: **the campaign submit gate checks only that anchor KEYS exist** (a stale anchor passes silently — D's unit); **`gen_substrate_manifest.py verify` EXITS 1 TODAY** (5 changed macro files + never-listed additions; tr_reconciled baked into the paper image unpinned — B's read-only unit; the re-pin with the cutover, the first since June).

## What was learned (evening)

- **A presence check is not a verification** (the submit gate; the silent-zero census defaults; the regex contract) — the class recurs wherever "is the key there?" stands in for "does it match?".
- **A pin that fails `verify` today certifies nothing**: nobody had run it since June. The re-pin is a cutover-day act, and the gate that reads it must fail closed on a manifest that does not verify itself.
- **Keep the provider's raw reasons**: an earlier grep had filtered exactly the lines that carried yfinance's per-symbol reason; the 78 → 75 correction came from reading them. Retry serially AFTER heavy fetching, never alongside.
- **An identity claim is a ruling, not a table entry** — the writer's rail refused a verified rename on two 0.042% steps and was right not to be loosened.

## Pick up next time

- The user's four decisions. After the push: the 03:00 janitor covers the real tree; B's 07:17 watch; D's R1 mirror upload; E's acct-3 redeploy (with E's user's confirmation); D builds the registry unit on 'approve'; B's image audit on 'approve'.
- B: the writer unit (classify_overlap in full_refetch refusing DIFFERENT_CONVENTION; the Alpaca path dropped or its constant corrected) → R (the planted mismatch is the lock) → merge → the write pass on the copy → the cutover proposal's numbers (the true unfetchable count; the dispersion wording; three survivorship treatments, no pick; §5's one re-run; L4 for the user; R's O-3 as a switch-on requirement) → R → the user.
- R: the guard build, (d), the registry unit, the cutover proposal, in that order as they arrive.
