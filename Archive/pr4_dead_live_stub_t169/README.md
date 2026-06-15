# Archived: the dead live-trading stub (PR-4, T-2026-06-15-169)

These three files were the pre-`paper_trader/` live-execution stub. They
were dead and partly non-functional; the real order path is now the
`paper_trader/` package (an order-state machine with broker-truth
reconciliation, T-160/163). Archived per CLAUDE.md (never delete).

- **`live_trader/`** (`broker_interface.py`, `live_controller.py`) — a
  64-line stub: fire-and-forget `gtc` MARKET orders (not OPG/CLS), no
  `client_order_id` idempotency, sized via the dead Path B (bypassed the
  whole Engine C chain), and it never routed exits. See the T-159 gap
  inventory (`docs/Core/paper_trading_readiness_design_t159.md`).
- **`state_manager.py`** (was `storage/state_manager.py`) — a single
  cash/positions/open_orders JSON blob trusted blindly; only ever
  imported by the archived `live_controller.py`. Superseded by
  `paper_trader/ledger_store.py` (belief-only, append-only, defensive
  read-back) + the order journal.
- **`alpaca_broker.py`** (was `brokers/alpaca_broker.py`) — read
  `ALPACA_API_SECRET`, a name that does NOT exist in `.env`
  (`ALPACA_SECRET_KEY`), so it could never authenticate (health_check
  MEDIUM, found in T-160). Its only consumer was the never-constructed
  `AlpacaExecutionAdapter` in `mode_controller` (the synthetic-fill
  anti-pattern — fabricated fills at intended prices), now deprecated.
  Superseded by `paper_trader/paper_client.py` (paper-pinned, tri-state
  error classifier).

Do not resurrect. The order path is `paper_trader/`.
