---
wire_schema: "1.0"
command: validate
artifact: analytics_enablement
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
  - artifact: analytics_enablement
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify enablement documents are complete and accurate
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Enablement Validate

## Validation Checks

- [ ] User guide covers: what the agent does, how to ask questions, source footer explanation, limitations, when to double-check
- [ ] User guide domain lists match `domains_launched` from launch gate
- [ ] Second wave date is correct
- [ ] Maintenance guide covers: model change workflow, metric addition workflow, monthly eval check
- [ ] Domain owner contacts in maintenance guide are correct and current
- [ ] Data freshness lag is accurately stated

## Status Update

```yaml
enablement:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
```
