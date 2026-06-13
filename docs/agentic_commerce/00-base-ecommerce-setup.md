# Base E-Commerce Site Setup via Lovable

A step-by-step guide to building a production-ready e-commerce storefront through Lovable's chat interface, culminating in a GitHub-synced codebase ready for agentic commerce feature development.

## Overview

This playbook walks through the exact prompts and configuration steps needed to go from a blank Lovable project to a fully functional Shopify-powered storefront. Once the base site is complete, the codebase is synced to GitHub where all subsequent AI/agentic feature development happens via Claude Code or a local IDE.

## Architecture

```
Lovable Chat Interface
  → React 18 + Vite + Tailwind + TypeScript scaffold
  → Shopify Storefront API integration
  → Zustand cart state management
  → Supabase (Lovable Cloud) backend
  → GitHub bidirectional sync
      → Clone locally / use Claude Code for agentic features
```

## Phase 1 — Project Creation & Brand Foundation

### Step 1: Create the Lovable Project

Create a new Lovable project. In the first prompt, establish the brand identity and visual direction:

**Example prompt:**

> Create a modern e-commerce storefront for [Brand Name], a [industry] brand. The design should be [aesthetic description — e.g. minimal, editorial, bold]. Use a serif/display font for headings and a clean sans-serif for body text. The colour palette should be [describe palette or reference]. Include a navbar with the brand name, category navigation, and a cart icon. Add a hero section with a tagline and a product grid below it. No mock products yet — just the empty grid with a "No products found" message.

### Step 2: Refine the Design System

Once the initial scaffold is rendered, refine the visual tokens:

**Example prompt:**

> Update the design system: set the primary colour to [HSL values], add a muted background tone, and ensure all colours use CSS custom properties via index.css. The navbar should have a subtle bottom border, and product cards should have hover elevation. Make sure the site looks good in both light and dark modes.

**Key considerations:**
- All colours should be defined as HSL CSS variables in `index.css`
- Tailwind config should reference semantic tokens (`--primary`, `--background`, etc.)
- Typography should use `font-display` for headings and a system/sans stack for body

### Step 3: Add Core Pages

**Example prompt:**

> Add the following pages with proper routing: a product detail page at /product/:handle, a contact page, and policy pages for shipping, refunds, and terms of service. The product detail page should show a large image gallery, title, price, variant selector, description, and an Add to Cart button. Use placeholder content for now.

## Phase 2 — Shopify Integration

### Step 4: Connect Your Shopify Store

Before prompting for Shopify integration, ensure you have:
- A Shopify store (even on a free trial)
- The Storefront API access token
- Products published to the **Headless** sales channel

**Example prompt:**

> Connect this site to my Shopify store. Use the Shopify Storefront API to fetch and display real products. Replace the empty product grid with live product data showing images, titles, prices, and product types. Each product card should link to its detail page at /product/[handle].

**What Lovable will do:**
- Create a `src/lib/shopify.ts` module with the Storefront API client
- Set up GraphQL queries for product listing and individual product fetch
- Create a `useShopifyProducts` hook for data fetching
- Wire up the product grid and detail page to live data

### Step 5: Configure the Product Catalog Display

**Example prompt:**

> Add category filtering to the product grid. Create navigation links for [your categories — e.g. "Shirts", "Trousers", "Accessories"]. Each category should filter products using a Shopify query parameter. Show all products by default. Make sure the grid is responsive — 1 column on mobile, 2 on tablet, 3-4 on desktop.

### Step 6: Set Up Cart & Checkout

**Example prompt:**

> Implement a full shopping cart using Zustand for state management. The cart should persist across page refreshes using localStorage. When items are added, create a Shopify cart via the Storefront API cartCreate mutation. Include a slide-out cart drawer accessible from the navbar cart icon, showing item thumbnails, quantities with +/- controls, a remove button, line totals, and a "Checkout with Shopify" button that opens the Shopify checkout URL in a new tab.

**Critical requirements to verify:**
- Cart uses Shopify Storefront API mutations (`cartCreate`, `cartLinesAdd`, `cartLinesUpdate`, `cartLinesRemove`)
- Checkout URL includes `?channel=online_store` parameter
- Checkout opens in a new tab via `window.open(url, '_blank')`
- Cart syncs on tab visibility change (handles post-checkout return)
- No manual/hardcoded checkout URLs

### Step 7: Add the Product Detail Page

**Example prompt:**

> Make the product detail page fully functional. Fetch the product by handle from the Shopify Storefront API. Show all product images in a gallery, display all variant options (size, colour, etc.) as selectable buttons, update the displayed price when variants change, and disable the Add to Cart button for out-of-stock variants. Include the full product description below.

## Phase 3 — Backend & Infrastructure

### Step 8: Enable Lovable Cloud (Supabase)

Lovable Cloud provides the backend infrastructure needed for agentic features later. Set it up now:

**Example prompt:**

> Set up the backend for this project. I'll need a database for caching search results and storing user interaction data later. For now, just ensure the Supabase client is configured and working.

**What this establishes:**
- Supabase client at `src/integrations/supabase/client.ts` (auto-generated)
- Edge functions runtime for future AI integrations
- Database for search caching, analytics events, user profiles
- File storage for user-uploaded images (e.g. virtual try-on)

### Step 9: Add Authentication (Optional but Recommended)

**Example prompt:**

> Add a sign-in/sign-up page at /auth using email and password authentication. Show a user avatar in the navbar when signed in, with a dropdown for sign-out. Don't enable auto-confirm — users should verify their email.

### Step 10: Add SEO & Meta

**Example prompt:**

> Add proper SEO to all pages. Each page should have a unique title tag under 60 characters and a meta description under 160 characters. The homepage should have a single H1. Product detail pages should use the product title as the H1 and include structured data (JSON-LD) for Product schema. Add a robots.txt and ensure images have alt text.

## Phase 4 — GitHub Sync & Handoff

### Step 11: Connect to GitHub

1. In the Lovable editor, go to **Project Settings → GitHub → Connect project**
2. Authorise the Lovable GitHub App
3. Select your GitHub account or organisation
4. Click **Create Repository**

This creates a new repository with the full project codebase. From this point, changes flow bidirectionally:
- Edits in Lovable auto-push to GitHub
- Pushes to GitHub auto-sync to Lovable

### Step 12: Clone & Verify Locally

```bash
git clone https://github.com/[your-org]/[your-repo].git
cd [your-repo]
npm install
npm run dev
```

Verify:
- Products load from Shopify
- Cart operations work (add, update, remove, checkout)
- Pages render correctly
- Authentication works (if enabled)

### Step 13: Set Up for Agentic Feature Development

Create a `.claude` or project instructions file in the repo root to guide AI-assisted development:

```markdown
# Project Context

This is a React 18 + Vite + Tailwind CSS + TypeScript e-commerce storefront.

## Key Architecture
- **Product data**: Shopify Storefront API (see src/lib/shopify.ts)
- **State management**: Zustand (see src/stores/)
- **Backend**: Supabase via Lovable Cloud (see src/integrations/supabase/)
- **Edge functions**: supabase/functions/ (auto-deployed)
- **Styling**: Tailwind with CSS custom properties (see src/index.css)

## Environment Variables
- VITE_SUPABASE_URL — Supabase project URL
- VITE_SUPABASE_PUBLISHABLE_KEY — Supabase anon key

## Adding New Features
- Edge functions go in supabase/functions/[name]/index.ts
- New pages go in src/pages/ and must be added to the router in App.tsx
- All API keys for external services should be stored as Supabase secrets
- Use the existing storefrontApiRequest() helper for Shopify API calls
```

## Pre-Flight Checklist

Before moving to agentic feature development, verify:

| Item | Status |
|------|--------|
| Products display from Shopify Storefront API | ☐ |
| Product detail pages render with variants | ☐ |
| Cart add/update/remove works | ☐ |
| Checkout opens Shopify checkout in new tab | ☐ |
| Cart persists across page refreshes | ☐ |
| Cart clears after completed checkout | ☐ |
| Category filtering works | ☐ |
| Mobile responsive layout | ☐ |
| GitHub repo synced and up to date | ☐ |
| Supabase client configured | ☐ |
| Edge functions directory exists | ☐ |
| SEO meta tags on all pages | ☐ |

## What Comes Next

With the base e-commerce site complete and the codebase in GitHub, you're ready to layer on agentic commerce capabilities. Each feature has its own playbook:

1. **Semantic Search** — Natural language product discovery via Vertex AI
2. **Conversational Shopping Assistant** — Multi-turn chat-driven commerce
3. **Virtual Try-On** — AI-powered product visualisation
4. **Visual Similarity** — "More like this" discovery
5. **LLM Chat with Tools** — Gemini-powered reasoning with API tool calling
6. **Personalisation Engine** — Behavioural tracking and dynamic recommendations
7. **UCP Merchant Server** — Standardised API for external AI agents
8. **Automated Demo Orchestration** — Scripted showcase flows

These features are developed against the GitHub-hosted codebase using Claude Code, Cursor, or any AI-assisted development environment, with changes syncing back to Lovable for preview and deployment.
