---
description: Classify in-scope items into region buckets for a tenant carve-out (candidates, never auto-removal)
argument-hint: <release-folder> [--region <code>]
---

# Classify in-scope items into region buckets for a tenant carve-out (candidates, never auto-removal)

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
description: Classify in-scope items into region buckets for a tenant carve-out — candidates for adjudication, never auto-removal
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: region_tagging` and `artifact_file_path: migration/region_tagging.md` before proceeding.

---

# Region Tagging — Generate

## Purpose

Reads the discovery audits and classifies every in-scope item into one of three region buckets for a tenant carve-out, emitting `region_tags.csv`. Each row carries the item id, its bucket, the signal that placed it there, and a confidence score.

**This command produces CANDIDATES, not decisions.** It is the first pass at "which of these items belong to the target region", and its only job is to sort items into a confident pile and an adjudication pile for a human to rule on at the review gate.

- It **never** emits a binary include/exclude flag.
- It **never** removes, excludes, or deletes any item.
- Every classification — including high-confidence ones — is a proposal carried into the human adjudication gate (`/wire:region-tagging-review`).

State this posture at the top of the generated artifact so no downstream reader treats the buckets as a scope decision.

This command runs only in **tenant carve-out** scope (`migration.scope == tenant_carveout`).

## Parameters

- `$ARGUMENTS` — the release folder.
- `--region <code>` — the target region to tag for. **Default: `de`.** Read it from `$ARGUMENTS`; if absent, use `de` and state the default in the output.

Example:
```
/wire:region-tagging-generate 01-migration --region de
```

## Prerequisites

- `migration.scope == tenant_carveout` in status.md
- The following discovery audits must have `review: approved`:
  - `dbt_audit`
  - `ingestion_audit`
  - `security_audit`
  - `db_object_audit`
  - `reverse_etl_audit` (the Hightouch sync inventory) — required when `migration.reverse_etl_tool` is set

If `scope` is not `tenant_carveout`, stop: "Region tagging runs in tenant carve-out scope only." If any required audit is not approved, list the pending audits and stop.

## Inputs

- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv` — model catalog (names, feature tags, refs)
- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md` — Hightouch sync inventory (sync names, destinations, warehouse objects)
- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md` — connectors and their landed schemas/destinations
- `.wire/releases/$ARGUMENTS/audit/security_audit.md` — roles/grants, tenant-scoped vs shared classification, tenant-key flags
- `.wire/releases/$ARGUMENTS/audit/db_object_audit.md` — tables/views catalog
- `.wire/releases/$ARGUMENTS/status.md` — `migration.scope`, `migration.tenant_predicate`

## Workflow

### Step 1: Resolve the target region

Read `--region` from `$ARGUMENTS` (default `de`). Record the resolved region code and the `migration.tenant_predicate` — both are the reference signals for classification.

### Step 2: Load all in-scope items

Read each audit and assemble the full list of in-scope items, each tagged with its `source_audit` and `item_type` (`connector`, `table`, `view`, `dbt_model`, `role`, `reverse_etl_sync`, `reverse_etl_destination`). This union is the classification scope — every item is classified exactly once.

### Step 3: Classify each item into one of three buckets

For each item, look for region signals and assign the strongest-matching bucket:

- **confident-region** — an explicit, object-level signal ties the item to the target region:
  - **name suffix / token match** — the item name carries the region token (e.g. `_de`, `de_`, `..._de_...`) matching `--region`;
  - **destination match** — a Hightouch sync destination or ingestion connector schema is dedicated to the region;
  - **WHERE-clause match** — a dbt model or view filters on the market/tenant key in a way that matches `migration.tenant_predicate` (e.g. `WHERE country = 'DE'`).
  Record which of these signals fired.

- **shared-row-level** — the item serves multiple regions within the same object; the region distinction lives at the row level, not the object level. There is no object-level signal, but the item carries the tenant/market key. These need a **lineage trace plus row inspection** to decide how (or whether) to split — they cannot be ruled on from the name or destination alone.

- **global-deferred** — no market tag at all (global/reference/shared dimensions with no tenant key). The split is **deferred** — not decided in this pass.

A confident-region match wins over shared-row-level; shared-row-level wins over global-deferred. Record the single signal (or "none") that placed the item.

**Roles classify by grant scope (v3.11.1).** A role has no rows and no destination, so the three signals above only partially apply: the **name-suffix** signal applies to role names exactly as to any other name, but a role with no name signal classifies by the region status of the objects its grants reference (from the security audit's grant inventory), evaluated after all non-role items are classified:

- every object the role's grants reference is itself `confident-region` → **confident-region**, signal `grant-scope` (the role's whole access surface lives in the target region);
- the grants reference a mix of confident-region and other objects, or reference any `shared-row-level` object → **shared-row-level** (the role's surface spans regions; adjudication decides whether to split the role);
- the role has no object-level grants at all (account-level / administrative roles) → **global-deferred**.

Tests mirror this rule (`wire/tests/platform_migration/validate_region_tagging_classification.py`).

### Step 4: Assign a confidence score

Give each row a confidence score in `[0.0, 1.0]`:
- confident-region with an explicit name/destination/WHERE signal → high (≥ 0.8)
- confident-region via the role `grant-scope` signal → medium-high (0.6–0.8) — derived from other items' classifications, so a notch below an explicit object-level signal
- shared-row-level → medium (≈ 0.4–0.7), reflecting that a human + lineage trace is still needed
- global-deferred → low / not-applicable (≤ 0.3)

The score reflects how strongly the signal supports the bucket, not a recommendation to include or exclude.

### Step 5: Emit region_tags.csv and the adjudication pile

**Output location**: `.wire/releases/$ARGUMENTS/migration/region_tags.csv`

Columns:
```
item_id,item_type,source_audit,bucket,signal,confidence_score
```
One row per in-scope item, classified exactly once. `bucket` is one of `confident-region | shared-row-level | global-deferred`. No include/exclude or removal column — this artifact carries candidates only.

The **adjudication pile** is the subset a human must rule on: every `shared-row-level` row, plus any `confident-region` or `global-deferred` row below a confidence threshold (default `< 0.8`). Carry it forward to the review gate.

### Step 6: Write the summary

**Output location**: `.wire/releases/$ARGUMENTS/migration/region_tagging.md`

Include:
- The CANDIDATES-not-decisions posture statement (from Purpose) at the top
- Target region and tenant predicate used
- Bucket counts: confident-region / shared-row-level / global-deferred
- The adjudication pile: items needing lineage + row inspection, with their signal and confidence
- A note that no item has been included, excluded, or removed — adjudication happens at `/wire:region-tagging-review`

### Step 7: Update status

```yaml
artifacts:
  region_tagging:
    generate: complete
    file: migration/region_tagging.md
    data_file: migration/region_tags.csv
    generated_date: "{{TODAY}}"
    target_region: "{{REGION}}"
    items_classified: N
    confident_region: N
    shared_row_level: N
    global_deferred: N
    adjudication_pile: N
```

### Step 8: Output summary

Print: target region, bucket counts, adjudication pile size, and next command:

```
/wire:region-tagging-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/region_tags.csv`
- `.wire/releases/$ARGUMENTS/migration/region_tagging.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `region_tagging` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `region_tagging` as artifact_id, `Region Tagging` as artifact_name, and the `file` value from `artifacts.region_tagging` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `region_tagging` as artifact, `generate` as action.

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
