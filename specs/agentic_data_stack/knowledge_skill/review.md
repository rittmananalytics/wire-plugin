---
wire_schema: "1.0"
command: review
artifact: knowledge_skill
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
  - artifact: knowledge_skill
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Domain owner review of knowledge skill files before agent configuration
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Knowledge Skill Review

## Purpose

Have each domain owner review their DOMAIN_REFERENCE.md file. They are the authority on what the data means, what the edge cases are, and what questions the agent is likely to get wrong. A 30-minute review per domain is standard.

## Workflow

### Step 1: Surface Meeting Context

Search Fathom for prior conversations where domain owners have described data edge cases, business logic exceptions, or "gotcha" behaviours — these often get missed in documentation and belong in DOMAIN_REFERENCE.md.

### Step 2: Domain Owner Review

For each domain, share the DOMAIN_REFERENCE.md with the domain owner and ask them to confirm:

1. **Coverage**: Are all the key entities and metrics represented? Any important fields missing?
2. **Accuracy**: Are the descriptions correct? Any subtle business logic issues in the field descriptions?
3. **Edge cases**: Are all known data quality issues, timezone quirks, and "gotcha" patterns documented?
4. **Common questions**: Do the example questions and answers represent what their team actually asks?

### Step 2: Incorporate Feedback

Update each DOMAIN_REFERENCE.md based on owner feedback. Domain owners will almost always identify:
- A field that behaves unexpectedly in edge cases
- A metric that looks right but uses the wrong filter for finance reporting purposes
- A question pattern not in the list that is actually the most common question they get

### Step 3: Record Sign-off

```markdown
# Knowledge Skill Review Sign-off

| Domain | Reviewer | Date | Status |
|---|---|---|---|
| orders | Jane Smith (Finance Lead) | YYYY-MM-DD | Approved |
| customers | Tom Brown (Analytics) | YYYY-MM-DD | Approved with changes |
```

### Step 4: Update Status

```yaml
knowledge_skill:
  review: approved
  reviewer: Multiple (see sign-off doc)
  review_date: YYYY-MM-DD
```
