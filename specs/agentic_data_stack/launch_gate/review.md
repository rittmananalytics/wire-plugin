---
wire_schema: "1.0"
command: review
artifact: launch_gate
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
  - artifact: launch_gate
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Platform owner sign-off on cleared domains and launch communications
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Launch Gate Review

## Purpose

Final sign-off from the platform owner before the agent is announced. Confirm cleared domains, agree launch communications, and schedule blocked domains for a second launch wave.

## Workflow

### Step 1: Surface Meeting Context

Search Fathom for any prior conversations about the agentic data stack launch timeline, stakeholder expectations, or concerns raised about data accuracy in executive meetings.

### Step 2: Present Launch Gate Report

Present the output of launch_gate validate. Do not negotiate the blocked domains — only cleared domains launch. If `adversarial_calibration_gate: blocked` in status.md, lead with that — it blocks every domain regardless of individual eval pass rates, so there's nothing to negotiate per-domain until it's resolved.

```
## Launch Gate Review

Adversarial calibration gate: [CLEARED / BLOCKED / not applicable]

Ready to launch: [N] domains ([list])
Blocked (second wave): [N] domains — [brief reason each]

For cleared domains, we recommend announcing to [audience] on [date].
```

### Step 3: Agree Launch Communications

Draft the internal announcement for cleared domains:

```
Subject: [Client] Agentic Data Stack now live — orders and customers domains

The agentic data stack is now available for questions about [domains].

Ask it questions like:
- "What was revenue last month by channel?"
- "How many active customers do we have this week?"
- "Show me top 10 customers by spend this quarter"

Every answer includes a source footer showing which tier the answer came from 
(Semantic / Curated / Raw) and data freshness.

Accuracy note: We tested [N] questions per domain and achieved [X]% accuracy. 
Some questions may still return incorrect answers — always verify high-stakes 
figures against your canonical dashboard before including in external reports.

Questions or issues? Contact [data-platform-owner].
```

### Step 4: Schedule Second Wave

Set a date for the second wave (blocked domains). Typical gap: 2 weeks for metric fixes, 4 weeks if significant semantic layer changes are required.

### Step 5: Record Sign-off

```yaml
launch_gate:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
  domains_launched: ["orders", "customers"]
  second_wave_date: YYYY-MM-DD
  launch_comms_drafted: true
```

## After Launch

Wire the eval suite into CI immediately after launch — do not wait for the second wave. Every PR to the dbt project should trigger the eval runner for cleared domains.

The agentic data stack will drift without active maintenance. The Anthropic post documents a fall from 95% to 65% accuracy within one month without it. Colocation of DOMAIN_REFERENCE.md with dbt models and the CI check are the maintenance mechanism — remind the data team of this at handover.
