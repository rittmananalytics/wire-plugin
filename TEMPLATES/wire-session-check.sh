#!/bin/bash
# Wire Framework — session-start status check
# Configured as a UserPromptSubmit hook in .claude/settings.json (created by /wire:new).
# Outputs a one-line Wire status reminder on the first prompt of each session.
# Output is injected into the conversation context before Claude processes the prompt.

# Fire once per repo per hour — approximates once per session for typical usage patterns.
# Uses a /tmp marker file keyed to the repo path and the current hour.
REPO_SLUG=$(echo "$PWD" | tr '/' '_' | sed 's/^_//' | tail -c 40)
SESSION_MARKER="/tmp/wire-session-${REPO_SLUG}-$(date +%Y%m%d-%H)"
[ -f "$SESSION_MARKER" ] && exit 0
touch "$SESSION_MARKER"

WIRE_DIR=".wire"
[ ! -d "$WIRE_DIR" ] && exit 0

# Find the most recently modified release folder
LATEST_RELEASE=$(ls -t "$WIRE_DIR/releases/" 2>/dev/null | head -1)

if [ -z "$LATEST_RELEASE" ]; then
  echo "[Wire] Engagement set up — no releases started yet. Run /wire:new to create your first release."
  exit 0
fi

STATUS_FILE="$WIRE_DIR/releases/$LATEST_RELEASE/status.md"
CONTEXT_FILE="$WIRE_DIR/engagement/context.md"

# Extract fields from YAML front matter
CLIENT=$(grep -m1 "^client_name:" "$CONTEXT_FILE" 2>/dev/null \
  | sed 's/^client_name: *//' | tr -d '"')
PROJECT_TYPE=$(grep -m1 "^project_type:" "$STATUS_FILE" 2>/dev/null \
  | sed 's/^project_type: *//' | tr -d '"')
APPROVED=$(grep -c "review: approved" "$STATUS_FILE" 2>/dev/null || echo "0")

# Suppress output if STATUS_FILE doesn't exist (release folder created but not initialised)
[ ! -f "$STATUS_FILE" ] && exit 0

echo "[Wire] ${CLIENT:-this engagement} / $LATEST_RELEASE (${PROJECT_TYPE:-unknown type}) — ${APPROVED} artifacts approved. Run /wire:start for status and next steps."
