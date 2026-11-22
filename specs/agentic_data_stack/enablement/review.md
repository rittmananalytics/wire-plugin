---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Sign-off on user guide and maintenance documentation before handover
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Enablement Review

## Workflow

### Step 1: User Guide Review

Share the user guide with a representative data consumer — ideally someone from finance or operations who will use the agent. Confirm:
- The "How to Ask Good Questions" section resonates with real usage patterns
- The limitations are honest and not underselling the agent's gaps
- The contact information is correct

### Step 2: Maintenance Guide Review

Review the maintenance guide with the data engineering lead. Confirm:
- The model change workflow matches their actual PR process
- The monthly eval check is feasible given their team capacity
- The CI check configuration is compatible with their CI setup

### Step 3: Handover Sign-off

```markdown
# Agentic Data Stack — Handover Sign-off

Signed off: [Data Platform Owner]
Date: YYYY-MM-DD

User guide: approved for distribution  
Maintenance guide: reviewed and accepted by data engineering team  
CI eval check: [configured / to be configured by data team]  
Second wave date confirmed: YYYY-MM-DD  
```

### Step 4: Update Status

```yaml
enablement:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
```
