---
project_id: "{{PROJECT_ID}}"
project_name: "{{PROJECT_NAME}}"
project_type: "agentic_commerce"
client_name: "{{CLIENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "storefront"

# Agentic Commerce metadata
ecommerce:
  platform: "shopify"                          # shopify | woocommerce | custom
  lovable_project_url: null
  github_repo: null
  supabase_project_url: null
  search_provider: null                        # vertex_ai | algolia | pgvector | openai_pinecone
  image_generation_model: null                 # gemini_flash | dalle3 | stable_diffusion

jira:
  project_key: null
  epic_key: null
  artifacts:
    storefront:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    semantic_search:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    conversational_assistant:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    virtual_tryon:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    visual_similarity:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    llm_tools:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    personalisation:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    ucp_server:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    demo_orchestration:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null

docstore:
  provider: null
  confluence:
    cloud_id: null
    space_key: null
    parent_page_id: null
  notion:
    parent_page_id: null

artifacts:
  storefront:
    generate: not_started
    validate: not_started
    review: not_started
    github_repo: null
    lovable_url: null
    generated_date: null
    generated_files: []
    revision_history: []
  semantic_search:
    generate: not_started
    validate: not_started
    review: not_started
    search_provider: null
    products_indexed: null
    generated_date: null
    generated_files: []
    revision_history: []
  conversational_assistant:
    generate: not_started
    validate: not_started
    review: not_started
    llm_provider: null
    generated_date: null
    generated_files: []
    revision_history: []
  virtual_tryon:
    generate: not_started
    validate: not_started
    review: not_started
    image_model: null
    generated_date: null
    generated_files: []
    revision_history: []
  visual_similarity:
    generate: not_started
    validate: not_started
    review: not_started
    approach: null         # realtime | precomputed
    generated_date: null
    generated_files: []
    revision_history: []
  llm_tools:
    generate: not_started
    validate: not_started
    review: not_started
    llm_provider: null
    generated_date: null
    generated_files: []
    revision_history: []
  personalisation:
    generate: not_started
    validate: not_started
    review: not_started
    event_store: null      # supabase | bigquery
    generated_date: null
    generated_files: []
    revision_history: []
  ucp_server:
    generate: not_started
    validate: not_started
    review: not_started
    payment_provider: null  # stripe
    generated_date: null
    generated_files: []
    revision_history: []
  demo_orchestration:
    generate: not_started
    validate: not_started
    review: not_started
    demo_modes: []          # shopping | search | tryon | full
    generated_date: null
    generated_files: []
    revision_history: []

notes:
  - "Project created: {{CREATED_DATE}}"

blockers: []
---

# Project Status: {{PROJECT_NAME}}

**Client**: {{CLIENT_NAME}}
**Project ID**: {{PROJECT_ID}}
**Type**: Agentic Commerce
**Created**: {{CREATED_DATE}}
**Last Updated**: {{LAST_UPDATED}}

**Lovable**: [not configured]
**GitHub Repo**: [not configured]
**Supabase**: [not configured]

## Current Phase: Storefront Setup

## Next Action

Run:
```
/wire:ac_storefront-generate {{PROJECT_ID}}
```

## Feature Status

| Phase | Feature | Generate | Validate | Review | Ready |
|-------|---------|----------|----------|--------|-------|
| **Foundation** | storefront | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Discovery** | semantic_search | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Engagement** | conversational_assistant | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | personalisation | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Visualisation** | virtual_tryon | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | visual_similarity | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Agentic** | llm_tools | ⏸️ | ⏸️ | ⏸️ | ❌ |
| | ucp_server | ⏸️ | ⏸️ | ⏸️ | ❌ |
| **Showcase** | demo_orchestration | ⏸️ | ⏸️ | ⏸️ | ❌ |

**Legend**: ✅ Complete | 🔄 In Progress | ❌ Failed | ⏸️ Not Started | ⚠️ Blocked

## Notes

[Add project-specific notes here]

## Blockers

[Add any blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|
