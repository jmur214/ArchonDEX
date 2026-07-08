#!/usr/bin/env bash
# scripts/build_paper_image.sh <git-ref> <full-ecr-ref> (T-186-exec)
#
# Sanctioned build for the LEAN paper-loop image (Dockerfile.paper). Same
# provenance discipline as build_backtest_image.sh — code+config come from
# `git archive <commit>`, NOT the live worktree, so uncommitted/stale files
# and host __pycache__ cannot leak in. Difference: NO data substrate is
# staged or baked (the paper loop reads none of it), so the image is small
# and builds on a tight disk where the full backtest image cannot.
#
# Registry-direct push only (streams layers to ECR without a local unpack).
# Requires a prior `aws ecr get-login-password | docker login`.
#
# Usage:
#   scripts/build_paper_image.sh HEAD \
#     407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:paper-sha-<short>
set -euo pipefail

REF="${1:?usage: build_paper_image.sh <git-ref> <full-ecr-ref>}"
TAG="${2:?usage: build_paper_image.sh <git-ref> <full-ecr-ref>}"
SHA="$(git rev-parse --verify "${REF}^{commit}")"
SHORT="$(git rev-parse --short "$SHA")"
case "$TAG" in */*) : ;; *) echo "[paper-build] ERROR: TAG must be a full registry ref" >&2; exit 70;; esac

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/archondex_paper_build.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

echo "[paper-build] staging code+config from git archive @ $SHORT ($SHA) — no data substrate"
git archive "$SHA" | tar -x -C "$STAGE"
[ -f "$STAGE/Dockerfile.paper" ] || { echo "[paper-build] ERROR: commit $SHORT has no Dockerfile.paper" >&2; exit 65; }

# T-290c: the ONE data file the paper image needs — the PIT S&P-500 membership
# panel that build_news_panel_t289.full_universe() reads. git-archive cannot
# carry it (data/ is gitignored + symlinked), so stage it explicitly.
# FAIL-CLOSED: without it full_universe() silently collapses to the ~10
# (mostly delisted) special-sits and the news step reports n_new=0 FOREVER while
# `degraded` reads False. Never build an image that would lie that way.
PIT_REL="data/universe/sp500_membership_pit.parquet"
PIT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/$PIT_REL"
[ -f "$PIT_SRC" ] || {
    echo "[paper-build] ERROR: missing $PIT_REL — the news universe would collapse" \
         "to the special-sits fallback (n_new=0 forever). Refusing to build." >&2
    exit 66
}
mkdir -p "$STAGE/$(dirname "$PIT_REL")"
cp "$PIT_SRC" "$STAGE/$PIT_REL"
echo "[paper-build] staged $PIT_REL ($(wc -c < "$PIT_SRC" | tr -d ' ') bytes, sha256 $(shasum -a 256 "$PIT_SRC" | cut -c1-16)…)"

echo "[paper-build] docker build (registry-direct, linux/arm64)"
# --platform arm64: the Fargate fleet is ARM64 (same as the backtest infra).
# --provenance/--sbom=false: attestation manifests confuse Fargate's pull.
docker build -f "$STAGE/Dockerfile.paper" \
    --platform "${ARCHONDEX_PLATFORM:-linux/arm64}" \
    --provenance=false --sbom=false \
    --label "org.archondex.commit=$SHA" \
    --label "org.archondex.image-variant=paper-loop" \
    -t "$TAG" \
    --push \
    "$STAGE"

echo "[paper-build] DONE"
echo "  image:  $TAG"
echo "  commit: $SHA"
