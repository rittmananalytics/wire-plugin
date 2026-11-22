---
wire_schema: "1.0"
command: generate
artifact: deployment
domain: deployment
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
auto_validate: false          # validate calls live Fivetran MCP connection-health tools via pipeline_tool_status.md
delegates_to:
  - utils/precondition_gate
description: Generate deployment from design and requirements
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# deployment Generate Command

Follow `specs/utils/delivery_lead_delegate.md` before executing the workflow below.

## Purpose

Generate a deployment plan that takes the platform from "built" to "live": environment and credentials setup, a pre-flight pipeline health check, an ordered cutover sequence, and — for every step in that sequence — an explicit rollback action. `deployment/validate.md` already gates on pipeline connection health being checked before go-live; this command is what produces the plan that gate validates.

## Usage

```bash
/wire:deployment-generate YYYYMMDD_project_name
```

## Prerequisites

Enforced by the precondition gate (`preconditions: dynamic` — see
`wire/release-types/<project_type>.yaml`), release-type dependent:

- **`full_platform`** / **`dashboard_first`**: `data_quality`: `validate: PASS`
  and `uat`: `review: approved`.
- **`dbt_development`**: `data_quality`: `validate: PASS` only — this release
  type has no `uat`/enablement phase.

## Workflow

### Step 1: Read Inputs

**Process**:
1. Read `requirements/requirements_specification.md` — extract environment names, access/credential requirements, and any stated go-live date or maintenance window
2. Read `status.md` to identify which development artifacts (`pipeline`, `orchestration`, `dbt`, `semantic_layer`, `dashboards`) are complete and need to be included in the cutover sequence
3. If `pipeline.generate == complete`, follow `wire/specs/utils/pipeline_tool_status.md` to get the current pipeline connection list and health — the deployment plan's connection references must match this, not be independently re-derived

### Step 2: Generate Environment & Credentials Section

- List each environment (e.g. dev/staging/prod, or client-specific names from requirements)
- List the credentials/access required per environment (warehouse service account, BI tool admin access, pipeline tool API keys) — sourced from `requirements_specification.md`'s stated scope, not invented
- Flag any credential requirement mentioned in requirements that has no corresponding environment entry yet

### Step 3: Generate Cutover Sequence

For every development artifact that's complete, add an ordered cutover step. Each step **must** have a paired rollback action — a step with no way to undo it needs an explicit "no rollback possible; requires [specific manual recovery]" note rather than a blank:

| Order | Step | Artifact | Rollback |
|-------|------|----------|----------|
| 1 | Verify pipeline connections healthy | pipeline | N/A — pre-flight check, not a cutover action |
| 2 | Deploy dbt models to production schema | dbt | `dbt run --target prod` failure: revert to previous production schema snapshot / re-point views to prior dataset |
| 3 | Switch orchestration schedule to production cadence | orchestration | Revert schedule to previous cadence / pause new jobs |
| 4 | Publish semantic layer / LookML to production | semantic_layer | Revert to previous LookML project commit |
| 5 | Point dashboards at production semantic layer | dashboards | Repoint dashboards at previous explore/model |

Order matters: pipeline health is always checked first (nothing downstream is trustworthy if ingestion is broken), dbt before semantic layer (the semantic layer depends on the warehouse), semantic layer before dashboards (dashboards depend on the semantic layer).

### Step 4: Generate Deployment Plan

**File**: `.wire/releases/[release_folder]/deploy/deployment_plan.md`

```markdown
# Deployment Plan: [Project Name]

**Generated**: [Date]
**Go-live date**: [from requirements, if stated]

## Environments & Credentials

| Environment | Purpose | Credentials Required |
|--------------|---------|------------------------|
| [prod] | [Live client-facing platform] | [Warehouse service account, BI admin access] |

## Pre-flight: Pipeline Connection Health

Per `wire/specs/utils/pipeline_tool_status.md`, current connection status:

| Connection | Status | Last Sync |
|------------|--------|-----------|
| [from pipeline_tool_status.md] | | |

**Gate**: deployment must not proceed past this section if any connection is `unhealthy` (see `deployment/validate.md` Step 2).

## Cutover Sequence

[Table from Step 3, in dependency order]

## Post-Cutover Verification

- [ ] Confirm dbt models materialized in production schema
- [ ] Confirm orchestration ran successfully on new schedule
- [ ] Confirm dashboards load and reflect production data
- [ ] Confirm no pipeline connection health regression since pre-flight
```

### Step 5: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.deployment section:
   ```yaml
   deployment:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `deployment`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `deployment`
- `artifact_name`: `Deployment Plan`
- `file_path`: `.wire/releases/[release_folder]/deploy/deployment_plan.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 8: Confirm and Suggest Next Steps

**Output**:
```
## deployment Generated Successfully

**Cutover steps**: [N]
**Steps with no rollback path**: [N] (flagged for manual recovery)

**File(s):** .wire/releases/[release_folder]/deploy/deployment_plan.md

### Next Steps

1. **Validate deployment**: `/wire:deployment-validate <project>`
2. After validation, review: `/wire:deployment-review <project>`
```

## Edge Cases

### Prerequisites Not Met

If requirements not approved:
```
Error: Requirements must be approved first.

Current status: [status]

Complete requirements approval: /wire:requirements-review <project>
```

### No Development Artifacts Complete

If none of `pipeline`, `orchestration`, `dbt`, `semantic_layer`, `dashboards` are complete:
```
Error: No development artifacts are complete yet, so there's nothing to deploy.

Complete at least one development artifact before generating a deployment plan.
```

### Pipeline Connections Already Unhealthy at Generation Time

If `pipeline_tool_status.md` reports `unhealthy` connections while generating the plan:
```
Warning: One or more pipeline connections are currently unhealthy: [list]

The deployment plan will still be generated, but /wire:deployment-validate will fail its pre-flight check until these are fixed. Fix connections now, or proceed with plan generation? (y/n)
```

## Output

This command creates:
- `.wire/releases/[release_folder]/deploy/deployment_plan.md` — environments/credentials, pipeline pre-flight status, ordered cutover sequence with paired rollback actions, and post-cutover verification checklist
- Updates `status.md`
