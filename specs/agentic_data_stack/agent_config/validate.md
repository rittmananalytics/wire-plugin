---
wire_schema: "1.0"
command: validate
artifact: agent_config
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
  - artifact: agent_config
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Verify agent config skill completeness and routing logic correctness
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Agent Config Validate

## Validation Checks

- [ ] SKILL.md contains all three routing tiers in correct order (Semantic → Curated → Raw)
- [ ] Every domain from knowledge_skill_index is listed in the Tier 2 domain table
- [ ] Adversarial review section is present with all 5 checks
- [ ] Provenance footer template is present with all required fields (tier, dataset, freshness, owner)
- [ ] Deprecated tables list matches governance_design deprecation list
- [ ] Installation instructions are complete and accurate
- [ ] dbt MCP server configuration is correct for the warehouse/project
- [ ] Skill frontmatter name and description are accurate for the client

## Smoke Test

Run the agent config skill against one test question per domain and confirm:
1. The skill routes to Tier 1 (semantic layer) for questions with defined metrics
2. The skill routes to Tier 2 (knowledge file) for questions without metrics
3. Provenance footer appears on every response

## Status Update

```yaml
agent_config:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
  smoke_test: pass
```
