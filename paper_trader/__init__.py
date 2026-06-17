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
from paper_trader.reconciliation import (
    ReconciliationEngine,
    ReconcileInputs,
    ReconcileResult,
    ReconcileFinding,
    ALL_CLASSES,
)
from paper_trader.scheduler import (
    PaperScheduler,
    DaySummary,
    DAILY_CLOCK,
    PR3_ENTRY_CRITERIA_CLOSED,
)
from paper_trader.paper_config import (
    PaperConfig,
    VALID_ALLOCATORS,
    load_designated_allocator,
)
from paper_trader.order_construction import PaperOrderConstructor, OrderSpec
from paper_trader.paper_telemetry import (
    DivergenceShadow,
    PromotionReport,
    RouterShadow,
    SafefWeeklyJob,
)
from paper_trader.market_calendar import MarketCalendar, now_et
from paper_trader.heartbeat import PaperHeartbeat, RunHeartbeat, HeartbeatVerdict

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
    "ReconciliationEngine",
    "ReconcileInputs",
    "ReconcileResult",
    "ReconcileFinding",
    "ALL_CLASSES",
    "PaperScheduler",
    "DaySummary",
    "DAILY_CLOCK",
    "PR3_ENTRY_CRITERIA_CLOSED",
    "PaperConfig",
    "VALID_ALLOCATORS",
    "load_designated_allocator",
    "PaperOrderConstructor",
    "OrderSpec",
    "DivergenceShadow",
    "PromotionReport",
    "RouterShadow",
    "SafefWeeklyJob",
    "MarketCalendar",
    "now_et",
    "PaperHeartbeat",
    "RunHeartbeat",
    "HeartbeatVerdict",
]
