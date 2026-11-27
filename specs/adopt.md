---
wire_schema: "1.0"
command: lifecycle
artifact: adopt
domain: adopt
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Adopt an in-flight project into the Wire Framework — assess current state, map existing work to Wire artifacts, set up engagement structure, and generate an adoption playbook
argument-hint: [repo-path-or-url]

workload: planning
---

# Wire Adopt Command

## Purpose

`/wire:adopt` onboards an existing in-flight project into the Wire Framework. It works on any repo regardless of prior Wire usage — from zero history to a partially complete or stalled Wire engagement — and produces a clear picture of what has been done, what exists but needs Wire import, and what still needs to be delivered.

The command works by gathering context from multiple sources simultaneously (repo contents, Slack, HubSpot, Harvest, Jira, Confluence, Fathom), synthesising them into a project assessment, setting up the `.wire/` folder structure with accurate initial states, and generating an **adoption playbook** — a specialised variant of the standard playbook that shows four-state status per artifact and cites source evidence for each assessment.

## Usage

```bash
/wire:adopt                              # adopt the current repo
/wire:adopt /path/to/local/repo          # adopt a local repo at a given path
/wire:adopt https://github.com/org/repo  # assess a remote repo (read-only — outputs plan only)
```

## Prerequisites

- Run from inside a git repository (or provide a path/URL)
- At least one of the external MCP sources should be accessible for best results, but all are optional — the command degrades gracefully

---

# Phase 1: Target Resolution

## Step 1.1: Resolve the Target Repo

If no argument is provided, confirm the current directory is a git repo:
```bash
git rev-parse --show-toplevel 2>/dev/null
```

If an argument is provided:
- **Local path**: verify the path exists and is a git repo. `cd` to it for subsequent operations.
- **GitHub URL**: clone to a temporary directory (`/tmp/wire-adopt-[timestamp]/`). Set a flag `remote_repo: true` — in remote mode the command produces a plan document but does not write to the repo or set up `.wire/` structure.

Capture:
- `repo_root`: absolute path to the repo
- `repo_name`: basename of the repo directory
- `remote_repo`: true/false

## Step 1.2: Derive the Client Name

Check sources in order, stopping at the first match:
1. `.wire/engagement/context.md` — read `client_name`
2. `README.md` — look for a project/client heading in the first 30 lines
3. Repo name — strip common suffixes (`-data`, `-analytics`, `-platform`, `-dbt`, `-looker`)
4. Ask the user directly:
   ```
   What is the client name for this project? (used to search Slack, HubSpot, Jira, Confluence)
   ```

Store as `client_name`.

---

# Phase 2: Multi-Source Discovery

Dispatch all external source queries in parallel as sub-agents. Each agent receives `client_name`, `repo_root`, and today's date as context. Each returns a structured findings object; the main session waits for all to complete before proceeding to Phase 3.

The repo scan (Agent E) runs in parallel with the external queries and does not block them.

## Agent A: Slack

**Goal**: Find recent team discussion about this client/project.

1. Use `slack_search_channels` to find candidate channels. Search for:
   - `clients-[client_name_lowercase_hyphenated]`
   - `clients-[first_word_of_client_name]`
   Try both hyphen and underscore variants. If multiple candidates found, include all that start with `clients-`.

2. For each candidate channel, use `slack_read_channel` to retrieve messages from the last 60 days.

3. Identify and read both the client-facing channel (`#clients-[name]`) and internal channel (`#clients-[name]-internal` or `#clients-[name]_internal`) if present.

4. Extract and return:
   - **Last message date** in each channel
   - **Active participants** (names/handles)
   - **Blockers or risks** mentioned (keyword scan: "blocked", "waiting", "issue", "problem", "stuck", "delayed", "at risk")
   - **Key decisions** mentioned (keyword scan: "decided", "agreed", "confirmed", "signed off", "approved")
   - **Recent status signals** — last 10 messages from each channel, summarised
   - **Channel names found** (for the report citations)

5. Fail gracefully if Slack MCP is unavailable or no matching channels are found. Return `slack: not_available` or `slack: no_channels_found`.

## Agent B: HubSpot

**Goal**: Find the deal, establish contract scope and status, retrieve the deal ID for Harvest cross-reference.

1. Use `search_crm_objects` to search Deals by client name. Try:
   - Exact client name
   - First word of client name
   Return all matches with stage, value, and close date.

2. If multiple deals found, select the most recently updated active deal. If ambiguous, present candidates and ask the user to confirm:
   ```
   Found [N] HubSpot deals for "[client_name]":
   1. [Deal name] — Stage: [stage], Value: [value], Updated: [date]
   2. ...
   Which deal is this engagement? (enter number, or "none")
   ```

3. For the selected deal, retrieve:
   - `deal_id`: internal HubSpot ID
   - `deal_name`: deal name as entered in HubSpot
   - `deal_stage`: current pipeline stage
   - `deal_value`: contract value
   - `close_date`: expected or actual close date
   - `deal_notes`: any notes or description on the deal
   - `hubspot_contacts`: associated contacts (name, role)
   - `hubspot_activity`: last 5 activities/notes logged

4. Return the full object including `deal_id` for use by Agent F (Harvest).

5. Fail gracefully if HubSpot MCP is unavailable or no deal is found. Return `hubspot: not_available` or `hubspot: no_deal_found`.

## Agent C: Atlassian (Jira + Confluence)

**Goal**: Find tracked work items and existing documentation.

**Jira**:
1. Use `searchJiraIssuesUsingJql` with:
   ```
   project text ~ "[client_name]" OR summary ~ "[client_name]" ORDER BY updated DESC
   ```
   Also try searching by first word of client name if no results.

2. For each matching project/epic found, retrieve:
   - Epic name and status
   - Count of issues by status (To Do / In Progress / Done)
   - Most recently updated issues (up to 10)
   - Any issues with labels matching Wire artifact names

3. Return: `jira_projects` (list), `issue_summary` (by status), `recent_issues`, `wire_artifact_issues` (issues that look like Wire artifacts).

**Confluence**:
1. Use `searchConfluence` with:
   ```
   text ~ "[client_name]" AND space.type = "global" ORDER BY lastModified DESC
   ```

2. For each result page, retrieve title, space, last modified date, and a brief excerpt.

3. Look specifically for pages whose titles suggest Wire artifact equivalents:
   - "requirements", "scope", "brief", "SOW" → `requirements`
   - "architecture", "pipeline", "data flow" → `pipeline_design`
   - "data model", "ERD", "entity" → `conceptual_model` / `data_model`
   - "dashboard", "mockup", "wireframe" → `mockups` / `dashboards`
   - "deployment", "go-live", "runbook" → `deployment`
   - "training", "enablement", "handover" → `training` / `documentation`
   - "test plan", "UAT" → `uat`

4. Return: `confluence_pages` (list with titles, spaces, dates, and mapped Wire artifact categories).

5. Fail gracefully if Atlassian MCP is unavailable. Return `atlassian: not_available`.

## Agent D: Fathom

**Goal**: Find call recordings for this client to surface recent decisions and action items.

Follow the same pattern as `wire/specs/utils/meeting_context.md` but scoped to the client generally (not a specific artifact):

1. Use `search_meetings` with `client_name` as search term.
2. Use `list_meetings` filtered to recent dates (last 90 days).
3. Deduplicate by recording ID. Retrieve summaries for the top 5 most recent/relevant meetings.
4. Extract: last call date, key decisions, open action items, participants.

5. Fail gracefully if Fathom MCP is unavailable. Return `fathom: not_available`.

## Agent E: Repo Scan

**Goal**: Establish what exists in the repo — Wire state, data stack components, and candidate content for artifact mapping.

### E1: Wire State Detection

Check `.wire/` directory:

```bash
ls .wire/ 2>/dev/null
ls .wire/engagement/ 2>/dev/null
ls .wire/releases/ 2>/dev/null
```

Classify into one of four states:

| State | Criteria | Label |
|-------|----------|-------|
| `none` | No `.wire/` directory | No prior Wire usage |
| `legacy` | `.wire/` exists but no `releases/` subfolder (old flat structure) | Previous Wire version |
| `stalled` | `.wire/engagement/context.md` + `releases/` exist, at least one release folder | Wire engaged but stalled |
| `active` | As stalled but last git commit to `.wire/` within 14 days | Wire recently active |

If `stalled` or `active`:
- Read `.wire/engagement/context.md`
- List all release folders under `.wire/releases/`
- For each release, read `status.md` and extract all artifact states

### E2: Data Stack Detection

Scan for file patterns that indicate which Wire artifact categories have work already done:

| Pattern | Wire artifact signal |
|---------|---------------------|
| `dbt/models/staging/**/*.sql` | `dbt` — staging layer |
| `dbt/models/integration/**/*.sql` | `dbt` — integration layer |
| `dbt/models/warehouse/**/*.sql` or `*_fact.sql`, `*_dim.sql` | `dbt` — warehouse layer |
| `*.view.lkml`, `*.model.lkml`, `*.explore.lkml` | `semantic_layer` |
| `*.dashboard.lookml` | `dashboards` |
| `fivetran_config*.yml`, `airbyte_config*/` | `pipeline` |
| `dags/*.py`, `*.airflow.py`, `cloud_scheduler*/` | `orchestration` |
| `terraform/`, `*.tf` | `deployment` |
| `tests/**/*.py`, `data_quality*/` | `data_quality` |

For each signal found, record:
- File count
- Most recent modification date (from git log)
- Naming convention check (do files follow Wire conventions?)

### E3: Document Scan

Search for document files that might correspond to Wire artifacts. Check these directories: `docs/`, `documentation/`, `deliverables/`, `analysis/`, `design/`, `requirements/`, repo root.

For each `.md`, `.pdf`, `.docx`, `.xlsx`, `.pptx` found:
- Record filename, path, size, last modified date
- Score against Wire artifact keywords (same mapping table as Agent C Confluence)
- Flag as a candidate recognized file with confidence: `high` (filename directly matches), `medium` (content keywords match), `low` (in a relevant folder but unclear)

### E4: Git Log Analysis

```bash
git log --oneline --since="90 days ago" --stat | head -100
git log --oneline --format="%ae %ad %s" --date=short | head -30
```

Extract:
- Last commit date
- Active committers (names/emails) in last 90 days
- Commit frequency (commits per week — signal for activity level)
- Most-changed directories (indicates where active work is happening)

### E5: Related Repo Signals

Look for signs that the client's work spans other repositories (wire#381, `specs/utils/repos.md`). Read only this repo; never clone or fetch another one here.

| Signal | Suggests a related repo with role |
|---|---|
| `sources:` in dbt YAML whose schema is loaded by nothing in this repo (no pipeline or DAG config here names it) | `orchestration` or `ingestion`: whatever lands those tables |
| DAG files (`dags/`, `dags_*/`) that call `dbt` (`dbt run`, `dbt build`, a dbt operator) when this repo has no `dbt_project.yml` | `dbt` |
| A `dbt_project.yml` here, and LookML or Omni files nowhere in this repo, with a BI tool named in the README | `lookml` or `omni` |
| A GitHub URL to another repository of the same org in `README*`, `docs/`, CI files, `packages.yml` (git packages) or `.gitmodules` | by its contents' description, else `other` |
| `client_repo:` in an existing `context.md` | already listed; do not propose again |

For each candidate record: the URL if one was found, the proposed id (the repo name, shortened) and role, and the evidence with its path in this repo. A signal with no URL is still reported ("the dbt sources in schema `landing_shop` are loaded elsewhere; which repository?"), so the person can name it.

Return all findings as a structured object.

## Agent F: Harvest (Sequential — requires Agent B output)

Wait for Agent B to return `deal_id` before dispatching.

**Goal**: Establish real hours burned by phase, budget status, and true activity date.

1. Use `Get_data_of_all_projects` filtered by client name or search for a project matching `deal_name` from HubSpot.

2. For the matching project, retrieve:
   - Total hours logged vs. budget
   - Hours broken down by task/phase (each Harvest task = a project phase)
   - Last time entry date (most reliable signal of real project activity)
   - Active team members (who has logged time in last 30 days)
   - `Get_data_of_all_time_entries` filtered to this project, grouped by task

3. Map Harvest task names to Wire artifact categories where possible (fuzzy match on task name).

4. Return: `harvest_project`, `hours_by_task`, `budget_burn_pct`, `last_entry_date`, `active_members`.

5. Fail gracefully if Harvest MCP is unavailable or no project found. Return `harvest: not_available` or `harvest: no_project_found`.

---

# Phase 3: Synthesis and Divergence Detection

Collect all agent results. Build a unified project picture.

## Step 3.1: Establish Ground Truth Activity Date and Engagement State

The most reliable indicator of when this project was last active, in priority order:
1. Harvest: `last_entry_date` (if available)
2. Git log: last commit date
3. Jira: most recently updated issue date
4. Slack `#shopfloor`: last EOD update mentioning the client (Move/Stuck/Watch — the most operationally accurate picture)
5. Slack `#clients-[name]`: last message date

Report the top two sources and flag if they diverge by more than 14 days.

**Engagement state**: Use `fathom.engagement_state_signal` from the client context to classify the project's current state. If Fathom is unavailable, infer from Slack signals:

| State | Wire implication |
|-------|-----------------|
| `steady_state_sprint` | Active delivery — Wire adopt should set up for resumption at the stalled artifact |
| `discovery` | Discovery phase in progress — adopt should create or resume a `discovery` or `sop_discovery` release |
| `closeout_suspension` | Engagement winding down — note explicitly in the adoption playbook; Wire setup may be for documentation/handover purposes only |
| `mobilisation` | Not yet in sprint cadence — Wire adopt is establishing structure ahead of delivery start |

This state affects how the adoption playbook frames "next steps" — a `closeout_suspension` engagement needs very different guidance than a `steady_state_sprint` one.

## Step 3.2: Divergence Detection

Check for mismatches between sources. Flag each as a named divergence with severity:

**High severity (⚠️)**:
- Harvest shows hours logged to a phase, but no corresponding files exist in the repo for that phase
- Jira issues marked "Done" for an artifact, but Fathom action items or Slack messages suggest it was never actually approved
- Slack `#clients-[name]-internal` mentions a blocker that has no corresponding Jira issue and no HubSpot note

**Medium severity (⚡)**:
- Last Harvest entry date and last git commit date differ by more than 21 days (billing or delivery running ahead/behind)
- HubSpot deal stage is "In Delivery" but Slack shows no client-facing activity in 30+ days
- Confluence page for an artifact is more recent than the corresponding file in the repo

**Low severity (ℹ️)**:
- Jira issue count for a phase is high but corresponding artifacts are sparse — indicates fine-grained task tracking rather than Wire-style artifact tracking
- Harvest tasks don't map cleanly to Wire artifact categories (typical for manually structured projects)

## Step 3.3: Infer Release Type

From repo scan findings, propose the most likely Wire release type:

| Evidence | Inferred type |
|----------|--------------|
| dbt all-3-layers + LookML + dashboard files | `full_platform` or `dbt_development` |
| dbt all-3-layers + LookML, no dashboards | `dbt_development` |
| Pipeline config only, no dbt | `pipeline_only` |
| LookML + dashboards, no dbt | `dashboard_extension` |
| Mockup docs + data model spec only | `dashboard_first` |
| Training/doc files only | `enablement` |
| Mixed/unclear | present top 2 candidates with evidence |

If Wire state is `stalled` or `active`, read `project_type` from the existing `status.md` and use that, noting any discrepancy with what the repo actually contains.

Present the inference to the user and ask for confirmation:
```
Based on the repo contents and external sources, this looks like a [inferred_type] engagement.
Does that sound right? (yes / no — if no, what type?)
```

## Step 3.4: Build the Artifact Map

For each artifact in the inferred release type's sequence, determine its state using this priority logic:

1. **Wire-complete** (✅): `.wire/` artifact exists with `review: approved`
2. **Wire-stalled** (⏳): `.wire/` artifact exists but `generate: complete` with `validate: fail` or `review: changes_requested`; or `generate: not_started` with `validate: not_started` when later artifacts are complete (implies it was skipped)
3. **Content recognized** (🔄): No `.wire/` artifact but a candidate file was found in repo scan or Confluence with `confidence: high` or `medium`. Also flag if Harvest shows hours logged to this phase.
4. **Not started** (⬜): None of the above

For each "content recognized" artifact, record:
- `recognized_file`: the best-match file path or Confluence page URL
- `recognized_confidence`: high / medium / low
- `recognized_source`: repo / confluence / harvest-hours-only
- `harvest_hours`: hours logged to this phase (if Harvest available)

## Step 3.5: Delivery Forecast

Invoke `wire/specs/utils/delivery_forecast.md` passing the full context already gathered — do not re-query any external sources.

Pass in:
- `releases`: list of release folders with their `status.md` content (from Agent E)
- `client_context`: the assembled context object from Phase 2 (Slack, HubSpot, Harvest, Jira, Fathom)

The utility returns a `DeliveryForecast` object. Store it as `forecast` for use in Phase 4 and Phase 6.

If the forecast utility returns `insufficient_data` for all releases, note this in the assessment and continue — it does not block the adoption workflow.

---

# Phase 4: Proposal and Confirmation

## Step 4.1: Present Assessment

Output the full project assessment to the user. This is informational — no files written yet.

```markdown
## Wire Adopt — Project Assessment

**Client**: [client_name]
**Repo**: [repo_root]
**Wire state**: [none / legacy / stalled / active]
**Inferred release type**: [type] ([confidence])
**Last real activity**: [date] (source: [Harvest/git/Jira/Slack])

### Sources Consulted
| Source | Status | Key Finding |
|--------|--------|-------------|
| Repo (git log) | ✅ | Last commit: [date], [N] active committers |
| Slack #clients-[name] | ✅ / ⚠️ not found | Last message: [date] |
| Slack #clients-[name]-internal | ✅ / ⚠️ not found | Last message: [date] |
| HubSpot | ✅ / ⚠️ not found | Deal: [name], Stage: [stage], Value: [value] |
| Harvest | ✅ / ⚠️ not found | [N]h logged, last entry: [date], budget: [X]% burned |
| Jira | ✅ / ⚠️ not found | [N] issues, [N] done |
| Confluence | ✅ / ⚠️ not found | [N] pages found |
| Fathom | ✅ / ⚠️ not found | [N] calls, last: [date] |

### Divergences Flagged
[list each divergence with severity icon and explanation]

### Delivery Forecast

[Render the DeliveryForecast object from Step 3.5 as a table. If forecast is insufficient_data, show a note and omit the table.]

| Release | % Done | ETA | Contractual date | Delta | Status | Confidence |
|---------|--------|-----|-----------------|-------|--------|------------|
| [release_name] | [N]% | [date or —] | [date or not found] | [+/-N days or —] | [icon] | [H/M/L] |
| ... | | | | | | |

For each release where status is 🟡 At Risk or 🔴 Overdue, append a one-line explanation:
> 🟡 **[release_name]**: ETA [date] vs contractual [date] (+[N] days). Key driver: [top blocker or velocity trend].

### Artifact Map (proposed)
| # | Artifact | Status | Evidence |
|---|----------|--------|----------|
| 1 | requirements | 🔄 Content recognized | `docs/requirements_v2.md` (high confidence), 24h logged in Harvest |
| 2 | conceptual_model | ✅ Wire-complete | `.wire/releases/02-data/design/conceptual_model.md` |
| 3 | pipeline_design | ⏳ Wire-stalled | Wire artifact exists, validate failed |
| 4 | data_model | ⬜ Not started | No content found |
| ... | | | |

### Related Repos (proposed)
| Id | Role | URL | Evidence |
|----|------|-----|----------|
| airflow | orchestration | https://github.com/<org>/<repo> | `models/staging/shop/_shop__sources.yml`: schema `landing_shop` is loaded by nothing in this repo; README links the DAGs repo |
```

Show the Related Repos table only when Agent E5 found a candidate. Each row is a proposal: nothing is written for it until Step 4.4.

## Step 4.2: Propose Adoption Mode

Offer two strategies:

```
How would you like to adopt this project into Wire?

A — Import mode (recommended for projects with substantial existing content)
    Wire takes ownership of recognized content: files are registered in status.md
    as "recognized" artifacts. Validate and review commands run against them in place.
    Existing files are NOT moved or modified.

B — Reference mode (lower disruption)
    Wire generates fresh artifacts using the recognized files as source inputs
    (treated like SOW documents). You end up with new Wire-standard artifacts
    alongside the existing ones.

Which approach? (A/B)
```

Default to Import for repos with Wire state `stalled` or `active`. Default to Reference for `none` or `legacy`.

## Step 4.3: Confirm Release Structure

If Wire state is `none` or `legacy`, ask:
```
What should the release folder be named?
(e.g. "02-data-foundation", "01-discovery", "03-platform-build")
Default: "01-[release_type]"
```

If Wire state is `stalled` or `active`, confirm the existing release folder name(s) should be used.

## Step 4.4: Confirm Before Writing

```
Ready to set up Wire structure for this project:
  - Engagement: .wire/engagement/ (context.md, sow link)
  - Release: .wire/releases/[release_folder]/status.md
  - Artifact states will reflect the assessment above
  - Adoption playbook will be written to planning/adoption_playbook.md
  - Related repos: [ids, or "none"] added to context.md (read only lookups)

Proceed? (yes/no)
```

If related repos were proposed in Step 4.1, ask about them separately before this prompt: **Add all / Pick / None**. A candidate with no URL is added only if the person gives one. Only the repos the person keeps appear on the line above.

If the target is a remote repo (`remote_repo: true`), skip the confirmation and instead output:
```
Remote repo mode — no files will be written. Outputting adoption plan only.
```

---

# Phase 5: Setup

Skip entirely if `remote_repo: true`.

## Step 5.1: Create or Update Engagement Structure

If `.wire/engagement/context.md` does not exist, create the full engagement structure:

```bash
mkdir -p .wire/engagement/calls
mkdir -p .wire/engagement/org
touch .wire/engagement/calls/.gitkeep
touch .wire/engagement/org/.gitkeep
```

Write `.wire/engagement/context.md` with fields synthesised from the discovery:
- `client_name` — from derivation in Phase 1
- `engagement_lead` — from Harvest active members or git committers (ask user to confirm)
- `deal_id` — from HubSpot (if found)
- `harvest_project_id` — from Harvest (if found)
- `jira_project_key` — from Jira (if found)
- `slack_channel` — confirmed channel names
- `adoption_date` — today
- `adoption_mode` — import / reference

Then, for each related repo the person kept in Step 4.4, run `python3 <wire>/scripts/related_repos.py add <github_url> --id <id> --role <role> --yes` (with `--paths` where the evidence named a folder). It adds the entry to `context.md` without touching the rest of the file. Do not refresh or clone the repos here; offer `/wire:utils-repos refresh` in the final output.

Make sure `.wire/local/` is git-ignored (it holds each person's own settings: persona override, where their clones are). If `.gitignore` has no `.wire/local/` line, append one:

```bash
grep -qxF '.wire/local/' .gitignore 2>/dev/null || echo '.wire/local/' >> .gitignore
```

## Step 5.2: Create Release Folder and Status File

```bash
mkdir -p .wire/releases/[release_folder]/planning
mkdir -p .wire/releases/[release_folder]/requirements
mkdir -p .wire/releases/[release_folder]/design
mkdir -p .wire/releases/[release_folder]/dev
mkdir -p .wire/releases/[release_folder]/test
mkdir -p .wire/releases/[release_folder]/deploy
mkdir -p .wire/releases/[release_folder]/enablement
```

Write `.wire/releases/[release_folder]/status.md` using the standard status template, but with artifact states set from the artifact map (Phase 3.4) rather than all `not_started`.

For **import mode**, use a new `recognized` state in the YAML:
```yaml
requirements:
  generate: "recognized"
  recognized_file: "docs/requirements_v2.md"
  recognized_confidence: "high"
  recognized_source: "repo"
  recognized_date: "[today]"
  validate: "not_started"
  review: "not_started"
```

For **Wire-complete** artifacts, copy the existing approved states as-is.

For **Wire-stalled** artifacts, copy the existing states as-is (the user will continue from where it left off).

For **not started** artifacts, use `not_started` as normal.

## Step 5.3: Link SOW/Supporting Docs

If HubSpot deal notes contain a SOW reference, or if a SOW-like file was found in the repo scan, copy or symlink it to `.wire/engagement/sow.md` (or `sow.pdf`) with a comment noting the source.

## Step 5.4: Commit Setup

```bash
git add .wire/ .gitignore
git commit -m "Wire adopt: set up engagement structure for [client_name]

Adoption mode: [import/reference]
Release type: [type]
Release folder: [folder]
Wire state at adoption: [none/legacy/stalled/active]
Sources consulted: [list]"
```

## Step 5.5: Propose Airflow and Review Settings (Airflow repos only)

Run this step when Agent E found an Airflow estate (a `dags/` folder with Python files that import `airflow`, Cloud Build or CI files that deploy to a Composer bucket, or `.claude/skills/` that describe DAG work). Skip it otherwise. It proposes two files for the client's team to check and commit. Wire does not commit them, and never fills a value it did not read from the repo.

1. **`.wire/engagement/airflow_environments.yml`** (schema in `wire/schemas/airflow-environments-schema.md`). Read:
   - Cloud Build files (`cloudbuild*.yaml`), GitHub Actions or other CI files: Composer environment names, projects, regions and buckets in `gcloud composer` and `gcloud storage`/`gsutil` commands, and the branch each deploy runs on (`branch:` triggers, `on.push.branches`, `if: github.ref == ...`).
   - Per-environment config files the DAGs read (`config/<env>.yml` and the like): worker sizes and fan-out caps where present.
   - The DAG folder's location, for `repo_root` and `dags_prefix`.
   Propose `deploy.allowed: [<the dev environment>]` and every other environment in `deploy.forbidden`. Leave `protected:` empty with a comment asking the team to list DAGs that run live only in dev and bucket paths not in the repo. Mark every value with the file it came from, and every value not found with `# TODO: not found in the repo`.
2. **`.wire/engagement/review_profile.yml`** (schema in `wire/schemas/review-profile-schema.md`). Read: the PR template (`.github/pull_request_template.md` and the other places GitHub looks), the tracker key in branch names and commit messages, and any review instructions in existing `.claude/skills/` or `CLAUDE.md`. Propose `pr_template`, `tracker`, and `review_mode: new_functionality`.
3. **Existing client skills.** List the repo's `.claude/skills/` and say, per skill, which parts Wire now covers (Airflow rules, deploy, run checks, review) and which are the client's own. Propose moving the client's own rules into `.wire/conventions/airflow.yml` with `extends: wire`, and keeping a short project skill in `.claude/skills/` for the rest that points to Wire's Airflow skill. Do not edit their skills.

Show both proposed files in full and ask: **Write for review / Skip**. On Write, write them uncommitted and say: "Check these with the team, correct the TODOs, then commit them." Record the step in the playbook's Engagement Context section.

---

# Phase 6: Adoption Playbook

Write `.wire/releases/[release_folder]/planning/adoption_playbook.md`.

This is distinct from the standard playbook generated by `/wire:playbook-generate`. It replaces BPMN-style "what to do" with a four-state "what exists and what's next" structure.

## Playbook Format

```markdown
# [Client Name] — Wire Adoption Playbook

**Date**: [today]
**Release**: [release_folder] ([release_type])
**Adoption mode**: [Import / Reference]
**Wire state at adoption**: [none / legacy / stalled / active]
**Assessed by**: Wire Adopt v[version]

---

## Status Legend

| Icon | Meaning | Next Action |
|------|---------|-------------|
| ✅ | Wire-complete — artifact exists and is approved | None required |
| 🔄 | Content recognized — manually created, imported into Wire | Run validate, then review |
| ⏳ | Wire-stalled — Wire artifact started but stuck | Fix issue and re-run the blocked command |
| ⬜ | Not started — no content found | Run generate command |

---

## Sources Used in This Assessment

| Source | Finding |
|--------|---------|
| Repo (git) | Last commit [date] by [author]. [N] models in dbt/. |
| Slack #clients-[name] | Last message [date]. [Key recent signal]. |
| Slack #clients-[name]-internal | [Key internal signal or "not found"]. |
| HubSpot | Deal "[name]" — [stage], [value]. |
| Harvest | [N]h logged, [X]% of budget. Last entry [date]. |
| Jira | [N] issues, [N] done. Project key: [key]. |
| Confluence | [N] pages found in [space]. |
| Fathom | [N] calls. Last call [date]. Last action items: [...] |

---

## Divergences to Resolve Before Proceeding

[Only include if divergences were found. Skip section if none.]

> ⚠️ **[Divergence name]**
> [Explanation]. Suggested resolution: [what to do].

---

## Artifact Sequence

[For each artifact in the release type's sequence:]

### [N]. [Artifact Name] [status icon]

[One of the following blocks depending on status:]

**[If ✅ Wire-complete]**
Approved Wire artifact.
File: `.wire/releases/[folder]/[path]/[file]`
No action required.

---

**[If 🔄 Content recognized]**
> Source: `[recognized_file]` — [confidence] confidence, found via [repo/Confluence/Harvest]
> [If Harvest] Hours logged to this phase: [N]h

Recognized content has been registered in `status.md`. The original file has not been moved.

**Next steps**:
1. Run `/wire:[artifact]-validate [release_folder]` — validates recognized content against Wire quality checks
2. If validate passes, run `/wire:[artifact]-review [release_folder]` — formal stakeholder sign-off
3. If validate fails, either fix the recognized file or run `/wire:[artifact]-generate [release_folder]` to regenerate using it as input

**Prerequisites**: [list any artifacts that must be approved first]

---

**[If ⏳ Wire-stalled]**
Wire artifact exists but is blocked.
File: `.wire/releases/[folder]/[path]/[file]`
Current state: generate=[state], validate=[state], review=[state]

**Why it stalled** (inferred): [e.g., "validate failed — check for naming convention errors", "review shows changes_requested — check Fathom for stakeholder feedback"]

**Next steps**:
1. [Specific command to run to unblock]
2. [Follow-on step]

---

**[If ⬜ Not started]**
No content found for this artifact.

**Next steps**:
1. Run `/wire:[artifact]-generate [release_folder]`
2. Prerequisites: [list what must be done first]

---

[Repeat for each artifact]

---

## Delivery Forecast

[Render the full per-release detail from the DeliveryForecast object. For each release, show a mini-scorecard.]

### Portfolio at a Glance

| Release | % Done | ETA | Contractual | Delta | Status |
|---------|--------|-----|-------------|-------|--------|
| [name] | [N]% | [date] | [date] | [+/-N days] | [icon] |
| ... | | | | | |

**Overall**: [overall_pct_delivered]% delivered across [N] releases. [N] on track, [N] at risk, [N] blocked.

---

### [Release Name] — Forecast Detail

**Progress**: [N]% delivered ([method]: checklist [N]% / Jira [N]% / Harvest [N]%)
**Remaining**: [N] open deliverables, ~[N] sprint-equivalents of work
**ETA**: [date] ([confidence] confidence — [method])
**Contractual**: [date] (source: [HubSpot/brief.md/not found])
**Verdict**: [🟢 On track by N days / 🟡 At risk — N days late / 🔴 Overdue by N days / ✅ Complete / 🚫 Blocked]

[If at risk or overdue:]
**Drivers**: [top 1-2 blockers or velocity signals]
**What changes the forecast**: [e.g. "Resolving RAP-240 would unblock ~8 open Jira issues and remove the primary schedule risk"]

[Repeat per release]

---

## Recommended Execution Order

[Ordered list of next commands to run, accounting for dependencies and current states. At-risk and overdue releases should appear first within each priority group.]

```
Priority 1 (resolve divergences first):
  [ ] [Action to resolve divergence]

Priority 2 (unblock stalled / at-risk releases):
  [ ] /wire:[artifact]-validate [folder]    # [stalled artifact name]

Priority 3 (validate recognized content):
  [ ] /wire:[artifact]-validate [folder]    # [recognized artifact name]
  [ ] /wire:[artifact]-validate [folder]    # [recognized artifact name]

Priority 4 (generate missing artifacts):
  [ ] /wire:[artifact]-generate [folder]    # [not-started artifact]
  [ ] /wire:[artifact]-generate [folder]    # [not-started artifact]
```

---

## Engagement Context

| Field | Value | Source |
|-------|-------|--------|
| Client | [client_name] | [source] |
| Deal value | [value] | HubSpot |
| Budget burned | [X]% ([N]h of [total]h) | Harvest |
| Last real activity | [date] | [source] |
| Engagement lead | [name] | [source] |
| Key stakeholders | [names] | HubSpot/Fathom |
| Slack channels | [#channels] | Slack |
| Jira project | [key] | Jira |
```

---

# Phase 7: Final Output

Output to the terminal:

```
--- Wire Adopt Complete ---

Client: [client_name]
Release: [release_folder] ([release_type])
Wire state at adoption: [state]
Adoption mode: [import/reference]

Artifact summary:
  ✅ Wire-complete:        [N]
  🔄 Content recognized:  [N]
  ⏳ Wire-stalled:         [N]
  ⬜ Not started:          [N]

[If divergences] ⚠️  [N] divergence(s) flagged — review adoption playbook before proceeding.

Delivery forecast:
  [For each release, one line:]
  [icon] [release_name]: [N]% done — ETA [date] [vs contractual [date] (+/-N days)] ([confidence])
  [e.g.]
  ✅ 00-discovery:                100% done — complete
  🟢 01-productionization:         38% done — ETA 2026-07-04 vs contractual 2026-06-30 (+4 days) (medium)
  🟡 02-customer-resolution:       52% done — ETA 2026-08-15 vs contractual 2026-07-31 (+15 days) (medium)
  🔴 03-customer-acquisition:      45% done — ETA 2026-09-12 vs contractual 2026-07-31 (+43 days) (low)
  🚫 04-core-trading-migration:    12% done — BLOCKED (Finance workshop outcome unrecorded)
  ⬜ 05-customer-ltv:               0% done — not yet started

  Overall: [overall_pct]% delivered across [N] releases.

Adoption playbook: .wire/releases/[folder]/planning/adoption_playbook.md
Status file:       .wire/releases/[folder]/status.md
Engagement:        .wire/engagement/context.md

Next command: /wire:[first_priority_artifact]-[action] [release_folder]
---
```

If `remote_repo: true`, instead output the assessment and playbook content to the terminal and clean up the temporary clone directory.

**Companion skill**: For a deeper delivery health picture anchored on SOW milestones, sprint velocity, and named ticket/MR status, the `engagement-status-report` skill (`wire/skills/engagement-status-report/SKILL.md`) can be run alongside `/wire:adopt`. It is particularly valuable for steady-state sprint and closeout/suspension states where delivery-level detail matters. `/wire:adopt` establishes the Wire framework structure; the delivery status skill explains what the team has actually been doing and how healthy the delivery is.

---

# Edge Cases

## No External Sources Available

If all external MCP sources return `not_available`, the command runs in repo-only mode. Output a warning:
```
⚠️ No external sources available (Slack, HubSpot, Harvest, Jira, Confluence, Fathom).
Running in repo-only mode. Assessment will be based on repo contents alone.
For a more complete assessment, configure the relevant MCP servers.
```

Proceed with Phase 3 using only Agent E (repo scan) results.

## Wire State is `legacy` (Previous Wire Version)

If `.wire/` exists but uses the old flat structure (no `releases/` subdirectory), detect which artifacts exist as flat files and attempt to map them to current artifact names using this table:

| Old name (flat .wire/) | Current name |
|------------------------|--------------|
| `data_architecture.md` | `pipeline_design` |
| `data_model.md` | `data_model` |
| `requirements.md` | `requirements` |
| `pipeline_spec.md` | `pipeline` |
| Any `*_spec.md` | corresponding artifact |

Treat mapped files as "content recognized" with `recognized_source: legacy_wire`. Note the version migration in the playbook.

## Multiple Releases Already in .wire/

If `.wire/releases/` contains multiple release folders, process each independently and ask:
```
Found [N] existing releases:
1. [folder] ([type]) — last activity: [date]
2. [folder] ([type]) — last activity: [date]

Adopt all releases? (yes / select specific: enter number(s))
```

Generate a separate adoption playbook per release.

## Ambiguous Release Type

If the evidence equally supports two release types, present both options:
```
The repo contents are consistent with two release types:
  A. dbt_development — evidence: [N] dbt models across all 3 layers, LookML files found
  B. full_platform   — evidence: as above + pipeline config found

Which release type applies? (A/B)
```
