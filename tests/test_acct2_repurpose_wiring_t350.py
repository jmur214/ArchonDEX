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
    blk = RUNNER[i:i + 2000]
    assert "DEPLOY-CAND" in blk and "core_weight" in blk and "buy_band_q" in blk


# ---------------- the repurpose IN PLACE ----------------
def test_account_2_keeps_its_key_secret_and_alarm_names():
    """The whole point: only the STRATEGY changes. If the key ever moves, the IAM
    ARNs, the S3 prefix and the alarm names all move with it — the July class."""
    assert 'dict(key="offense-sso", strategy="deploy_candidate"' in PROV
    assert "REPURPOSED IN PLACE" in PROV


def test_the_offense_science_is_annotated_as_preserved_not_deleted():
    assert "damped_offense_t298" in PROV


def test_account_2_stays_dormant_until_the_arming_protocol_runs():
    """Repurposing does not arm it — the alarms stay suppressed-with-reason until
    the drill-3 ALARM→OK→ALARM protocol is run at arming."""
    i = PROV.index('strategy="deploy_candidate"')
    assert "dormant=" in PROV[i:i + 900]


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
