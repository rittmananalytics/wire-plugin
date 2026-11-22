---
wire_schema: "1.0"
command: lifecycle
artifact: new
domain: new
release_types: []
action_type: lifecycle
logs_execution: true
description: Create a new Wire engagement or add a release to an existing engagement

delegates_to:
  - utils/director_operating_model
workload: planning
---

# Wire New Command

## Purpose

Interactive workflow to create a new engagement or add a new release to an existing engagement. Handles two-tier folder structure (engagement + releases), status file setup, and artifact scope determination based on the selected release type.

## Terminology

- **Engagement**: A complete client engagement. Contains engagement-wide context (SOW, calls, org charts) and one or more releases.
- **Release**: A scoped, time-boxed unit of delivery within an engagement. Discovery release types (`discovery`, `sop_discovery`) and delivery release types (`full_platform`, `pipeline_only`, etc.) are all release types.

## Release Types

| Type | Description | Typical Artifacts |
|------|-------------|------------------|
| `discovery` | Discovery (Shape Up): scoped, problem-first, solution-shaped before commitment | problem_definition, pitch, release_brief, sprint_plan |
| `sop_discovery` | RA Canonical (SOP) discovery: wide-ranging structured discovery leading to a go/no-go decision on a program of work. Exit deliverable is the sponsor-facing Findings Playback deck. | engagement_brief, stakeholder_map, stakeholder_interview, requirements_matrix, discovery_analyses, findings_playback, delivery_roadmap |
| `full_platform` | Complete data platform (pipelines + dbt + BI + enablement) | All artifacts |
| `pipeline_only` | Data pipeline development only | pipeline_design, pipeline, data_quality, deployment |
| `dbt_development` | dbt models and semantic layer | data_model, dbt, semantic_layer, data_quality |
| `dashboard_extension` | New dashboards on existing platform | requirements, mockups, dashboards, training |
| `dashboard_first` | Interactive mocks drive data model | mockups, viz_catalog, data_model, seed_data, dbt, semantic_layer, dashboards, data_refactor |
| `enablement` | Training and documentation only | training, documentation |
| `agentic_data_stack` | Self-service agentic data stack: governed data layer + semantic layer + per-domain knowledge skills + eval suite. Delivers an installable Claude agentic data stack. | dataset_audit, metric_audit, query_audit, governance_design, semantic_layer_design, canonical_models, lookml_views (Looker only), semantic_layer, knowledge_skill, agent_config, eval_suite, adversarial_config, launch_gate, enablement |
| `droughty` | Schema-introspection and base-layer generation using Droughty. Covers discovery on an existing warehouse (ERD, field docs, QA) and post-dbt base-layer generation (staging SQL, schema tests, base LookML views). Works as a standalone release type or as an optional phase within any delivery release. | droughty_setup, droughty_introspect, droughty_dbml, droughty_docs, droughty_qa, droughty_stage, droughty_dbt_tests, droughty_lookml |
| `custom` | Bespoke scope from SoW or project docs — Wire analyses documents and proposes a tailored release structure with custom specs | Derived from source documents |

## Workflow

### Step 0: Duplicate release detection

Before doing anything else, check whether any release already exists in this repo.

```bash
ls .wire/releases/ 2>/dev/null
```

If `.wire/releases/` exists and contains one or more subdirectories, read each subdirectory name and check whether it contains a `status.md`. If any release with a `status.md` is found:

1. List the existing releases:
   ```
   Found existing releases in this repo:
     - [release_folder_1]  ([release_type from status.md] — [generate/validate/review state of first artifact])
     - [release_folder_2]  ...
   ```

2. Ask the user directly in chat:
   ```
   A release already exists in this repo. To add another release to this engagement, continue (yes).
   To work on an existing release instead, run /wire:start or /wire:status.

   Add a new release? (yes/no)
   ```

3. If "no": stop immediately. Output:
   ```
   Run /wire:status to see the current state of all releases.
   Run /wire:start to pick up where you left off.
   ```

4. If "yes": continue to Step 1 (the engagement context already exists — Step 1 will detect this and jump to Step 6).

This guard prevents a second consultant from accidentally running `/wire:new` on an already-initialised project and overwriting the engagement context or status files.

---

### Step 0b: Invoked by the orchestrating session

When the orchestrating session invokes this command
(`specs/utils/director_operating_model.md`), it has already read the SOW and
the director's directive and derived every answer Steps 1 to 6 would ask for.
It passes them in. In that case:

1. Do not ask Steps 1 to 6. Take the values as given:
   `client_name`, `engagement_name`, `engagement_lead` (from `git config
   user.name`), client domain (from the SOW's contact details, for Fathom
   Sync), `repo_mode`, `sow_path`, `release_type`, `release_name`, and the
   profile where the release type declares one (Step 6b).
2. **Every derived value carries its reason.** The release type in particular:
   the confirmation block says why that type was chosen, in one line, from the
   SOW. A derived value the director cannot check is a guess wearing a
   confirmation prompt.
3. **Anything not derivable is asked, one question at a time, before the
   confirmation block.** The orchestrator does not invent a client name or a
   release name.
4. Go straight to Step 7's confirmation block. It is the one confirmation, and
   it is not optional: nothing is created until the director confirms it.
5. On "Change settings", fall back to the interactive path from Step 2 as
   normal.

Everything after Step 7 runs identically whether the answers were typed or
derived. The engagement structure, `status.md`, the context file and the log
rows are the same either way.

### Step 1: New Engagement or Additional Release?

Check whether `.wire/engagement/context.md` already exists:

```bash
ls .wire/engagement/context.md 2>/dev/null
```

**If `.wire/engagement/context.md` exists** (engagement already set up):
- Ask directly in chat:
  ```
  An engagement already exists in this repo. Add a new release to it? (yes/no)
  If yes, what is the release type?
  ```
- If yes, skip to **Step 6 (Determine Release ID)** and proceed from there.
- If no, confirm whether they want to create a new engagement in the same repo (unusual — confirm explicitly).

**If no engagement exists** (first time):
- Proceed to Step 2.

### Step 2: Ask for Engagement Details

Ask directly in chat (one question at a time):

```
What is the client name for this engagement?
(e.g. "Acme Corporation", "Client M", "Liberus")
```

Wait for user response.

```
What is the engagement name? (descriptive, used in folder names)
(e.g. "acme_data_platform", "power_digital_analytics", "liberus_reporting")
```

Wait for user response.

```
What is your name (engagement lead)?
```

Wait for user response.

```
What is the client's email domain? (e.g. "acme.com")
Used to automatically sync Fathom call transcripts for this engagement into
.wire/engagement/calls/, matched against calendar invitees on each call — so
only calls this client actually attended get pulled in, not unrelated meetings.
Leave blank to skip automatic Fathom sync for this engagement.
```

Wait for user response — this may be blank.

**Derive**:
- `client_name`: Display name as provided
- `engagement_name`: Lowercase, underscores for spaces, no special chars
- `engagement_lead`: As provided
- `client_domain_input`: the domain as provided, or blank

**Resolve `fathom_sync` — enabled by default whenever it's safe to be:**

1. If `client_domain_input` is blank, set `fathom_sync.enabled: false` and `fathom_sync.client_domain: null`. There's nothing safe to filter on without a domain — do **not** fall back to matching on `client_name` as free text; a text search has no way to distinguish "this specific client" from any other meeting that happens to mention the same words.
2. If `client_domain_input` is RA's own domain (`rittmananalytics.com`, case-insensitive, or a subdomain of it) — **or** `client_name` is self-referential (matches "Rittman Analytics", "RA", or similar close variants) — this is an internal engagement, not a client one. Refuse automatic sync regardless of what was typed:
   ```
   This looks like an internal Rittman Analytics engagement, not a client one.
   Fathom Sync matches by calendar-invitee domain — and your own domain is on
   every meeting your team has, internal or client-facing, so it can't safely
   narrow anything here. Skipping automatic Fathom sync for this engagement;
   you can still pull specific calls manually with /wire:utils-meeting-context
   if needed.
   ```
   Set `fathom_sync.enabled: false`, `fathom_sync.client_domain: null` (don't store the RA domain — it should never end up as an active filter, even accidentally, if this field gets read elsewhere later).
3. Otherwise, a real, external, non-RA domain was given: set `fathom_sync.enabled: true`, `fathom_sync.client_domain: <client_domain_input>`. This is the default outcome for a normal client engagement — no separate opt-in question, no extra step; giving a client domain is already part of setting up the engagement.

### Step 3: Repo Mode

Ask directly in chat:

```
Is this repo the client's code repo, or a dedicated delivery repo?

Option A — Combined: The .wire/ folder lives directly in the client's code repo.
           Simple setup. Default for most engagements.

Option B — Dedicated delivery repo: This repo is exclusively for Wire delivery
           artifacts. The client's code repo is separate.
           Use for regulated clients (where adding files to their code repo isn't
           acceptable) or clients with multiple code repos.

Which applies? (A/B)
```

Wait for user response.

**If Option B (dedicated delivery repo)**:

Ask:
```
Please provide the client code repo details:
1. GitHub URL (e.g. https://github.com/client-org/client-repo)
2. Local path on your machine (e.g. /Users/you/Projects/client-repo)
3. Default branch (default: main)
```

Store:
- `client_repo_url`
- `client_repo_local_path`
- `client_repo_branch`

### Step 4: Ask About SOW

Ask directly in chat:

```
Do you have a Statement of Work (SOW) or proposal document?
- If yes, provide the file path (e.g. "path/to/SOW.pdf")
- If no, type "no"
```

Wait for user response. If a path is provided, verify the file exists.

### Step 5: Ask About First Release Type

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What type is the first release for this engagement?",
    "header": "First Release Type",
    "options": [
      {"label": "Discovery (Shape Up)", "description": "Discovery (Shape Up): scoped problem-shaping. Problem definition → pitch → release brief → sprint plan. Use when the problem to solve is reasonably understood and you need to shape a single bet."},
      {"label": "Discovery (SOP / Canonical)", "description": "RA Canonical discovery: wide-ranging structured discovery leading to a go/no-go decision on a program of work. Engagement brief → stakeholder map → interviews → consolidation → three analyses → Findings Playback deck → roadmap. Use when scope is unclear at SoW signature or a new analytical domain is being introduced."},
      {"label": "Full platform", "description": "Complete implementation (pipelines, dbt, BI, enablement)"},
      {"label": "Pipeline only", "description": "Data pipeline development"},
      {"label": "dbt development", "description": "dbt models and semantic layer"},
      {"label": "Dashboard extension", "description": "New dashboards on existing platform"},
      {"label": "Dashboard-first rapid dev", "description": "Interactive mocks drive data model"},
      {"label": "Enablement", "description": "Training and documentation"},
      {"label": "Platform Migration", "description": "Full lifecycle migration of a data platform from one warehouse stack to another. Covers ingestion audit, db object audit, security audit, dbt audit, orchestration audit → migration inventory → strategy → target setup → parallel ingestion → batched dbt translation (models and snapshots, with SCD-2 snapshot history preserved) → orchestration migration → equivalency validation loop → cutover."},
      {"label": "Agentic Data Stack", "description": "Build a governed self-service agentic data stack — dataset governance, semantic layer expansion, per-domain knowledge skills, and an eval suite with per-domain accuracy gates. Delivers an installable Claude agentic data stack skill and maintenance infrastructure."},
      {"label": "Droughty", "description": "Schema introspection and base-layer generation using Droughty. Use for discovery sprints on existing warehouses (ERD, field docs, QA) or as a post-dbt phase to generate staging SQL, schema tests, and base LookML views. Can also be added as an optional phase to any delivery release."},
      {"label": "BI tool migration (Looker to Omni)", "description": "Migrate a reporting layer from Looker to Omni on the same warehouse: audit the Looker estate, decide what moves, build the Omni model on a branch, move the content, prove tile-level parity, cut over."},
      {"label": "Custom", "description": "Bespoke scope not covered by a standard release type. Wire analyses your SoW or plan and proposes a tailored release structure — mapping deliverables to existing commands where possible, generating new project-scoped specs for the rest."}
    ],
    "multiSelect": false
  }]
}
```

Map selection to `release_type`:

| Selected label | `release_type` value |
|---|---|
| Discovery (Shape Up) | `discovery` |
| Discovery (SOP / Canonical) | `sop_discovery` |
| Full platform | `full_platform` |
| Pipeline only | `pipeline_only` |
| dbt development | `dbt_development` |
| Dashboard extension | `dashboard_extension` |
| Dashboard-first rapid dev | `dashboard_first` |
| Enablement | `enablement` |
| Platform Migration | `platform_migration` |
| Agentic Data Stack | `agentic_data_stack` |
| Droughty | `droughty` |
| BI tool migration (Looker to Omni) | `bi_migration` |
| Custom | `custom` |

### Step 6: Determine Release ID

**Process**:
1. Count existing releases in `.wire/releases/` — next release number = count + 1 (padded to 2 digits)
2. For the first release, `release_number = "01"`
3. Ask for a release name:
   ```
   What is the name for this release?
   (e.g. "discovery", "data-foundation", "reporting-layer")
   ```
4. `release_folder = "[release_number]-[release_name]"` (e.g. `01-discovery`)
5. Today's date as `release_id` = `YYYYMMDD` (for status file ID, distinct from folder name)

### Step 6b: Ask the Profile, Where the Release Type Has One

Some release types offer more than one route through the same phases, and
record the choice in `status.md`. Read
`wire/release-types/<release_type>.yaml`: if it declares a `profiles:` block,
ask which one, and write the answer to the front-matter field named by
`profile_field`.

| Release type | `profile_field` | Options | Default |
|---|---|---|---|
| `dashboard_first` | `build_profile` | `seeded`, `live_data` | `seeded` |
| `sop_discovery` | `discovery_profile` | `diagnostic`, `modelling_led` | `diagnostic` |

Ask it with `AskUserQuestion`, using each profile's own `name` and
`description` from the YAML as the option label and description, and marking
the `default_profile` as recommended. Do not hardcode the list here: a release
type that gains a profile in a registry PR must get its question without this
spec being touched.

If the release type declares no `profiles:` block, skip this step and write no
profile field.

**Why this is asked at all.** Until now nothing asked, and the profile field
was left unwritten, so `default_profile` applied silently. `live_data` on a
`dashboard_first` release was only reachable by hand-editing `status.md` after
creation — a route nobody found, on a choice that changes which phases exist.
The default is still the default; it is now a decision rather than an
accident.

Record the answer in the confirmation block below, and in `decisions.md` as a
ruling when the orchestrating session invoked this command.

### Step 7: Confirm Settings

Show derived values:

```
I'll create this engagement and release with these settings:

Engagement:
  Client:         [client_name]
  Engagement:     [engagement_name]
  Lead:           [engagement_lead]
  Repo mode:      [Combined | Dedicated delivery]
  [If dedicated:] Client repo: [client_repo_url]
  SOW:            [sow_path or "none"]

First Release:
  Type:           [release_type]
  [If the type declares profiles:] Profile: [profile_id] — [profile name]
  Folder:         .wire/releases/[release_folder]/
  Release ID:     [release_id]

[When invoked by the orchestrating session, add:]
  Chosen because:  [one line, from the SOW]
  Budget:          [lanes_max] lanes, warehouse spend [none|estimate_required|cap:N], stop at [decisions|phase_end|never]
```

Use `AskUserQuestion` to confirm:

```json
{
  "questions": [{
    "question": "Create this engagement and first release?",
    "header": "Confirm",
    "options": [
      {"label": "Yes, create it", "description": "Create the engagement and release with these settings"},
      {"label": "Change settings", "description": "Let me provide different settings"}
    ],
    "multiSelect": false
  }]
}
```

If "Change settings", return to Step 2.

### Step 8: Git Branch Check

**Process**:
1. Run `git rev-parse --abbrev-ref HEAD` via Bash
2. If command fails (not a git repo), skip silently
3. If branch is `HEAD` (detached), skip silently
4. If branch is `main` or `master`:
   - Suggested branch: `feature/[engagement_name]`
   - Use `AskUserQuestion` to confirm or customise the branch name
   - Create and switch: `git checkout -b [branch_name]`
5. Store `branch_name` for display in the confirmation step

### Step 8.5: Tenant Carve-out Scope Check (existing engagements only)

This step only runs when **both** of these are true:
1. `.wire/engagement/context.md` already existed at the start of this run — this is the same detection used in Step 1 to distinguish "new engagement" from "new release in an existing engagement" (re-run `ls .wire/engagement/context.md 2>/dev/null` here if the result wasn't retained).
2. The release type selected for this new release is `platform_migration`.

If either is false, skip this step entirely and proceed to Step 9 — the `migration.scope` question stays in its normal place at Step 14 Question 9, and Steps 9/9.5 run unmodified.

If both are true, ask the scope question now (pulled forward from Step 14 Question 9) so Steps 9 and 9.5 below can branch on it:

"Is this a **full platform migration** or a **tenant carve-out** (extracting a single tenant's data into the target)?" (Options: Full migration (default) / Tenant carve-out). If **Tenant carve-out** is selected, also ask: "What is the **tenant predicate** that scopes the extracted tenant — the WHERE clause or tenant key? (e.g. `tenant_id = 4815`)".

Store `migration.scope` (`full_migration` | `tenant_carveout`) and `migration.tenant_predicate` here. Step 14 Question 9 must reuse these stored values instead of re-asking when they were already captured in this step.

**If `migration.scope` resolves to `tenant_carveout`**, identify the parent release this carve-out is being spawned from:
1. Read each subdirectory in `.wire/releases/` and check its `status.md` frontmatter for `project_type: "platform_migration"`.
2. If exactly one such release is found, store its folder name as `parent_release_folder`.
3. If more than one is found, ask the user directly: "Which existing release is the parent for this carve-out?" and list the candidates by folder name.
4. If none is found, there is no parent to share from — proceed to Steps 9 and 9.5 as normal (the carve-out branches below only fire when a `parent_release_folder` is identified).

### Step 9: Issue Tracker Integration (Optional)

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Would you like to track this engagement in an issue tracker?",
    "header": "Issue Tracker",
    "options": [
      {"label": "Jira", "description": "Create or link Jira Epic, Tasks, and Sub-tasks"},
      {"label": "Linear", "description": "Create or link a Linear Project, Issues, and Sub-issues"},
      {"label": "Both Jira and Linear", "description": "Track in both Jira and Linear simultaneously"},
      {"label": "No, skip issue tracking", "description": "Track progress in status.md only"}
    ],
    "multiSelect": false
  }]
}
```

**Tenant carve-out branch**: If Step 8.5 identified `migration.scope: tenant_carveout` with a `parent_release_folder`, replace the tracker-specific setup questions below with this upfront share-or-separate choice, asked once per tracker selected above. For non-carve-out releases, or when no `parent_release_folder` was identified, this branch does not fire — proceed with the setup questions exactly as written below.

If Jira or Both was selected:
```json
{
  "questions": [{
    "question": "This carve-out release can either share the parent release's Jira project, or use its own — which do you want?",
    "header": "Carve-out Jira Setup",
    "options": [
      {"label": "Share the parent's Jira project", "description": "Reuse [parent_release_folder]'s Jira project key — this release still gets its own Epic and Tasks, inside that same project"},
      {"label": "Use a separate Jira project", "description": "Set up a new, dedicated Jira project for this carve-out release"}
    ],
    "multiSelect": false
  }]
}
```
- If "Share the parent's Jira project": read `jira.project_key` from `parent_release_folder`'s `status.md` and use it directly as `jira_project_key`. Still ask the normal "How would you like to set up Jira?" mode question below to determine `jira_mode`/`jira_structure` for this release's own issue hierarchy — only the project key question is skipped.
- If "Use a separate Jira project": continue with the normal Jira setup questions below, unchanged (fresh project key + mode).

If Linear or Both was selected, ask the equivalent question for Linear:
```json
{
  "questions": [{
    "question": "This carve-out release can either share the parent release's Linear team/project, or use its own — which do you want?",
    "header": "Carve-out Linear Setup",
    "options": [
      {"label": "Share the parent's Linear team/project", "description": "Reuse [parent_release_folder]'s Linear team and project — this release's issues are created inside that same project"},
      {"label": "Use a separate Linear team/project", "description": "Set up a new, dedicated Linear team identifier and/or project for this carve-out release"}
    ],
    "multiSelect": false
  }]
}
```
- If "Share the parent's Linear team/project": read `linear.team_id` and `linear.project_id` from `parent_release_folder`'s `status.md` and use them directly, with `linear_mode: "create_in_existing"` — skip Questions 1–3 below.
- If "Use a separate Linear team/project": continue with the normal Linear setup Questions 1–3 below, unchanged.

**If Jira or Both selected**: Ask for the Jira project key and preferred mode:
```json
{
  "questions": [{
    "question": "How would you like to set up Jira?",
    "header": "Jira Setup",
    "options": [
      {"label": "Create new Jira issues — sub-tasks per command", "description": "Create Epic per release → one Task per artifact → three Sub-tasks per artifact (generate / validate / review). Each command transitions its own Sub-task."},
      {"label": "Create new Jira issues — single issue per artifact", "description": "Create Epic per release → one Task per artifact (no sub-tasks). The single Task moves through To Do → In Progress (generate) → In Review (validate) → Done (review approved). Requires the Jira project's workflow to support those four states."},
      {"label": "Link to existing Jira issues", "description": "Search a Jira project for existing issues and link them — sub-tasks structure assumed"}
    ],
    "multiSelect": false
  }]
}
```
Store `jira_project_key`, `jira_mode` (`create` or `link`), and `jira_structure` (`subtasks` for the first / third option, `single_issue` for the second). Pass all three to Step 15.

**If Linear or Both selected**: Ask the following as three separate questions in sequence:

**Question 1** — Ask directly in chat:
```
What is the Linear team identifier? (e.g., ENG, DATA, ACME)
```

**Question 2** — Use `AskUserQuestion`:
```json
{
  "questions": [{
    "question": "How would you like to set up Linear?",
    "header": "Linear Setup",
    "options": [
      {"label": "Create new project + new issues", "description": "Wire will create a new Linear project with issues and sub-issues from scratch"},
      {"label": "Use existing project + create new issues", "description": "Wire will create fresh issues inside an existing project — you'll provide the project URL or ID next"},
      {"label": "Link to existing project + existing issues", "description": "Wire will search the team for matching issues and link them to Wire artifacts — you'll provide the project URL or ID next"}
    ],
    "multiSelect": false
  }]
}
```

**Question 3** — Only if "Use existing project + create new issues" or "Link to existing project + existing issues" was selected, ask directly in chat:
```
Paste the Linear project URL or ID (e.g. https://linear.app/acme/project/my-project-abc123):
```

Store `linear_team_id`, `linear_project_id` (if provided, extract from URL or use as-is), and `linear_mode` ("create", "create_in_existing", or "link") for use in Step 15.

### Step 9.5: Document Store Integration (Optional)

**Question 1** — Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Would you like to replicate generated documents to a client-accessible document store for review and annotation?",
    "header": "Document Store",
    "options": [
      {"label": "Confluence", "description": "Publish documents to a Confluence space — reviewers can comment and annotate inline"},
      {"label": "Notion", "description": "Publish documents to a Notion workspace — reviewers can comment and edit pages"},
      {"label": "Both Confluence and Notion", "description": "Publish to both simultaneously"},
      {"label": "No, skip document store", "description": "Documents stay in GitHub only"}
    ],
    "multiSelect": false
  }]
}
```

**Tenant carve-out branch**: If Step 8.5 identified `migration.scope: tenant_carveout` with a `parent_release_folder`, replace Questions 2 and 3 below with this upfront share-or-separate choice, asked once per provider selected in Question 1. For non-carve-out releases, or when no `parent_release_folder` was identified, this branch does not fire — proceed with Questions 2 and 3 exactly as written below.

If Confluence or Both Confluence and Notion was selected:
```json
{
  "questions": [{
    "question": "This carve-out release can either share the parent release's Confluence space, or use its own — which do you want?",
    "header": "Carve-out Confluence Setup",
    "options": [
      {"label": "Share the parent's Confluence space", "description": "Publish this release's documents into [parent_release_folder]'s existing Confluence space"},
      {"label": "Use a separate Confluence space", "description": "Publish this release's documents into their own, dedicated Confluence space"}
    ],
    "multiSelect": false
  }]
}
```
- If "Share the parent's Confluence space": read `docstore.confluence.space_key` from `parent_release_folder`'s `status.md` and use it directly as `confluence_space_key` — skip Question 2 below.
- If "Use a separate Confluence space": continue with Question 2 below, unchanged (ask for a new space key).

If Notion or Both Confluence and Notion was selected, ask the equivalent question for Notion:
```json
{
  "questions": [{
    "question": "This carve-out release can either share the parent release's Notion parent page, or use its own — which do you want?",
    "header": "Carve-out Notion Setup",
    "options": [
      {"label": "Share the parent's Notion parent page", "description": "Publish this release's documents under [parent_release_folder]'s existing Notion parent page"},
      {"label": "Use a separate Notion parent page", "description": "Publish this release's documents under their own, dedicated Notion parent page"}
    ],
    "multiSelect": false
  }]
}
```
- If "Share the parent's Notion parent page": read `docstore.notion.parent_page_id` from `parent_release_folder`'s `status.md` and use it directly as `notion_parent_page_id` — skip Question 3 below.
- If "Use a separate Notion parent page": continue with Question 3 below, unchanged.

**Question 2** — If "Confluence" or "Both Confluence and Notion" was selected, ask directly in chat:
```
What is the Confluence space key where Wire documents should be published?
(e.g. PROJ, ACME, DATA — found in the space URL: /wiki/spaces/PROJ/...)
```
Store `confluence_space_key`.

**Question 3** — If "Notion" or "Both Confluence and Notion" was selected, ask directly in chat:
```
What is the Notion parent page for Wire documents?
Paste the page URL or ID (e.g. https://www.notion.so/My-Projects-abc123 or just the ID).
This page must already exist and be accessible via the Notion MCP.
```
Store `notion_parent_page_id` (extract ID from URL if a full URL was given).

If any document store is selected, follow the workflow in `specs/utils/docstore_setup.md`. Pass the engagement name, release folder, provider choice, `confluence_space_key` (if set), and `notion_parent_page_id` (if set) — the utility should skip re-asking for these when they are already supplied.

If skipped, continue to Step 9.6.

### Step 9.6: Data Model Registry — Automatic Setup Attempt (Conditional, Silent)

This step exists to close a gap: `data_model-generate`'s canonical-vertical matching (see `wire/schemas/data-model-registry.md`) only ever *checks* for a local registry copy, it never *fetches* one — so even an RA consultant with real access to `wire-data-model-registry` would get the feature silently skipped forever unless they happened to know about and manually run `/wire:utils-data-model-registry-setup` first, unprompted. The actual gate should be GitHub repo access, not "did you separately remember to run a setup command." This step makes that true, without adding noise or unnecessary network calls for engagements that will never use the registry.

1. **Check relevance first.** Read `wire/release-types/<release_type>.yaml` for the `release_type` selected in Step 5 (skip this check entirely for `custom` — its scope isn't known yet). If no `phases[].artifacts[]` entry has `id: data_model`, this release type will never call `data_model-generate` — **skip this whole step silently**, nothing to set up. (`pipeline_only`, `dashboard_extension`, `enablement`, `platform_migration`, `agentic_data_stack`, `droughty`, and both discovery types never need this; `full_platform`, `dbt_development`, and `dashboard_first` do.)
2. **Check whether setup was already attempted.** `ls ~/.wire/data_model_registry_setup_attempted 2>/dev/null`. If it exists, skip this step silently — already handled on a prior engagement on this machine, don't re-attempt every time a new engagement is created.
3. **Attempt it.** If the release type needs it and no attempted-marker exists, follow `specs/utils/data_model_registry_setup.md` as an automated (non-interactive) caller — see that spec's Step 1.5 for what changes in that mode. It writes the attempted marker itself; nothing further to do here.
4. **Report minimally.** On success, the setup spec's own automated-mode output (one unobtrusive line) is enough — don't add anything else. On failure, say nothing at all; continue to Step 10 exactly as if this step didn't exist.

If skipped for any reason above, continue to Step 10.

`fathom_sync.enabled`/`client_domain` were already resolved in Step 2 — nothing further to ask here. (Requires the Fathom MCP server to be configured to actually do anything; if it isn't set up yet, `fathom_sync.enabled: true` just means nothing happens until it's reachable — see `skills/fathom-sync/SKILL.md`.)

### Step 10: Create Engagement Folder Structure

```bash
mkdir -p .wire/engagement/calls
mkdir -p .wire/engagement/org
mkdir -p .wire/research/sessions
touch .wire/engagement/calls/.gitkeep
touch .wire/engagement/org/.gitkeep
touch .wire/research/sessions/.gitkeep
```

Make sure `.wire/local/` is git-ignored. It holds each person's own settings (persona override, where their clones of related repos are; `specs/utils/personas.md`, `specs/utils/repos.md`) and is never committed:

```bash
grep -qxF '.wire/local/' .gitignore 2>/dev/null || echo '.wire/local/' >> .gitignore
```

### Step 10.5: Scaffold GitHub PR Template

Create `.github/pull_request_template.md` from the Wire PR template so that every PR raised against this repo is Wire-aware by default.

```bash
mkdir -p .github
```

Read `TEMPLATES/pr_template.md` and write it verbatim to `.github/pull_request_template.md`.

Skip this step silently if `.github/pull_request_template.md` already exists (do not overwrite a customised template).

### Step 11: Create Engagement Context File

Read `TEMPLATES/engagement-context-template.md` and populate:
- `{{ENGAGEMENT_NAME}}` → engagement_name
- `{{CLIENT_NAME}}` → client_name
- `{{CREATED_DATE}}` → today's date (YYYY-MM-DD)
- `{{ENGAGEMENT_LEAD}}` → engagement_lead
- `{{REPO_MODE}}` → `combined` or `dedicated_delivery`
- `{{FATHOM_SYNC_ENABLED}}` → `true` or `false`, resolved in Step 2
- `{{FATHOM_SYNC_CLIENT_DOMAIN}}` → the client domain as a quoted string, or `null` (literal, unquoted) if not set — resolved in Step 2

If repo mode is `dedicated_delivery`, populate the `client_repo` section with the provided URL, local path, and branch.

Leave `related_repos` as the template's commented example. If the person mentioned other client repositories (an Airflow repo, a LookML repo), say they can be listed afterwards with `/wire:utils-repos add`, for read only lookups.

Write to `.wire/engagement/context.md`.

### Step 12: Copy SOW (if provided)

```bash
cp [sow_path] .wire/engagement/sow.md   # or sow.pdf if PDF
```

### Step 13: Create Release Folder Structure

**For discovery release types (`discovery`, `sop_discovery`)**:
```bash
mkdir -p .wire/releases/[release_folder]/{artifacts,planning}
touch .wire/releases/[release_folder]/artifacts/.gitkeep
```

For `sop_discovery`, also create the interview folder used by the per-stakeholder write-ups:
```bash
mkdir -p .wire/releases/[release_folder]/planning/interviews
touch .wire/releases/[release_folder]/planning/interviews/.gitkeep
```

**For `platform_migration` release type**:
```bash
mkdir -p .wire/releases/[release_folder]/{audit,strategy,migration,migration/target_setup_scripts}
touch .wire/releases/[release_folder]/audit/.gitkeep
```

**For `agentic_data_stack` release type**:
```bash
mkdir -p .wire/releases/[release_folder]/{artifacts,artifacts/eval_suite,artifacts/knowledge_skill}
touch .wire/releases/[release_folder]/artifacts/.gitkeep
```

**For `droughty` release type**:
```bash
mkdir -p .wire/releases/[release_folder]/artifacts/droughty
mkdir -p .wire/releases/[release_folder]/artifacts/droughty/field_descriptions
touch .wire/releases/[release_folder]/artifacts/droughty/.gitkeep
```

**For `bi_migration` release type**:
```bash
mkdir -p .wire/releases/[release_folder]/{audit,migration,migration/omni_model,migration/omni_content}
touch .wire/releases/[release_folder]/audit/.gitkeep
```

**For all other release types**:
```bash
mkdir -p .wire/releases/[release_folder]/{artifacts,planning,requirements,design,dev,test,deploy,enablement}
touch .wire/releases/[release_folder]/requirements/.gitkeep
touch .wire/releases/[release_folder]/design/.gitkeep
touch .wire/releases/[release_folder]/dev/.gitkeep
touch .wire/releases/[release_folder]/test/.gitkeep
touch .wire/releases/[release_folder]/deploy/.gitkeep
touch .wire/releases/[release_folder]/enablement/.gitkeep
```

### Step 14: Create Release Status File

**For `discovery` release type**:
1. Read `TEMPLATES/discovery-status-template.md`
2. Replace placeholders:
   - `{{RELEASE_ID}}` → release_id
   - `{{RELEASE_NAME}}` → release_folder (the human-readable name)
   - `{{CLIENT_NAME}}` → client_name
   - `{{ENGAGEMENT_NAME}}` → engagement_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
3. Write to `.wire/releases/[release_folder]/status.md`

**For `sop_discovery` release type**:
1. Read `TEMPLATES/sop-discovery-status-template.md`
2. Replace the same placeholders as above
3. Write to `.wire/releases/[release_folder]/status.md`

**For `platform_migration` release type**:

Ask the following additional questions (one at a time):

1. "What is the **source platform**?" (Options: BigQuery / Snowflake)
2. "What is the **target platform**?" (Must differ from source — re-ask if same platform selected)
3. "What is the **dbt project path**?" (Default: `./dbt` — accept if user presses Enter)
4. "What is the **orchestration tool**?" (Options: Dagster / dbt Cloud / Airflow / None)
5. "What is the **ingestion tool**?" (Options: Fivetran / RudderStack / Coupler.io / Segment / Airbyte / Other). Store as `migration.ingestion_tool` with values `fivetran` / `rudderstack` / `coupler-io` / `segment` / `airbyte` / `other`. Each named tool has a corresponding skill at `wire/skills/<tool>/SKILL.md` and a tool-specific branch in `ingestion-audit-generate`. "Other" covers Stitch, Estuary, and custom-built ingestion — falls back to CSV-driven audit.
6. "What is the **connectivity mode** to the source platform?" (Options: Public endpoint / Private network with MCP tunnel)
   - Also ask: "What **reporting / BI tool** does the client use?" (Options: Looker / Metabase / Omni / OAC / None / Other). Store as `migration.reporting_tool` with values `looker` / `metabase` / `omni` / `oac` / `none` / `other`. `metabase` enables the `metabase-audit` and `metabase-migration` commands; `omni` enables the `omni-audit` and `omni-migration` commands (same reporting-layer migration role, adapted to Omni's connection → model → topic → workbook/tile object hierarchy); `oac` enables the `oac-audit` and `oac-migration` commands (same reporting-layer migration role, adapted to OAC's SMML physical/logical/presentation layer object model); `looker` is the Wire default. This is independent of `migration.scope`.
   - Also ask: "Does the client use a **reverse ETL tool**?" (Options: Hightouch / None / Other). Store as `migration.reverse_etl_tool` with values `hightouch` / `none` / `other`. `hightouch` enables `reverse-etl-audit` and `reverse-etl-migration` as a sixth audit alongside the five core audits (see `wire/skills/hightouch/SKILL.md`); `none` is the default — the sixth audit simply doesn't run. "Other" covers Census and Polytomic, which `reverse-etl-audit`'s spec documents as following the same output shape via tool-specific API branches, but aren't implemented yet — falls back to the same manual `migration.reverse_etl_tool` value with a note that automated cataloguing isn't available for that tool.
7. "What is the **target project / account**?" (The GCP project ID for BigQuery, or Snowflake account identifier for the target environment — the place all migration writes will land.)
8. "Are there any **production project IDs** that should be treated as off-limits for writes?" (Comma-separated list, or press Enter to skip. These are client production environment IDs that Claude will refuse to write to during migration commands.) Store as `data_safety.production_projects` list.
9. "Is this a **full platform migration** or a **tenant carve-out** (extracting a single tenant's data into the target)?" (Options: Full migration (default) / Tenant carve-out). If **Tenant carve-out** is selected, also ask: "What is the **tenant predicate** that scopes the extracted tenant — the WHERE clause or tenant key? (e.g. `tenant_id = 4815`)". Store as `migration.scope` (`full_migration` | `tenant_carveout`) and `migration.tenant_predicate`. If the user selects Full migration or presses Enter, leave `migration.scope` at its default of `full_migration` and `migration.tenant_predicate` null. **If `migration.scope` and `migration.tenant_predicate` were already captured in Step 8.5** (adding a tenant-carve-out release to an existing engagement), skip this question entirely and reuse the stored values — do not ask again.

If **Private network with MCP tunnel** is selected, output these setup instructions and wait for confirmation before proceeding:

```
Private network connectivity selected.

To proceed, set up the MCP tunnel to your source platform:
1. Ensure the MCP tunnel agent is running on your network
2. Add the tunnel MCP server to .claude/settings.json under mcpServers
3. Test connectivity: the tunnel should expose source platform SQL access

Confirm when the tunnel is active and accessible. (Type "tunnel ready" to continue)
```

Wait for confirmation before continuing.

Store `source_platform`, `target_platform`, `dbt_project_path`, `orchestration_tool`, `ingestion_tool`, `reporting_tool`, `reverse_etl_tool`, `connectivity`, `target_project_or_account`, `production_projects`, `scope`, `tenant_predicate`.

1. Read `TEMPLATES/migration/status_migration.md`
2. Replace placeholders:
   - `{{PROJECT_ID}}` → release_id
   - `{{PROJECT_NAME}}` → release_folder
   - `{{CLIENT_NAME}}` → client_name
   - `{{ENGAGEMENT_NAME}}` → engagement_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
   - `{{SOURCE_PLATFORM}}` → source_platform
   - `{{TARGET_PLATFORM}}` → target_platform
   - `{{DBT_PROJECT_PATH}}` → dbt_project_path
   - `{{ORCHESTRATION_TOOL}}` → orchestration_tool
   - `{{INGESTION_TOOL}}` → ingestion_tool
   - `migration.reporting_tool` → reporting_tool if captured; otherwise leave the template default `none` unchanged
   - `migration.reverse_etl_tool` → reverse_etl_tool if captured; otherwise leave the template default `none` unchanged
   - `{{CONNECTIVITY}}` → connectivity
   - `migration.target_project` (BigQuery) or `migration.target_account` (Snowflake) → target_project_or_account
   - `data_safety.target_project` → target_project_or_account (same value — mirrors the migration section)
   - `data_safety.production_projects` → production_projects list (empty list if user skipped)
   - `migration.scope` → `tenant_carveout` if the user selected tenant carve-out; otherwise leave the template default `full_migration` unchanged
   - `migration.tenant_predicate` → tenant predicate string if captured; otherwise leave null
3. Write to `.wire/releases/[release_folder]/status.md`

> When `migration.scope` is left at `full_migration` (the default for any non-carve-out migration), every existing migration command behaves exactly as before — `scope` and `tenant_predicate` carry their default values and no command branches on them. The carve-out steps only activate when `scope` is explicitly `tenant_carveout`.

**For `agentic_data_stack` release type**:

Ask seven additional questions (one at a time):

1. "What **BI tool** is in use?" (Options: Looker / Tableau / Power BI / Metabase / Omni / Other)
2. "What **semantic layer** exists?" (Options: dbt Semantic Layer / MetricFlow / LookML explores / Cube / Omni model / OAC (SMML) / None)
3. "What is the **dbt project path**?" (Default: `./` — accept if user presses Enter; enter "none" if no dbt project)
4. "What **warehouse** does the client use?" (Options: BigQuery / Snowflake / Databricks / Redshift)
5. "What is the **primary business domain**?" (Options: ecommerce / SaaS / marketing analytics / finance / Other)
6. "Approximately how many tables are in the analytics schema?" (Free text — used to calibrate audit scope)
7. "Is **query history** accessible?" (Options: Yes — full query log access / Yes — limited (last 30 days) / No — will use stakeholder input)

Store `bi_tool`, `semantic_layer`, `dbt_project_path`, `warehouse`, `primary_domain`, `table_count_approx`, `query_history_access`.

1. Read `TEMPLATES/agentic_data_stack/status_agentic_data_stack.md`
2. Replace placeholders:
   - `YYYYMMDD_client_agentic_data_stack` → release_id
   - `Client Name` → client_name
   - `Consultant Name` → engagement_lead
   - `YYYY-MM-DD` (start_date) → today's date
   - Update `warehouse`, `bi_tool`, `semantic_layer`, `dbt_project_path`, `primary_domain`, `query_history_access` from answers above
3. Write to `.wire/releases/[release_folder]/status.md`

Also create the agentic_data_stack release folder structure:
```bash
mkdir -p .wire/releases/[release_folder]/{artifacts,artifacts/eval_suite,artifacts/knowledge_skill}
touch .wire/releases/[release_folder]/artifacts/.gitkeep
```

**For `droughty` release type**:

Ask two additional questions (one at a time):

1. "What **warehouse** does the client use?" (Options: BigQuery / Snowflake)
2. "What is the **Droughty context** for this release?" (Options: Discovery / audit on existing warehouse / Post-dbt deploy — generate base layer from deployed models / Both — full sequence)

Map context to `droughty_context` value: `discovery` / `post_dbt` / `full`

Store `warehouse` and `droughty_context`.

1. Read `TEMPLATES/droughty-status-template.md`
2. Replace placeholders:
   - `{{RELEASE_ID}}` → release_id
   - `{{RELEASE_NAME}}` → release_folder
   - `{{CLIENT_NAME}}` → client_name
   - `{{ENGAGEMENT_NAME}}` → engagement_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
   - `{{DROUGHTY_CONTEXT}}` → droughty_context
3. Set `droughty.warehouse` from the warehouse answer
4. Write to `.wire/releases/[release_folder]/status.md`

**For `custom` release type**:
1. Read `TEMPLATES/custom-status-template.md`
2. Replace placeholders:
   - `{{PROJECT_ID}}` → release_id
   - `{{PROJECT_NAME}}` → release_folder
   - `{{CLIENT_NAME}}` → client_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
   - `{{RELEASE_FOLDER}}` → release_folder
   - `{{SOURCE_DOCUMENTS}}` → "TBD — provided in /wire:custom-define"
3. Write to `.wire/releases/[release_folder]/status.md`
4. **Invoke `wire/specs/custom/define.md`** to handle document ingestion, deliverable mapping, custom spec generation, and `.claude/commands/` wrapper creation. The `define` command handles all remaining scaffolding — do not write a standard deliverables section to status.md; `define` does this after the user confirms the proposed structure.

**For `bi_migration` release type**:

First ask: "Is the source **Looker**, **Looker Studio** (Data Studio), **Tableau**, **Metabase** or **Omni**?" Omni records `bi_pair: omni_to_looker` (experimental: say so in one sentence and point to the tutorial's limitations), and asks for the Omni base URL, the shared model id and CLI profile, the dashboards or folders in scope (or all), the Looker base URL and project, and the LookML repo URL; it writes them to the `bi_migration.source` and `bi_migration.target` blocks and skips the other sources' questions. Tableau and Metabase then ask for the target, Looker or Omni. With Omni as the target, Tableau records `bi_pair: tableau_to_omni` and Metabase records `bi_pair: metabase_to_omni` (both experimental: say so in one sentence); each asks the same source questions as its Looker pair below, then the Omni base URL, model id and CLI profile and the parallel-run days, writes them under `bi_migration` and skips the LookML and Looker questions. With Looker as the target, Metabase records `bi_pair: metabase_to_looker` (experimental: say so in one sentence and point to the tutorial's limitations), and asks for the instance URL, the dashboards in scope (or all), the Looker base URL and project, and the LookML repo URL; it writes them to the `bi_migration.source` and `bi_migration.target` blocks and skips the other sources' questions. Tableau records `bi_pair: tableau_to_looker` (experimental: say so in one sentence and point to the tutorial's limitations), and asks for the edition (Cloud, Server, or Desktop files), the server URL and site or the files path, the Looker base URL and project, and the LookML repo URL; it writes them to the `bi_migration.source` and `bi_migration.target` blocks and skips the other source's questions. Looker records `bi_pair: looker_to_omni` and asks the questions below. Looker Studio then asks for the target, Omni or Looker: Omni records `bi_pair: looker_studio_to_omni`, Looker records `bi_pair: looker_studio_to_looker` and also asks for the Looker base URL and project and the LookML repo URL (both experimental: say so when offering them, in one sentence, and point to the tutorial's limitations). Both ask: the report URLs in scope; a short client slug for object identities (`looker_studio_namespace`); who approved automated read-only access to the reports and when (`looker_studio_capture_consent`, may be left empty until the audit); the Omni base URL, model id and CLI profile; the parallel-run days. It writes them under `bi_migration` in the status file and skips the LookML and Looker questions.

For Looker, ask the following additional questions (one at a time):

1. "Where is the **LookML repo** checked out locally?" (Default: `./lookml`. Accept if the user presses Enter. The path must exist.)
2. "What is the **Looker base URL**?" (e.g. `https://client.looker.com`)
3. "What is the **Omni base URL**?" (e.g. `https://client.omniapp.co`)
4. "What is the **Omni model id** the migrated model will be built in?" (From the Omni model IDE URL. The model must already exist; `/wire:omni-target-setup-generate` creates the branch, not the model.)
5. "Which **Omni CLI profile** should Wire use?" (Optional. Press Enter to use the active profile from `omni config show`.)
"Is the LookML project in a **git repository Wire can clone**? Give the GitHub URL (repo root, or `/tree/<branch>/<subfolder>`), or press Enter to use the local path only." Storing a URL registers the `lookml` source so the audit reads a refreshed snapshot and every row carries a commit; the local path alone cannot support `migration-drift-generate`.
"Is the **Omni model git-connected**? Give the model repo URL, or press Enter for none." Storing a URL registers the `omni_model` source and a `bi_target_model` client repo so `omni-model-reverse-port` can read what client modellers change in Omni.
6. "How many days will Looker and Omni **run in parallel** before cutover?" (Default: 60)

Store `lookml_repo_path`, `looker_base_url`, `omni_base_url`, `omni_model_id`, `omni_profile`, `parallel_run_days`.

1. Read `TEMPLATES/bi-migration-status-template.md`
2. Replace placeholders:
   - `{{PROJECT_ID}}` → release_id
   - `{{PROJECT_NAME}}` → release_folder
   - `{{CLIENT_NAME}}` → client_name
   - `{{ENGAGEMENT_NAME}}` → engagement_name
   - `{{CREATED_DATE}}` → today's date
   - `{{LAST_UPDATED}}` → today's date
   - `{{LOOKML_REPO_PATH}}` → lookml_repo_path
   - `{{LOOKER_BASE_URL}}` → looker_base_url
   - `{{OMNI_BASE_URL}}` → omni_base_url
   - `{{OMNI_MODEL_ID}}` → omni_model_id
   - `{{PARALLEL_RUN_DAYS}}` → parallel_run_days
   - `bi_migration.omni_profile` → omni_profile if given; otherwise leave the template default `null`
   - `migration_sources.lookml` → when a LookML repo git URL was given, the block `migration-source-register` would write (`specs/migration/migration_source/register.md` Step 4: `git_repo`, `branch`, `subfolder`, `local_snapshot_path` `.wire/releases/[release_folder]/migration/source_snapshot/lookml/`, `last_refreshed: null`, `last_commit: null`); otherwise leave `null` and rely on `bi_migration.lookml_repo_path`
   - `migration_sources.omni_model` and `migration.client_repos[]` (`role: bi_target_model`) → when an Omni model git repo URL was given; otherwise leave `null` and `[]`
3. Write to `.wire/releases/[release_folder]/status.md`

The `bi_pair` field is written by the profile step below (the release type declares eight profiles, `looker_to_omni`, which is the default, `looker_studio_to_omni`, `tableau_to_omni`, `metabase_to_omni`, `looker_studio_to_looker`, `tableau_to_looker`, `metabase_to_looker` and `omni_to_looker`). When the orchestrating session runs this command from a directive, it derives these answers from the directive and the SOW where it can and asks only for what is missing, per `specs/utils/director_operating_model.md`.

**For all other release types**:
1. Read `TEMPLATES/status-template.md`
2. Replace placeholders (same pattern, using `{{PROJECT_ID}}` → release_id etc.)
3. Set artifact scope based on release type (same logic as prior `new.md` Step 8)
4. Write to `.wire/releases/[release_folder]/status.md`

**Applies to every release type — after the template is written:**

1. **Profile.** If Step 6b asked a profile question, write the answer to the
   front-matter field named by the release type's `profile_field`. Where the
   release type declares profiles and the field is absent from the template,
   add it.
2. **Budget.** If the director gave budget instructions in prose ("two lanes,
   nothing against a warehouse, stop at decisions"), write the `budget:` block
   from `specs/utils/director_operating_model.md`, with `set_by` as the
   director's name and `set_at` as today. If they gave none, omit the block —
   the defaults apply (4 lanes, no warehouse restriction, stop at decisions)
   and an absent block is how a release says "no budget was set".
3. **Claim.** When the orchestrating session created the release, it claims it:
   write `agents.mode: orchestrated` and the `coordinator_session` block (user,
   session id, current branch, `claimed_at`, `last_write`). When a person
   created it by hand, leave `agents.mode` null. A claim is written by whatever
   is going to dispatch, not by creation itself.
4. **Parked decisions.** `parked_decisions: []`. A new release has none.

### Step 15: Set Up Issue Tracker(s) (if opted in)

**If Jira or Both selected**: Follow the workflow in `specs/utils/jira_create.md`. Pass `jira_project_key`, `jira_mode`, `jira_structure`, release type, and artifact scope.

**If Linear or Both selected**: Follow the workflow in `specs/utils/linear_create.md`. Pass `linear_team_id`, `linear_mode`, release type, and artifact scope.

When **Both** is selected, run both workflows. They operate independently — failures in one do not block the other.

### Step 16: Confirm Creation and Guide Next Steps

```
## Engagement Created ✅

**Client**: [client_name]
**Engagement**: [engagement_name]
**Branch**: [branch_name]
**Repo mode**: [Combined | Dedicated delivery]

### Folder Structure

.wire/
├── engagement/
│   ├── context.md          # Engagement overview and stakeholders
│   ├── sow.md              # [if copied]
│   ├── calls/              # Call transcripts
│   └── org/                # Org charts and stakeholder details
├── releases/
│   └── [release_folder]/   # [release_type]
│       ├── status.md       # Release tracking
│       ├── artifacts/      # Source materials
│       └── planning/       # [discovery: planning docs; sop_discovery also has planning/interviews/]
└── research/
    └── sessions/           # Research findings (auto-populated)

### Next Steps

[If `discovery`]:
1. Generate the problem definition:
   /wire:problem-definition-generate [release_folder]

2. Or start a session first:
   /wire:session-start [release_folder]

[If `sop_discovery`]:
1. Draft the engagement brief from the signed SoW and deal record:
   /wire:engagement-brief-generate [release_folder]

2. Then build the stakeholder map:
   /wire:stakeholder-map-generate [release_folder]

3. Or start a session first:
   /wire:session-start [release_folder]

[If delivery release type]:
1. Add source materials to .wire/releases/[release_folder]/artifacts/
2. Generate requirements:
   /wire:requirements-generate releases/[release_folder]

3. Or start a session first:
   /wire:session-start [release_folder]

[If `droughty` release type]:
1. Configure Droughty — install and connect to the warehouse:
   /wire:droughty-setup releases/[release_folder]

2. Then run the Droughty phase (or individual commands):
   /wire:droughty-generate releases/[release_folder]

[If `custom` release type]:
Custom spec generation is already underway via /wire:custom-define.
Once complete, invoke your first custom generate command:
  /[first-artifact-name]-generate [release_folder]

Or check what commands were created:
  ls .wire/releases/[release_folder]/custom-commands/

### Quick Commands

| Command | Purpose |
|---------|---------|
| `/wire:session-start [folder]` | Start a focused working session |
| `/wire:status releases/[folder]` | Check release status |
| `/wire:problem-definition-generate [folder]` | [discovery] Start the Shape Up workflow |
| `/wire:engagement-brief-generate [folder]` | [sop_discovery] Start the SOP discovery workflow |
| `/wire:requirements-generate releases/[folder]` | [delivery] Generate requirements |
| `/wire:migration-audit-all [folder]` | [platform_migration] Run all 5 source platform audits in parallel |
| `/wire:ingestion-audit-generate [folder]` | [platform_migration] Audit Fivetran connectors on source platform |
| `/wire:ads-audit-all [folder]` | [agentic_data_stack] Run all three audits in parallel |
| `/wire:ads_dataset-audit-generate [folder]` | [agentic_data_stack] Inventory warehouse tables and grade governance maturity |
| `/wire:ads_metric-audit-generate [folder]` | [agentic_data_stack] Inventory metric definitions and coverage gaps |
| `/wire:ads_query-audit-generate [folder]` | [agentic_data_stack] Analyse query history for question patterns |
| `/wire:droughty-setup [folder]` | [droughty] Install Droughty and generate profile.yaml + droughty_project.yaml |
| `/wire:droughty-generate [folder]` | [droughty] Run the full Droughty phase in sequence |
```

## Edge Cases

### Adding a release to an existing engagement

If `.wire/engagement/context.md` already exists, skip Steps 2–5 (engagement setup) and jump to Step 6. Read the existing engagement context to pre-populate client name, engagement name, and lead. Only ask for the release type and name.

### Not a Git Repository

If `git rev-parse --abbrev-ref HEAD` fails, skip the branch check silently.

### Release name conflicts

If `.wire/releases/[release_folder]/` already exists, append a letter suffix (`-b`, `-c`).

### SOW File Not Found

If the SOW path provided doesn't exist, prompt again or offer to continue without SOW.

## Output

This command creates:
- `.wire/engagement/` directory and `context.md`
- `.wire/releases/[release_folder]/` directory structure
- `.wire/releases/[release_folder]/status.md`
- `.wire/research/sessions/` directory
- `.github/pull_request_template.md` (Wire-aware PR template)
- Copies SOW to `engagement/` if provided
