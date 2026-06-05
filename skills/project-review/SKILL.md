---
name: project-review
description: Skill for generating a standardised Wire Framework & Claude Code usage review for a client engagement. Activates when the user asks to review Wire usage, audit Claude Code activity, or generate a project review for a client. Gathers usage telemetry from BigQuery, Wire artifacts from the delivery GitHub repo, Jira tickets, and Fathom call transcripts, then produces a structured review document in wire/docs/reviews/.
---

# Project Review Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | project-review | activated | project review or audit work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.



## When This Skill Activates

Activate when the user asks to:
- Review Wire Framework usage for a client or project
- Audit Claude Code activity on an engagement
- Generate a project review, usage report, or Wire adoption report
- Understand how Wire was used (or not used) on a project

**Keywords to watch for:**
- "project review", "usage review", "Wire review", "Claude Code review"
- "how was Wire used on [client]", "audit [client] usage"
- "generate a review for [client]"

---

## Step 1 — Gather Parameters

Before doing any research, collect the four required inputs. Ask all four in a single message:

> To generate the project review I need four things:
>
> 1. **Client name** — e.g. "Client A" (used in the report title and repo clone path)
> 2. **Wire delivery repo URL** — the GitHub URL of the client's Wire delivery repo (e.g. `https://github.com/rittmananalytics/rapha-delivery`)
> 3. **Project directory basename** — the exact `project_dir_basename` value in BigQuery telemetry (e.g. `rapha-dbt`, `halocollar-delivery`). This is usually the name of the dbt or delivery repo folder on the consultant's machine.
> 4. **Jira project key** *(optional)* — the Jira project key for this engagement (e.g. `RAP`, `HC`). If you don't know it, leave blank and the skill will search Jira by client name.

Wait for all four answers before proceeding.

---

## Step 2 — Gather Data (run all sources in parallel)

Once you have the four parameters, run the following research tasks in parallel. Do not wait for one before starting the others.

### 2a — BigQuery: Pull usage telemetry

Run this SQL, substituting `{PROJECT_DIR_BASENAME}` with the value from Step 1:

```sql
SELECT
    (FORMAT_TIMESTAMP('%F %T', coding_agent_prompts_fact.event_ts)) AS event_time,
    coding_agent_prompts_fact.prompt_sequence_in_session             AS prompt_seq,
    coding_agent_prompts_fact.slash_command_raw                      AS slash_command,
    coding_agent_prompts_fact.consultant_name                        AS consultant,
    coding_agent_prompts_fact.git_repo_canonical                     AS git_repo,
    coding_agent_prompts_fact.project_dir_basename                   AS project_dir,
    coding_agent_prompts_fact.truncated_display                      AS prompt_text,
    (CASE
        WHEN coding_agent_prompts_fact.slash_command_raw LIKE '/wire:%' THEN 'Yes'
        ELSE 'No'
    END) AS is_wire_command
FROM `ra-development.analytics.coding_agent_prompts_fact` AS coding_agent_prompts_fact
WHERE coding_agent_prompts_fact.project_dir_basename = '{PROJECT_DIR_BASENAME}'
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
ORDER BY 1
```

Use `mcp__claude_ai_BigQuery_MCP__execute_sql_readonly` with `projectId: "ra-development"`.

The result set may be large. If it exceeds the context window, use a subagent to process the file:

```
Analyze the BigQuery result at <path>. It is JSON with schema:
{rows: [{event_time, prompt_seq, slash_command, consultant, git_repo, project_dir, prompt_text, is_wire_command}]}.

Produce:
1. Total prompts, distinct consultants, active days, date range
2. Wire command invocations — count per command, chronological list
3. Session-by-session narrative (group by date): date, consultant, wire commands used,
   key non-wire prompts (quote prompt_text verbatim for interesting ones)
4. Pre-wire prep patterns: what prompts immediately preceded Wire commands?
5. Post-wire correction patterns: what prompts immediately followed Wire commands?
6. Wire commands that should have been used but weren't (based on the prompt_text content)
7. Recurring non-wire patterns that appear 3+ times and have no Wire equivalent
```

### 2b — GitHub: Clone and explore the delivery repo

```bash
gh repo clone {REPO_URL} /tmp/{CLIENT_NAME_LOWER}-delivery-review
```

Then read the following (all in parallel):
- `.wire/engagement/context.md` — engagement overview, stakeholders, releases
- All `.wire/releases/*/status.md` files — release status and session history
- `.wire/releases/*/brief.md` files — release scope
- File tree of `.wire/` to understand overall structure

### 2c — Jira: Pull all project issues

**If a Jira project key was provided**, query directly:
- Tool: `mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql`
- `cloudId: "https://rittmananalytics.atlassian.net"`
- `jql: "project = {JIRA_PROJECT_KEY} ORDER BY created ASC"`
- `maxResults: 100`
- `fields: ["summary", "status", "issuetype", "created", "assignee", "description"]`

**If no key was provided, or the key returns zero results**, search by client name:
1. Call `mcp__claude_ai_Atlassian__getVisibleJiraProjects` to list all projects
2. Find the project whose name most closely matches the client name (case-insensitive substring match)
3. Use the discovered key in the JQL query above
4. If `getVisibleJiraProjects` is unavailable, try `mcp__claude_ai_Atlassian__search` with the client name as the query and filter results to Jira issues only

If the result is too large, use a subagent to extract: issue keys, types, statuses, assignees, and summaries grouped by epic/theme. Then map each issue to a Wire Framework phase (requirements, design, development, testing/QA, deployment, enablement) and identify phases with no Jira coverage.

### 2d — Fathom: Find relevant meetings

Use `mcp__claude_ai_Fathom__search_meetings` with the client name as the query and `recorded_by: "mark.rittman@rittmananalytics.com"`. If no results, try with other team lead emails. Note: the delivery repo's `.wire/engagement/calls/` directory contains pre-pulled Fathom transcripts — check there too.

---

## Step 3 — Analyse the Data

Before writing the review, synthesise across all four sources:

**Wire adoption rate:**
- Total prompts vs. Wire command invocations → adoption percentage
- Which Wire commands were actually used and which were used correctly in sequence

**Discovery phase comparison:**
- What discovery artifacts exist in the repo vs. what Wire's canonical discovery flow would have produced
- Were `/wire:problem-definition-generate`, `/wire:pitch-generate`, `/wire:release-brief-generate`, `/wire:sprint-plan-generate` used? If not, what was done instead?

**Release-by-release coverage:**
- For each release in `.wire/releases/`, list which Wire generate/validate/review commands were invoked and which were skipped
- Identify development phases where Wire was bypassed but the work was clearly done (evidenced by BigQuery prompts or Jira tickets)

**Pre/during/post-Wire prompt patterns:**
- What context did consultants inject before or after Wire commands?
- Were Wire commands invoked correctly (generate before validate, validate before review)?
- Did consultants abort and restart Wire commands?

**Gap analysis:**
- Wire commands that exist and were directly applicable but never used
- Recurring free-form prompts that appear 3+ times and represent an unmet Wire need

---

## Step 4 — Write the Review Document

Create the review at:
```
wire/docs/reviews/{YYYY-MM}-{CLIENT_NAME_LOWER}-wire-usage-review.md
```

Use today's year-month for `{YYYY-MM}` and the client name lowercased and hyphenated for `{CLIENT_NAME_LOWER}` (e.g. `rapha`, `halo-collar`).

The document must follow this structure exactly:

---

```markdown
# Wire Framework & Claude Code Usage Review — {CLIENT_NAME}

**Engagement:** {CLIENT_NAME}
**Review Date:** {MONTH YEAR}
**Review Author:** Generated from BigQuery telemetry, {REPO_URL}, Jira {JIRA_PROJECT_KEY}
**Period Covered:** {START_DATE} – {END_DATE}
**Consultants:** {LIST}

---

## Contents

1. Executive Summary
2. Engagement Overview
3. Wire Framework Adoption — Quantitative Summary
4. Discovery Phase: Actual vs. Canonical Wire
5. Release-by-Release Wire Usage Analysis
6. Claude Code Prompt Patterns: Before, During and After Wire Commands
7. Gap Analysis: Wire Commands Never Used but Applicable
8. Recurring Manual Patterns — Candidates for New Wire Commands
9. Recommendations

---

## 1. Executive Summary

[3–5 paragraphs. Lead with adoption rate and the single most important finding.
Cover: what Wire was used for vs. what it should have been used for;
the highest-friction manual activities; top 3 recommendations.]

---

## 2. Engagement Overview

### Client & Scope
[1–2 paragraphs from context.md]

### Technology Stack
[Table: layer → technology, sourced from context.md]

### Delivery Releases
[Table: # | name | type | status | key scope — from context.md and release brief.md files]

### Key Stakeholders
[Table from context.md stakeholders section]

---

## 3. Wire Framework Adoption — Quantitative Summary

### Overall Statistics
[Table: total prompts, active days, consultants, Wire command invocations, Wire %, date range]

### Wire Commands Actually Used
[Table: command | count | context — list every invocation with the date and what preceded/followed it]

### Observations on Command Namespace / Version
[Note any deprecated command names used, version mismatches, or signs of confusion about command names]

---

## 4. Discovery Phase: Actual vs. Canonical Wire

### What Was Produced
[List all discovery artifacts found in the repo]

### Canonical Wire Discovery Flow vs. What Happened
[Table: wire artifact | wire command | what actually happened — one row per discovery artifact]

### Root Cause of Discovery Phase Gap
[Why weren't Wire discovery commands used? Timeline, adoption state, pre-Wire structure?]

### Specific Discovery Phase Gaps
[One paragraph per missing artifact type]

---

## 5. Release-by-Release Wire Usage Analysis

[One section per release. Each section covers:
- Wire commands used (count and list)
- Development approach (free-form summary)
- What worked / what didn't
- Wire status.md quality assessment
- Specific gaps for this release]

---

## 6. Claude Code Prompt Patterns: Before, During and After Wire Commands

### Pre-Wire Preparation Patterns
[What context did consultants prepare before invoking Wire commands?
Did they prep first or invoke then inject context?]

### During Wire Command Patterns
[How many corrective prompts followed each Wire invocation?
What types of corrections were needed?]

### Post-Wire Patterns
[What did consultants do immediately after Wire commands?
Recurring follow-up patterns?]

---

## 7. Gap Analysis: Wire Commands Never Used but Applicable

[Table: command | evidence of manual equivalent | estimated prompt saving
Only include commands where BigQuery evidence clearly shows manual equivalent work.
Include total estimated prompt saving at the bottom.
Then explain why each command wasn't used — based on evidence in the prompt sequence.]

---

## 8. Recurring Manual Patterns — Candidates for New Wire Commands

[One subsection per pattern. Each subsection:
- Pattern name and proposed command name
- Evidence: quote actual prompt_text examples, count occurrences
- Proposed command behaviour
- What input it needs and what output it produces]

Minimum 3 patterns. Only include patterns with 5+ occurrences.

---

## 9. Recommendations

[Numbered list R1–RN, each with:
- Title and priority (High / Medium / Low)
- Problem statement (what friction does this solve?)
- Proposed solution
- Implementation pointer (which spec file to create or modify)]

Group by: (a) new Wire commands, (b) improvements to existing commands,
(c) process/adoption changes.

---

## Appendix: Data Sources

[Table: source | content | records/size]
[Note the BigQuery query used, repo URL, Jira project key]

---

*Review generated {DATE}. Data cut-off: {BIGQUERY_MAX_DATE} for BigQuery telemetry.*
```

---

## Step 5 — Commit and Push

After writing the review:

```bash
git add wire/docs/reviews/
git commit -m "docs: add {CLIENT_NAME} Wire Framework usage review ({YYYY-MM})"
git push origin main
```

Confirm the file path and commit SHA to the user.

---

## Quality Checks Before Finishing

Before reporting done, verify:

- [ ] Every section of the template is populated (no `[placeholder]` text remaining)
- [ ] The Wire adoption rate is calculated correctly (Wire invocations ÷ total prompts)
- [ ] Every Wire command in the "used" table has at least one real date and context note
- [ ] The discovery phase table has one row per canonical Wire artifact
- [ ] Each release in the repo has its own section in Section 5
- [ ] Gap analysis only includes commands where BigQuery evidence is explicit
- [ ] Recurring patterns section only includes patterns with 5+ documented occurrences
- [ ] All recommendations are numbered, have a priority, and reference a spec file
- [ ] The review file is committed and pushed

---

## Notes

- If BigQuery returns no rows for `project_dir_basename`, ask the user to confirm the exact value. Common variants: the basename of the client's dbt repo (`{client}-dbt`), the delivery repo name (`{client}-delivery`), or a project folder name. Run `SELECT DISTINCT project_dir_basename FROM \`ra-development.analytics.coding_agent_prompts_fact\` WHERE project_dir_basename LIKE '%{client_fragment}%' LIMIT 20` to discover the right value.
- If the Jira project key is unknown or returns no results, search for the project by client name first: use `mcp__claude_ai_Atlassian__search` with the client name as the query, or use `mcp__claude_ai_Atlassian__getVisibleJiraProjects` to list all projects and match on name. Only skip Jira entirely if the MCP itself is unavailable — note that in the appendix.
- If Fathom returns no results, check `.wire/engagement/calls/` in the delivery repo — Fathom transcripts are often pre-pulled there.
- The SQL has no person-name filter — it returns all consultants who worked in that project directory. The analysis should break down usage per consultant where multiple consultants appear.
- Review documents live in `wire/docs/reviews/` in the Wire framework repo (not the client delivery repo).
