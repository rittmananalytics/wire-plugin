# Changelog

All notable changes to the Rittman Analytics Claude Skills repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [3.4.8] — April 2026

### Added

**Looker Dashboard Mockup** (`looker-dashboard-mockup/SKILL.md`)
- Generates pixel-accurate, interactive Looker dashboard HTML mockups from a plain-language description
- Activates on any request to mock up, prototype, visualise, or design a Looker dashboard
- Reads a bundled design system reference (`references/design-system.md`) for exact CSS properties, component classes, and Chart.js patterns
- Produces a single self-contained HTML file with full Looker UI chrome: teal sidebar, header, filter pills, tab bar, KPI stat cards, Chart.js charts, data tables, and footer
- Used by `/wire:mockups-generate` for dashboard-first projects; also available standalone for ad-hoc dashboard prototyping

---

## [3.4.0] — March 2026

### Added (Wire Framework v3.4.0)

**Skills**:
- Research Persistence (`research/SKILL.md`) — auto-activates during technical research; saves structured summaries to `.wire/research/sessions/`; `session:start` surfaces prior findings

**Wire Framework**:
- Two-tier engagement structure (`.wire/engagement/` + `.wire/releases/`)
- Discovery release type (Shape Up methodology): problem definition → pitch → release brief → sprint plan
- Session lifecycle commands: `session:start` / `session:end`
- `/wire:migrate` command for migrating pre-v3.4.0 flat layouts
- Wire Studio: all UI labels updated from "Project" to "Release"

---

## [3.3.2] — February 2026

### Added

**Skills**:
- dbt Fusion Migration (`dbt-fusion/SKILL.md`) — migrates dbt projects to the Fusion runtime
- dbt MCP Server (`dbt-mcp-server/SKILL.md`) — sets up dbt MCP server for Claude Code
- dbt Analytics Q&A (`dbt-analytics-qa/SKILL.md`) — answers business data questions against dbt projects
- dbt DAG Visualisation (`dbt-dag/SKILL.md`) — generates Mermaid lineage flowcharts

---

## [3.3.1] — January 2026

### Added

**Skills**:
- Dagster (`dagster/SKILL.md`) — assets-first pattern, dagster-dbt integration, Wire-specific conventions

---

## [3.3.0] — January 2026

### Added

**Skills**:
- dbt Semantic Layer (`dbt-semantic-layer/SKILL.md`)
- dbt Unit Testing (`dbt-unit-testing/SKILL.md`)
- dbt Migration (`dbt-migration/SKILL.md`)
- dbt Troubleshooting (`dbt-troubleshooting/SKILL.md`)

---

## [1.0.0] - November 2025

### Initial Release

This is the first release of the Rittman Analytics Claude Skills collection, consolidating 8 custom skills developed for business operations.

#### Added

**Skills**:
- Daily Briefing - Automated daily summaries and meeting preparation
- Xero Aged Debtors Analysis - Accounts receivable and collections management
- Xero Bookkeeping - UK accounting compliance and procedures
- Harvest Project Creator - Automated project setup from HubSpot deals
- Google Doc Proposal Generator - Client proposals from templates
- Business Performance Looker - Business metrics and analytics
- Jira Cycle Time Analysis - Development productivity metrics
- dbt Development - Code quality validation

**Documentation**:
- README.md - Comprehensive overview and skill catalog
- INSTALLATION.md - Detailed installation and setup guide
- QUICK-REFERENCE.md - Fast command lookup
- LICENSE.md - Proprietary license terms
- This CHANGELOG.md

**Features**:
- Multi-tool integration support
- Automated workflows across business functions
- UK-specific accounting compliance
- Meeting context enrichment
- Analytics and reporting capabilities
- Code quality validation

#### Tool Integrations

Supports integration with:
- Xero (Accounting)
- Slack (Communications)
- Google Workspace (Calendar, Gmail, Drive)
- HubSpot (CRM)
- Harvest (Project Management)
- Looker (Business Intelligence)
- Fathom (Meeting Recordings)
- Atlassian/Jira (Project Management)

---

## Future Plans

### Planned Enhancements

**Version 1.1** (Planned):
- Enhanced error handling across all skills
- Additional Looker explore support
- Expanded Xero reporting capabilities
- Integration with additional tools

**Version 1.2** (Planned):
- Skills for marketing automation
- Enhanced analytics and forecasting
- Client portal integrations
- Advanced workflow automation

### Ideas Under Consideration

- Intercom integration for customer support
- Notion integration for knowledge management
- Advanced financial forecasting
- Automated compliance checking
- Team capacity planning
- Client health scoring

---

## Version History Summary

| Version | Date | Skills | Notes |
|---------|------|--------|-------|
| 3.4.0 | Mar 2026 | Research Persistence | Wire v3.4.0 engagement planning |
| 3.3.2 | Feb 2026 | dbt Fusion, dbt MCP Server, dbt Analytics Q&A, dbt DAG | 4 new dbt agent skills |
| 3.3.1 | Jan 2026 | Dagster | Orchestration skill |
| 3.3.0 | Jan 2026 | dbt Semantic Layer, Unit Testing, Migration, Troubleshooting | 4 new dbt skills |
| 1.0.0 | Nov 2025 | 8 business ops skills | Initial release |

---

## Contributing

Changes to skills should be:
1. Tested thoroughly in development
2. Documented in the relevant SKILL.md
3. Noted in this CHANGELOG
4. Reviewed by team lead before deployment

---

**Maintained by**: Rittman Analytics Team
**Last Updated**: November 2025
