---
wire_schema: "1.0"
command: validate
artifact: data_residency_assessment
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
  - artifact: data_residency_assessment
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the data residency assessment — all required sections present and non-empty, processor-not-counsel framing intact

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Data Residency Assessment — Validate

## Purpose

Checks the data residency assessment for completeness: every required section is present and non-empty, the processor-not-counsel framing is intact, and the legal determinations are flagged for the client rather than asserted by RA. Produces a PASS/FAIL report.

## Prerequisites

- `migration/data_residency_assessment.md` exists (data_residency_assessment generate: complete)

## Validation Checks

**Check 1 — All required sections present and non-empty**
The document contains all seven sections, each with substantive content (not a placeholder heading):
1. Scope and purpose
2. Data inventory in scope
3. GDPR scope and lawful basis
4. Residency constraints for the target region
5. Historical-window legal review
6. Processor safeguards
7. Required client input / open legal questions
PASS: all seven present and non-empty. FAIL: list missing or empty sections.

**Check 2 — Processor-not-counsel framing present**
The document leads with the banner stating RA prepared it as data processor and that it is not legal advice; the controller/processor split is stated in the GDPR section.
PASS/FAIL.

**Check 3 — Legal determinations flagged, not asserted**
The lawful basis and the historical-window retention ruling are marked **[CLIENT DPO/LEGAL]**, not answered by RA. RA must not state a lawful basis as fact.
PASS: determinations flagged. FAIL: RA asserts a lawful basis or retention ruling without flagging it as the client's.

**Check 4 — Required client input section non-empty**
Section 7 lists at least the lawful basis and the historical-window retention ruling. It must never be empty.
PASS/FAIL.

**Check 5 — Target region and historical window stated**
The document states the target region (and BigQuery location) and the specific historical window (date range) being assessed, matching status.md.
PASS/FAIL.

**Check 6 — Historical-window review is specific**
Section 5 reviews the actual window being migrated — its date range, retention basis, and minimisation options — not a generic retention statement.
PASS/FAIL.

**Check 7 — Sign-off block present**
The document contains the sign-off block with both a client DPO/legal line and an RA line.
PASS/FAIL.

### Write validation report

Append a `## Validation` section to `migration/data_residency_assessment.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

Update status:
```yaml
artifacts:
  data_residency_assessment:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

If PASS: `/wire:data-residency-assessment-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact_id, `Data Residency Assessment` as artifact_name, and the `file` value from `artifacts.data_residency_assessment` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `data_residency_assessment` as artifact, `validate` as action.
