# Data Lifecycle — local vs S3 retention

**Status:** active 2026-05-22 onward.
**Companion:** [`CLOUD_USAGE.md`](CLOUD_USAGE.md) (how to use the cloud); this doc covers what data lives where and for how long.

The Mac's local disk is a working set, not a permanent record. S3 is the permanent record. This doc spells out which directories belong on which side and the routine to keep the split tidy.

---

## What stays local (working set)

| Path | Purpose | Why it must stay local |
|---|---|---|
| `data/processed/` | Cleaned Alpaca bars (Parquet), substrate data | Every backtest reads this. Re-fetch from raw is hours of API calls. |
| `data/raw/` | Original Alpaca CSV downloads | Source-of-truth for `data/processed/`; small (~50 MB). |
| `data/governor/` | Live edge weights, lifecycle state, anchors | Engine F mutates this every backtest. Active state. |
| `data/observability/` | run_registry.sqlite | `scripts/metrics_report.py --since <date>` reads this. |
| `data/coordination/` | Inboxes/outboxes/queue | Three-session protocol runtime state. |
| `data/macro/`, `data/earnings/`, `data/insider/`, etc. | Small alternative-data caches | < 20 MB each; cheap to keep. |
| Recent `data/trade_logs/<run_id>/` (last 7-14 days) | Outputs from current measurement work | `metrics_report.py` + audit-doc cross-references pull from here. |

## What moves to S3 (archive)

| Path | Bucket | Trigger |
|---|---|---|
| `data/trade_logs/<run_id>/` older than 14 days | `s3://archondex-archives-407539788432/trade_logs/<yyyy>/<run_id>/` | Time-based |
| `data/research/*.parquet` from completed campaigns | `s3://archondex-archives-407539788432/research/<campaign>/` | Per-campaign at completion |
| `logs/*.log` files older than 7 days | `s3://archondex-archives-407539788432/logs/<yyyy_mm_dd>/` | Time-based (logs/ is local-only, not symlinked across worktrees) |
| Any `data/Archive_*` snapshot folders | `s3://archondex-archives-407539788432/data_archives/` | Already named "Archive" — move on next housekeeping pass |

## What goes to S3 results bucket (campaign outputs, not archive)

| Path | Bucket |
|---|---|
| Per-cell trade logs from cloud campaigns | `s3://archondex-results-407539788432/<launch_id>/<cell_id>/` (written automatically by `scripts/cloud_entrypoint.sh`) |

Results bucket is for cloud-campaign outputs the director will pull back. Archives bucket is for older-than-working-set local data we're moving off the Mac.

---

## Storage classes & cost

| Class | $/GB-month | Min storage | Use case |
|---|---:|---|---|
| STANDARD | $0.023 | none | Frequently-read data (don't use for archive) |
| STANDARD_IA | $0.0125 | 30 days | First archive destination — readable on-demand, ~half-price |
| GLACIER_IR (Instant Retrieval) | $0.004 | 90 days | Older archive, ms retrieval, no surcharge per read |
| DEEP_ARCHIVE | $0.00099 | 180 days | Cold storage; ~12 hr retrieval; 99% cheaper than STANDARD |

**Recommended lifecycle policy (one-time bucket setup):**
- Day 0 → upload as STANDARD_IA
- Day 90 → transition to GLACIER_IR
- Day 365 → transition to DEEP_ARCHIVE

Configure once via `aws s3api put-bucket-lifecycle-configuration` — see "Lifecycle policy" below.

**Sample cost @ 50 GB archived:**
- All in STANDARD_IA: ~$0.63/month
- After full transition (DEEP_ARCHIVE): ~$0.05/month
- For perspective: a single Discord Nitro is more.

---

## Routine commands

### Upload a single run_id's trade logs to archive

```bash
RUN_ID=<uuid>
aws s3 cp data/trade_logs/$RUN_ID/ \
  s3://archondex-archives-407539788432/trade_logs/2026/$RUN_ID/ \
  --recursive --storage-class STANDARD_IA \
  --profile archondex --region us-east-1
# Verify, then:
mv data/trade_logs/$RUN_ID ~/.Trash/
```

### Bulk-archive all trade_logs older than 14 days

```bash
# DO NOT RUN while Agent A or B has a backtest in flight — they may be
# writing to data/trade_logs/ (the dir is symlinked across all worktrees).
# Wait for both agents to report DONE before running.

find data/trade_logs -maxdepth 1 -mindepth 1 -type d -mtime +14 -print0 \
  | while IFS= read -r -d '' run_dir; do
      run_id=$(basename "$run_dir")
      year=$(stat -f "%Sm" -t "%Y" "$run_dir")
      aws s3 cp "$run_dir/" \
        "s3://archondex-archives-407539788432/trade_logs/$year/$run_id/" \
        --recursive --storage-class STANDARD_IA \
        --profile archondex --region us-east-1 --quiet \
      && mv "$run_dir" ~/.Trash/
    done
```

### Restore a single run_id from archive

```bash
RUN_ID=<uuid>
mkdir -p data/trade_logs/$RUN_ID
aws s3 cp s3://archondex-archives-407539788432/trade_logs/2026/$RUN_ID/ \
  data/trade_logs/$RUN_ID/ --recursive \
  --profile archondex --region us-east-1
# If the object is in GLACIER_IR or DEEP_ARCHIVE, run `aws s3api restore-object`
# first; STANDARD_IA reads immediately.
```

### List what's archived

```bash
aws s3 ls s3://archondex-archives-407539788432/trade_logs/2026/ \
  --profile archondex --region us-east-1 | head -20
```

---

## Lifecycle policy (one-time bucket setup)

**Status:** APPLIED 2026-05-22 to `archondex-archives-407539788432` via the PUT below. Read-back is currently blocked by the `claude-code-cli` IAM policy (missing `s3:GetLifecycleConfiguration`) — not blocking; the rule is in effect. Future IAM-policy update should add the GET action for visibility.

Run once after the bucket is in active use. After this, S3 auto-transitions objects through the cheaper classes without any further action:

```bash
cat > /tmp/archives_lifecycle.json << 'EOF'
{
  "Rules": [{
    "ID": "archive-tiering",
    "Status": "Enabled",
    "Filter": {"Prefix": ""},
    "Transitions": [
      {"Days": 90,  "StorageClass": "GLACIER_IR"},
      {"Days": 365, "StorageClass": "DEEP_ARCHIVE"}
    ]
  }]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket archondex-archives-407539788432 \
  --lifecycle-configuration file:///tmp/archives_lifecycle.json \
  --profile archondex --region us-east-1
```

---

## Sharing constraint (CRITICAL)

`data/trade_logs/`, `data/research/`, `data/processed/`, `data/raw/`, and other `data/*` subdirs in the director's worktree are **symlinked from each agent worktree** (verified 2026-05-22). Moving or deleting files in any of these dirs affects all three sessions immediately.

**Rule:** never modify `data/trade_logs/`, `data/research/`, `data/processed/`, or `data/raw/` while any agent has a backtest in flight. Wait for `DONE` in both agent outboxes before running the bulk-archive command above.

`logs/` (top level, not under `data/`) is director-only and not symlinked — safe to clean any time.

---

## Restart safety

If the user wants to restart the Mac mid-archive: `aws s3 cp` is resumable for multipart uploads but not for the dir-recurse loop above. Each per-run-id upload is small (~10-50 MB typically) and the loop can be re-run safely — already-uploaded run_ids will be re-uploaded (cheap, idempotent) unless you add `--no-overwrite` or check existence first. The `mv ~/.Trash/` step is what makes the local copy go away, so resuming from interruption is safe.
