# Archived 2026-10-22 — three edge modules that existed in code but were never registered, and are REFUTED

Archived by the edges.yml single-writer unit (the user's decision on
`docs/Sources/edge_registry_single_writer_brief_2026-10-14.md` §"Your decision before the first sync",
2026-10-22: **archive, not register**). Under pure imports these edges would never have reached the
registry; under the old import-time writer they appeared in `edges.yml` only while one of the scripts
below was running. Registering them would have queued three experiments their own ledger rows closed.

| module (was `engines/engine_a_alpha/edges/`) | edge id | ledger rows (`docs/State/TASK_LEDGER.md`) | verdict |
|---|---|---|---|
| `betting_against_beta_edge.py` | `betting_against_beta_v1` | T-123 (2026-06-06), T-129 (2026-06-10) | REFUTED — factor-α −0.77 %, t −0.13, "statistically ZERO"; the 26-year referendum "CONFIRMED THE MISS" |
| `overnight_intraday_edge.py` | `overnight_intraday_v1` | T-135 (2026-06-10); harvest NO upheld by T-157 (2026-06-12) | REFUTED — "FIRST strict-gate α ever measured — and unharvestable"; the re-price kept the harvest verdict at NO |
| `volatility_risk_premium_edge.py` | `volatility_risk_premium_v1` | T-122 (2026-06-06), T-174 (2026-06-16) | REFUTED — factor-α −0.21 %, t −0.36; "fails the pre-registered ci_low>0 gate in every overlay form" |

No test file under `tests/` imported any of the three (checked by grep for the module names, the edge ids and
the class names on 2026-10-22), so nothing moved from `tests/`.

## Their only importers, archived with them

`Archive/scripts/edges_refuted_2026_10/`:
- `run_bab_gauntlet_t123.py` (the T-123 gauntlet dispatch),
- `run_vrp_gauntlet_t122.py` (the T-122 gauntlet dispatch),
- `analyze_vrp_factor_t122.py` (the T-122 factor analysis).

Each existed to run the refuted edge; with the edge archived, running them would re-propose a refuted
experiment, so they are archived rather than repointed (the brief's "or refuse").

## The one edit made at archive time

Each module's `from ..edge_base import EdgeBase` became the absolute
`from engines.engine_a_alpha.edge_base import EdgeBase`, so the modules still resolve from this path. The
reason is `scripts/build_signal_panel_b1.py`: its signal inventory is a FROZEN pre-registration (prereg §4,
§5.2; the B-1 decisive test, T-365, closed 2026-10-14) that names `overnight_intraday_v1` and
`betting_against_beta_v1`, and a pre-registered inventory is not edited after the fact. The builder's
`make_edges` now resolves those two entries from this archive path (a dotted module in the inventory) and
every other entry from `engines.engine_a_alpha.edges` as before. Nothing else imports from here.

The modules' import-time `EdgeRegistry().ensure(...)` blocks are untouched: since the single-writer unit,
`ensure()` registers in memory only and never writes, and `scripts/sync_edge_registry.py` collects only the
modules under `engines/engine_a_alpha/edges/`, so an import from this archive can never put these ids back
into `edges.yml`.

The contract test `tests/test_edge_classes_registered_or_archived.py` asserts that every edge class
reachable by import under `engines/engine_a_alpha/edges/` is either registered in `edges.yml` or named in
its explicit, pinned exception list — the class of defect these three were.
