---
description: Generate agentic data stack Wire skill with routing logic and provenance footer
argument-hint: <release-folder>
---

# Generate agentic data stack Wire skill with routing logic and provenance footer

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

---
description: Generate the agentic data stack Wire skill — query workflow, routing logic, adversarial review, and provenance footer
argument-hint: <release-folder>
---

# Agentic Data Stack — Agent Config Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Produce the agentic data stack as an installable Wire skill (`SKILL.md`) that the client's Claude Code instance can use. The skill encodes the complete query workflow: check the semantic layer first, consult the knowledge skill index if no metric applies, fall back to curated SQL, and attach a provenance footer to every response. This is what the client's data consumers will use after the engagement closes.

## Usage

```bash
/wire:ads_agent-config-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `knowledge_skill.review: approved`
- `semantic_layer.review: approved`
- All DOMAIN_REFERENCE.md files approved

## Workflow

### Step 1: Read Configuration Inputs

1. Read `artifacts/knowledge_skill_index.md` — domain file paths
2. Read `artifacts/governance_design.md` — tiering policy and canonical table list
3. Read status.md for `warehouse`, `semantic_layer`, `bi_tool`, `dbt_project_path`

### Step 2: Generate the Agentic Data Stack SKILL.md

Write the skill file to `<dbt_project_path>/.claude/skills/agentic-data-stack/SKILL.md` (or `.wire/<release-folder>/artifacts/agentic-data-stack-SKILL.md` if no dbt project path is set):

````markdown
---
name: agentic-data-stack
description: Self-service agentic data stack for [client] — answers business questions using the semantic layer, domain knowledge files, and canonical dbt models. Activates on analytical questions about revenue, customers, orders, marketing, or other business metrics.
---

# [Client] Agentic Data Stack

## On Activation

Append to `.wire/execution_log.md`:
```
| YYYY-MM-DD HH:MM | skill | agentic-data-stack | activated | [question summary] |
```

## Purpose

Answer business analytics questions using the [client] data platform. 
Always follow the routing order below — never skip straight to raw SQL.

## Routing Order (MANDATORY — do not deviate)

### Tier 1: Semantic Layer (always check first)

Check whether a semantic layer metric answers the question:

**[dbt Semantic Layer]:**
```bash
dbt sl list metrics  # find the relevant metric
dbt sl query --metrics <metric_name> --group-by <dimensions> --where <filter> --limit 20
```

**[LookML / Looker]:**
Use the defined measure in the canonical explore — `<explore_name>.<measure_name>`.

If a metric exists and answers the question: use it. Do not fall through to Tier 2 or 3.
Attach provenance: `tier: semantic`.

### Tier 2: Domain Knowledge Files (if no semantic metric applies)

Read the DOMAIN_REFERENCE.md for the relevant domain:

| Domain | File |
|---|---|
| orders/revenue | `models/marts/orders/DOMAIN_REFERENCE.md` |
| customers | `models/marts/customers/DOMAIN_REFERENCE.md` |
| marketing | `models/marts/marketing/DOMAIN_REFERENCE.md` |
| [add remaining domains] | |

Use the canonical table and example SQL patterns from the reference file.
Only use canonical tables listed in governance_design — never query deprecated tables.
Attach provenance: `tier: curated`.

### Tier 3: Raw SQL Fallback (last resort only)

Only use raw SQL if:
1. No semantic metric exists for this question
2. The DOMAIN_REFERENCE.md has no relevant example pattern
3. The question cannot be answered from canonical tables

When using Tier 3:
- Write SQL against canonical tables only (never deprecated tables)
- Note in your response that this question is a gap the semantic layer does not currently cover
- Suggest the metric that should be added
Attach provenance: `tier: raw`.

## Adversarial Review (built-in — always on)

Before sending any quantitative answer to the user, apply this self-check:

1. **Source check**: Did I use the canonical table? Would a different table give a different answer?
2. **Filter check**: Are the filters in my query correct for the question asked? (e.g. confirmed orders only for revenue — not all order rows)
3. **Grain check**: Is the result at the correct granularity? (e.g. asked for monthly but returned daily)
4. **Plausibility check**: Does the number make sense? An order count of 3 when the client processes 1000+/day is a red flag.
5. **Definition check**: Does my definition of the metric match the canonical definition in the DOMAIN_REFERENCE.md?

If any check fails, fix the query before responding. Do not present an answer you suspect is wrong.

## Provenance Footer (attach to every response)

Every answer must include:

```
---
Source tier: [Semantic | Curated | Raw]
Dataset: [table or metric name]
Freshness: [last dbt run timestamp, or "unknown"]
Domain owner: [email from DOMAIN_REFERENCE.md]
---
```

## Known Limitations

- Revenue figures are net throughout. For gross comparisons, use `gross_revenue` explicitly.
- [Add client-specific limitations from knowledge skill review]

## Deprecated Tables — Never Query These

| Table | Sunset date | Use instead |
|---|---|---|
| orders_raw | YYYY-MM-DD | fct_orders |
| revenue_v2 | YYYY-MM-DD | fct_orders |
| [complete from governance_design] | | |
````

### Step 3: Write Installation Instructions

Write `.wire/<release-folder>/artifacts/agent_config_install.md`:

```markdown
# Agentic Data Stack — Installation

## Install the skill in Claude Code

Copy `agentic-data-stack-SKILL.md` to your dbt project:
```bash
mkdir -p .claude/skills/agentic-data-stack
cp agentic-data-stack-SKILL.md .claude/skills/agentic-data-stack/SKILL.md
```

Or for the full Wire plugin users — the skill auto-activates.

## Configure MCP Server (for dbt Semantic Layer)

Ensure the dbt MCP server is running for Tier 1 access:
```bash
claude mcp add dbt -- dbt-mcp --profiles-dir <profiles_dir> --project-dir <project_dir>
```

See the `dbt-mcp-server` Wire skill for full setup instructions.

## Test Installation

Run a test query: "What was total revenue last month?"

Expected response includes:
- A number from the semantic layer
- Provenance footer: `Source tier: Semantic`
```

### Step 4: Update Status

```yaml
agent_config:
  generate: complete
  generated_date: YYYY-MM-DD
  skill_file: agentic-data-stack-SKILL.md
  routing_tiers: 3
  adversarial_review: enabled
  provenance_footer: enabled
```

## Output

- `agentic-data-stack-SKILL.md` (or in `<dbt_project_path>/.claude/skills/agentic-data-stack/SKILL.md`)
- `.wire/<release-folder>/artifacts/agent_config_install.md`
- Updated `status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
