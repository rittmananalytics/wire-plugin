#!/bin/bash
# concept_leg.sh — run one leg of the 5.0 concept run (wire#408 item 5) and measure it.
#
#   bash wire/cli/tools/concept_leg.sh <repo-copy> <release> <task a|b> <leg-name> <out-dir> -- <wire run flags...>
#
# From a clean working tree: branch concept/<task>-<leg> from concept/baseline-<task>,
# `wire run --yes --once` with the given harness flags, measure with
# concept_measure.py into <out-dir>/<task>-<leg>.json, commit the record on the
# leg branch, remove lane worktrees and branches. Never stops the caller: every
# step reports and the script moves on, so a batch of legs runs unattended.

REPO="$1"; RELEASE="$2"; TASK="$3"; LEG="$4"; OUT="$5"; shift 5
[ "$1" = "--" ] && shift
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEASURE="${HERE}/concept_measure.py"
mkdir -p "$OUT"
cd "$REPO" || { echo "no repo at $REPO"; exit 0; }

cleanup() {
  for w in "$REPO"/.wire/local/worktrees/*; do [ -d "$w" ] && git worktree remove --force "$w" >/dev/null 2>&1; done
  git worktree prune >/dev/null 2>&1
  for b in $(git branch --list 'wire/lane/*' | tr -d ' *'); do git branch -D "$b" >/dev/null 2>&1; done
}

echo "=== leg ${TASK}-${LEG} ($(date -u +%H:%M:%SZ))"
cleanup
if [ -n "$(git status --porcelain)" ]; then
  echo "working tree not clean; committing the leftover record on $(git branch --show-current)"
  git add -A .wire/releases >/dev/null 2>&1; git commit -qm "concept: leftover record" >/dev/null 2>&1 || true
  git checkout -q -- . 2>/dev/null; git clean -qfd 2>/dev/null
fi
git checkout -q -B "concept/${TASK}-${LEG}" "concept/baseline-${TASK}" || { echo "could not branch from concept/baseline-${TASK}"; exit 0; }
echo "on $(git branch --show-current) from $(git rev-parse --short HEAD)"

START=$(date +%s)
WIRE_NO_BANNER=1 wire run "$RELEASE" "$@" --yes --once > "${OUT}/${TASK}-${LEG}.run.log" 2>&1
RC=$?
echo "wire run rc=$RC elapsed=$(( $(date +%s) - START ))s"
grep -E "^  [a-z_]+: |^Next:" "${OUT}/${TASK}-${LEG}.run.log" | cut -c1-300

REF=""
if [ "$TASK" = "a" ]; then REF="${REPO}/.wire/local/reference_data_model_specification.md"; else REF="${REPO}/.wire/local/reference_dbt_models_summary.md"; fi
python3 "$MEASURE" --repo "$REPO" --release "$RELEASE" --task "$TASK" --leg "$LEG" --reference "$REF" --base "concept/baseline-${TASK}" --out "${OUT}/${TASK}-${LEG}.json" > /dev/null 2>&1 || echo "measure failed"
python3 - "${OUT}/${TASK}-${LEG}.json" <<'EOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    print("no measure:", e); sys.exit(0)
r, o = d["record"], d["output"]
row = r.get("log_row") or {}
print("row:", {k: row.get(k) for k in ("result", "duration", "tokens", "cost")})
print("detail:", row.get("detail", "")[:220])
print("status:", r.get("status_outcome"), "| status ok:", r.get("status_file_ok"), "| hooks:", {k: v for k, v in r.get("hooks", {}).items() if k != "deny_reasons"})
for rr in r.get("hooks", {}).get("deny_reasons", []):
    print("  DENY:", rr)
keys = ("present", "bytes", "grain_lines", "er_diagram", "model_count", "overlap_ratio_of_reference") if d["task"] == "a" else ("model_count", "overlap_ratio_of_reference", "lint", "sql_files")
print("output:", {k: o.get(k) for k in keys})
EOF

git add -A .wire/releases >/dev/null 2>&1
git commit -qm "concept leg ${TASK}-${LEG}: record" >/dev/null 2>&1 || true
cleanup
git checkout -q master 2>/dev/null
echo "=== end ${TASK}-${LEG} ($(date -u +%H:%M:%SZ))"
exit 0
