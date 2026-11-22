---
wire_schema: "1.0"
command: generate
artifact: agent_config
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: semantic_layer
    action: review
    outcome: approved
  - artifact: knowledge_skill
    action: review
    outcome: approved
auto_validate: false          # validate's smoke test runs one live question per domain through the actual skill against the semantic layer
delegates_to:
  - utils/precondition_gate
description: Generate the agentic data stack Wire skill — query workflow, routing logic, adversarial review, and provenance footer
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

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

### Step 5: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `agent_config`
- `artifact_name`: `Agent Config`
- `file_path`: `.wire/[release_folder]/artifacts/agent_config_install.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Output

- `agentic-data-stack-SKILL.md` (or in `<dbt_project_path>/.claude/skills/agentic-data-stack/SKILL.md`)
- `.wire/<release-folder>/artifacts/agent_config_install.md`
- Updated `status.md`
