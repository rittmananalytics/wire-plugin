---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of security audit

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Security Audit — Review

## Purpose

Internal RA review confirming the security model is fully captured and that the migration team understands the privilege translation work required before target setup begins.

## Prerequisites

- `audit/security_audit.md` with `validate: pass`

## Workflow

### Step 1: Present audit summary

Display:
- Role count and hierarchy summary
- Users and service accounts in scope
- RLS and masking policies — count and complexity
- Objects requiring evaluation before target setup

### Step 2: Gather reviewer feedback

Ask the reviewer:

1. Are there any roles or users missing from this audit?
2. Do the evaluate decisions make sense — do we know how to handle them on the target?
3. Any compliance or regulatory constraints that affect how permissions should be migrated?
4. Is the service account list complete for all integration tools?

### Step 3: Apply feedback and record decision

Append review block to `audit/security_audit.md`:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested
```

### Step 4: Update status

```yaml
artifacts:
  security_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```
