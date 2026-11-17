#!/usr/bin/env bash
# Test stub for archive.sh: maps s3://BUCKET/key to $FAKE_S3/key on local disk.
# FAKE_FAIL may name a mode: read_live | mv | none
set -u
to_local() { echo "$FAKE_S3/${1#s3://*/}"; }
cmd="$1 $2"; shift 2
case "$cmd" in
  "s3 cp")
    src="$1"; dst="$2"
    if [ "$dst" = "-" ]; then
      [ "${FAKE_FAIL:-none}" = "read_live" ] && [[ "$src" != *archive_* ]] && { echo "AccessDenied" >&2; exit 1; }
      f=$(to_local "$src"); [ -f "$f" ] || { echo "404 NoSuchKey" >&2; exit 1; }; cat "$f"
    else
      s=$(to_local "$src"); d=$(to_local "$dst"); [ -f "$s" ] || { echo "404" >&2; exit 1; }
      mkdir -p "$(dirname "$d")"; cp "$s" "$d"
    fi ;;
  "s3 mv")
    [ "${FAKE_FAIL:-none}" = "mv" ] && { echo "AccessDenied (DeleteObject)" >&2; exit 1; }
    s=$(to_local "$1"); d=$(to_local "$2"); mkdir -p "$(dirname "$d")"; mv "$s" "$d" ;;
  "s3api head-object")
    key=""; while [ $# -gt 0 ]; do [ "$1" = "--key" ] && key="$2"; shift; done
    f="$FAKE_S3/$key"; [ -f "$f" ] || exit 1; echo "\"$(md5 -q "$f")\"" ;;
  *) echo "stub: unsupported $cmd" >&2; exit 2 ;;
esac
