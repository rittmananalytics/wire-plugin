#!/usr/bin/env bash
# Wire Framework — execution-log metrics backfill (Claude Code hook).
#
# Fires on Stop, i.e. when the turn that ran a /wire: slash command ends.
# Delegates to wire_metrics.py, which reads the session transcript, sums the
# measured token usage for the just-finished command, and backfills the
# Duration / Tokens / Cost (USD) cells of the most recent execution_log.md
# row (see specs/utils/execution_log.md — Metrics Backfill). It must never
# block, delay, or fail the command it is reporting on: always exits 0.
#
# Opt-out: WIRE_METRICS=false disables the backfill.

[ "${WIRE_METRICS:-true}" = "false" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "${SCRIPT_DIR}/wire_metrics.py" 2>/dev/null

exit 0
