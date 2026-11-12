---
name: report-the-checks-actual-scope
description: Quote a verification at the scope it actually ran (my check compared post-seam text FROM seam+14, I reported "post-seam identical"); and record the exact recipe of any digest you quote
metadata:
  type: feedback
---

When a check is scoped (e.g. "post-seam lines from seam+14", "csv only", "these 12 names"), the report and
every doc must carry that scope verbatim. T-387: my copy-vs-v4 check compared post-seam text from row seam+14
and the build rule allows ATR (first 14 rows) and PrevClose (seam row) to change — yet I wrote "post-seam
text identical on all 575" in the runbook, the CLI docstring and the report. The reviewer measured 13–14
changed ATR rows per file and flagged it as an overclaim.

Also: a digest quoted as proof (my `data/processed` listing md5) is worthless if the reviewer cannot
reproduce it — ~25 variants missed. Record the exact command (incl. `LC_ALL=C sort`, `md5 -r` vs `md5sum`
format, `./` prefix) or cite the project's committed manifest (`config/substrate_manifest.sha256`) instead.

**Why:** the user's standard is "report honestly"; an overclaim that the code does not even make is a
self-inflicted review finding, and an irreproducible number is not evidence.
**How to apply:** before writing "identical/unchanged", re-read what the check compared; quote the canonical
manifest verify (0/0/0) as the canon-unchanged proof, with any extra digest's recipe beside it.
