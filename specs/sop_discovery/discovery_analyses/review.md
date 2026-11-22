---
wire_schema: "1.0"
command: review
artifact: discovery_analyses
domain: sop_discovery
release_types:
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: discovery_analyses
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of the three analyses (Head of Delivery + peer consultant)

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Discovery Analyses — Review

## Purpose

The internal RA review gate before the Findings Playback deck is generated. Reviewer is the **Head of Delivery + one peer Lead Consultant**. This is the playbook's Phase 3 Step 10 review — its job is to challenge the diagnoses, especially the Maturity pin, before the analyses get baked into a sponsor-facing deck.

Not sponsor-facing.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- `.wire/releases/$ARGUMENTS/planning/discovery_analyses_validation.md`
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read inputs.

### Step 2: Pull document store comments

If a document store is configured, follow `specs/utils/docstore_fetch.md` — reviewers often annotate the Confluence mirror with margin comments.

### Step 3: Present for review

Output:
1. The Maturity pin and justification
2. The Hierarchy diagnosis bullets + chart counts
3. The PPT diagnosis bullets + chart counts
4. The Sponsor decisions required list
5. Phase 1 MoSCoW summary (Must/Should counts)

Then prompt:

```
Review focus — the playbook's explicit challenge points:

1. **Maturity pin** — is it placed too generously? Prior engagements have landed at Data Chaos and the engagements were better for it. If the prose doesn't justify the pin, push back.

2. **Hierarchy/PPT consistency** — does the Hierarchy chart contradict the PPT diagnosis? (E.g. Hierarchy top-heavy + PPT diagnosis says foundations are missing → one of them is wrong.)

3. **Diagnosis specificity** — are the bullets specific enough to land with the sponsor, or are they consultant-speak?

4. **Phase 1 scope** — does Phase 1 fit the SoW budget? If 28 rows are Phase 1 Must and the SoW says 6 weeks, something has to give.

5. **Vision Statement** — the deck will derive its Vision Statement from these analyses. Is the diagnosis strong enough that the Vision Statement will write itself? If not, the analyses aren't ready.
```

Then `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the internal RA review of the three analyses?",
    "header": "Discovery Analyses Review",
    "options": [
      {"label": "Approved", "description": "Ready to draft the Findings Playback deck"},
      {"label": "Approved with edits", "description": "Specific diagnosis bullets or word-cloud labels need tightening"},
      {"label": "Re-pin Maturity Curve", "description": "Pin is too generous or too harsh — re-place with evidence"},
      {"label": "Re-analyse", "description": "Material issue with Hierarchy/PPT classification or Phase scoping — go back to Step 3"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Capture corrections

Apply inline edits if approved-with-edits. For pin re-placement, ask for the new pin + justification and apply directly. For re-analyse, append a `## Review Decisions` section listing what needs to change and reset `discovery_analyses.generate: not_started`.

### Step 5: Update status

```yaml
artifacts:
  discovery_analyses:
    review: complete    # or "pending_rework"

sponsor_validation:
  maturity_pin: "<confirmed pin>"   # only set if review approves
```

### Step 6: Output review summary

```
## Discovery Analyses Review Complete

**Outcome**: [Approved / Approved with edits / Re-pin / Re-analyse]
**Maturity pin (confirmed)**: [Data Chaos / Order / ...]
**Edits applied**: [N]

### Next Steps

[If approved]:
Generate the Findings Playback deck:
/wire:findings-playback-generate $ARGUMENTS

[If re-analyse]:
Update the analyses:
/wire:discovery-analyses-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
