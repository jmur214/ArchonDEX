---
name: feedback-pandas3-dtypes-and-monkeypatch-defaults
description: pandas 3 patterns that worked (list-column explode/groupby, lookaround word regex, json_normalize + fixed pa.schema) and pitfalls hit in T-405/T-416 (astype("string") NA flavour, groupby.apply dropping keys, default args defeating monkeypatch, df.style is the Styler, test subprocess env must derive from os.environ)
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

- (T-416, 2026-11-20) A column named `style` must be bracket-indexed: `df.style` is pandas' Styler
  accessor, so `df.style.tolist()` raises `'Styler' object has no attribute 'tolist'` (and a set() over it
  would silently be wrong). The same applies to any column that shadows a DataFrame attribute.
- (T-416) `pd.json_normalize(list_of_snapshot_dicts)` + `reindex(columns=MAP).rename(columns=MAP)` flattens
  nested API payloads with missing sub-objects into fixed columns without a hand loop. A fixed `pa.schema`
  passed to `pa.Table.from_pandas(..., schema=, safe=True)` casts pandas `Int64` -> int32, python `date` ->
  date32 and `str` -> string cleanly, and keeps per-day files read-compatible as a directory dataset.
- (T-416) Repo lock `test_every_subprocess_env_in_tests_inherits_os_environ`: a test's `subprocess.run(env=…)`
  must be derived from `os.environ` (`{**os.environ, "PATH": …}`); a hand-built minimal env fails the suite.

**Why:** each cost a debug loop in T-405; the default-arg one produced a test that passed without testing anything.
**How to apply:** whenever a test patches a module constant, check every use site is a call-time read.
