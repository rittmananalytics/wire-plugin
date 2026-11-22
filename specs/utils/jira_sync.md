---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Sync a single artifact lifecycle state to Jira
argument-hint: <project-folder> <artifact> <action>

---

# Jira Status Sync Utility

## Purpose

Sync a single artifact's lifecycle state change to Jira. Transitions the corresponding Sub-task and adds a detailed comment with file names, revision history, reviewer details, and feedback. Also records the event in the artifact's `revision_history` in `status.md` for audit trail tracking. Called by generate/validate/review commands after they update `status.md`.

## Usage

```bash
/wire:utils-jira-sync YYYYMMDD_project_name requirements generate
```

Typically invoked automatically by lifecycle commands after updating status.md.

Optionally, pass `sync_scope: full` to also reconcile acceptance criteria and assignee (Step 6.6):

```bash
/wire:utils-jira-sync YYYYMMDD_project_name requirements generate sync_scope=full
```

| Input | Description | Default |
|-------|-------------|---------|
| `sync_scope` | `status` — lifecycle state, comments, and revision_history only (all steps below except 6.6). `full` — also runs Step 6.6 (acceptance criteria + assignee reconciliation). | `status` |

**Existing callers are unaffected.** Every generate/validate/review spec that currently invokes this utility without a `sync_scope` argument continues to get exactly today's behavior — `sync_scope` defaults to `status`, and Step 6.6 does not run unless a caller explicitly opts in.

## Prerequisites

- Atlassian MCP server must be configured
- Project must have Jira keys in `status.md` (created by `/wire:utils-jira-create`)
- For `sync_scope: full`: `jira.artifacts.[artifact].ac_field_id` must be configured for AC reconciliation, and `artifacts.[artifact].owner` must be set in status.md for assignee reconciliation. Either or both may be absent — see Step 6.6, which skips whichever sub-step lacks its input.

## Workflow

### Step 1: Check Jira Configuration

**Process**:
1. Read the project's `status.md`
2. Check for `jira` section in YAML frontmatter
3. If no `jira` section exists, skip silently (no output, no error)
4. Extract `jira.project_key`, `jira.structure` (defaults to `subtasks` if absent — backwards compatible), and the artifact's issue keys
5. Resolve `sync_scope` from the caller's input, defaulting to `status` if not passed

### Step 2: Look Up Issue Key

The lookup branches on `jira.structure`:

**If `jira.structure == "single_issue"`**:
1. Look up `jira.artifacts.[artifact].task_key` — this is the single Task that moves through workflow states for all three commands (generate / validate / review).
2. If the key is null or missing, skip silently.
3. Proceed to **Step 3 — Single-issue transitions** below.

**If `jira.structure == "subtasks"` (default — original behaviour)**:
1. Determine the sub-task key from `jira.artifacts.[artifact].[action]_key`
   - Example: for `requirements` + `generate`, look up `jira.artifacts.requirements.generate_key`
2. If the key is null or missing, skip silently.
3. Proceed to **Step 3 — Sub-task transitions** below.

### Step 3: Determine Target Transition

#### Step 3 — Single-issue transitions (`jira.structure == "single_issue"`)

The single Task moves through four workflow states as commands run. Map the local action + state to a target Jira state:

| Action | Local State | Target Jira Status | Notes |
|--------|-------------|-------------------|-------|
| generate | `complete` | "In Progress" | Generation done, awaiting validate |
| validate | `pass` | "In Review" | Validation passed, awaiting human review |
| validate | `fail` | "In Progress" | Generation needs rework; Task is back with the generator |
| review | `approved` | "Done" | All gates passed |
| review | `changes_requested` | "In Progress" | Reviewer requested changes; back to the generator |
| review | `pending` | (no change) | Review not yet started or in flight; leave as "In Review" |

Apply the transition to `task_key` (not a sub-task — there are no sub-tasks in this structure).

#### Step 3 — Sub-task transitions (`jira.structure == "subtasks"`)

Map the local status to a Jira transition on the relevant Sub-task:

| Action | Local State | Target Jira Status |
|--------|-------------|-------------------|
| generate | `complete` | "Done" |
| validate | `pass` | "Done" |
| validate | `fail` | "To Do" |
| review | `approved` | "Done" |
| review | `changes_requested` | "To Do" |
| review | `pending` | "In Progress" |

### Step 4: Get Available Transitions

Let `[target_issue_key]` refer to whichever key Step 2 resolved: the sub-task key under `subtasks` structure, or the task key under `single_issue` structure. The rest of the spec uses `[target_issue_key]` interchangeably.

```
getTransitionsForJiraIssue:
  issueKey: "[target_issue_key]"
```

**Resolve the target status label** using this two-step lookup:

**Step 4a — Check for custom state mapping in status.md**

Read `jira.state_mapping` from status.md. This optional block maps Wire's canonical state names to the custom Jira workflow labels used by this specific project:

```yaml
jira:
  state_mapping:
    done: "Internal QA Complete"
    in_progress: "In Development"
    in_review: "Awaiting Sign-off"
    to_do: "Backlog"
```

If `jira.state_mapping` is present and contains a key for the target state, use that label as the transition target. For example, if the target is "Done" and `state_mapping.done` is "Internal QA Complete", look for a transition named "Internal QA Complete".

**Step 4b — Fall back to default flexible matching**

If `jira.state_mapping` is absent or does not contain a key for the target state, match the target status name flexibly against the available transition names:
- "Done" matches: "Done", "Resolved", "Closed", "Complete"
- "To Do" matches: "To Do", "Open", "Reopened", "Backlog"
- "In Progress" matches: "In Progress", "In Development", "Active"
- "In Review" matches: "In Review", "Review", "Code Review", "In QA", "QA", "Awaiting Review"

### Step 5: Transition the Sub-task

**IMPORTANT: Only transition — do NOT call `editJiraIssue` to update the description. Issue descriptions are set at creation time and must never be modified by sync operations. All lifecycle progress is recorded as comments (Step 6), never by editing the description.**

**This rule scopes narrowly to the narrative description field.** It does not forbid `editJiraIssue` outright — `sync_scope: full` (Step 6.6, optional, off by default) is explicitly permitted to call `editJiraIssue` against two specific fields: a dedicated acceptance-criteria custom field (`jira.artifacts.[artifact].ac_field_id`) and the `assignee` field. Neither is the `description` field. If `sync_scope: full` is not requested, no `editJiraIssue` call of any kind happens anywhere in this spec, and behavior is identical to before this rule was added.

```
transitionJiraIssue:
  issueKey: "[target_issue_key]"
  transitionId: "[matched_transition_id]"
```

### Step 5.5: Discover Generated Files

Before building the comment, identify the files this artifact produced. This provides concrete detail in the Jira comment.

**Process**:
1. Check `artifacts.[artifact].generated_files` in status.md
2. If the list is populated, use it directly
3. If empty or missing, discover files using Glob based on the artifact type. Use the project's subdirectory within `.wire/[folder]/` as the base path:

| Artifact | Glob Pattern |
|----------|-------------|
| requirements | `requirements/*.md` |
| workshops | `requirements/workshop*.md` |
| conceptual_model | `design/conceptual_model*.md` |
| pipeline_design | `design/pipeline*.md` |
| data_model | `design/data_model*.md` |
| mockups | `design/mockup*.md`, `design/dashboard_mockup*.md` |
| pipeline | `dev/pipeline*.*` |
| dbt | Use `models/**/*.sql` and `models/**/*.yml` in the **repository root** (dbt files live outside the project folder) |
| semantic_layer | Use `*.lkml` files in the repository's LookML project directory |
| dashboards | Use `dashboards/*.lkml` or `dev/dashboard*.md` |
| data_quality | `test/data_quality*.md` |
| uat | `test/uat*.md` |
| deployment | `deploy/*.md` |
| training | `enablement/training*.md` |
| documentation | `enablement/doc*.md`, `enablement/*_guide*.md` |

4. Update `artifacts.[artifact].generated_files` in status.md with the discovered list (so subsequent calls don't need to re-discover)

**For large file lists** (more than 10 files, common with dbt and semantic_layer): group by category in the comment rather than listing individually. For example: "12 files: 4 staging models, 3 integration models, 5 warehouse models" or "8 LookML files: 5 views, 2 explores, 1 dashboard".

### Step 5.6: Compute Revision Number

Determine how many times this artifact has been through the generate cycle, to provide context in the comment.

**Process**:
1. Read `artifacts.[artifact].revision_history` from status.md
2. If the list exists, count entries where `action` is `"generate"` — this is the current revision number
3. If revision_history doesn't exist or is empty, this is revision 1
4. If the current action is `generate` and this is a re-generation (revision_history already has a generate entry), the revision number is previous generate count + 1

**For review comments**: also extract the previous review entries from revision_history to show the feedback trail.

### Step 6: Add Comment with Details

Add a comment to the Sub-task with detailed information about the lifecycle event:

```
addCommentToJiraIssue:
  issueKey: "[target_issue_key]"
  body: "[comment_text]"
```

**Comment templates by action**:

**Generate complete:**
```
**[Artifact Display Name] — Generated**

**Revision**: [N] ([if N>1: "revised after feedback from [previous reviewer name from revision_history]"] / [if N=1: "initial generation"])
**Generated**: [generated_date from status.md]

**Files created:**
[For single-file artifacts:]
- [file path relative to project folder]

[For dbt, include:]
- [models_count] models, [tests_count] tests configured
[Then list files, grouped by layer if >10:]
- Staging: [list or count]
- Integration: [list or count]
- Warehouse: [list or count]
- YAML docs: [list or count]

[For multi-file artifacts with <=10 files, list each:]
- [file path 1]
- [file path 2]
- ...

**Next**: Validate → /wire:[artifact]:validate [folder]
```

**Validate pass:**
```
**[Artifact Display Name] — Validation Passed**

**Validated**: [today's date]
**Revision**: [N]

[For dbt, include test results:]
**Test results**: [tests_passed] passed, [tests_failed] failed

**Checks completed**: All validation checks passed.

**Next**: Submit for review → /wire:[artifact]:review [folder]
```

**Validate fail:**
```
**[Artifact Display Name] — Validation Failed**

**Validated**: [today's date]
**Revision**: [N]

[For dbt, include test results:]
**Test results**: [tests_passed] passed, [tests_failed] failed

**Action**: Fix issues and re-validate.
See validation report in status.md for details.
```

**Review approved:**
```
**[Artifact Display Name] — Approved**

**Reviewer**: [reviewed_by from status.md]
**Date**: [reviewed_date from status.md]
**Revision**: [N]

[If N > 1, include revision summary showing the path to approval:]
**Revision history:**
[For each previous entry in revision_history with action "review":]
- [date]: [result] by [reviewer][if feedback present: " — " + first 150 chars of feedback]

[Example:]
- 2026-02-05: Changes requested by Chris Loveday — "Need to add assignment marks model and cross-reference with ProSolution enrolment data"
- 2026-02-08: Approved by Chris Loveday

This artifact is now locked and ready for downstream phases.
```

**Review changes_requested:**
```
**[Artifact Display Name] — Changes Requested**

**Reviewer**: [reviewed_by from status.md]
**Date**: [reviewed_date from status.md]
**Revision**: [N]

**Feedback:**
> [Full feedback text from artifacts.[artifact].feedback in status.md]

[If N > 1, include previous review context:]
**Previous reviews:**
[For each previous entry in revision_history with action "review":]
- [date]: [result] by [reviewer]

**Action**: Address feedback, revise artifact, re-validate, and re-submit for review.
```

**Artifact display name mapping** (use the same mapping as `jira_create.md`):

| Artifact | Display Name |
|----------|-------------|
| requirements | Requirements Specification |
| workshops | Workshops |
| conceptual_model | Conceptual Model |
| pipeline_design | Pipeline Design |
| data_model | Data Model Design |
| mockups | Dashboard Mockups |
| pipeline | Data Pipeline |
| dbt | dbt Models |
| semantic_layer | Semantic Layer |
| dashboards | Dashboards |
| data_quality | Data Quality Tests |
| uat | User Acceptance Testing |
| deployment | Deployment |
| training | Training Materials |
| documentation | Documentation |

### Step 6.5: Record Revision History

After writing the Jira comment (whether or not the comment succeeded), append an entry to `artifacts.[artifact].revision_history` in status.md. This maintains an audit trail of all lifecycle events for the artifact.

**Process**:
1. Read the current `artifacts.[artifact].revision_history` list from status.md
2. If the list doesn't exist (older status.md without this field), create it as an empty list
3. Append a new entry based on the action:

**For generate:**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "generate"
  files: [list from generated_files]
```

**For validate:**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "validate"
  result: "[pass|fail]"
```

**For review (approved):**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "review"
  result: "approved"
  reviewer: "[reviewed_by from status.md]"
```

**For review (changes_requested):**
```yaml
- date: "[today's date YYYY-MM-DD]"
  action: "review"
  result: "changes_requested"
  reviewer: "[reviewed_by from status.md]"
  feedback: "[feedback text from status.md]"
```

4. Write the updated `revision_history` list back to status.md

**Edge case**: If Jira sync failed (MCP unavailable, transition error), still record the revision history entry — the audit trail should be maintained regardless of Jira connectivity.

### Step 6.6: Acceptance Criteria and Assignee Reconciliation (OPTIONAL — `sync_scope: full` only)

**Skip this entire step if `sync_scope` is `status` (the default) or absent.** Nothing below changes the behavior of an existing caller that doesn't pass `sync_scope: full`.

This step reconciles two things the rest of this spec doesn't touch: whether the artifact's own stated acceptance criteria match what's recorded in Jira, and whether the Jira issue's assignee matches the artifact's recorded owner. Both operate on `[target_issue_key]` — the same key resolved in Step 2 (the Sub-task under `subtasks` structure, or the Task under `single_issue` structure).

#### Step 6.6a: Acceptance Criteria Reconciliation

**Applies only to artifacts that have their own AC construct.** Today that's `requirements` — each `### FR-N: [Name]` section in the generated requirements file has a `**Acceptance Criteria**:` checklist (see `wire/specs/requirements/generate.md` §4). If the artifact type has no equivalent AC section, skip Step 6.6a silently.

**Process**:
1. Look up `jira.artifacts.[artifact].ac_field_id` in status.md — the custom field ID that holds acceptance criteria in this project's Jira (e.g. `customfield_10050`).
   - **This field must be explicitly configured. Do not guess a custom field ID and do not fall back to writing into the description.** If `ac_field_id` is absent, skip and note: `Note: sync_scope: full requested AC reconciliation for [artifact] but jira.artifacts.[artifact].ac_field_id is not configured — skipped.`
2. Read the artifact's source file(s) from `artifacts.[artifact].generated_files` (or `artifacts.[artifact].file` for single-file artifacts) and extract each requirement's AC checklist, grouped by requirement ID (FR-1, FR-2, ...).
3. Fetch the field's current value:
   ```
   getJiraIssue:
     issueKey: "[target_issue_key]"
     fields: ["[ac_field_id]"]
   ```
4. Diff the artifact's AC text against the field's current text (requirement by requirement).
   - **No diff**: no action.
   - **Diff found**: update the field only:
     ```
     editJiraIssue:
       issueKey: "[target_issue_key]"
       fields:
         [ac_field_id]: "[formatted AC text, grouped by requirement ID]"
     ```
     This call touches only `[ac_field_id]`. It must never include `description` in the same `fields` payload.
5. If a diff was applied, add a short comment: `Acceptance criteria field updated to match [artifact] (source: [file path]).`
6. If `editJiraIssue` fails (field not editable in this project's screen scheme, permissions error), log: `Note: Could not update AC field on [target_issue_key]. [error summary]` and continue — do not block the rest of the sync.

#### Step 6.6b: Assignee Reconciliation

**Process**:
1. Read `artifacts.[artifact].owner` from status.md — the artifact's recorded owner. If this field doesn't exist (status.md predates this convention, or no owner has been recorded for this artifact), skip Step 6.6b silently. Treat this the same as the forward-compatible handling already used for `generated_files` and `revision_history` elsewhere in this spec.
2. Resolve the owner to a Jira account:
   ```
   lookupJiraAccountId:
     query: "[owner name or email from status.md]"
   ```
   If no match is found, log: `Note: sync_scope: full could not resolve Jira account for owner "[owner]" on [artifact] — assignee left unchanged.` and skip.
3. Fetch the issue's current assignee:
   ```
   getJiraIssue:
     issueKey: "[target_issue_key]"
     fields: ["assignee"]
   ```
4. Compare the current assignee's account ID to the resolved account ID.
   - **Match (or already assigned to the resolved account)**: no action.
   - **Mismatch, or currently unassigned**:
     ```
     editJiraIssue:
       issueKey: "[target_issue_key]"
       fields:
         assignee:
           accountId: "[resolved_account_id]"
     ```
5. If `editJiraIssue` fails, log: `Note: Could not set assignee on [target_issue_key]. [error summary]` and continue.

**Neither sub-step ever calls `editJiraIssue` with `description` in the payload.** Step 6.6 exists precisely to carve out two narrow, named fields (a custom AC field, and `assignee`) from the description-immutability rule in Step 5 — it does not reopen it more broadly.

### Step 7: Check Parent Task Completion

After transitioning the Sub-task, check if all Sub-tasks under the parent Task are now "Done":

1. Look up the artifact's `task_key` from `jira.artifacts.[artifact].task_key`
2. Check all sub-task keys for this artifact (`generate_key`, `validate_key`, `review_key`)
3. Read their current states from `status.md`:
   - generate == `complete`
   - validate == `pass` (or artifact has no validate step)
   - review == `approved`
4. If all applicable steps are done, transition the parent Task to "Done"

```
getTransitionsForJiraIssue:
  issueKey: "[task_key]"

transitionJiraIssue:
  issueKey: "[task_key]"
  transitionId: "[done_transition_id]"

addCommentToJiraIssue:
  issueKey: "[task_key]"
  body: "All lifecycle steps complete. Artifact is ready."
```

### Step 8: Check Epic Completion

After transitioning a Task to "Done", check if all artifact Tasks under the Epic are done:

1. Read all artifact task states from `status.md`
2. For each in-scope artifact, check if all steps are complete
3. If ALL artifacts are fully complete, transition the Epic to "Done"

```
addCommentToJiraIssue:
  issueKey: "[epic_key]"
  body: "All project artifacts complete. Project ready for closure."
```

### Step 9: Handle Edge Cases

**Atlassian MCP not available:**
- Skip the Jira transition and comment silently. No output, no error. The lifecycle command continues normally.
- **Still record the revision history entry** in status.md (Step 6.5) — audit trail is maintained even without Jira.

**Sub-task already in target state:**
- Skip the transition (avoid duplicate transitions)
- Still add the comment for audit trail

**Transition not available:**
- Log a brief note: `Note: Could not transition [key] to [target]. Current Jira status may differ from local status.`
- Continue without failing

**API error:**
- Log a brief note: `Note: Jira sync failed for [key]. Local status updated successfully.`
- Continue without failing

**Missing revision_history field:**
- If `artifacts.[artifact].revision_history` doesn't exist in status.md (older projects created before this field was added), create it as an empty list and append the current entry. This provides forward compatibility with older status files.

**Missing generated_files field:**
- If `artifacts.[artifact].generated_files` doesn't exist, create it using the Glob discovery from Step 5.5. This provides forward compatibility with older status files.

**`sync_scope: full` requested but `ac_field_id` or `owner` missing:**
- Skip the relevant sub-step of Step 6.6 silently (with a note, per Step 6.6a/6.6b), never fail the whole sync.

In all cases, the calling lifecycle command is never blocked by Jira sync issues.

## Output

This utility:
- Transitions Jira Sub-tasks to match local artifact state
- Adds detailed comments with file lists, revision numbers, reviewer details, and feedback for audit trail
- Records each lifecycle event in `artifacts.[artifact].revision_history` in status.md
- Updates `artifacts.[artifact].generated_files` in status.md (via Glob discovery if not already populated)
- Cascades completion up to parent Task and Epic
- Fails gracefully and silently if Jira is unavailable
- Maintains revision_history even when Jira is unavailable
- With `sync_scope: full` (optional, off by default): also reconciles a configured acceptance-criteria custom field and the issue assignee against the artifact's own AC content and recorded owner in status.md — touching only those two named fields, never the description
