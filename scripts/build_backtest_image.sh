#!/usr/bin/env bash
# scripts/build_backtest_image.sh <git-ref> [image-tag]
#
# T-2026-06-09-127: clean-source image build. NEVER builds from the live
# worktree.
#
# Why this exists — the failure class it kills (forensics: T-126/T-127):
#   * Builds used to run `docker build .` from a LIVE WORKTREE. Whatever
#     happened to be on disk got baked: uncommitted/stale tracked files,
#     untracked config backups, nested __pycache__ (incl. bytecode from a
#     different Python), .DS_Store. Two builds of the "same commit" on
#     different days produced different images → different trade canons →
#     a week of contradictory 26-yr baselines (T-109/T-125 vs T-126).
#   * The data substrate (data/processed, data/raw, data/governor) was
#     baked from the host with NO pin at all.
#
# What this script guarantees:
#   1. Code + config come from `git archive <ref>` — the COMMIT, not the
#      worktree. Untracked junk cannot leak in; dirty worktrees are
#      irrelevant by construction.
#   2. Data is staged from the host (symlinks followed) and VERIFIED
#      against the committed manifest config/substrate_manifest.sha256
#      (the manifest itself comes from the git archive, i.e. the reviewed
#      expectation at that commit). Drifted data = loud build failure.
#   3. The image is tagged with the commit sha and labeled with full
#      provenance (commit, substrate manifest md5, base digest from the
#      Dockerfile pin).
#
# Two builds of the same ref against manifest-clean data produce
# content-identical /app trees — the cross-day reproducibility T-126
# proved we didn't have.
#
# Usage:
#   scripts/build_backtest_image.sh HEAD                 # tag archondex-backtest:dev + :<short-sha>
#   scripts/build_backtest_image.sh 8103118 my:tag       # explicit tag
#
# Data root: data/ subdirs of the CURRENT worktree (symlinks followed, so
# agent worktrees that symlink data/ back to the director work unchanged).
set -euo pipefail

REF="${1:?usage: build_backtest_image.sh <git-ref> [image-tag]}"
SHA=$(git rev-parse --verify "${REF}^{commit}")
SHORT=$(git rev-parse --short "$SHA")
TAG="${2:-archondex-backtest:dev}"

STAGE=$(mktemp -d "${TMPDIR:-/tmp}/archondex_build.XXXXXX")
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

echo "[build] staging code+config from git archive @ $SHORT ($SHA)"
git archive "$SHA" | tar -x -C "$STAGE"

echo "[build] staging data substrate (symlinks followed, junk excluded)"
mkdir -p "$STAGE/data"
for d in processed raw; do
    rsync -aL \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
        "data/$d" "$STAGE/data/"
done
# T-2026-06-10-133: LIVE mutable governor files are NOT baked. T-131
# proved they are canon-irrelevant (isolated() restores every scoped
# file from _isolated_anchor/ ON ENTRY; edge_metrics/decision_diary are
# write-only observability, lazily re-created in-container). Excluding
# them removes the last image-content surface that varies with local
# run activity — images of the same commit are now byte-identical
# regardless of what ran in the worktree. The ANCHORS keep being baked:
# they are what the in-container harness executes from. Exclusion list
# mirrors LIVE_MUTABLE_GOVERNOR in scripts/gen_substrate_manifest.py.
# NOTE: patterns are ANCHORED ('/governor/<name>') — a bare 'edges.yml'
# would basename-match at any depth and strip _isolated_anchor/edges.yml,
# the very file the in-container harness restores from.
rsync -aL \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
    --exclude='/governor/edges.yml' --exclude='/governor/edge_weights.json' \
    --exclude='/governor/regime_edge_performance.json' \
    --exclude='/governor/lifecycle_history.csv' \
    --exclude='/governor/ga_population.yml' \
    --exclude='/governor/lifecycle_journal.jsonl' \
    --exclude='/governor/.journal_apply_mark' \
    --exclude='/governor/edge_metrics.json' \
    --exclude='/governor/decision_diary.jsonl' \
    "data/governor" "$STAGE/data/"

echo "[build] verifying substrate against committed manifest"
if [ ! -f "$STAGE/config/substrate_manifest.sha256" ]; then
    echo "[build] ERROR: commit $SHORT has no config/substrate_manifest.sha256." >&2
    echo "[build]        Pre-manifest commits must be built with an explicit override:" >&2
    echo "[build]        ARCHONDEX_SKIP_SUBSTRATE_VERIFY=1 (records UNVERIFIED provenance)." >&2
    if [ "${ARCHONDEX_SKIP_SUBSTRATE_VERIFY:-0}" != "1" ]; then
        exit 65
    fi
    SUBSTRATE_MD5="UNVERIFIED"
else
    python3 "$STAGE/scripts/gen_substrate_manifest.py" verify --root "$STAGE" \
        --manifest config/substrate_manifest.sha256
    SUBSTRATE_MD5=$(md5 -q "$STAGE/config/substrate_manifest.sha256" 2>/dev/null \
        || md5sum "$STAGE/config/substrate_manifest.sha256" | awk '{print $1}')
fi

BASE_DIGEST=$(grep -oE 'python:3\.14-slim@sha256:[a-f0-9]{64}' "$STAGE/Dockerfile.backtest" | head -1 || true)
echo "[build] base: ${BASE_DIGEST:-UNPINNED (pre-T-125 commit)}"

echo "[build] docker build"
docker build -f "$STAGE/Dockerfile.backtest" \
    --label "org.archondex.commit=$SHA" \
    --label "org.archondex.substrate-manifest-md5=$SUBSTRATE_MD5" \
    -t "$TAG" -t "archondex-backtest:sha-$SHORT" \
    "$STAGE"

echo "[build] DONE"
echo "  image:     $TAG (+ archondex-backtest:sha-$SHORT)"
echo "  commit:    $SHA"
echo "  substrate: $SUBSTRATE_MD5"
