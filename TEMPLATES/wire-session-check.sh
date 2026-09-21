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

CONTEXT_FILE="$WIRE_DIR/engagement/context.md"

# --- Active-release resolution -------------------------------------------------
# Order (specs/utils/director_operating_model.md; /wire:start Step B1):
#   1. the release whose folder matches the current git branch or worktree
#   2. the only release with a status.md write in the last 7 days
#   3. otherwise print the candidates and let the session ask — never guess
# The old rule was "most recently modified", which with two releases in flight
# silently picked whichever was touched last.

RELEASES=()
while IFS= read -r d; do
  [ -n "$d" ] && RELEASES+=("$(basename "$d")")
done < <(find "$WIRE_DIR/releases" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)

if [ ${#RELEASES[@]} -eq 0 ]; then
  echo "[Wire] Engagement set up — no releases started yet. Run /wire:new to create your first release."
  exit 0
fi

# --show-current is empty on a detached HEAD; rev-parse returns the literal
# string "HEAD" there, which would match a release folder called HEAD and
# nothing else. Either way an empty BRANCH just falls through to step 2.
BRANCH=$(git branch --show-current 2>/dev/null)
if [ -z "$BRANCH" ]; then
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  [ "$BRANCH" = "HEAD" ] && BRANCH=""
fi
ACTIVE=""

# 1. Branch match: the release's recorded coordinator branch, then its folder name.
if [ -n "$BRANCH" ]; then
  for r in "${RELEASES[@]}"; do
    CLAIMED_BRANCH=$(grep -m1 "^    branch:" "$WIRE_DIR/releases/$r/status.md" 2>/dev/null \
      | sed 's/^ *branch: *//' | tr -d '"')
    if [ -n "$CLAIMED_BRANCH" ] && [ "$CLAIMED_BRANCH" = "$BRANCH" ]; then
      ACTIVE="$r"; break
    fi
  done
  if [ -z "$ACTIVE" ]; then
    for r in "${RELEASES[@]}"; do
      case "$BRANCH" in
        *"$r"*) ACTIVE="$r"; break ;;
      esac
    done
  fi
fi

# 2. Exactly one release written to in the last 7 days.
if [ -z "$ACTIVE" ]; then
  RECENT=()
  for r in "${RELEASES[@]}"; do
    S="$WIRE_DIR/releases/$r/status.md"
    [ -f "$S" ] || continue
    if find "$S" -mtime -7 2>/dev/null | grep -q .; then
      RECENT+=("$r")
    fi
  done
  if [ ${#RECENT[@]} -eq 1 ]; then
    ACTIVE="${RECENT[0]}"
  elif [ ${#RECENT[@]} -eq 0 ] && [ ${#RELEASES[@]} -eq 1 ]; then
    ACTIVE="${RELEASES[0]}"
  elif [ ${#RECENT[@]} -gt 1 ]; then
    # 3. Ambiguous — name the candidates rather than picking one.
    echo "[Wire] More than one release active: ${RECENT[*]}. Say which one, or run /wire:start to pick."
    exit 0
  fi
fi

# Every release is stale and there is more than one: still ambiguous.
if [ -z "$ACTIVE" ]; then
  echo "[Wire] ${#RELEASES[@]} releases, none written to in the last 7 days: ${RELEASES[*]}. Run /wire:start to pick one."
  exit 0
fi

STATUS_FILE="$WIRE_DIR/releases/$ACTIVE/status.md"
# Suppress output if STATUS_FILE doesn't exist (release folder created but not initialised)
[ ! -f "$STATUS_FILE" ] && exit 0

# Extract fields from YAML front matter
CLIENT=$(grep -m1 "^client_name:" "$CONTEXT_FILE" 2>/dev/null \
  | sed 's/^client_name: *//' | tr -d '"')
PROJECT_TYPE=$(grep -m1 "^project_type:" "$STATUS_FILE" 2>/dev/null \
  | sed 's/^project_type: *//' | tr -d '"')
APPROVED=$(grep -c "review: approved" "$STATUS_FILE" 2>/dev/null || echo "0")

# Parked decisions waiting on the release director, and the orchestration mode.
PARKED=$(awk '/^parked_decisions:/{f=1;next} f&&/^[a-z_]+:/{exit} f&&/^  - id:/{n++} END{print n+0}' \
  "$STATUS_FILE" 2>/dev/null || echo "0")
MODE=$(awk '/^orchestration:/{f=1;next} f&&/^[a-z_]+:/{exit} f&&/^  mode:/{print $2;exit}' \
  "$CONTEXT_FILE" 2>/dev/null)
MODE=${MODE:-orchestrated}

LINE="[Wire] ${CLIENT:-this engagement} / $ACTIVE (${PROJECT_TYPE:-unknown type}) — ${APPROVED} artifacts approved"
if [ "${PARKED:-0}" -gt 0 ] 2>/dev/null; then
  LINE="$LINE, ${PARKED} decision(s) waiting"
fi
if [ "$MODE" = "manual" ]; then
  LINE="$LINE. Manual mode. Run /wire:start for status and next steps."
else
  LINE="$LINE. Say what you want done, or run /wire:start."
fi
echo "$LINE"
