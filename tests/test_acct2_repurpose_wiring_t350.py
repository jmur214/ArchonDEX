# tests/test_acct2_repurpose_wiring_t350.py
"""T-350 Act 2 item 2 — the account-2 repurpose IN PLACE.

The load-bearing property is what does NOT change: key, secret, S3 prefix and
alarm names all stay, because a cosmetic rename touches IAM ARNs and the jobdef
binding — the deploy-drift class that produced the July outage. Only the strategy
moves. These tests lock that, and lock the transition script's one-shot shape.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = (ROOT / "scripts/run_paper_cloud_day.py").read_text()
PROV = (ROOT / "scripts/provision_paper_fleet.py").read_text()
TRANS = (ROOT / "scripts/transition_acct2_to_deploy_candidate_t350.py").read_text()


def test_the_runner_accepts_and_routes_the_new_strategy():
    assert '"deploy_candidate",' in RUNNER            # argparse choices
    assert 'elif args.strategy == "deploy_candidate":' in RUNNER
    assert "DeployCandidateConstructor(" in RUNNER


def test_the_new_strategy_rides_the_family_pipeline_everywhere():
    """Three separate call sites gate on the fleet strategy tuple; missing one
    silently drops the tracker or the exec gates for this account."""
    for frag in ('("offense_sso", "sleeve_btc", "llm_analyst", "deploy_candidate")',):
        assert RUNNER.count(frag) >= 2


def test_it_has_its_own_stream_token_and_tracker():
    assert '"deploy_candidate": "deploycand-a2"' in RUNNER
    assert "deploy_candidate_tracking.json" in RUNNER


def test_the_allocation_announces_itself_in_the_banner():
    """A config-driven weight that is only true in a JSON file is the
    silent-wrongness shape — the run must print what it is actually running."""
    i = RUNNER.index('elif args.strategy == "deploy_candidate":')
    j = RUNNER.index('elif args.strategy == "llm_analyst":', i)
    blk = RUNNER[i:j]                    # the WHOLE branch, not a fixed window
    assert "DEPLOY-CAND" in blk and "core_weight" in blk and "buy_band_q" in blk


# ---------------- the repurpose IN PLACE ----------------
def test_account_2_keeps_its_key_secret_and_alarm_names():
    """The whole point: only the STRATEGY changes. If the key ever moves, the IAM
    ARNs, the S3 prefix and the alarm names all move with it — the July class."""
    assert 'dict(key="offense-sso", strategy="deploy_candidate"' in PROV
    assert "REPURPOSED IN PLACE" in PROV


def test_the_offense_science_is_annotated_as_preserved_not_deleted():
    assert "damped_offense_t298" in PROV


def test_account_2_was_armed_DELIBERATELY_and_the_protocol_is_recorded():
    """Repurposing alone did not arm it. The account went live on 2026-09-11 at
    the Act-2 transition — after the legacy position was closed and the account
    verified flat — and the arming carries its protocol obligation in writing:
    an alarm is not trusted until a fresh ALARM→OK→ALARM transition is PROVEN."""
    i = PROV.index('strategy="deploy_candidate"')
    seg = PROV[i:i + 1200]
    assert "dormant=" not in seg                       # armed
    assert "ARMED 2026-09-11" in seg
    assert "ALARM→OK→ALARM" in seg and "PROVEN" in seg


# ---------------- the transition script ----------------
def test_the_transition_requires_an_explicit_execute_and_offers_a_dry_run():
    assert "--dry-run" in TRANS and "--execute" in TRANS
    assert "add_mutually_exclusive_group(required=True)" in TRANS


def test_it_snapshots_BEFORE_it_changes_anything():
    """Ordering asserted inside main(), not the whole file — the docstring
    mentions the steps too, so a whole-file index would pass on prose."""
    body = TRANS[TRANS.index("def main("):]
    assert body.index('print("1. SNAPSHOT') < body.index('2. CLOSE')
    assert body.index('2. CLOSE') < body.index('3. ARCHIVE')


def test_it_archives_rather_than_deletes():
    assert "NN-ARCHIVE" in TRANS
    assert "archive_offense_" in TRANS
    # the archive copy must precede the clear
    i = TRANS.index('aws("s3", "cp", src, dest')
    j = TRANS.index('aws("s3", "rm", src)')
    assert i < j


def test_it_does_NOT_deploy_the_lump_sum_itself():
    """The arrival event is a first artifact of the SCHEDULED firing, not a side
    effect buried in a migration script."""
    assert "does NOT deploy the lump sum" in TRANS
    assert "not run from here" in TRANS


def test_it_refuses_to_call_itself_complete_on_a_cap_mismatch():
    assert "MISMATCH — fix before arming" in TRANS and "return 70" in TRANS


def test_the_close_runs_through_the_accounts_own_jobdef_not_a_laptop():
    """The CLI user deliberately has no GetSecretValue; a migration is not a
    reason to cross that boundary."""
    assert "submit-job" in TRANS
    flat = " ".join(TRANS.split())          # the rationale is hard-wrapped
    assert "no GetSecretValue by design" in flat


# ---------------- item 3: the enforcing wash guard ----------------
def test_the_wash_guard_enforces_on_the_deploy_candidate_and_nothing_else():
    assert 'WASH_GUARDED_STRATEGIES = {"deploy_candidate"}' in RUNNER
    assert "wash_guard=om_wash" in RUNNER


def test_account_1_stays_byte_neutral_absent_from_the_guarded_set():
    """acct-1's gate-d record must stay byte-neutral for single-account Roth-only
    operation — a locked property, not a preference."""
    i = RUNNER.index("WASH_GUARDED_STRATEGIES")
    decl = RUNNER[i:i + 200]
    assert "trend_sleeve" not in decl


def test_a_guard_that_cannot_be_built_REFUSES_to_trade_unguarded():
    """An enforcing guard that silently becomes None is worse than no guard — the
    record would claim a protection it did not have."""
    i = RUNNER.index("om_wash = None")
    blk = RUNNER[i:i + 2200]
    assert "NN-FAIL-CLOSED" in blk and "refusing to trade unguarded" in blk
    assert "return 69" in blk


def test_the_acct1_coupling_is_documented_at_the_wiring_site():
    """REFRAMED T-358. This used to assert that the wiring site documented the
    coupling as a live fact — and it passed, because the comment said so. The
    comment was FALSE (audit A1): the guard is single-account, so drill 12
    cannot fire at all. A test that locks a claim, rather than the behaviour
    behind it, passes hardest exactly when the claim is wrong.

    The intent survives: a maintainer must meet the coupling situation before
    the guard is constructed. What must be documented is now the TRUTH — that
    it is not wired yet, and what it would take."""
    i = RUNNER.index("om_wash = None")
    blk = RUNNER[max(0, i - 3000):i + 200]
    assert "US_LARGE_BLEND" in blk
    assert "NOT CROSS-ACCOUNT YET" in blk
    assert "drill 12" in blk and "CANNOT fire" in blk


# ---------------- item 4: Rule-B contributions ----------------
def test_contributions_grow_only_on_WHOLE_months():
    from paper_trader.deploy_candidate_constructor import contributed_cap
    cfg = {"contributions": {"enabled": True, "monthly_usd": 583.0,
                             "start_date": "2026-09-11"}}
    assert contributed_cap(10_000.0, "2026-09-11", cfg)[0] == 10_000.0   # month 0
    assert contributed_cap(10_000.0, "2026-10-10", cfg)[0] == 10_000.0   # not yet
    assert contributed_cap(10_000.0, "2026-10-11", cfg)[0] == 10_583.0   # one month
    assert contributed_cap(10_000.0, "2026-12-11", cfg)[0] == 11_749.0   # three


def test_the_arrival_lump_sum_is_not_double_counted_as_a_contribution():
    """start_date IS the arrival date, so month 0 adds nothing."""
    import json
    cfg = json.loads((ROOT / "config/deploy_candidate.json").read_text())
    from paper_trader.deploy_candidate_constructor import contributed_cap
    start = cfg["contributions"]["start_date"]
    assert contributed_cap(10_000.0, start, cfg)[0] == 10_000.0


def test_a_broken_contributions_config_falls_back_to_the_BASE_cap():
    from paper_trader.deploy_candidate_constructor import contributed_cap
    for bad in ({}, {"contributions": {"enabled": True}},
                {"contributions": {"enabled": True, "monthly_usd": 583,
                                   "start_date": "nonsense"}}):
        cap, why = contributed_cap(10_000.0, "2026-12-11", bad)
        assert cap == 10_000.0 and "base cap only" in why


def test_the_uplift_is_STATED_every_run_never_silent():
    assert "contrib_why" in RUNNER and 'DEPLOY-CAND  {contrib_why}' in RUNNER
    from paper_trader.deploy_candidate_constructor import contributed_cap
    _, why = contributed_cap(10_000.0, "2026-12-11",
                             {"contributions": {"enabled": True, "monthly_usd": 583.0,
                                                "start_date": "2026-09-11"}})
    assert "no broker money moves" in why


def test_the_contribution_grown_cap_is_what_actually_sizes_the_book():
    assert "cap=(deploy_cap if deploy_cap is not None" in RUNNER
