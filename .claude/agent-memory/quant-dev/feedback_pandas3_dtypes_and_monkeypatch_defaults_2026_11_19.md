---
name: feedback-pandas3-dtypes-and-monkeypatch-defaults
description: pandas 3 patterns that worked (list-column explode/groupby, lookaround word regex) and three pitfalls hit in T-405 (astype("string") NA flavour, groupby.apply dropping keys, default args defeating monkeypatch)
metadata:
  type: feedback
---

Patterns that worked (repo runs pandas 3.0.x; paper image pins 3.0.1):
- Ragged list column (Kalshi `tags`): `s.explode().astype("string").str.lower()` → `.where(isin(allowed)).groupby(level=0).first()` → `reindex(original_index)`. Vectorized, no per-row lambda.
- Whole-word keyword regex: `(?<![a-z0-9])(alt1|alt2)(?![a-z0-9])` + re.IGNORECASE, alts sorted longest-first and re.escape'd. `\b` misfires on "s&p 500"/"eur/usd". Use a NON-capturing variant for `str.contains` (a capture group triggers a UserWarning) and a capturing one for `str.extract`.
- `pd.util.hash_pandas_object(df.sort_values(keys), index=False)` → sha256 is a cheap "old rows byte-identical after append" proof.

Pitfalls:
- `astype("string")` gives StringDtype(na_value=<NA>); files written by pandas 3 default inference carry `str` (na_value=nan). Leave text columns inferred when appending to an existing parquet.
- pandas 3 `groupby(...).apply(f)` drops the grouping column from the frame f sees; use `groupby(k).head(n)` instead.
- A module constant used as a DEFAULT ARGUMENT (`def f(max_pages=CONST)`) is bound at def time, so `monkeypatch.setattr(m, "CONST", 3)` silently does nothing — a test passed for the wrong reason. Read the constant at call time (`max_pages = max_pages or CONST`) and assert the effect (count the requests).

- **`pd.to_datetime(s, errors="coerce")` on API timestamps WITHOUT `format="ISO8601"`** infers ONE format from the first value and silently NaTs every value of the other shape ("…:00Z" vs "…:00.484355Z"). It dropped all 28 between-events Kalshi series from one live discovery with "0 errors" printed. Always pass `format="ISO8601"` for API timestamps, test BOTH shapes in BOTH orders, and fail closed when a value that came back does not parse. Never `max()` ISO strings ("…:00Z" > "…:00.48Z" as text).
- `Series.to_numpy(dtype=bool)` can return a READ-ONLY view; `mask &= other` then raises "output array is read-only". Write `mask = mask & other`.
- A never-raise wrapper (`try: return _impl() except Exception: return "FAILED …"`) on an archiver hides such bugs from tests that only check side effects — the read-only error surfaced as "nothing looked up". Assert on the returned message too, or debug the `_impl` directly.

**Why:** each cost a debug loop in T-405; the default-arg one produced a test that passed without testing anything.
**How to apply:** whenever a test patches a module constant, check every use site is a call-time read.
