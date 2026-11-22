---
wire_schema: "1.0"
command: review
artifact: query_audit
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: query_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Stakeholder sign-off on query patterns and semantic layer addition priorities
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Query Audit Review

## Purpose

Confirm the question pattern list with data consumers and agree priorities for the semantic layer design phase. This review should include both the data team and at least one representative business stakeholder — the people who actually ask these questions.

## Workflow

### Step 1: Surface Meeting Context

Search Fathom for prior conversations about analytics questions, dashboard requests, or recurring data asks that stakeholders have raised in meetings.

### Step 2: Present Pattern Summary

Lead with the coverage number — it anchors the conversation:

```
## Query Audit Review

Today, [X]% of your most common analytical questions can be answered 
from the semantic layer without raw SQL. This release targets [Y]% coverage.

### Top 10 Patterns (by frequency)

| Question | Current | Target |
|---|---|---|
| Monthly revenue by channel | Raw SQL | SL metric |
| Active customers last 30 days | Raw SQL | SL metric |
| ...
```

### Step 2: Validate Pattern List

Ask the reviewer:
1. Are these the real questions your team asks? Any important patterns missing?
2. Are the frequency estimates plausible?
3. Any patterns on the list that are actually one-off or deprecated queries?

### Step 3: Confirm Priorities

Walk through the SL-gap list and confirm priority ratings. Business stakeholders often re-rank — marketing might value their gaps more highly than the query frequency suggests.

### Step 4: Record Decisions

Write `.wire/<release-folder>/artifacts/query_audit_decisions.md` with confirmed priorities and any patterns added or removed from the list.

### Step 5: Update Status

```yaml
query_audit:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
```
