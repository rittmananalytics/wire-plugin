---
name: segment
description: Skill for working with Twilio Segment as an event-tracking ingestion source. Activates when the user mentions Segment, the Segment Public API, tracking plans, sources, destinations, or event taxonomy in the Segment sense. Uses the Segment Public API directly (no MCP server) — bearer-token REST.
---

# Segment Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | segment | activated | Segment Public API work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.

---

## When This Skill Activates

- The user mentions **Segment** (Twilio Segment) as a CDP, **Segment Public API**, or **Segment Config API**.
- The user wants to **list, inspect, or audit** Segment sources, destinations, tracking plans, or workspaces.
- The user is **planning a Segment-based event ingestion architecture** or **migrating off** Segment (typically to RudderStack).
- Wire's `ingestion_audit` is running against a client that uses Segment.

---

## How Segment is accessed from Wire

Segment does **not** ship an official MCP server. This skill drives Segment via the **Segment Public API** — token-authenticated REST endpoints, called using `WebFetch` or by writing throwaway Python / curl scripts inside the release's `dev/` folder.

**Base URLs** (region matters):
| Workspace region | Base URL |
|---|---|
| US (default) | `https://api.segmentapis.com` |
| EU | `https://eu1.api.segmentapis.com` |

**Authentication**: Bearer token, generated inside the Segment workspace at **Settings → Access Management → Tokens**. Use a **Public API token** (distinct from the legacy Config API token). Treat the token as a secret.

**Auth header** (verbatim):
```
Authorization: Bearer $SEGMENT_TOKEN
```

**Transport**: HTTPS only (port 443). HTTP/1.1 and HTTP/2 are accepted; plain HTTP on port 80 is rejected.

Reference: https://docs.segmentapis.com/

---

## Common endpoints used in Wire workflows

The Public API is GraphQL-style under REST. The endpoints most relevant to ingestion-audit work:

| Endpoint | Purpose |
|---|---|
| `GET /` | Workspace identity — sanity check the token works |
| `GET /sources` | List all sources in the workspace |
| `GET /sources/{id}` | Source detail: type, slug, attached schema, library config |
| `GET /destinations` | List all destinations |
| `GET /destinations/{id}` | Destination detail: target, settings, source filter |
| `GET /sources/{id}/connected-destinations` | Source → destination routing |
| `GET /tracking-plans` | List tracking plans |
| `GET /tracking-plans/{id}` | Tracking plan rules: events, properties, types, allowed values |
| `GET /tracking-plans/{id}/sources` | Sources using a given tracking plan |
| `GET /workspaces/{id}` | Workspace metadata |

For the full surface refer to https://docs.segmentapis.com/.

---

## Setup

1. **Generate a Public API token**: Segment workspace → Settings → Access Management → Tokens → **Create token** (Public API, not Config API).
2. **Store the token** in your environment, never in a tracked file:
   ```bash
   export SEGMENT_TOKEN='your-token-here'
   export SEGMENT_BASE='https://api.segmentapis.com'   # or eu1 variant for EU workspaces
   ```
3. **Sanity check**:
   ```bash
   curl -s -H "Authorization: Bearer $SEGMENT_TOKEN" "$SEGMENT_BASE/" | head -20
   ```

---

## Use within Wire workflows

### `ingestion_audit` for a `platform_migration` release where source = Segment

When `migration.ingestion_tool: segment` is set in `status.md`:

1. The ingestion_audit step iterates `GET /sources` and writes the source inventory to `audit/ingestion_audit.md` and the machine-readable CSV.
2. Per source: capture type (analytics.js / iOS / Android / server / cloud source), slug, library version, attached tracking plan, and the list of connected destinations.
3. Per destination: capture type (warehouse / marketing / analytics), settings (without secret values), and the source filter rules if any.
4. Per tracking plan: capture event count, mandatory properties, and any validation failures observed in the workspace.

Output is the standard `ingestion_audit.md` format. The Segment-specific addition: a **migration path matrix** flagging which destinations have direct RudderStack equivalents (most do), which need replacement (e.g. some legacy custom destinations), and which are warehouse destinations that the platform_migration release will rebuild on the new warehouse.

### Migration to RudderStack

The most common Segment migration is to RudderStack (Segment's main open-source / self-hostable alternative). The tracking-plan schema is nearly identical; the SDKs are drop-in replacements at the API level. The migration_strategy artifact for `from: segment` → `to: rudderstack` is largely **client SDK swap + tracking plan re-host + destination re-mapping** rather than warehouse migration.

If migrating Segment + a warehouse together, run two parallel `platform_migration` releases: one for Segment → RudderStack, one for the warehouse pair (e.g. BigQuery → Snowflake).

### New ingestion build using Segment

When a new `pipeline_only` or `full_platform` release picks Segment as the ingestion tool:

1. Generate the tracking plan first; the SDKs are a downstream artifact.
2. Use Segment's analytics.js for web, native SDKs for mobile, language SDKs for servers. The Wire `pipeline-generate` step should follow Segment's source-specific patterns.
3. Configure destinations via the Public API rather than the UI where possible — keeps the configuration auditable.

---

## Segment core concepts

| Term | What it means |
|---|---|
| **Source** | A point where events enter Segment (analytics.js, iOS SDK, Android SDK, server SDK, cloud source) |
| **Destination** | A target where events are routed (warehouse, marketing tool, analytics tool) |
| **Tracking plan** | Schema for the events a source is allowed to emit |
| **Workspace** | Top-level Segment account; tokens are workspace-scoped |
| **Public API token** | Bearer token for the modern Public API (Settings → Access Management → Tokens) |
| **Config API** | The older API; deprecated in favour of the Public API for new work |

---

## Tokens, secrets, and audit hygiene

- **Never** check the Segment token into git — not in `.wire/`, not in env files, not in scripts.
- For automation in a Wire engagement, use a CI-side secret store (GitHub Actions secrets, GCP Secret Manager, etc.) and reference the token by name.
- For local exploration, use a shell session variable as shown in Setup.
- The Wire `ingestion_audit.md` output captures destination + source **names**, not credentials — secrets never appear in audit artifacts.

---

## What this skill does NOT do

- Does not write tracking calls inside client apps — that's an engineering task following the tracking plan.
- Does not author destinations on the destination side (e.g. writing to BigQuery is configured in Segment; the warehouse and IAM are set up separately).
- Does not decide whether Segment is the right CDP for the engagement — that's a discovery / requirements decision.
- Does not store the bearer token. The token lives in the user's shell or secret store; this skill drives the API using whatever's in `$SEGMENT_TOKEN`.
