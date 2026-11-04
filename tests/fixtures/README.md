# tests/fixtures

Real artifacts pulled from the live system, vendored so tests lock against what
the machine actually produces rather than against a hand-written idea of it.

- `agentic_note_2026-09-15.json` — one real agentic analyst note, from
  `s3://archondex-results-407539788432/paper_state/data/intel/analyst_notes_agentic/note_2026-09-15.json`.
  Used by `test_agentic_shadow_book_t355.py`. Its value is precisely that it was
  NOT written by a test author: a synthetic stand-in for this note passed the
  eye and failed `validate_note` with 10 errors, which is how a fixture quietly
  stops testing the real thing. No secrets (model ids, prompt hashes, token
  counts).
- `edges_registry_snapshot_2026_10_22.yml` — the real `data/governor/edges.yml`
  (218 rows, 59,244 bytes, sha256 `edf1ffaf…4380`) as it stood when the
  edges.yml single-writer unit cut over (2026-10-22). Used by
  `test_edge_registry_single_writer.py`: the byte-level migration lock (the one
  canonical serialiser, every writer and a sync all reproduce these bytes
  exactly) and the pure-import lock's "healthy registry" case. A hand-written
  registry would not carry the real file's key order, params and extras.
