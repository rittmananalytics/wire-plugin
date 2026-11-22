---
wire_schema: "1.0"
command: review
artifact: adversarial_config
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
  - artifact: adversarial_config
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Technical review of adversarial review configuration and calibration
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Adversarial Config Review

## Workflow

### Step 1: Review Calibration Results

Present calibration test results. For each test, show:
- The intentionally wrong query
- What the adversarial check caught
- The corrected answer

### Step 2: Review Plausibility Bounds

Walk through the plausibility bounds with a domain owner who knows the business metrics. Wrong bounds produce false positives (adversarial flags correct answers) which erode trust in the agent.

### Step 3: Confirm Mode

Confirm the adversarial mode (inline vs standalone) matches the client's latency and cost requirements.

### Step 4: Update Status

```yaml
adversarial_config:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
```
