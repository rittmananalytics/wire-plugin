---
name: wire-usage-analysis
description: Skill for analysing Wire Framework and Claude Code usage across the team and per-project using BigQuery telemetry. Activates when the user asks to review Wire adoption, audit Claude Code activity across staff or projects, or generate usage reports. Queries ra-development.analytics.coding_agent_prompts_fact, analyses prompt patterns and Wire command sequences, and produces structured markdown review documents per user and/or per project.
triggers:
  - Reviewing Wire Framework adoption or Claude Code usage across the team
  - Generating usage reports for staff members or client projects
  - Analysing why Wire adoption is low
  - Auditing which Wire commands consultants are and aren't using
  - Identifying natural language substitution patterns (asking Claude to do Wire-equivalent work without commands)
---

# Wire Usage Analysis Skill

## When This Skill Activates

Activate when the user asks to:
- Review or audit Wire Framework usage — team-wide, per-person, or per-project
- Generate staff usage reviews or project usage reviews from telemetry
- Understand why Wire adoption is low on an engagement or across the team
- Identify what consultants are doing with Claude Code and where Wire commands are missing
- Analyse prompt patterns before/after Wire commands

**Keywords to watch for:**
- "wire adoption", "usage review", "audit wire", "claude code usage"
- "how is [person] using wire", "wire stats", "wire telemetry"
- "generate reviews for staff", "project usage report"
- "why is wire adoption low"

---

## Step 1 — Confirm Scope

Before running queries, confirm the analysis scope with the user in a single message:

> I can analyse Wire Framework + Claude Code usage at three scopes:
>
> 1. **Team overview** — all consultants, all projects, date range of your choice
> 2. **Per-person deep-dive** — one or more named consultants
> 3. **Per-project** — one or more client project repo names
>
> Which scope do you need, and should I write the results to review files or just summarise inline?

If the user's original message already makes the scope clear (e.g. "generate usage reviews for all staff"), skip this question and proceed.

**Date range default:** If no date range is specified, query all available data (no date filter).

---

## Step 2 — Run the Telemetry Query

Use `mcp__claude_ai_BigQuery_MCP__execute_sql_readonly` with `projectId: "ra-development"`.

### Base query (use as-is for team-wide analysis)

```sql
SELECT
    FORMAT_TIMESTAMP('%F %T', coding_agent_prompts_fact.event_ts) AS event_time,
    persons_dim.person_name                                        AS person_name,
    coding_agent_prompts_fact.prompt_sequence_in_session           AS prompt_seq,
    coding_agent_prompts_fact.user_email                           AS user_email,
    coding_agent_prompts_fact.git_repo_canonical                   AS git_repo,
    coding_agent_prompts_fact.project_dir                          AS project_dir,
    coding_agent_prompts_fact.project_dir_basename                 AS project_dir_basename,
    coding_agent_prompts_fact.seconds_since_prev_prompt_in_session AS seconds_since_prev,
    coding_agent_prompts_fact.hostname                             AS hostname,
    coding_agent_prompts_fact.truncated_display                    AS prompt_text,
    coding_agent_prompts_fact.slash_command_raw                    AS slash_command_raw,
    coding_agent_prompts_fact.slash_command_name                   AS slash_command_name,
    CASE
        WHEN coding_agent_prompts_fact.slash_command_raw LIKE '/wire:%' THEN 'Yes'
        ELSE 'No'
    END                                                            AS is_wire_command,
    coding_agent_prompts_fact.slash_command_namespace              AS slash_command_namespace,
    coding_agent_commands_dim.command_name                         AS command_name
FROM `ra-development.analytics.coding_agent_prompts_fact`  AS coding_agent_prompts_fact
LEFT JOIN `ra-development.analytics.coding_agent_commands_dim`  AS coding_agent_commands_dim
    ON coding_agent_prompts_fact.coding_agent_command_fk = coding_agent_commands_dim.coding_agent_command_pk
LEFT JOIN `ra-development.analytics.persons_dim`  AS persons_dim
    ON coding_agent_prompts_fact.consultant_fk = persons_dim.person_pk
ORDER BY event_time ASC
```

### Filtered variants

**By person** — add to the WHERE clause:
```sql
WHERE persons_dim.person_name = '{PERSON_NAME}'
```

**By project** — add to the WHERE clause:
```sql
WHERE coding_agent_prompts_fact.project_dir_basename = '{PROJECT_DIR_BASENAME}'
```

**By date range** — add to the WHERE clause:
```sql
WHERE coding_agent_prompts_fact.event_ts >= TIMESTAMP('{YYYY-MM-DD}')
  AND coding_agent_prompts_fact.event_ts <  TIMESTAMP('{YYYY-MM-DD}')
```

**Discovery query — find project basenames for a client:**
```sql
SELECT DISTINCT project_dir_basename, git_repo_canonical, COUNT(*) AS prompt_count
FROM `ra-development.analytics.coding_agent_prompts_fact`
WHERE LOWER(project_dir_basename) LIKE '%{client_fragment}%'
   OR LOWER(git_repo_canonical)   LIKE '%{client_fragment}%'
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 20
```

---

## Step 3 — Handle Large Result Sets

The full telemetry query can return hundreds of thousands of rows, exceeding the context window. Use this protocol:

1. **Run the query** and check the result size.
2. **If the result fits in context** (~3,000 rows or fewer), analyse directly.
3. **If the result is too large**, save it to a file and delegate analysis to a subagent:

```
Save the BigQuery result to /tmp/wire_telemetry_{scope}_{date}.json

Then spawn a subagent with:

"Analyse the BigQuery telemetry at /tmp/wire_telemetry_{scope}_{date}.json.
Schema: {event_time, person_name, prompt_seq, user_email, git_repo,
project_dir_basename, seconds_since_prev, hostname, prompt_text,
slash_command_raw, is_wire_command, slash_command_namespace, command_name}

Produce the following (verbatim output, no truncation):

1. SUMMARY TABLE
   person_name | total_prompts | active_days | date_range | wire_commands | wire_pct
   One row per person. Sort by total_prompts desc.

2. WIRE COMMANDS USED (per person)
   For each person: list every Wire command invoked, count, chronological dates.
   Flag deprecated namespaces: /dp:, /session:, /wire:dp-* (these predate current /wire: namespace).

3. SESSION-BY-SESSION NARRATIVE (per person, grouped by calendar date)
   date | person | project | wire_commands_used | key_prompt_quotes
   Quote prompt_text verbatim for: Wire invocations, prompts that should have been
   Wire commands but weren't, and recurring non-Wire patterns.

4. WIRE-ADJACENT NATURAL LANGUAGE (per person)
   Prompts where the user asked Claude to perform a Wire-equivalent action via
   conversation rather than a command. Quote exact prompt_text. Map each to the
   Wire command it should have been.
   Examples to detect:
   - 'update the wire status' → /wire:status
   - 'what's the next step' → /wire:session-start context
   - 'update wire docs from this transcript' → /wire:requirements-review
   - 'review this against business questions' → /wire:requirements-review
   - 'publish this to confluence' → /wire:utils-docstore-sync
   - 'generate the data model' → /wire:data_model-generate
   - 'validate the requirements' → /wire:requirements-validate

5. COMMAND SEQUENCE QUALITY (per person)
   For each set of Wire commands on a release, assess:
   - Did generate precede validate? validate precede review?
   - Were validate/review steps skipped after generate?
   - Were commands aborted and restarted?

6. TOP REPOS BY ACTIVITY (team-wide)
   project_dir_basename | total_prompts | wire_commands | wire_pct | consultants
   Sort by total_prompts desc. Top 15.

7. RECURRING NON-WIRE PATTERNS (team-wide)
   Patterns appearing 5+ times across any person/project that have no Wire command
   equivalent. Quote examples. These are candidates for new Wire commands.
"
```

---

## Step 4 — Analyse Adoption

Once you have the structured output from Step 3, compute the following before writing any reports.

### Adoption rate calculation

**Headline rate:** Wire command invocations ÷ total prompts × 100

**Adjusted rate (recommended):** Exclude framework development repos from the denominator. Repos that are Wire framework repos themselves (`ra-claude-skills-repo`, `wire`, similar) inflate the total prompt count without being delivery work. Apply this correction and note it.

**Namespace correction:** Count `/dp:*` and `/session:*` commands as Wire-equivalent — they are the pre-migration namespace. The current `/wire:*` namespace replaced them; both represent Wire Framework usage.

### Wire command quality tiers

When reporting on Wire usage, classify each consultant's usage into one of:

| Tier | Description |
|------|-------------|
| **Full lifecycle** | generate → validate → review all used in correct sequence for at least one release |
| **Partial lifecycle** | generate used; validate or review missing |
| **Session management only** | Only session-start / session-end / status used |
| **Command-adjacent** | Wire commands used but mostly via natural language substitution |
| **None** | No Wire commands; all Wire-equivalent work done via conversation |

### Natural language substitution gap

This is the most important finding on most projects. For each person, list:
- Total Wire-equivalent prompts done via conversation
- Total Wire commands actually used
- Gap ratio: substitution prompts ÷ (substitution prompts + Wire commands)

A gap ratio above 0.5 means the person understands what Wire does but isn't using the commands.

---

## Step 5 — Write Review Documents

### For team-level or per-person analyses

Create one file per person at:
```
user_usage_reviews/{person_name_lower_hyphenated}.md
```

Each file must follow this structure:

```markdown
# Wire Framework & Claude Code Usage Review — {Person Name}

**Role:** {from context — e.g. Analytics Engineer, Delivery Lead}
**Period:** {date range from telemetry}
**Total Prompts:** {N}
**Wire Commands:** {N} ({pct}%)
**Wire Quality Tier:** {from Step 4}
**Last Active:** {most recent date}

---

## Activity Summary

### By Project
| Project | Prompts | Wire Commands | Wire % | Dates |
|---------|---------|---------------|--------|-------|
...

### By Month
| Month | Prompts | Wire % |
|-------|---------|--------|
...

---

## Wire Framework Usage

### Commands Actually Used
| Date | Command | Project | Context |
|------|---------|---------|---------|
...

### Namespace Notes
[Any deprecated namespaces used, migration events, version confusion]

---

## What {Person} Works On (from prompt telemetry)

### [Period / Phase title]
[3–5 verbatim prompt quotes illustrating the work; brief analysis of patterns]

[Repeat for each distinct phase of work]

---

## Wire-Adjacent Natural Language

| What was said | Should have been | Count |
|---------------|-----------------|-------|
...

---

## Key Observations

1. [Most important finding]
2. [Second finding]
...

---

## Recommendations

1. [Specific, actionable recommendation]
...
```

### For team overview

Create a summary file at:
```
user_usage_reviews/README.md
```

Structure:

```markdown
# Wire Framework & Claude Code — Team Usage Summary

**Period:** {date range}
**Report generated:** {date}

---

## Team Overview

| Person | Prompts | Wire % | Quality Tier | Last Active |
|--------|---------|--------|--------------|-------------|
...

---

## Wire Framework Adoption by Person

[Ranking from highest to lowest, 1–2 sentences per person]

---

## Cross-Team Patterns

### What Wire is being used for (across all projects)
[Bulleted list]

### What Wire is NOT yet being used for
[Bulleted list]

### Natural Language Substitution Gap (team-wide)
[Table of most common substitution patterns across all consultants]

---

## Recommended Actions

[Numbered list R1–RN]
```

### For per-project analyses

Create one file per project at:
```
project_usage_reviews/{client_name_lower}.md
```

See the `project-review` skill for the full per-project report template. This skill focuses on the telemetry analysis step — if a full Wire project review is needed, activate the `project-review` skill which also pulls from GitHub, Jira, and Fathom.

---

## Step 6 — Commit and Push

After writing all review files:

```bash
git add user_usage_reviews/ project_usage_reviews/
git commit -m "docs: add Wire Framework + Claude Code usage reviews ({YYYY-MM})"
git push origin main
```

Report the file paths and commit SHA to the user.

---

## Quality Checks Before Finishing

- [ ] Adoption rates calculated correctly (Wire invocations ÷ total prompts)
- [ ] Namespace correction applied — `/dp:*` and `/session:*` counted as Wire-equivalent
- [ ] Framework repos excluded from adjusted rate with a note
- [ ] Each person has a Quality Tier assigned
- [ ] Natural language substitution table populated with real prompt_text quotes (not paraphrases)
- [ ] Recurring patterns section contains 5+ occurrence examples only
- [ ] All recommendations are specific and actionable
- [ ] Review files committed and pushed

---

## Notes

- **person_name may be NULL** for some rows where the consultant_fk join fails. Check `user_email` as a fallback identifier and note unmatched rows.
- **project_dir_basename is the local folder name**, not the GitHub repo name. The same client project may appear under multiple basenames if different consultants have it checked out to different paths. Use `git_repo_canonical` to deduplicate if needed.
- **seconds_since_prev** is useful for identifying session boundaries (large gaps indicate a new working session) and for estimating effort on Wire commands vs. conversational work.
- **slash_command_namespace** distinguishes `wire`, `dp` (legacy Wire), `session` (older Wire session commands), and custom commands. Don't conflate custom commands (e.g. `/effort`, `/dagster-expert`) with Wire commands — only count commands where `slash_command_raw LIKE '/wire:%'` or namespace is `dp` as Wire adoption.
- **The telemetry is truncated** — `truncated_display` contains the first ~200 characters of each prompt. Exact wording may vary from the original but is sufficient for pattern recognition.
- **Sensitive content:** Occasionally consultants accidentally paste credentials into prompts. If you spot a pattern like `sk-ant-api03-...`, `AKIA...`, or similar in `truncated_display`, flag it immediately to the user as a security concern — the key should be rotated. Do not reproduce the key in any report.
