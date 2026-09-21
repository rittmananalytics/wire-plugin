#!/usr/bin/env bash
# Wire Framework — anonymous usage telemetry (Claude Code hook).
#
# Fires on UserPromptExpansion, i.e. whenever a /wire: slash command is run.
# Replaces the old in-command Bash telemetry call so nothing shows in the
# console: this runs inside the harness, backgrounds the network request,
# prints nothing to stdout/stderr, and always exits 0. It must never block,
# delay, or fail the command it is reporting on.
#
# DxXwrT6ucDMRmouCsYDwthdChwDLsNYL and 4.0.0 are substituted at build time by
# wire/scripts/build-packages.sh.

# Opt-out: WIRE_TELEMETRY=false disables all tracking.
[ "${WIRE_TELEMETRY:-true}" = "false" ] && exit 0

# Read the hook payload (JSON) from stdin. We only need to recover which
# /wire: command was expanded. The exact field carrying it is not a documented
# contract for UserPromptExpansion, so scan the raw payload for the slash-command
# token rather than depend on a specific key.
PAYLOAD="$(cat 2>/dev/null)"

# First /wire:<name> token, with the wire: prefix stripped so the reported
# command matches the historical format (e.g. dbt-migration-generate).
COMMAND="$(printf '%s' "$PAYLOAD" | grep -oE 'wire:[A-Za-z0-9_-]+' | head -n1 | sed 's/^wire://')"

# Not a Wire slash command → nothing to report.
[ -z "$COMMAND" ] && exit 0

WRITE_KEY="DxXwrT6ucDMRmouCsYDwthdChwDLsNYL"
WIRE_VERSION="4.0.0"

# Who invoked this command. The hook fires at prompt expansion and cannot see the
# caller, so the caller says: the orchestrating session exports
# WIRE_INVOKED_BY=orchestrator, sets WIRE_INVOKED_BY=lane in each lane's
# environment, and Autopilot exports WIRE_INVOKED_BY=autopilot. Nothing else sets
# it, so a command a person typed reports "typed" without anyone doing anything.
# This replaced a hardcoded "autopilot":"false", which meant typed and
# agent-invoked runs were indistinguishable — and the director model drives typed
# counts down, so without this the adoption measure reads as abandonment.
# See specs/utils/telemetry.md.
case "${WIRE_INVOKED_BY:-typed}" in
  orchestrator|lane|autopilot|typed) INVOKED_BY="${WIRE_INVOKED_BY:-typed}" ;;
  *)                                 INVOKED_BY="typed" ;;
esac

# Fire-and-forget in a detached subshell with all fds redirected, so the hook
# returns instantly and the prompt is never delayed.
(
  TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  # Identity (first run only): create a stable anonymous id and send identify.
  if [ ! -f "$HOME/.wire/telemetry_id" ]; then
    mkdir -p "$HOME/.wire"
    WIRE_UID="$(python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]')"
    printf '%s' "$WIRE_UID" > "$HOME/.wire/telemetry_id"
    curl -s -X POST https://api.segment.io/v1/identify \
      -H "Content-Type: application/json" \
      -d "{\"writeKey\":\"$WRITE_KEY\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"$WIRE_VERSION\",\"first_seen\":\"$TS\"}}" >/dev/null 2>&1
  fi

  WIRE_UID="$(cat "$HOME/.wire/telemetry_id" 2>/dev/null || echo unknown)"
  curl -s -X POST https://api.segment.io/v1/track \
    -H "Content-Type: application/json" \
    -d "{\"writeKey\":\"$WRITE_KEY\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"$COMMAND\",\"timestamp\":\"$TS\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"$WIRE_VERSION\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"invoked_by\":\"$INVOKED_BY\"}}" >/dev/null 2>&1
) >/dev/null 2>&1 &

exit 0
