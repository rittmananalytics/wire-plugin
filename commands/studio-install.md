---
description: Install Wire Studio local web UI on this machine
argument-hint: (no arguments)
---

# Install Wire Studio local web UI on this machine

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

# Wire Studio: Install

Install Wire Studio locally so it can be used as a visual browser-based interface alongside the Wire CLI.

Wire Studio provides an artifact workflow graph, IDE-style document tabs, file explorer, and real-time command execution — as an alternative to the CLI.

## Prerequisites check

Before installing, verify the following:

1. **Node.js 18+**: Run `node --version` and confirm the major version is 18 or higher. If not, ask the user to install Node.js from https://nodejs.org/ before continuing.
2. **Git**: Run `git --version` to confirm git is available.
3. **Anthropic API key**: Check if `ANTHROPIC_API_KEY` is set in the environment. If not, ask the user to provide it.

If any prerequisite is missing, stop and inform the user clearly before proceeding.

## Installation steps

Run the following steps in sequence. Inform the user of progress at each step.

### Step 1: Download Wire Studio

```bash
TMPDIR_CLONE=$(mktemp -d)
git clone --depth=1 --filter=blob:none --sparse \
  https://github.com/rittmananalytics/wire.git "$TMPDIR_CLONE" --quiet
cd "$TMPDIR_CLONE"
git sparse-checkout set wire-web-ui
```

### Step 2: Copy to install directory

```bash
mkdir -p "$HOME/.wire-studio"

# Preserve existing .env.local and SQLite DB if updating
[ -f "$HOME/.wire-studio/wire-web-ui/.env.local" ] && \
  cp "$HOME/.wire-studio/wire-web-ui/.env.local" "$TMPDIR_CLONE/.env.local.bak"
[ -f "$HOME/.wire-studio/wire-web-ui/prisma/dev.db" ] && \
  cp "$HOME/.wire-studio/wire-web-ui/prisma/dev.db" "$TMPDIR_CLONE/dev.db.bak"

rm -rf "$HOME/.wire-studio/wire-web-ui"
cp -r wire-web-ui "$HOME/.wire-studio/wire-web-ui"

# Restore preserved files
[ -f "$TMPDIR_CLONE/.env.local.bak" ] && \
  cp "$TMPDIR_CLONE/.env.local.bak" "$HOME/.wire-studio/wire-web-ui/.env.local"
[ -f "$TMPDIR_CLONE/dev.db.bak" ] && \
  cp "$TMPDIR_CLONE/dev.db.bak" "$HOME/.wire-studio/wire-web-ui/prisma/dev.db"

rm -rf "$TMPDIR_CLONE"
```

### Step 3: Install npm dependencies

```bash
cd "$HOME/.wire-studio/wire-web-ui"
npm install --prefer-offline
```

This may take a minute. Inform the user it is in progress.

### Step 4: Build Wire Studio

```bash
cd "$HOME/.wire-studio/wire-web-ui"
npm run build
```

### Step 5: Configure API key

If `$HOME/.wire-studio/wire-web-ui/.env.local` does not already exist:

- If `ANTHROPIC_API_KEY` is set in the environment, write it to the file:
  ```bash
  echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" > "$HOME/.wire-studio/wire-web-ui/.env.local"
  ```
- Otherwise, ask the user for their Anthropic API key and write it to the file.

### Step 6: Configure GitHub token (optional)

This allows Wire Studio to clone private repositories. If `$HOME/.wire-studio/wire-web-ui/.env.local` does not already contain a `GITHUB_TOKEN` line:

1. Check if the GitHub CLI is available: run `gh auth token 2>/dev/null`.
   - If it outputs a token, ask the user: *"GitHub CLI detected — use this token for cloning repos? (y/n)"*. If yes, append `GITHUB_TOKEN=<token>` to `.env.local`.
2. If no CLI token, ask: *"Enter a GitHub Personal Access Token for cloning repos (press Enter to skip)"*. If provided, append `GITHUB_TOKEN=<token>` to `.env.local`.
3. If skipped, inform the user they can connect GitHub later in Wire Studio via **Clone from GitHub > Save Token**.

### Step 7: Set up the database

```bash
cd "$HOME/.wire-studio/wire-web-ui"
npx prisma db push --skip-generate --accept-data-loss
```

### Step 8: Install the `wire-studio` CLI

Write the following script to `/usr/local/bin/wire-studio` (fall back to `$HOME/.local/bin/wire-studio` if `/usr/local/bin` is not writable without sudo):

```bash
#!/usr/bin/env bash
# wire-studio — Control the Wire Studio local server

INSTALL_DIR="$HOME/.wire-studio/wire-web-ui"
PID_FILE="$HOME/.wire-studio/wire-studio.pid"
LOG_FILE="$HOME/.wire-studio/wire-studio.log"

case "${1:-start}" in
  start)
    PORT="${2:-${WIRE_STUDIO_PORT:-3000}}"
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Wire Studio is already running (PID $(cat "$PID_FILE")). Run: wire-studio stop"
      exit 0
    fi
    set -a; source "$INSTALL_DIR/.env.local" 2>/dev/null; set +a
    cd "$INSTALL_DIR"
    nohup node_modules/.bin/next start --port "$PORT" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1
    open "http://localhost:$PORT" 2>/dev/null || \
      xdg-open "http://localhost:$PORT" 2>/dev/null || true
    echo "Wire Studio running at http://localhost:$PORT  (PID $(cat "$PID_FILE"))"
    echo "Stop with: wire-studio stop"
    ;;
  stop)
    if [[ -f "$PID_FILE" ]]; then
      kill "$(cat "$PID_FILE")" 2>/dev/null && rm "$PID_FILE" && echo "Wire Studio stopped."
    else
      echo "Wire Studio is not running."
    fi
    ;;
  status)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Running (PID $(cat "$PID_FILE"))"
    else
      echo "Not running."
    fi
    ;;
  update)
    echo "Updating Wire Studio..."
    bash <(curl -fsSL https://raw.githubusercontent.com/rittmananalytics/wire/main/install-wire-studio.sh)
    ;;
  logs)
    [[ -f "$LOG_FILE" ]] && tail -f "$LOG_FILE" || echo "No log file yet."
    ;;
  *)
    echo "Usage: wire-studio [start [port] | stop | status | update | logs]"
    exit 1
    ;;
esac
```

Make it executable: `chmod +x /usr/local/bin/wire-studio` (or `$HOME/.local/bin/wire-studio`).

If installing to `$HOME/.local/bin/`, inform the user they may need to add `~/.local/bin` to their PATH.

## Completion

Once all steps are complete, confirm success and show the user:

```
Wire Studio installed successfully!

Start:   wire-studio start
Stop:    wire-studio stop
Update:  wire-studio update
Logs:    wire-studio logs

Wire Studio will open at http://localhost:3000
```

Then ask if the user would like to start Wire Studio now. If yes, run `wire-studio start`.

Execute the complete workflow as specified above.
