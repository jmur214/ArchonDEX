"""paper_trader — the paper-trading loop (T-160, PR-1 + PR-2).

Pure-new package implementing §6 of
``docs/Core/paper_trading_readiness_design_t159.md``. It reuses the
production order-CONSTRUCTION path (Engine A → Engine C → Engine B,
wired in PR-3) and replaces only the EXECUTION layer with a real
order-state machine against Alpaca's PAPER endpoint.

PR-1 (this commit): OrderManager (lifecycle + OPG/CLS TIF + deterministic
client_order_id + append-only order journal), LedgerStore
(positions/cash as-we-believe), and the paper REST client.
PR-2: ReconciliationEngine (three-way diff + the §2 divergence taxonomy)
and the DRY-RUN daily scheduler.

NOTHING here imports engines/ or backtester/ (that is PR-3, propose-
first). No live-money endpoint appears anywhere in this package.
"""
from paper_trader.order_manager import (
    OrderManager,
    OrderRecord,
    OrderState,
    TimeInForce,
    make_client_order_id,
)
from paper_trader.ledger_store import LedgerStore, LedgerPosition
from paper_trader.paper_client import (
    AlpacaPaperClient,
    FakePaperClient,
    PaperClient,
)

__all__ = [
    "OrderManager",
    "OrderRecord",
    "OrderState",
    "TimeInForce",
    "make_client_order_id",
    "LedgerStore",
    "LedgerPosition",
    "AlpacaPaperClient",
    "FakePaperClient",
    "PaperClient",
]
