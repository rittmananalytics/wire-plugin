---
wire_schema: "1.0"
command: review
artifact: agent_config
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
  - artifact: agent_config
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Technical review of agentic data stack skill before eval suite build
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Agent Config Review

## Purpose

Technical review by the data engineering lead to confirm the agent skill is correctly wired to the client's infrastructure before building the eval suite against it.

## Workflow

### Step 1: Live Demo

Run 3 questions live in the review — one that hits the semantic layer (Tier 1), one that hits the knowledge file (Tier 2), and one that requires raw SQL fallback (Tier 3). Show the provenance footer on each.

### Step 2: Confirm Routing Logic

Walk through each tier with the data team:
- Is the semantic layer correctly configured?
- Are the knowledge file paths correct?
- Is the deprecated tables list complete?

### Step 3: Adversarial Review Check

Run one question where the naive answer would be wrong (e.g. a revenue question against a domain where the filter matters). Confirm the adversarial review catches the error and corrects it before responding.

### Step 4: Record Sign-off

```yaml
agent_config:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
  live_demo: pass
```
