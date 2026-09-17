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
