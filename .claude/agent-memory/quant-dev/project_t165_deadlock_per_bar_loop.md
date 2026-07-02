---
name: project-t165-deadlock-per-bar-loop
description: The T-165 in-process harness deadlock lives in BacktestController's per-bar loop (threaded logger-flush), not in data-load — so an execution-only replay does NOT avoid it.
metadata:
  type: project
---

The T-165 deadlock (symptom: 0% CPU, process state Ss, log frozen mid-backtest) hangs INSIDE `BacktestController.run`'s per-bar loop, not in the data-load/signal-load stage. The loop carries threading machinery that can wedge: `flush_logger_with_timeout` spawns daemon threads (`backtester/backtest_controller.py:919` and `:1362`), `time.sleep(0)` yields, periodic `gc.collect()`, and a KeyboardInterrupt handler that joins daemon threads (`:1554`).

Hit by: T-230's deployable ON backtest (local), T-211's "tractable 6yr" composition re-runs (both deadlocked). The director's "6yr is tractable locally" assumption did NOT hold on re-run.

**Implication for replay plans:** any execution-only replay that reuses the REAL execution code drives this SAME loop → hits the SAME deadlock. A replay does not dodge it. It's a latent infra bug worth fixing (the threaded flush + gc + sleep mix), but orthogonal to producing a deployable curve.
