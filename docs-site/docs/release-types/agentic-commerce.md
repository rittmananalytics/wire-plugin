---
sidebar_position: 10
title: Agentic Commerce
---

# Agentic Commerce Release

The Agentic Commerce release type (`project_type: agentic_commerce`) is for engagements where the deliverable is an AI-powered ecommerce storefront. It combines Lovable (rapid frontend scaffolding), Shopify (product catalog and cart), GitHub (code hosting), Supabase (backend state), Google Cloud (AI/search), and optionally Stripe (payments).

**In-scope features**: `ac_storefront`, `ac_semantic_search`, `ac_conversational_assistant`, `ac_virtual_tryon`, `ac_visual_similarity`, `ac_llm_tools`, `ac_personalisation`, `ac_ucp_server`, `ac_demo_orchestration`

## Prerequisites

| Service | What you need | Used by |
|---------|--------------|---------|
| Lovable | Account + new project | `ac_storefront` and all AI features |
| Shopify | Store + Storefront API access token | `ac_storefront`, `ac_personalisation` |
| GitHub | Account + Lovable GitHub App authorised | `ac_storefront` (code sync) |
| Supabase | Project enabled in Lovable Cloud | `ac_storefront`, `ac_personalisation` |
| GCP | Project with Vertex AI Retail API + BigQuery APIs enabled | `ac_semantic_search`, `ac_conversational_assistant` |
| Stripe | Account + secret key | `ac_ucp_server` |

## Workflow

```
/wire:new                                          # release_type: agentic_commerce

# Phase 1 — Base storefront (prerequisite for all other features)
/wire:ac_storefront-generate <release-folder>
/wire:ac_storefront-validate <release-folder>
/wire:ac_storefront-review <release-folder>

# Phase 2 — Agentic features (can be developed in parallel after storefront approved)
/wire:ac_semantic_search-generate <release-folder>
/wire:ac_semantic_search-validate <release-folder>
/wire:ac_semantic_search-review <release-folder>

/wire:ac_conversational_assistant-generate <release-folder>
/wire:ac_conversational_assistant-validate <release-folder>
/wire:ac_conversational_assistant-review <release-folder>

/wire:ac_virtual_tryon-generate <release-folder>
/wire:ac_virtual_tryon-validate <release-folder>
/wire:ac_virtual_tryon-review <release-folder>

/wire:ac_visual_similarity-generate <release-folder>
/wire:ac_visual_similarity-validate <release-folder>
/wire:ac_visual_similarity-review <release-folder>

/wire:ac_llm_tools-generate <release-folder>
/wire:ac_llm_tools-validate <release-folder>
/wire:ac_llm_tools-review <release-folder>

/wire:ac_personalisation-generate <release-folder>
/wire:ac_personalisation-validate <release-folder>
/wire:ac_personalisation-review <release-folder>

/wire:ac_ucp_server-generate <release-folder>
/wire:ac_ucp_server-validate <release-folder>
/wire:ac_ucp_server-review <release-folder>

/wire:ac_demo_orchestration-generate <release-folder>
/wire:ac_demo_orchestration-validate <release-folder>
/wire:ac_demo_orchestration-review <release-folder>

/wire:archive <release-folder>
```

## What each generate command does

**`/wire:ac_storefront-generate`** — walks through a 5-phase Lovable prompt sequence: brand foundation → product grid layout → Shopify Storefront API wiring → cart and checkout flow → GitHub sync.

**`/wire:ac_semantic_search-generate`** — implements AI-powered product search using Google Cloud Retail API (Vertex AI for Retail) for semantic vector search.

**`/wire:ac_conversational_assistant-generate`** — builds a multi-turn shopping assistant using Google Cloud Retail API Conversational Search.

**`/wire:ac_virtual_tryon-generate`** — adds a "Try it on" button to product pages with Lovable AI Gateway (Gemini Flash) composite image generation.

**`/wire:ac_visual_similarity-generate`** — adds "Find similar" on product cards using Gemini multimodal embeddings.

**`/wire:ac_llm_tools-generate`** — implements Gemini 2.5 Flash with function calling: `search_products`, `get_product_details`, `add_to_cart`, `get_recommendations`.

**`/wire:ac_personalisation-generate`** — sets up anonymous user profiles in Supabase, event tracking, and dynamic UX elements.

**`/wire:ac_ucp_server-generate`** — implements a Universal Commerce Protocol merchant server with Stripe payment intent integration.

**`/wire:ac_demo_orchestration-generate`** — adds a floating demo control panel with a 5-phase state machine.

## Dependency order

`ac_storefront` must reach **Approved** status before any other `ac_*` feature can begin. After that, features can be developed in parallel. `ac_demo_orchestration` should be the final feature — it wraps all others into a cohesive demo flow.

## Tips

- Run the full Lovable prompt sequence from `ac_storefront-generate` **before** making any code edits in GitHub
- After GitHub sync is complete, all subsequent development happens in the GitHub repo via Claude Code
- Keep the Shopify Storefront API token out of the frontend bundle — pass it via Supabase Edge Functions
