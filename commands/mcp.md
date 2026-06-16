---
description: Wire-aware MCP server overview and pre-flight check — list servers with Wire purpose, view details, check release readiness
argument-hint: [list/view/check] [server-name or release-folder]
---

# Wire-aware MCP server overview and pre-flight check — list servers with Wire purpose, view details, check release readiness

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.9.7\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"mcp\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.9.7\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Manage and configure MCP server connections for the Wire Framework
argument-hint: [list/view/check] [server-name or release-folder]
---

# Wire MCP Command

## Purpose

List configured MCP servers with their Wire purpose, inspect details for a specific server, and run pre-flight connectivity checks before audit or migration sessions.

**Relationship to `claude mcp`**: `/wire:mcp` is a Wire-aware overlay on top of the built-in `claude mcp` CLI. Use `claude mcp` (or Claude Code's `/mcp` command) for live connection status, adding/removing servers, and OAuth flows. Use `/wire:mcp` when you want Wire-specific context — which servers a given release needs, what Wire commands each server powers, and whether you're ready to start a session.

## Usage

```
/wire:mcp                             — Interactive menu
/wire:mcp list                        — List all configured servers with their Wire purpose
/wire:mcp view <server>               — Full details for one server
/wire:mcp check [release-folder]      — Pre-flight connectivity check for a release
```

## Wire MCP Server Catalog

The following servers are recognised by the Wire Framework:

| Key | Default URL | Transport | Wire Purpose |
|-----|-------------|-----------|-------------|
| `atlassian` | `https://mcp.atlassian.com/v1/sse` | SSE | Jira issue tracking; Confluence document store and search |
| `linear` | `https://mcp.linear.app/sse` | SSE | Alternative/complementary Linear issue tracking |
| `fathom` | `https://your-fathom-mcp-server/mcp` | SSE | Meeting transcript retrieval during review commands |
| `context7` | `https://mcp.context7.com/mcp` | HTTP | Library documentation lookups during development |
| `notion` | `https://mcp.notion.com/mcp` | HTTP | Notion document store for client artifact review |
| `amplitude` | `https://mcp.amplitude.com/mcp` | HTTP | Amplitude product analytics — charts, dashboards, experiments, session replay, instrumentation, taxonomy |

All servers use **OAuth2** authentication managed by Claude Code's built-in auth system. No credentials or tokens are stored in `settings.json` — only the server URL and transport type.

## Workflow

### Step 1: Determine mode

If no argument was provided, present an interactive menu:

```
Wire MCP Server Manager
═══════════════════════════════════════════

  1. List all configured servers
  2. View details for a server
  3. Pre-flight connectivity check

Enter a number, or type a command directly (e.g. "view atlassian"):
```

Wait for the user's choice and route to the appropriate step below.

If an argument was provided, route directly:
- `list` → Step 2
- `view <server>` → Step 3
- `check [release-folder]` → Step 4

---

### Step 2: List configured servers

1. Read `.claude/settings.json` in the current working directory. If not found, read `~/.claude/settings.json`. If neither exists, report that no MCP configuration was found and show the default catalog with instructions to add servers via `claude mcp add`.

2. For each server in Wire's known catalog, determine its status:
   - **Configured** — key is present in `settings.json`
   - **Not configured** — key is absent from `settings.json`

3. If `settings.json` contains server keys not in Wire's catalog, list them separately under "Other configured servers".

4. Display the full table:

```
Wire MCP Servers
════════════════════════════════════════════════════════════════════════════

  Server      Status          URL                                          Transport
  ──────────  ──────────────  ───────────────────────────────────────────  ─────────
  atlassian   ✓ configured    https://mcp.atlassian.com/v1/sse             SSE
  linear      ✓ configured    https://mcp.linear.app/sse                   SSE
  fathom      ✗ not configured  (default: https://mcp-fathom-server-...)   SSE
  context7    ✓ configured    https://mcp.context7.com/mcp                 HTTP
  notion      ✗ not configured  (default: https://mcp.notion.com/mcp)     HTTP

Config file: /path/to/.claude/settings.json

Note: Authentication status cannot be read here. Run /mcp in Claude Code to
see live connection status for each server.

To add or re-authenticate a server, use claude mcp add / claude mcp remove in a terminal,
or Claude Code → Settings → MCP Servers.

Run /wire:mcp view <server> for full details.
```

---

### Step 3: View server details

Display full details for the named server:

```
Atlassian MCP Server
════════════════════════════════════════════════════════════════════════════

  Key:          atlassian
  Status:       ✓ configured
  URL:          https://mcp.atlassian.com/v1/sse
  Transport:    SSE (type: "url")
  Auth method:  OAuth2 — managed by Claude Code
  Config file:  /path/to/.claude/settings.json

Wire Usage
──────────
  This server powers:
  • /wire:new (Step 3) — auto-detects Atlassian Cloud ID and creates Confluence parent page
  • /wire:utils-jira-create — creates Jira Epic + Tasks + Sub-tasks for issue tracking
  • /wire:utils-jira-sync — syncs artifact status to Jira after every generate/validate/review
  • /wire:utils-jira-status-sync — full Jira reconciliation (called by /wire:status)
  • /wire:utils-atlassian-search — searches Confluence for context during reviews
  • /wire:utils-docstore-setup — sets up Confluence as document store for client review
  • /wire:utils-docstore-sync — publishes generated artifacts to Confluence pages
  • /wire:utils-docstore-fetch — retrieves Confluence comments as review context

  All of the above fail gracefully if this server is unavailable.

To add or re-authenticate
─────────────────────────
  claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/sse
  (Remove first if already present:  claude mcp remove atlassian)
```

Adapt the "Wire Usage" section to match the actual server's role (see catalog above). For servers not in Wire's catalog, show only the raw config details without a Wire usage section. Use `--transport http-sse` instead of `sse` for HTTP-type servers (`notion`, `amplitude`).

---

### Step 4: Pre-flight connectivity check

This subcommand is release-aware: it reads `status.md` to determine which servers the engagement actually requires, probes each one, and reports readiness. Run it at the start of any session involving audit or migration commands.

**Step 4.1 — Determine required servers**

Read `.wire/releases/<release-folder>/status.md`. Extract:
- `release_type`
- `migration.source_platform` and `migration.target_platform`
- `migration.ingestion_tool`
- `jira.project_key` (presence means Jira is configured)
- `docstore.provider`

Build the required server list using this mapping:

| Condition | Required server | Probe call |
|-----------|-----------------|------------|
| `release_type: platform_migration`, `source_platform: snowflake` | Snowflake MCP | `mcp__claude_ai_Snowflake__authenticate` |
| `release_type: platform_migration`, `source_platform: bigquery` OR `target_platform: bigquery` | BigQuery MCP | `mcp__claude_ai_BigQuery_MCP__list_dataset_ids` with `project_id` from `migration.target_project` |
| `migration.ingestion_tool: fivetran` | Fivetran MCP | `mcp__fivetran__get_account_info` |
| `migration.ingestion_tool: rudderstack` | RudderStack MCP | `mcp__plugin_wire_rudderstack__user_details` |
| `jira.project_key` is non-null | Atlassian MCP | `mcp__claude_ai_Atlassian__getAccessibleAtlassianResources` |
| `docstore.provider: confluence` | Atlassian MCP | (same as Jira probe — deduplicate) |
| `docstore.provider: notion` | Notion MCP | `mcp__notion__authenticate` |
| Any `review` step in use | Fathom MCP | `mcp__claude_ai_Fathom__get_identity` |

If no release folder is provided, check the union of required servers across all releases in `.wire/releases/`. If `status.md` cannot be read, probe all servers Wire ever uses.

**Step 4.2 — Probe each required server**

For each server in the required list, run the probe call. Apply a 5-second timeout per probe.

Interpret results:
- Probe succeeds → `CONNECTED`
- Probe returns auth error (401/403) → `AUTH_REQUIRED`
- Probe returns not found or tool unavailable → `UNAVAILABLE`
- Probe times out or MCP is not configured → `NOT_CONFIGURED`

For servers not required but configured in `.claude/settings.json`, record as `OPTIONAL` and probe anyway.

**Step 4.3 — Output connectivity table**

```
## MCP Pre-flight Check — [release_folder]

Release type:  platform_migration
Source:        snowflake → bigquery

| Server       | Required | Status        | Action |
|--------------|----------|---------------|--------|
| BigQuery     | ✅ Yes   | ✅ Connected  | — |
| Snowflake    | ✅ Yes   | ⚠️ Auth req.  | claude mcp remove snowflake && claude mcp add --transport sse snowflake <url> |
| Fivetran     | ✅ Yes   | ✅ Connected  | — |
| Atlassian    | ✅ Yes   | ✅ Connected  | — |
| Fathom       | ✅ Yes   | ❌ Not config | claude mcp add --transport sse fathom <url> — see /wire:mcp view fathom |
| Notion       | ➖ No    | ✅ Connected  | — |
```

**Step 4.4 — Overall readiness verdict**

If all required servers are `Connected`:
```
✅ All required MCP servers are connected. Safe to proceed with audit/migration commands.
```

If one or more required servers have issues:
```
⚠️ [N] required server(s) need attention before starting.
   Run the claude mcp commands shown above, then re-run /wire:mcp check [release-folder] to confirm.
```

---

### Step 5: Suggest next steps

After completing any operation, suggest a logical next action:

- After **list**: "Run `/wire:mcp view <server>` for details on a specific server."
- After **view**: "Use `claude mcp add / remove` in a terminal to add or re-authenticate this server."
- After **check**: "If all required servers are connected, proceed with your next audit or migration command."

## Edge Cases

- **Settings file not found**: Report the missing path, show the default catalog, and direct the user to `claude mcp add` to configure servers.
- **Malformed JSON**: Report the parse error with the file path and line hint.
- **Unknown server key**: Accept it for `view` but note it is not part of Wire's known catalog and list which Wire commands use it (none).

Execute the complete workflow as specified above.
