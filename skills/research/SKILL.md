---
name: Research Persistence
description: Proactive skill for saving and retrieving technical research findings across sessions. Auto-activates when performing technical research within a Wire engagement.
triggers:
  - Investigating a client system, API, or data source
  - Researching architecture options or technology choices
  - Reviewing documentation for a new tool or platform
  - Exploring an unknown codebase or data model
  - Any research task where the findings would be useful in a future session
---

# Research Persistence Skill

## When This Skill Activates

This skill activates automatically when you are about to perform technical research in the context of a Wire engagement — i.e., when the working directory contains a `.wire/` folder and you are about to:

- Query documentation, GitHub, or web sources for technical information
- Explore a client codebase, schema, or API to understand how it works
- Evaluate tool or platform options for an architectural decision
- Investigate a bug, performance issue, or data quality problem that requires research

**Purpose**: Research findings are time-consuming to re-derive. Persisting them at engagement level means future sessions (and other team members) can build on previous findings rather than starting from scratch.

## Pre-Research Check

**Before starting any research task**, check whether it has already been done:

1. Use Glob to list `.wire/research/sessions/*/summary.md`
2. If prior sessions exist, read the most recent 3–5 summaries (scan quickly — don't block on this)
3. If a prior session directly addresses the current research question:
   - Surface the finding: "This was researched on [date]: [summary]. Is this still relevant?"
   - Ask the user whether to proceed with new research or build on the prior finding
4. If no relevant prior research found, proceed normally

Do NOT block on this check — if `.wire/research/` doesn't exist or is empty, proceed immediately.

## Post-Research Save

**After completing a significant research task**, save findings to the engagement research store:

### When to save
Save when the research:
- Reveals non-obvious facts about a client system (API behaviour, schema quirks, access patterns)
- Documents an architectural decision and the reasons for it
- Identifies a technology constraint or requirement that future work needs to respect
- Contains findings that required significant time or effort to produce
- Would be useful to another consultant joining the engagement

### When NOT to save
Skip saving when:
- The research is trivial (confirmed a well-known fact)
- The findings are already in project documentation
- The research is purely exploratory with no actionable conclusions

### How to save

1. **Create the session directory** (use current timestamp):
   ```bash
   mkdir -p .wire/research/sessions/YYYY-MM-DD-HHMM
   ```

2. **Write the summary file** at `.wire/research/sessions/YYYY-MM-DD-HHMM/summary.md`:

   ```markdown
   # Research Session: YYYY-MM-DD-HHMM

   **Engagement**: [client_name from engagement/context.md, or "unknown"]
   **Release**: [current release folder, if applicable]
   **Phase**: [current phase, if applicable]
   **Topic**: [one-line topic description]
   **Date**: [date]

   ## Summary

   [2–4 paragraph summary of findings. Write for a consultant who is starting fresh — assume no context.]

   ## Key Facts

   - [Specific, actionable finding 1]
   - [Specific, actionable finding 2]
   - [Specific, actionable finding 3]

   ## Implications for This Engagement

   [How these findings affect the current work — what decisions they inform, what constraints they impose]

   ## Sources

   - [URLs, file paths, or document names consulted]

   ## Caveats and Expiry

   [Any caveats about reliability, version-specificity, or when these findings might become stale]
   ```

3. **Optional: Save raw research material** in the same session folder:
   - API response samples: `raw_api_response.json`
   - Schema extracts: `schema_extract.sql`
   - Code snippets: `code_sample.py`
   - These are reference material — the summary.md is the primary record

### Tell the user

After saving, briefly mention it:
```
Research saved to .wire/research/sessions/[timestamp]/summary.md
```
Keep this notification to one line — don't interrupt the flow of the main task.

## Session Start Integration

When `session:start` is run, it automatically reads the 2–3 most recent research summaries and surfaces any that are relevant to the current release and phase. This skill does not need to do anything special for this — just ensure summaries are written clearly and include the release/phase metadata.

## Privacy and Confidentiality

Research saved here may include client system details, API credentials context, or proprietary schema information. The `.wire/research/` directory should be treated with the same confidentiality as all other Wire project artifacts:
- Do NOT include actual credentials or secrets in research summaries
- Reference credential names (e.g. "API key stored in `.env.ACME_API_KEY`") rather than values
- If the engagement repo is private (as it should be for client work), research is automatically protected by repo access controls

## Engagement-Level Scope

Research is saved at engagement level (`.wire/research/sessions/`), not within a specific release folder. This is intentional: architectural decisions and system findings are relevant across all releases in an engagement. A finding from the discovery release about the client's BigQuery schema structure is equally relevant to a later dbt development release.
