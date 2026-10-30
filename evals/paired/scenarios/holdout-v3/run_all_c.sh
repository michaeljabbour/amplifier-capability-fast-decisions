#!/usr/bin/env bash
# Serial, memory-guarded validation of holdout-v3 batch C. No model calls.
# Usage: run_all_c.sh <new-out.jsonl>. The output must not already exist; historical results stay unchanged.
# Exit 0: all requested scenarios ran successfully; 1: validation/output failure;
# 2: incomplete (memory guard, no scenarios or invalid input).
set -uo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1
if [ "$#" -ne 1 ]; then
  echo "usage: run_all_c.sh <new-out.jsonl> (existing results are never overwritten)" >&2
  exit 2
fi
OUT="$1"
if ! (set -o noclobber; : > "$OUT") 2>/dev/null; then
  echo "INCOMPLETE: output already exists or cannot be created: $OUT" >&2
  exit 2
fi
LOG_DIR="$(mktemp -d "${OUT}.logs.XXXXXX")" || exit 1
export MEMGUARD_MAX_CONCURRENT=1
shopt -s nullglob
files=("$HERE"/knowledge/*.yaml "$HERE"/repos/*.yaml)
if [ "${#files[@]}" -eq 0 ]; then
  echo "INCOMPLETE: no batch-C scenarios found" >&2
  exit 2
fi
failed=0
skipped=0
for f in "${files[@]}"; do
  id="$(basename "$f" .yaml)"
  if [[ ! "$id" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
    echo "INCOMPLETE: invalid scenario ID: $id" >&2
    skipped=1
    continue
  fi
  if ! free=$(memory_pressure 2>/dev/null | awk '/free percentage/ {gsub("%","",$5); print $5}'); then free=""; fi
  if [[ ! "$free" =~ ^[0-9]+$ ]] || [ "$free" -lt 50 ]; then
    echo "SKIP $id: free memory is ${free:-unknown}% (need 50%)" >&2
    printf '{"id": "%s", "errors": ["memory below 50%% free or unavailable"]}\n' "$id" >> "$OUT" || exit 1
    skipped=1
    continue
  fi
  echo "== $id (free ${free}%)" >&2
  if ! python3 "$HERE/validate_c.py" --ids "$id" --cap-gb 4 --grader-timeout 300 --json "$OUT" >/dev/null 2>"$LOG_DIR/$id.stderr"; then
    echo "FAILED $id: validator did not complete successfully (stderr: $LOG_DIR/$id.stderr)" >&2
    failed=1
  fi
done
[ "$failed" -eq 0 ] || exit 1
[ "$skipped" -eq 0 ] || exit 2
