---
wire_schema: "1.0"
command: generate
artifact: playbook
domain: playbook
release_types: []
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Generate a step-by-step BPMN delivery playbook for any Wire release
argument-hint: <release-folder>

---

# Playbook Generate

Follow `specs/utils/delivery_lead_delegate.md` before executing the workflow below.

## Purpose

Generate a step-by-step delivery playbook for any Wire release. The playbook has two parts: a BPMN-style Mermaid control-flow diagram, followed by a narrative step-by-step guide. It is a planning utility — it does not create a tracked artifact in `status.md` but it does sync to the release's Confluence page if one is configured.

Ideal run point: after the first scope-setting artifact is complete (`engagement_brief` for `sop_discovery`, `problem_definition` for `discovery`, `requirements` for all delivery release types). Can also run immediately after `/wire:new` for a template-level playbook — the diagram and narrative will lack open questions, dates, and team names.

## Prerequisites

- `.wire/releases/<release-folder>/status.md` must exist
- `.wire/engagement/context.md` should exist (optional but recommended for client name, team, and dates)

## Workflow

### Step 1 — Locate the release

Resolve `.wire/releases/<release-folder>/status.md`. Read:
- `release_type`
- `release_name`
- `release_id`
- `confluence_page_id` (if present)
- The full artifact block (all artifacts and their generate/validate/review gate states)

Read `.wire/engagement/context.md` for: client name, engagement lead, team members, and target dates.

If no artifact has `generate: complete`, continue but prepend the following notice to the output:

> **Playbook generated at template level — re-run after [first artifact] to incorporate open questions, dates, and team context.**

If a playbook file already exists at `.wire/releases/<release-folder>/planning/<release_name>_playbook.md`, ask the user: **"A playbook already exists. Overwrite or update?"** Wait for their response before proceeding.

---

### Step 2 — Extract context from completed artifacts

Read every artifact file listed in `status.md` where `generate: complete`. The artifact files live under `.wire/releases/<release-folder>/` in subdirectories matching the artifact name (e.g. `requirements/requirements_specification.md`, `planning/engagement_brief.md`).

From these files extract:

- All open questions (rows labelled `OQ-N` or `DQ-N`) and flag which are marked as blockers or must-close
- Named owners for each OQ/DQ
- Target dates (kick-off, playback, go-live, sprint end, etc.)
- Named team members and their roles
- Known risks and constraints
- Any repeat-cycle steps (e.g. per-session workshop loops, per-stakeholder interview cycles)

---

### Step 3 — Determine the artifact sequence and parallel structure

Use this canonical mapping to determine phases and whether the release type has parallel work streams:

| Release type | Phases | Parallel streams in Week 1? |
|---|---|---|
| `sop_discovery` | Pre-sprint → Week 1 (parallel) → Week 2 consolidation | Yes: Gold Layer Audit, Hightouch Classification, dbt Audit, Domain Workshops (×N sessions) |
| `discovery` | Pre-sprint → Shaping → Review | No |
| `full_platform` | Requirements → Design → Development → Testing → Deployment → Enablement | No |
| `pipeline_only` | Requirements → Design → Development → Testing → Deployment | No |
| `dbt_development` | Requirements → Design → Development → Testing → Deployment | No |
| `dashboard_extension` | Requirements → Mockups → Development → Review | No |
| `dashboard_first` | Mockups → Data Model → Development → Review | No |
| `enablement` | Content → Delivery | No |
| `platform_migration` | Phase 1: Audit (parallel) → Phase 2: Inventory & Strategy → Phase 3: Target Setup → Phase 4: Migration (parallel batches; dbt models and snapshots, each snapshot ordered ahead of its dependents) → Phase 5: Equivalency → Phase 6: Cutover | Yes: Phase 1 audits run in parallel; Phase 4 dbt batches run in parallel per batch group |

For `platform_migration` the canonical Phase 2 step sequence is:

1. `/wire:migration-audit-all` (or individual audit commands in parallel)
2. `/wire:lineage-generate` — generates an interactive HTML dependency explorer showing the full migration scope from ingestion sources through to warehouse objects. Run immediately after the inventory is complete; the lineage map is the primary tool for scoping batches and communicating migration complexity to the client.
3. `/wire:migration-inventory-generate`
4. `/wire:migration-strategy-generate`

Include `/wire:lineage-generate` explicitly in the Phase 2 section of every `platform_migration` playbook, between the audit phase and the inventory step.

For `platform_migration` playbooks, also include a **Session Start** section at the top of the narrative as the recommended sequence to run at the beginning of every working session:

```
Session start sequence (run at the start of every session):
  1. /wire:start [release-folder]       — reorient, see current state and next action
  2. /wire:mcp check [release-folder]   — verify all required MCP servers are reachable
  3. [continue with the next audit or migration command]
```

#### Tenant carve-out variant (`migration.scope == tenant_carveout`)

Read `migration.scope` from `status.md`. When it is absent or `full_migration`, **omit this block entirely** — the standard six-phase `platform_migration` sequence above is unchanged. Only when `migration.scope == tenant_carveout` insert the following carve-out steps into the sequence (both the narrative and the BPMN diagram), at the positions noted, using `migration.tenant_predicate` to scope the extracted tenant. Mark each inserted node clearly as a carve-out-only step.

- **After Phase 1 audits** — region-tagging: tag every in-scope item with the region / tenant boundary it belongs to, scoped by `migration.tenant_predicate`. Run `/wire:region-tagging-generate <release> [--region <code>]` → `/wire:region-tagging-validate` → `/wire:region-tagging-review` (the human adjudication gate).
- **Alongside Phase 2 strategy** — data-residency-assessment: the GDPR and data-residency assessment, including the legal review of the historical data window being migrated. Run `/wire:data-residency-assessment-generate <release>` → `-validate` → `-review` (the client DPO/legal sign-off gate). RA prepares this as data processor; the lawful-basis and retention determinations are the client's. This is a Stage 1 contractual deliverable with its own gate.
- **Phase 4 migration** — bulk-copy-migration **in place of the re-ingest assumption**: a tenant-scoped Snowflake→BigQuery bulk copy filtered by `migration.tenant_predicate`, instead of re-running ingestion connectors. This copy also moves each `copy_and_continue` snapshot's built SCD-2 history (payload + `dbt_scd_id`/`dbt_updated_at`/`dbt_valid_from`/`dbt_valid_to`, frozen at the baseline `T`, tenant-filtered) so the target `dbt snapshot` run adopts and continues it rather than restarting history from empty. Run `/wire:bulk-copy-migration-generate <release>` → `-validate` → `-review` (safety gate before the first copy).
- **Reporting layer** — reinstate the tenant's reporting layer against the target, tool-dependent on `migration.reporting_tool`: for `metabase`, run `/wire:metabase-migration-generate <release>` → `-validate` → `-review` (preceded by `/wire:metabase-audit-*` if not yet catalogued); for `omni`, run `/wire:omni-migration-generate <release>` → `-validate` → `-review` (preceded by `/wire:omni-audit-*` if not yet catalogued); for `oac`, run `/wire:oac-migration-generate <release>` → `-validate` → `-review` (preceded by `/wire:oac-audit-*` if not yet catalogued). Reporting-layer commands are gated on `migration.reporting_tool` being set to the matching tool, not on scope.
- **Before Phase 6 cutover** — logical-access-uat: verify tenant-scoped logical access (roles, row-level security, masking) on the target before cutover. Run `/wire:logical-access-uat-generate <release> [--region <code>]` → `-validate` → `-review` (the isolation-proof sign-off gate).

For `sop_discovery` and any release type with parallel streams: the diagram will include parallel fork and join gateways. For all others: linear sequence.

---

### Step 4 — Generate the BPMN-style Mermaid diagram

The diagram **MUST** be a `flowchart TD` BPMN-style diagram. Apply the following rules without exception.

#### Node shapes — map directly to BPMN element types

| Mermaid syntax | BPMN element | Use for |
|---|---|---|
| `([Label])` | Circle event | Start and end events only |
| `[Label]` | Rectangle task | Offline work tasks and Wire generate/validate/review steps |
| `{Label}` | Diamond gateway | Exclusive gateways — decisions, yes/no branches |
| `{{Label}}` | Hexagon gateway | Parallel gateways — fork and join points |

#### Subgraphs

Use one `subgraph` per phase. Label each subgraph with the phase name and date range where known from the context extracted in Step 2.

#### Parallel structure

For `sop_discovery` (and any release type with parallel streams):
1. Emit a `{{PARALLEL FORK}}` hexagon node after the pre-sprint subgraph.
2. Connect it to each parallel stream subgraph.
3. After all parallel streams end, emit a `{{PARALLEL JOIN}}` hexagon node. All stream terminal nodes must point into it.
4. Label both gateway nodes with the expected calendar date if it can be inferred from extracted context.

#### Decision gates for blockers

For every OQ or DQ extracted in Step 2 that is flagged as a blocker or must-close:
1. Insert a `{OQ-N resolved?}` diamond node at the point in the flow where it must be resolved.
2. The **No / not yet resolved** branch must go to an offline chase node: `[Chase [owner] — [OQ label]]`, which loops back to the decision diamond.
3. The **Yes / resolved** branch continues the main flow.

#### Rework loops

Wherever a generate → validate → review cycle can result in changes being requested, the "changes requested" branch of the review decision node must loop back to the generate node for that artifact.

#### Class definitions

Define and apply all five of the following `classDef` classes. Every node must have exactly one class:

```
classDef wireCmd fill:#1a3a5c,stroke:#4a90d9,color:#fff
classDef offline fill:#2d4a1e,stroke:#6abf4b,color:#fff
classDef decision fill:#5c3a00,stroke:#d98c1a,color:#fff
classDef gate fill:#4a1a5c,stroke:#a04ad9,color:#fff
classDef event fill:#1a1a1a,stroke:#888,color:#fff
```

Apply as follows:
- Wire generate/validate/review command nodes → `wireCmd`
- Offline work task nodes → `offline`
- Decision diamond nodes → `decision`
- Parallel gateway hexagon nodes → `gate`
- Start and end event nodes → `event`

#### Wire command node labels

Label Wire command nodes with the exact command including the leading slash: e.g. `/wire:engagement-brief-generate`. Where validate and review are shown together to save space, combine them on one node with a line break using `<br/>`.

#### Pre-write validation

Before writing the diagram, mentally trace every path from start to end and verify:
- No dangling nodes
- Every fork has a matching join
- Every loop has an exit condition

---

### Step 5 — Generate the narrative playbook

After the diagram, produce a narrative section for each step in the release sequence. Each step section must contain:

1. **Step heading** — numbered, with the Wire artifact name and a plain-English label (e.g. `Step 4 — Gold Layer Audit → discovery_analyses`)
2. **Offline prerequisites** — what files need to exist in the artifact directory before running generate, who produces them, and any naming conventions
3. **Wire commands** — the exact generate, validate, and review commands with the actual `<release-folder>` argument filled in from the release name
4. **OQ/DQ checkpoint** — any open questions that must be resolved at or before this step, with the named owner from extracted context and the escalation path if unresolved
5. **Done when** — one sentence defining what "complete" looks like for this step before moving on

Also include the following sections at the end:

**Daily rhythm** — covering `/wire:session-plan` and how to scope each session (applicable to any release type with workshop or interview steps).

**What Wire does and does not do** — write this as two short paragraphs, not a single bullet.

*Wire writes the artifacts.* List the specific output types relevant to this release type — for example: requirements specs, conceptual + physical data models, pipeline code, dbt staging/integration/warehouse models, LookML views and explores, dashboards, audit reports, migration translations, kickoff decks, training materials, documentation. Wire also runs the mechanical validations (naming conventions, structural checks, test coverage, FK referential integrity, etc.).

*Wire does not take decisions on the team's or sponsor's behalf.* Workshops and interviews are run by humans; open-question resolution happens in conversation, not in Wire commands; sponsor sign-off, UAT approval, and external communications (email, Slack, client meetings) remain human-owned. Every `-generate` command is followed by a `-validate` and a `-review` — the review is the human gate. Do NOT claim Wire "doesn't write code" or "doesn't run audits" — both are wrong for every release type that includes those artifacts.

**Wire command reference table** — every command used in the playbook with a one-line description.

---

### Step 6 — Write output

Create the directory if it does not exist:

```bash
mkdir -p .wire/releases/<release-folder>/planning
```

Write the file to `.wire/releases/<release-folder>/planning/<release_name>_playbook.md`.

File structure:

```
# [Client] [Release name] — Wire Framework Playbook
[metadata: sprint dates, end deliverable, engagement lead]
---
## Sprint Control Flow
[Mermaid diagram block]
---
## How the Framework Works for This [Release type]
[artifact → work stream mapping table]
---
## Step-by-step Playbook
[numbered steps]
---
## Daily Rhythm
## What Wire Does Not Do
## Wire Command Reference
```

---

### Step 7 — Update execution log and sync to Confluence

Append one row to `.wire/releases/<release-folder>/execution_log.md` in the standard table format:

```
| [timestamp] | /wire:playbook-generate | complete | <release_name>_playbook.md generated — [N]-step playbook with BPMN diagram |
```

If `confluence_page_id` is present in `status.md` for this release, sync the playbook file to Confluence as a child page of the release page, titled `[Release name] — Delivery Playbook`. Follow `specs/utils/docstore_sync.md`.
