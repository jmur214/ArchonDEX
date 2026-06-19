# T-188 — Dashboard data-layer API contract + design spec (React/Next.js ← FastAPI)

**Date:** 2026-06-17
**Agent:** C (branch `feature/dashboard-api-contract-t188`)
**Status:** DESIGN SPEC ONLY — **no FastAPI/React code** (the build is gated on the user's visual/IA approval). This is the look-INDEPENDENT backbone: what data exists, the endpoints + schemas that expose it, what's real-time, which Dash loaders to port, and what's locked vs IA-dependent.

The React app will NOT read files directly (the current Dash app does). It talks to a thin, **read-only** FastAPI layer that wraps the existing Python data-loading. This decouples the front-end from on-disk formats and is the one piece we can lock now.

---

## 0. Architectural decisions (lock these first)
1. **Read-only by construction.** Every endpoint READS files / sqlite / computes a metric. NONE trade, mutate engine state, or write governor files. (Edge status mutation, discovery triggers, etc. are explicitly OUT of scope for v1 — the dashboard observes; the autonomous loop acts.)
2. **Reuse the Python loaders, not the Dash UI.** Port `cockpit/dashboard_v2/utils/*_loader.py` into a shared `dashboard_api/loaders/` package that BOTH the (legacy) Dash app and the new FastAPI import. One data-loading source of truth; the rebuild replaces only the view layer. (§4.)
3. **Localhost-bound, same trust model as the Dash app** (`127.0.0.1`, no LAN). If the React app is served separately, add a single allow-listed CORS origin; no auth in v1 (local single-user). Flag if the user wants remote access → then auth is required (IA-dependent, §5).
4. **Nothing here is genuinely streaming.** The paper loop is **daily/batch**; backtests are discrete. "Real-time" = *file-mtime-changed* push, not a tick stream. SSE on the Live surface is a UX nicety over a 2–5s poll, NOT a market feed. Stated honestly so we don't over-engineer a websocket tier (§3).
5. **One canonical metric path.** Sharpe/MDD/CAGR are recomputed from equity per CLAUDE.md `[NN-SHARPE-CI]` (the `core.metrics_engine` + `core.combined_candidate_scorecard` path); the API never re-derives metrics ad-hoc — it serves what the producers wrote + what those modules compute.

---

## 1. Data catalog — what the system already produces

Legend: **cadence** = how often it changes; **rt** = a dashboard wants near-real-time (mtime-push) vs request/response.

### Research / performance
| source | path | format | key fields | producer | cadence | rt |
|---|---|---|---|---|---|---|
| Per-run perf summary | `data/trade_logs/<uuid>/performance_summary.json` | JSON | `Sharpe Ratio`,`CAGR (%)`,`Max Drawdown (%)`,`Total Trades`, `bootstrap_distribution{sharpe,sortino:{ci_low,ci_high,point_estimate}}`, **`census{…}`** (T-181), `after_tax_detail`, `safe_f`/`safef_detail`, `divergence_detail`, `cost_completeness_layer_v1`, `path_a_modules` | `backtest_controller._compute_summary` + `_build_census` | per backtest | no |
| Run registry | `data/observability/run_registry.sqlite` | SQLite | `run_id, sharpe, cagr, max_drawdown, win_rate, psr, sortino, n_trades, engine_{a..f}_version, perf_summary_path, snapshot_at` | `core/observability/run_registry.py --rebuild` | per run | no |
| Equity / trades | `data/trade_logs/<uuid>/{portfolio_snapshots.csv,trades.csv}` | CSV | snapshots: `timestamp,equity,cash,positions,peak_equity,current_drawdown_pct,gross_notional,sleeve_equity,run_id`; trades: `timestamp,ticker,side,qty,fill_price,commission,pnl,edge,edge_id,trigger,regime_label,run_id` | `cockpit/logger.py` | per run | no |
| Anchors | `docs/State/CURRENT_STATE.md` table + `data/governor/_isolated_anchor/` | MD table / files | per window: `canon_md5, sharpe, ci_low, cagr, mdd` (2022 `eb48742e`/1.512; 16yr `3e9ea427`/1.162/0.676; 26yr `158fe678`/0.751/0.382) | `run_isolated.save_anchor` (chmod 0o444) | rare | no |
| Combined-candidate scorecard | `core/combined_candidate_scorecard.py` (computed; no fixed store) | dataclass→dict | `build_scorecard(base)→{proxy:[ScorecardRow]}`; ScorecardRow: `label,n_days,start,end,sharpe,ci_low,ci_high,maxdd_pct,cagr_pct,ann_vol_pct` | T-176 | on demand (slow: bootstrap) | no |

### Paper / live (T-160/163/169/185/186)
| source | path | format | key fields | producer | cadence | rt |
|---|---|---|---|---|---|---|
| **Heartbeat** (dead-man's-switch) | `data/state/paper_heartbeat.json` | JSON (atomic rewrite) | `last_run{run_date,run_ts,canonical,reason,reconcile_clean_cycles,reconcile_total_cycles,halted,submitted,fills,account_flat,census_failures}, alert, alert_reason, updated_ts, _schema:"paper_heartbeat/v1"` | `paper_trader/heartbeat.py` | per trading day | **YES** |
| Alert log | `data/state/paper_alerts.log` | text (append) | `"{ISO}  {msg}"` | heartbeat | per alert | **YES** |
| Order journal | `data/paper_state/orders.jsonl` | JSONL (append) | `client_order_id,trade_date,ticker,side,qty,tif,state∈{staged,submitted,acked,partially_filled,filled,rejected,expired,canceled},broker_order_id,filled_qty,filled_avg_price,last_broker_status,history[],event` | `paper_trader/order_manager.py` | per order event | **YES** |
| Ledger (belief) | `data/paper_state/ledger.jsonl` | JSONL (append) | `cash,positions{tkr:{qty,avg_price}},realized_pnl,seq,event,account` | `paper_trader/ledger_store.py` | per fill | **YES** |
| Reconciliation log | `data/paper_state/recon.jsonl` | JSONL (append) | `trade_date,step,clean,halt,counts{class:int},findings[{klass,action,halt,manual,ticker,detail}]` | `paper_trader/reconciliation.py` | per cycle (3–5/day) | **YES** |
| Cloud mirror (T-186) | `s3://$BUCKET/$PREFIX/` of the 5 durable files + CloudWatch `ArchonDEX/PaperLoop{PaperRunHappened,PaperRunCanonical}` | S3 / metrics | same files, pushed per cloud run | `scripts/run_paper_cloud_day.py` + `CloudState` | per cloud run | poll |
| §5 scorecard | `docs/State/paper_run_scorecard.md` | MD table | 6 criteria + status (trading days, auction fills, slippage vs T-146, reconcile clean-rate, monitor FA, kill violations) | manual + paper run | per update | no |
| Promotion telemetry | `paper_trader/paper_telemetry.py` (in-memory `PromotionReport`) | dataclass | `slippage_bps[], rejects{}, divergence_z[], n_trading_days, n_fills, reconcile_*` + `promotion_criteria{duration_ok,slippage_ok,reconcile_ok}` | T-152/169 | per run | no |

> ⚠️ **Account snapshot (equity/cash/positions) is NOT persisted** as a standalone file — only the heartbeat summary (`submitted/fills/account_flat`) + the ledger belief survive. An endpoint that wants live broker equity must read the ledger (belief) + note it's belief, or the paper loop must persist the Alpaca `get_account()` snapshot (recommend the loop write `data/paper_state/account.json` per cycle — a Phase-2 ask to the paper-loop owner).

### Discovery / governance / system
| source | path | format | key fields | producer | cadence | rt |
|---|---|---|---|---|---|---|
| Edge registry | `data/governor/edges.yml` | YAML | per edge: `edge_id,category,module,version,params,status∈{active,paused,retired,archived,candidate},tier∈{alpha,feature,context},regime_gate,combination_role,failure_reason,superseded_by,extra` | Engine F + Discovery | per lifecycle decision | no |
| Edge weights | `data/governor/edge_weights.json` (+ `edge_weights_history.csv`) | JSON/CSV | `{edge_id: weight∈[0,1]}` | Engine F | per reweight | no |
| Edge metrics | `data/governor/edge_metrics.json` | JSON | per edge: `trade_count,sr,sortino,mdd,current_dd,corr_penalty` | `governor.update_from_trade_log` | per eval | no |
| Regime-edge attribution | `data/governor/regime_edge_performance.json` | JSON v2 | `{_version:2, data:{…}, trigger_data:{…}}` per-edge×per-regime | Governor (from `trades.csv.regime_label`) | per eval | no |
| Lifecycle history | `data/governor/lifecycle_history.csv` | CSV | `timestamp,edge_id,old_status,new_status,triggering_gate,edge_sharpe,benchmark_sharpe,edge_mdd,trade_count,days_active,notes` | `governor.evaluate_lifecycle` | per decision | no |
| Decision diary | `data/governor/decision_diary.jsonl` | JSONL | `timestamp,decision_type,what_changed,expected_impact,actual_impact,rationale_link,extra{}` | `core/observability.append_entry` | per decision | no |
| Genome registry | `data/governor/genome_registry.json` | JSON | discovery genomes (verify shape at build) | Engine D | per cycle | no |
| Discovery log | `data/research/discovery_log.jsonl` | JSONL | hunt/GA/validation/cycle events (⚠️ **schema not fully verified** — confirm fields against the writer before locking) | Engine D | per cycle | no |
| Feature foundry | `core/feature_foundry/model_cards/*.yml` | YAML | `feature_id,source_url,license,point_in_time_safe,status,ablation_history` | Feature Foundry | per ablation | no |
| Regime CURRENT state | **not persisted** — `regime_detector.detect_regime()` returns it live (5 axes + hmm + advisory + macro_regime) | dict | see §catalog below | Engine E | per bar (live only) | — |
| System state | `data/governor/system_state.json` | JSON | engine/system state (verify shape) | F | per run | no |
| Health check | `docs/State/health_check.md` | MD | active/resolved issues by severity+engine | human + `sync_docs` | per session | no |
| Live-state dashboard | `docs/State/CURRENT_STATE.md` | MD | anchors, hard caps, last-reconciled stamp | human/hooks | per change | no |
| Divergence monitors | embedded in `performance_summary.json.divergence_detail` | JSON | `cusum_mean/cusum_var/page_hinkley{n_obs,n_alarms,alarms_per_year,alarm_dates}, operating_points` | `backtester/divergence_monitors.py` | per backtest | no |
| Allocation recs | `data/research/allocation_recommendations.json*` (T-162 held, **stale 2026-04 artifact**) | JSON | per-regime `params/metrics/score` | Engine C/F | inactive | no |

**Key catalog takeaways for the contract:**
- The single richest object is `performance_summary.json` (metrics + census + tax + safe_f + divergence) — most Research/System endpoints are projections of it (and of the `run_registry` index over many of them).
- **Regime current-state has no on-disk home** — a real contract decision (§5).
- **Nothing streams.** The "real-time" surfaces are 5 paper files whose freshness a dashboard wants to reflect within seconds of the daily run — mtime-push, not a feed.

---

## 2. FastAPI endpoints + schemas, by surface

Conventions: all `GET`, JSON, read-only. `200` + payload, or `200` + `{"available": false, "reason": "..."}` for graceful-missing (NEVER 500 on absent data — the dashboard renders a pending state, mirroring the T-182 loaders). Response schemas below are sketches (field → type); the build pins them as Pydantic models.

### 2.1 LIVE surface (paper run + integrity — the "is it running + clean" view)
| endpoint | backing source | response (sketch) | rt |
|---|---|---|---|
| `GET /api/live/health` | newest census-bearing `performance_summary.json` via `core.census.assert_census_file` | `{canonical:bool, census_present:bool, failures:[str], warnings:[str], run_path:str, census:{edges_blind,fundamentals_blind,regime_unknown_frac,n_trades,n_in_panel,n_resolved,config_provenance.degraded}}` | **SSE** |
| `GET /api/live/heartbeat` | `data/state/paper_heartbeat.json` | the heartbeat schema verbatim + `alive:bool` (derived: trading-day & canonical & fresh) | **SSE** |
| `GET /api/live/paper` | `paper_state/{ledger,orders,recon}.jsonl` (last records) | `{persisted:bool, ledger:{cash,positions,realized_pnl,seq}, open_orders:[{ticker,side,qty,state,filled_qty}], last_reconcile:{clean,halt,findings[]}, clean_rate}` | **SSE** |
| `GET /api/live/deploy-bar` | `core.combined_candidate_scorecard.build_scorecard(base)` over paper equity (or backtest base, labelled) | `{base_source,is_backtest_base, blocks:{proxy:[{label,sharpe,ci_low,maxdd_pct,cagr_pct}]}}` | poll (cached by mtime) |
| `GET /api/live/scorecard` | `docs/State/paper_run_scorecard.md` (parsed) | `{found, rows:[{metric,target,status,verdict}], as_of}` | poll |
| `GET /api/live/alerts?n=50` | `data/state/paper_alerts.log` (tail) | `{alerts:[{ts,msg}]}` | **SSE** |

### 2.2 RESEARCH surface (backtests, anchors, attribution, compare)
| endpoint | backing | response (sketch) | 
|---|---|---|
| `GET /api/research/runs?limit&sort` | `run_registry.sqlite` | `{runs:[{run_id,sharpe,cagr,max_drawdown,n_trades,snapshot_at,engine_versions}]}` |
| `GET /api/research/runs/{run_id}` | that run's `performance_summary.json` | full summary (incl census, bootstrap, after_tax, safe_f, divergence) |
| `GET /api/research/runs/{run_id}/equity` | `portfolio_snapshots.csv` | `{dates:[…], equity:[…], drawdown:[…], gross_notional:[…]}` (down-sampled) |
| `GET /api/research/runs/{run_id}/trades?edge&regime` | `trades.csv` | filtered trade rows |
| `GET /api/research/anchors` | CURRENT_STATE table (or a small anchors.json if we add one) | `{anchors:[{window,canon_md5,sharpe,ci_low,cagr,mdd}]}` |
| `GET /api/research/attribution` | `regime_edge_performance.json` + `edge_metrics.json` | `{by_edge:{…}, by_edge_x_regime:{…}}` (A's T-187 is the canonical attribution producer — align the response to its output; see §5) |
| `GET /api/research/compare?run_a&run_b` | two summaries | side-by-side metric deltas |

### 2.3 DISCOVERY surface (GA / lifecycle / foundry)
| endpoint | backing | response (sketch) |
|---|---|---|
| `GET /api/discovery/log?limit` | `discovery_log.jsonl` (⚠ verify schema) | paginated discovery events |
| `GET /api/discovery/lifecycle` | `lifecycle_history.csv` | status-transition timeline |
| `GET /api/edges` | `edges.yml` + `edge_weights.json` + `edge_metrics.json` (joined) | `{edges:[{edge_id,status,tier,category,weight,sr,sortino,mdd,trade_count,regime_gate,failure_reason}]}` |
| `GET /api/edges/{edge_id}` | joined per-edge | single edge detail + lifecycle history slice |
| `GET /api/discovery/genomes` | `genome_registry.json` | candidate genomes (verify) |
| `GET /api/foundry/features` | `core/feature_foundry/model_cards/*.yml` | `{features:[{feature_id,license,point_in_time_safe,status}]}` |

### 2.4 SYSTEM surface (engine health, governor, regime, logs)
| endpoint | backing | response (sketch) | rt |
|---|---|---|---|
| `GET /api/system/health` | `health_check.md` (parsed) + `CURRENT_STATE.md` caps | `{issues:[{severity,engine,status,description}], caps:{…}, last_reconciled}` | no |
| `GET /api/system/regime/current` | **decision needed** (§5): compute live, or read newest run's last-bar regime, or a new persisted snapshot | the `detect_regime()` schema (5 axes + hmm + macro_regime + advisory) | poll |
| `GET /api/system/governor` | `edge_weights.json` + `decision_diary.jsonl` (recent) | `{weights:{…}, recent_decisions:[…]}` |
| `GET /api/system/macro/{ticker}` | `data/macro/<ticker>.parquet` | `{dates:[…], values:[…]}` |
| `GET /api/system/divergence` | newest summary `divergence_detail` | the divergence block |
| `GET /api/system/diary?type&limit` | `decision_diary.jsonl` | filtered diary entries |

---

## 3. Real-time list (SSE vs request/response)
**Use SSE (server-sent events, mtime-watched push) for exactly the LIVE-surface integrity signals** — they're the ones a watcher leaves open and wants to flip the instant the daily paper run lands:
- `/api/live/health` (census canonical/non-canonical), `/api/live/heartbeat`, `/api/live/paper`, `/api/live/alerts`.

**Everything else is request/response** (the React app fetches on navigation / a manual refresh). Rationale (decision #4): the paper loop is **daily batch** — there is no sub-second data. SSE here is "push when `paper_heartbeat.json`/`recon.jsonl` mtime changes," implemented with a single filesystem watcher (watchdog) fanning out to subscribers. **Do NOT build a websocket/market-tick tier** — there's no tick data to carry, and the cloud variant (T-186) already surfaces liveness via CloudWatch alarms. If/when an intraday paper loop exists, revisit. A 2–5s poll is an acceptable v1 fallback if SSE slips.

---

## 4. Dash `utils/*_loader.py` logic worth PORTING (reuse the data layer, drop the Dash UI)
The rebuild keeps the **Python data-loading**; only the view changes. Port these into `dashboard_api/loaders/` (pure functions returning dataclasses/dicts — already the idiom), then both FastAPI and the legacy Dash app import them:
| Dash loader | what it does | port priority | note |
|---|---|---|---|
| `cockpit/dashboard_v2/utils/paper_loader.py` (my **T-182**) | census banner (`load_census`), paper run (`load_paper_run`), §5 scorecard parse (`load_scorecard_criteria`), equity-vs-robo (`load_equity_vs_robo`) — already graceful-missing dataclasses | **HIGH — backs the entire LIVE surface** | ⚠️ **repoint `PAPER_DIR`**: it currently targets the guessed `data/paper/latest/`; the REAL T-185 paths are `data/paper_state/{ledger,orders,recon}.jsonl` + `data/state/paper_heartbeat.json`. The port MUST add heartbeat reading + fix the paths. |
| `cockpit/dashboard_v2/utils/capital_allocation_loader.py` | per-run trades/edges joins, rolling views (pure pandas) | MED | backs Research attribution |
| `cockpit/dashboard_v2/utils/chart_helpers.py` | down-sampling / figure-data shaping | MED — keep the DATA-shaping, drop plotly figure objects | FastAPI returns series arrays; the React app renders. Strip the `go.Figure` construction; keep the transforms. |
| `cockpit/dashboard_v2/utils/datamanager.py` | run-dir discovery, trade-log reads | MED | overlaps run_registry; prefer the sqlite index for listing |
| `cockpit/dashboard_v2/utils/feature_foundry_loader.py` | model-card reads | LOW | backs Discovery/foundry |
| `core/observability/run_registry.py` | the sqlite index (already a clean Python API) | **HIGH — reuse as-is** | Research `runs` list/detail |
| `core/census.py` (my T-181) + `core/combined_candidate_scorecard.py` (my T-176) | the gate + the deploy-bar metric | **HIGH — import directly** | already pure, no Dash coupling |

**Anti-pattern to avoid:** do NOT let FastAPI endpoints read files inline — route every read through a ported loader so the Dash app and the API can't drift (this is the same producer/consumer-contract discipline that the T-090/T-181 contract tests enforce; a `tests/test_dashboard_loaders.py` should assert each endpoint's response keys ⊆ its loader's output).

---

## 5. Locked vs IA-dependent (what the user's design decision can still change)
**LOCKED (look-independent — safe to build against now):**
- The data catalog (§1) and which file backs which concept.
- The 4-surface split (Live/Research/Discovery/System) — these mirror data producers, not aesthetics.
- The LIVE-surface SSE set (§3) and the graceful-missing contract (§0).
- Reusing the ported loaders + run_registry + census + combined_candidate_scorecard (§4).

**IA-DEPENDENT / TBD (flag — a user IA choice changes the contract):**
1. **Surface granularity / nav.** If the user's IA merges or splits surfaces (e.g., a single "Live" landing vs separate Paper/Health tabs), endpoint *grouping* changes, not the underlying loaders. Cosmetic to the contract.
2. **`/api/system/regime/current` source** — the one genuine gap: regime has no persisted home. Three options, user/architecture to pick: (a) compute live in the API (imports Engine E + needs the data panel → heavyweight, slow first-call); (b) read the newest run's **last-bar** regime from its logged `market_state` (cheap, but as-of-last-backtest, not now); (c) have the paper loop persist a `data/state/regime_snapshot.json` each cycle (cleanest, but a Phase-2 ask to the paper-loop owner). **Recommend (c)**; until then (b) as a labelled fallback.
3. **Live account equity** — not persisted (§1 ⚠). If the IA wants a live equity number (not just the ledger belief), the paper loop must persist the Alpaca `get_account()` snapshot (`data/paper_state/account.json`). Phase-2 ask; until then show ledger belief + a "belief, not broker-confirmed" label.
4. **Attribution shape** — `/api/research/attribution` should serve **A's T-187** per-edge×per-regime output; its exact schema is A's deliverable. **Coordinate with A** before pinning this response model (catalog has the current `regime_edge_performance.json` v2 shape as the interim).
5. **Auth / remote access** — v1 assumes localhost single-user (no auth). If the user wants to view it off-box, add auth + TLS (changes the deployment contract, not the data schemas).
6. **Discovery log schema** — `discovery_log.jsonl`'s field set was not fully verified against its writer; confirm before pinning `/api/discovery/log`.
7. **Write actions** — v1 is read-only. If the IA wants in-dashboard controls (pause an edge, trigger a discovery cycle, arm the paper loop), that's a separate, security-sensitive POST contract (touches Engine F / live_trader → propose-first, NOT this spec).

---

## 6. Recommended build sequence (when design is approved — for the director's planning)
1. `dashboard_api/loaders/` — port paper_loader (repointed), wrap run_registry/census/combined_scorecard. + `tests/test_dashboard_loaders.py` (response⊆loader contract).
2. LIVE surface first (it's the going-live priority + reuses T-182 wholesale) — 6 endpoints + the SSE watcher.
3. Research surface (run_registry + per-run projections).
4. System + Discovery surfaces.
5. Resolve the 3 Phase-2 data gaps in parallel (regime snapshot, account snapshot, T-187 attribution) with the paper-loop / Engine-A owners.

No FastAPI/React code in this task per the dispatch — this spec is the contract the build implements once the user approves the look/IA.
