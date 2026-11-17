#!/usr/bin/env bash
# Test stub for the ops scripts — NEVER calls AWS. Maps s3://<bucket>/<key> to $FAKE_S3/<key>,
# serves `scheduler get-schedule` from the JSON file $FAKE_SCHED, and answers
# `batch describe-job-definitions` with "$FAKE_REV<TAB>$FAKE_IMAGE".
# FAKE_FAIL injects ONE fault:
#   read_live    a read (`s3 cp <live key> -`) of a key under $PFX/data/ is denied
#   mv           every `s3 mv` is denied (the DeleteObject case)
#   corrupt_copy an s3→s3 copy into an archive_* prefix writes different bytes
#   etag_wrong   head-object reports a wrong ETag for keys under archive_* prefixes
#   head_denied  every head-object is AccessDenied (absence cannot be proven)
#   corrupt_mv   every `s3 mv` lands different bytes at the destination
#   none         no fault (default)
set -u
pos=(); query=""; key=""; recursive=0
while [ $# -gt 0 ]; do
  case "$1" in
    --profile|--region|--output|--bucket|--name|--job-definition-name|--status) shift 2 ;;
    --query) query="$2"; shift 2 ;;
    --key) key="$2"; shift 2 ;;
    --recursive) recursive=1; shift ;;
    --no-progress) shift ;;
    *) pos+=("$1"); shift ;;
  esac
done
FAULT="${FAKE_FAIL:-none}"
loc() { local k="${1#s3://}"; echo "$FAKE_S3/${k#*/}"; }        # s3://bucket/key -> local path
keyof() { local k="${1#s3://}"; echo "${k#*/}"; }
deny() { echo "An error occurred (AccessDenied) when calling the $1 operation: Access Denied" >&2; exit 1; }
cmd="${pos[0]:-} ${pos[1]:-}"
case "$cmd" in
  "s3 cp")
    src="${pos[2]}"; dst="${pos[3]}"
    if [ "$recursive" = 1 ]; then
      s="$(loc "$src")"; [ -d "$s" ] || { echo "no such prefix" >&2; exit 1; }
      mkdir -p "$dst"; cp -R "$s"/. "$dst"/
    elif [ "$dst" = "-" ]; then
      k="$(keyof "$src")"
      [ "$FAULT" = read_live ] && [[ "$k" == */data/* ]] && [[ "$k" != *archive_* ]] && [[ "$k" != *aside_* ]] && deny GetObject
      f="$(loc "$src")"; [ -f "$f" ] || { echo "An error occurred (404) when calling the HeadObject operation: Key not found" >&2; exit 1; }
      cat "$f"
    elif [[ "$src" == s3://* ]]; then
      s="$(loc "$src")"; d="$(loc "$dst")"; [ -f "$s" ] || { echo "404" >&2; exit 1; }
      mkdir -p "$(dirname "$d")"; cp "$s" "$d"
      if [ "$FAULT" = corrupt_copy ] && [[ "$(keyof "$dst")" == *archive_* ]]; then echo "CORRUPTED" >> "$d"; fi
    else
      d="$(loc "$dst")"; mkdir -p "$(dirname "$d")"; cp "$src" "$d"
    fi ;;
  "s3 mv")
    [ "$FAULT" = mv ] && deny DeleteObject
    s="$(loc "${pos[2]}")"; d="$(loc "${pos[3]}")"; [ -f "$s" ] || { echo "404" >&2; exit 1; }
    mkdir -p "$(dirname "$d")"; mv "$s" "$d"
    if [ "$FAULT" = corrupt_mv ]; then echo "CORRUPTED" >> "$d"; fi ;;
  "s3 ls")
    p="$(loc "${pos[2]}")"; [ -e "$p" ] || exit 1
    find "$p" -type f | sort | while read -r f; do
      echo "2026-11-18 10:00:00 $(wc -c < "$f" | tr -d ' ') ${f#"$FAKE_S3"/}"; done ;;
  "s3api head-object")
    if [ "$FAULT" = head_denied ]; then deny HeadObject; fi
    f="$FAKE_S3/$key"
    [ -f "$f" ] || { echo "An error occurred (404) when calling the HeadObject operation: Not Found" >&2; exit 254; }
    if [ "$query" = "ETag" ]; then
      if [ "$FAULT" = etag_wrong ] && [[ "$key" == *archive_* ]]; then echo '"00000000000000000000000000000000"'
      else echo "\"$(md5 -q "$f")\""; fi
    else echo '{"ETag": "\"'"$(md5 -q "$f")"'\""}'; fi ;;
  "scheduler get-schedule")
    [ -f "${FAKE_SCHED:-/nonexistent}" ] || { echo "ResourceNotFoundException" >&2; exit 254; }
    if [ "$query" = "State" ]; then python3 -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["State"])' "$FAKE_SCHED"
    else cat "$FAKE_SCHED"; fi ;;
  "batch describe-job-definitions")
    printf '%s\t%s\n' "${FAKE_REV:?}" "${FAKE_IMAGE:?}" ;;
  *) echo "fake_aws: unsupported: $cmd" >&2; exit 2 ;;
esac
