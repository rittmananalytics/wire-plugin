---
wire_schema: "1.0"
command: validate
artifact: canonical_models
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
  - artifact: canonical_models
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify canonical models compile, tests pass, and deprecation notices are in place
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Canonical Models Validate

## Validation Checks

Run `dbt test --select tag:canonical` and check:

- [ ] All canonical model tests pass (0 failures)
- [ ] Every canonical model has a schema.yml description
- [ ] Every canonical model PK has `unique` + `not_null` tests
- [ ] Every foreign key has a `relationships` test
- [ ] Every deprecated model has the `deprecated` tag and a sunset date in its description
- [ ] No canonical model references a deprecated table via `{{ ref() }}`
- [ ] `dbt compile` completes with 0 errors

Run structural checks:

```bash
# Check all canonical models have descriptions
grep -r "description:" <dbt_project_path>/models/marts/ | grep -v "^Binary" | wc -l

# Check deprecated tag applied
dbt ls --select tag:deprecated --output json | jq 'length'
```

## Status Update

```yaml
canonical_models:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
  dbt_test_pass_rate: 100%
```
