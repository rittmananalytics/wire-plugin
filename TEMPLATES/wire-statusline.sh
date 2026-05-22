#!/bin/sh
# Wire-aware Claude Code status line
# Reads JSON from stdin, outputs a formatted status line

input=$(cat)

# --- Wire version ---
# Prefer the installed plugin manifest; fall back to the source repo
WIRE_VERSION=""
for candidate in \
    "$HOME/.claude/plugins/wire/.claude-plugin/plugin.json" \
    "$HOME/.claude/plugins/wire@rittman-analytics/.claude-plugin/plugin.json" \
    "$HOME/GitHub/ra-claude-skills-repo/wire/packaging/claude-plugin/.claude-plugin/plugin.json"; do
  if [ -f "$candidate" ]; then
    v=$(python3 -c "import json,sys; print(json.load(open('$candidate'))['version'])" 2>/dev/null)
    if [ -n "$v" ]; then
      WIRE_VERSION="$v"
      break
    fi
  fi
done

# --- Active release (most-recently modified folder under .wire/releases/) ---
WIRE_RELEASE=""
CWD=$(echo "$input" | jq -r '.workspace.current_dir // empty')
if [ -n "$CWD" ]; then
  RELEASES_DIR="$CWD/.wire/releases"
  if [ -d "$RELEASES_DIR" ]; then
    # Pick the most recently modified subdirectory
    latest=$(ls -1t "$RELEASES_DIR" 2>/dev/null | head -1)
    [ -n "$latest" ] && WIRE_RELEASE="$latest"
  fi
fi

# --- Context remaining ---
CONTEXT_REMAINING=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')

# --- Shell identity ---
USER_HOST="$(whoami)@$(hostname -s)"
DIR=$(echo "$input" | jq -r '.workspace.current_dir // empty')
if [ -n "$DIR" ]; then
  # Abbreviate $HOME to ~
  SHORT_DIR="${DIR/#$HOME/~}"
else
  SHORT_DIR="$(basename "$(pwd)")"
fi

# --- Assemble ---
# Wire badge
if [ -n "$WIRE_VERSION" ]; then
  WIRE_BADGE="[Wire v${WIRE_VERSION}]"
else
  WIRE_BADGE="[Wire]"
fi

# Release indicator
if [ -n "$WIRE_RELEASE" ]; then
  RELEASE_PART=" > ${WIRE_RELEASE}"
else
  RELEASE_PART=""
fi

# Context indicator (only when at least one API call has been made)
if [ -n "$CONTEXT_REMAINING" ]; then
  CTX_PART=" ctx:${CONTEXT_REMAINING}%"
else
  CTX_PART=""
fi

printf "%s %s:%s%s%s\n" "$WIRE_BADGE" "$USER_HOST" "$SHORT_DIR" "$RELEASE_PART" "$CTX_PART"
