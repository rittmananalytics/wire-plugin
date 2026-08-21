---
description: Generate a region-scoped logical-access UAT plan and evidence pack (tenant carve-out)
argument-hint: <release-folder> [--region <code>]
---

# Generate a region-scoped logical-access UAT plan and evidence pack (tenant carve-out)

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

## Workflow Specification

---
description: Generate a region-scoped logical-access UAT plan and evidence pack for a tenant carve-out
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: logical_access_uat` and `artifact_file_path: migration/logical_access_uat_plan.md` before proceeding.

---

# Logical-Access UAT — Generate

## Purpose

Generates the UAT test plan and evidence pack that proves the tenant carve-out's access boundaries hold: users in the extracted tenant's target project reach **only** that project and see **no other tenant's data**. The plan derives its tests directly from the IAM boundaries written in the target_setup security work (`04_security.sql`) — tenant-scoped GRANTs, the row-level security predicate on the tenant key, the scoped service account, and the PII policy-tag taxonomy.

Every boundary gets **both** a positive test (the authorised role can do what it should) and at least one **negative** test (the role cannot reach another tenant's data or another project). The artifact is a runnable plan plus an evidence template to capture results, with a written sign-off block completed at review.

This command runs only in **tenant carve-out** scope (`migration.scope == tenant_carveout`).

## Parameters

- `$ARGUMENTS` — the release folder.
- `--region <code>` — the target region under test. **Default: `de`** (matches `region-tagging`).

## Prerequisites

- `migration.scope == tenant_carveout` in status.md
- `target_setup review: approved` — the security DDL (`04_security.sql`) must be approved, since its boundaries are what UAT proves

If `scope` is not `tenant_carveout`, stop: "Logical-access UAT runs in tenant carve-out scope only." If `target_setup` is not approved, stop and point to `/wire:target-setup-review`.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/04_security.sql` — the source of truth for IAM boundaries (tenant-scoped GRANTs, RLS predicate, scoped service account, policy-tag masking)
- `.wire/releases/$ARGUMENTS/audit/security_audit.md` — tenant_scoped vs shared role classification, tenant-key flags per table
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md` — the two-project / tenant-scoped IAM model and RLS predicate definition
- `.wire/releases/$ARGUMENTS/status.md` — `migration.scope`, `migration.tenant_predicate`, target project

## Workflow

### Step 1: Enumerate the IAM boundaries

Parse `04_security.sql` (cross-referenced with the migration strategy security section) and list every access boundary it establishes. Typical boundaries:

- **Tenant-scoped role grants** — each `tenant_scoped` role is granted only on the tenant's target project/dataset; it must not reach any other project.
- **Row-level security** — the RLS predicate on the tenant key restricts shared tables to the tenant's rows.
- **Scoped service account** — the copy/runtime service account has access only to the tenant's project (and dedicated staging bucket).
- **Column masking** — PII policy tags mask sensitive columns for non-privileged roles.
- **Shared roles** — platform-wide roles behave as designed without leaking cross-tenant.

Each boundary is a testable assertion. Record it with the role(s) it governs and the resource it scopes.

### Step 2: Derive positive and negative tests per role

For every boundary × role, define:

- **Positive test** — the authorised action succeeds. E.g. "role `tenant_de_analyst` queries `<target_project>.analytics.orders` and receives rows."
- **Negative test (at least one per boundary)** — the prohibited action is denied or returns no other-tenant data. E.g. "role `tenant_de_analyst` queries another tenant's project → permission denied"; "the same role queries a shared table without the RLS context → returns only `de` rows, zero rows for any other market"; "a non-privileged role selects a PII column → value is masked."

Negative tests must assert one of: **access denied**, **zero rows from another tenant**, or **masked value** — never a soft "should be fine".

### Step 3: Write the UAT plan and evidence template

**Output location**: `.wire/releases/$ARGUMENTS/migration/logical_access_uat_plan.md`

Structure:

1. **Scope** — target region, tenant predicate, target project, and the list of IAM boundaries under test.
2. **Test matrix** — one section per boundary; within each, a table of tests:

   | Test ID | Boundary | Role | Type (positive/negative) | Action / query | Expected result |
   |---------|----------|------|--------------------------|----------------|-----------------|

3. **Evidence template** — for each test ID, a capture block to be filled during execution:

   ```markdown
   ### Evidence — {{TEST_ID}}
   - Boundary: {{BOUNDARY}}
   - Role / principal: {{ROLE}}
   - Type: positive | negative
   - Action: {{QUERY_OR_ACTION}}
   - Expected: {{EXPECTED}}
   - Actual: {{ACTUAL}}            <!-- query output, error text, or masked value -->
   - Evidence ref: {{SCREENSHOT_OR_LOG}}
   - Result: PASS | FAIL
   - Tester: {{NAME}}   Date: {{DATE}}
   ```

4. **Sign-off block** — completed at review (left blank here):

   ```markdown
   ## Sign-off
   - All positive tests passed: ☐
   - At least one negative test passed per IAM boundary: ☐
   - No cross-tenant data was reachable in any negative test: ☐

   **Signed off by**: ________________   **Role**: ____________   **Date**: __________
   **Decision**: approved | changes_requested
   ```

### Step 4: Update status

```yaml
artifacts:
  logical_access_uat:
    generate: complete
    file: migration/logical_access_uat_plan.md
    generated_date: "{{TODAY}}"
    target_region: "{{REGION}}"
    boundaries_under_test: N
    positive_tests: N
    negative_tests: N
```

### Step 5: Output next command

```
/wire:logical-access-uat-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/logical_access_uat_plan.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `logical_access_uat` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `logical_access_uat` as artifact_id, `Logical-Access UAT` as artifact_name, and the `file` value from `artifacts.logical_access_uat` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `logical_access_uat` as artifact, `generate` as action.

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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
