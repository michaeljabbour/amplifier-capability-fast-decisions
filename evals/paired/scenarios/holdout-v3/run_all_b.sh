#!/usr/bin/env bash
# Serial, memory-guarded validation of holdout-v3 batch B. No model calls.
# Usage: run_all_b.sh [id ...] (default: every scenario in mixed/ and polyglot/).
# Exit 0: all requested scenarios ran successfully; 1: validation/output failure;
# 2: incomplete (memory guard, no scenarios or invalid input). Existing results are never overwritten.
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1
cd "$HERE/../../../.." || exit 1
export MEMGUARD_MAX_CONCURRENT=1
shopt -s nullglob
ids=("$@")
if [ "${#ids[@]}" -eq 0 ]; then
  for f in "$HERE"/mixed/*.yaml "$HERE"/polyglot/*.yaml; do
    ids+=("$(basename "$f" .yaml)")
  done
fi
if [ "${#ids[@]}" -eq 0 ]; then
  echo "INCOMPLETE: no batch-B scenarios found" >&2
  exit 2
fi
OUT="${B_OUT:-$(mktemp -d "${TMPDIR:-/tmp}/holdout-b.XXXXXX")}" || exit 1
mkdir -p -- "$OUT" || exit 1
failed=0
skipped=0
for id in "${ids[@]}"; do
  if [[ ! "$id" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
    echo "INCOMPLETE: invalid scenario ID: $id" >&2
    skipped=1
    continue
  fi
  result="$OUT/$id.json"
  if [ -e "$result" ] || [ -L "$result" ]; then
    echo "FAILED $id: refusing to overwrite $result" >&2
    failed=1
    continue
  fi
  if ! free=$(memory_pressure 2>/dev/null | awk '/free percentage/ {gsub("%","",$5); print $5}'); then free=""; fi
  if [[ ! "$free" =~ ^[0-9]+$ ]] || [ "$free" -lt 50 ]; then
    echo "SKIP $id: free memory is ${free:-unknown}% (need 50%)" >&2
    skipped=1
    continue
  fi
  echo "== $id (free ${free}%)"
  # sed succeeds for an empty successful validator output; pipefail retains a validator failure.
  if ! python3 "$HERE/validate_b.py" --ids "$id" --cap-gb 4 --grader-timeout 300 --json "$result" 2>&1 | sed '/^$/d'; then
    echo "FAILED $id: validator did not complete successfully" >&2
    failed=1
  fi
done
[ "$failed" -eq 0 ] || exit 1
[ "$skipped" -eq 0 ] || exit 2
