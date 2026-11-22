---
wire_schema: "1.0"
command: validate
artifact: security_audit
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: security_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate security audit completeness

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Security Audit — Validate

## Purpose

Checks that the security audit covers all role types, that every policy has a migration approach, and that service accounts used by integrations are explicitly captured.

## Validation Checks

**Check 1 — All roles have migration approach**
Every role in the audit has a non-null `migration_approach`.
PASS/FAIL with list of gaps.

**Check 2 — All users and service accounts listed**
The audit includes at least one user entry and explicitly notes all service accounts used by Fivetran, dbt Cloud, and any BI tools.
PASS: Service accounts documented.
FAIL: Note which service accounts appear to be missing.

**Check 3 — Row-level security policies have SQL**
Every RLS policy has the full policy SQL definition captured.
PASS: All RLS policies have definitions.
FAIL: List policies missing definitions.

**Check 4 — Column masking policies documented**
Every masking policy has its logic documented (at minimum: which columns it applies to and what the masking rule is).
PASS: All masking policies documented.
FAIL: List policies with incomplete documentation.

**Check 5 — Evaluate objects have assessment notes**
All objects with `migration_approach: evaluate` have notes explaining what further investigation is needed.
PASS: All evaluate objects have notes.
FAIL: List objects without notes.

**Check 6 — Network policies documented**
If any network policies exist, they are listed with their IP allowlist/denylist rules.
PASS: Network policies documented or none exist.
FAIL: Network policies present but not documented.

### Update status

```yaml
artifacts:
  security_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `security_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `security_audit` as artifact_id, `Security Audit` as artifact_name, and the `file` value from `artifacts.security_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `security_audit` as artifact, `validate` as action.
