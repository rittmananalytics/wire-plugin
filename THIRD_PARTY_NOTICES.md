# Third-party notices

The Wire Framework is copyright Rittman Analytics Ltd and licensed under the Functional Source License, Version 1.1, Apache 2.0 Future License (`LICENSE`). That licence covers Rittman Analytics' own work only. The components below are third-party work and remain under their own licences. Verbatim licence texts are in `third_party/licenses/`.

Source of truth: `wire/third_party/manifest.yaml`. Checked by `wire/tests/core/validate_third_party_notices.py`.

## 1. Shipped in the Wire packages

### 1.1 Skills adapted from dbt Labs

Source: https://github.com/dbt-labs/dbt-agent-skills. Copyright 2026 dbt Labs. Licence: Apache License 2.0 (`third_party/licenses/dbt-agent-skills.Apache-2.0.txt`). Modified by Rittman Analytics Ltd. Each folder has `LICENSE.txt` and `NOTICE.md`.

| Wire skill | Upstream skill |
|---|---|
| dbt-troubleshooting | troubleshooting-dbt-job-errors |
| dbt-unit-testing | adding-dbt-unit-test |
| dbt-semantic-layer | building-dbt-semantic-layer |
| dbt-migration | migrating-dbt-project-across-platforms, migrating-dbt-core-to-fusion |
| dbt-fusion | migrating-dbt-core-to-fusion |
| dbt-mcp-server | configuring-dbt-mcp-server |
| dbt-analytics-qa | answering-natural-language-questions-with-dbt |
| dbt-dag | creating-mermaid-dbt-dag |

### 1.2 Skills adapted from Google

Source: https://github.com/google/skills. Copyright Google LLC. Licence: Apache License 2.0 (`third_party/licenses/google-skills.Apache-2.0.txt`). Modified by Rittman Analytics Ltd.

bigquery-basics, cloud-run-basics, gcloud, google-cloud-recipe-auth, google-cloud-waf-cost-optimization, google-cloud-waf-security.

### 1.3 Skills adapted from Amplitude

Source: https://github.com/amplitude/mcp-marketplace. Copyright (c) 2026 Amplitude, Inc. Licence: MIT (`third_party/licenses/amplitude-mcp-marketplace.MIT.txt`).

add-analytics-instrumentation, analyze-account-health, analyze-ai-topics, analyze-chart, analyze-dashboard, analyze-experiment, analyze-feedback, compare-user-journeys, create-chart, create-dashboard, daily-brief, debug-replay, diagnose-errors, diff-intake, discover-analytics-patterns, discover-event-surfaces, discover-opportunities, instrument-events, investigate-ai-session, monitor-ai-quality, monitor-experiments, monitor-reliability, replay-ux-audit, review-agent-insights, taxonomy, weekly-brief.

### 1.4 Other adapted skills

| Wire skill | Source | Copyright | Licence |
|---|---|---|---|
| snowflake-semantic-views | https://github.com/MiguelElGallo/snowflake-semantic-view-skill | (c) 2025 Miguel P Z | MIT |
| snowflake-development (AI-readiness assessment section only) | https://github.com/Snowflake-Labs/ai-ready-data | Snowflake Inc. | Apache License 2.0 |

### 1.5 Vendored code and fonts

| Component | Version | Location | Copyright | Licence |
|---|---|---|---|---|
| Mermaid | 11.4.1 | `decks/kickoff/mermaid.min.js` | (c) 2014-2022 Knut Sveidqvist | MIT (`decks/kickoff/MERMAID-LICENSE.txt`) |
| DOMPurify, inside the Mermaid bundle | 3.2.1 | as above | Cure53 and contributors | Apache-2.0 OR MPL-2.0 (header kept in file) |
| js-yaml, lodash, cytoscape, inside the Mermaid bundle | as bundled | as above | their authors | MIT (headers kept in file) |
| Google Sans font | 2025 release | `decks/*/fonts/`, `skills/cowork-hubspot-sales-pipeline-weekly/design/fonts/` | (c) 2025 The Google Sans Project Authors | SIL Open Font License 1.1 (`OFL.txt` beside the fonts). "Google" and "Google Sans" are trademarks of Google LLC. |

### 1.6 Trademarks

Product names and logos in the kick-off deck (`decks/kickoff/assets/`), including partner badges, are trademarks of their owners and are used to describe Rittman Analytics' partnerships. No licence to them is granted.

## 2. Distributed separately: the Wire CLI's standalone agent

Experimental (wire#408). Not part of the plugin or extension packages. Published as release assets of the Wire CLI on `rittmananalytics/wire-plugin`.

| Component | Built from | Copyright | Licence |
|---|---|---|---|
| `wire-agent`: OpenAI Codex CLI with Wire branding | https://github.com/openai/codex, forked at https://github.com/rittmananalytics/codex (branch `wire/brand-<codex version>`, cut from the upstream release tag) | Copyright 2025 OpenAI; changes by Rittman Analytics Ltd | Apache License 2.0 (`third_party/licenses/openai-codex.Apache-2.0.txt`, upstream NOTICE in `third_party/licenses/openai-codex.NOTICE.txt`) |

Each `wire-agent` archive carries the upstream `LICENSE`, the upstream `NOTICE` and `WIRE-CHANGES.txt`, which states the files Rittman Analytics changed (Apache License 2.0, section 4). The changes are branding only: the welcome screen and the session title. "OpenAI" and "Codex" are names of OpenAI's company and software, used to say what the agent is built on; no endorsement by OpenAI is implied. The binary also contains the Rust crates Codex depends on, under their own licences (mostly MIT and Apache-2.0); Codex's NOTICE records the code it derives from Ratatui.

## 3. Not shipped: installed or loaded at run time

These are not part of the Wire packages. Wire's instructions install or load them on the user's machine, under their own licences.

| Component | Version | Licence |
|---|---|---|
| Omni agent skills (exploreomni/omni-agent-skills) | | Apache-2.0 |
| Metabase agent skills (metabase/agent-skills) | | MIT |
| Airbyte agent SDK (airbytehq/airbyte-agent-sdk) | | Elastic License 2.0 |
| RudderStack agent skills (rudderlabs/rudder-agent-skills) | | MIT |
| HubSpot admin skills (TomGranot/hubspot-admin-skills) | | MIT |
| Droughty | 0.20.1 | MIT |
| dbt Labs Agents Schema (`agents-schema`) | 0.0.11 | MIT |
| PyYAML, jsonschema, lkml, sqlglot, python-pptx, beautifulsoup4, sqlfluff | | MIT |
| Jinja2, WeasyPrint | | BSD-3-Clause |
| cairosvg | | LGPL-3.0-or-later |
| dbt-core, dbt-mcp | | Apache-2.0 |
| Chart.js (cdnjs) | 4.4.1 | MIT |
| marked (cdnjs, Wire Studio document preview) | 12.0.2 | MIT |
| DOMPurify (cdnjs, Wire Studio document preview) | 3.1.6 | MPL-2.0 OR Apache-2.0 |
| Mermaid (cdnjs, Wire Studio document preview) | 11.4.0 | MIT |
| vis-network (unpkg) | 9.1.2 | Apache-2.0 OR MIT |
| Font Awesome Free (cdnjs) | 5.15.4 | CC-BY-4.0 (icons), OFL-1.1 (fonts), MIT (code) |
| Inter, IBM Plex Mono, Lato, Roboto (Google Fonts) | | OFL-1.1 |
| OpenAI Codex CLI (`npm install -g @openai/codex`; the Wire CLI's `codex` harness) | | Apache-2.0 |
| Claude Code (the Wire CLI's `claude` harness) | | Proprietary, Anthropic Commercial Terms |
| LiteLLM (`wire bridge`, installed with pip into `~/.wire/bridge`) | | MIT, outside its enterprise folder |
