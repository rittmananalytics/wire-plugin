---
wire_schema: "1.0"
command: validate
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
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify adversarial review configuration and calibration results
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Adversarial Config Validate

## Validation Checks

- [ ] Client decision on adversarial review mode is recorded (enabled/disabled)
- [ ] If enabled: adversarial section is present in agentic-data-stack-SKILL.md
- [ ] All 5 calibration checks are defined: source, filter, grain, plausibility, definition
- [ ] Plausibility bounds are set and reviewed by domain owner (not default guesses)
- [ ] Calibration test results are recorded
- [ ] At least 4/5 calibration tests passed (adversarial caught the error)

## Status Update

```yaml
adversarial_config:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
```
