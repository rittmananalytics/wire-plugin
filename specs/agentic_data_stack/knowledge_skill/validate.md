---
wire_schema: "1.0"
command: validate
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
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Check knowledge skill files are complete, accurate, and correctly colocated
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Knowledge Skill Validate

## Validation Checks

- [ ] A DOMAIN_REFERENCE.md exists for every domain in governance_design
- [ ] Every file has the required frontmatter (domain, canonical_table, owner, last_updated)
- [ ] Every file has: "What This Domain Covers", "Canonical Table" with field list, "Semantic Layer Metrics", "Common Questions", "Known Limitations", "Deprecated Tables"
- [ ] Deprecated tables section matches governance_design deprecation list
- [ ] Semantic layer metric names in each file match the actual metrics implemented in semantic_layer
- [ ] Every "Common Questions" example has been tested and returns correct output
- [ ] Files are colocated in the dbt project (not in .wire/ folder) — unless no dbt project exists
- [ ] Knowledge skill index file exists and is complete

## Cross-Reference Check

For each DOMAIN_REFERENCE.md metric reference, verify the metric name matches an implemented metric:
```bash
grep -h "^\| " models/marts/*/DOMAIN_REFERENCE.md | grep -v "^| Field\|^| Metric\|^| Table" | awk '{print $2}' | sort -u
# Compare against: dbt sl list metrics
```

## Status Update

```yaml
knowledge_skill:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
  domains_covered: N
```
