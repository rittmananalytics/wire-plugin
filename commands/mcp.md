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
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'mcp',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

---
wire_schema: "1.0"
command: lifecycle
artifact: mcp
domain: mcp
release_types: []
action_type: lifecycle
logs_execution: false
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Manage and configure MCP server connections for the Wire Framework
argument-hint: "[list/view/check] [server-name or release-folder]"
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
| `atlassian` | `https://mcp.atlassian.com/v1/mcp` | SSE | Jira issue tracking; Confluence document store and search |
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
  atlassian   ✓ configured    https://mcp.atlassian.com/v1/mcp             SSE
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
  URL:          https://mcp.atlassian.com/v1/mcp
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
  claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/mcp
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
| `migration.ingestion_tool: rudderstack` | RudderStack MCP (configured per engagement in `.claude/settings.json`, not bundled with the plugin) | `mcp__rudderstack__user_details` |
| `jira.project_key` is non-null | Atlassian MCP | `mcp__claude_ai_Atlassian__getAccessibleAtlassianResources` |
| `docstore.provider: confluence` | Atlassian MCP | (same as Jira probe — deduplicate) |
| `docstore.provider: notion` | Notion MCP | `mcp__notion__authenticate` |
| Any `review` step in use | Fathom MCP | `mcp__claude_ai_Fathom__get_identity` |

If no release folder is provided, check the union of required servers across all releases in `.wire/releases/`. If `status.md` cannot be read, probe all servers Wire ever uses.

**BigQuery MCP showing `UNAVAILABLE`/`NOT_CONFIGURED` is not necessarily a blocker.** The migration commands that read/write BigQuery (`dbt-migration-generate`, `target-setup-generate`, `equivalency-validate`) fall back to the `bq` CLI automatically per `specs/utils/bigquery_mcp_fallback.md` — this pre-flight check surfaces the MCP's own status, not whether those commands can actually proceed.

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
