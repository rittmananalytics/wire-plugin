# Quick Reference Guide

Fast lookup for all skill commands and capabilities.

## Daily Briefing

**Purpose**: Automated daily summaries and meeting prep

**Quick Commands**:
- `Give me my daily briefing`
- `What did I do today?`
- `What's on tomorrow?`
- `Prepare me for tomorrow's meetings`
- `Review today and preview tomorrow`

**Tools Used**: Google Calendar, Slack, Gmail, Fathom, Google Drive

**Key Features**:
- Time-aware (morning vs evening briefings)
- Multi-source aggregation
- Meeting context from recordings
- Sends to Slack DM automatically

---

## Xero Aged Debtors Analysis

**Purpose**: Accounts receivable and collections

**Quick Commands**:
- `What's our aged debtors position?`
- `Show me outstanding invoices`
- `Which clients owe us money?`
- `What's our accounts receivable?`
- `Who hasn't paid?`

**Tools Used**: Xero

**Key Features**:
- Aging buckets (Current, 30, 60, 90+ days)
- Multi-currency conversion
- Largest exposure identification
- Actionable collection recommendations

---

## Xero Bookkeeping

**Purpose**: UK accounting compliance and procedures

**Quick Commands**:
- `Guide me through daily reconciliation`
- `Help me prepare VAT return`
- `What are the month-end procedures?`
- `Show me year-end checklist`
- `Payroll integration steps`

**Tools Used**: Xero

**Key Features**:
- Structured workflows
- HMRC compliance
- VAT return procedures
- Payroll integration
- Year-end processes

---

## Harvest Project Creator

**Purpose**: Automated project setup from deals

**Quick Commands**:
- `Create Harvest project for [deal name]`
- `Set up project from HubSpot deal [ID]`
- `Show me recent HubSpot deals`
- `Generate project plan for [client]`

**Tools Used**: HubSpot, Harvest

**Key Features**:
- Deal analysis
- Project plan generation
- Automatic project creation
- Draft invoice generation
- Complete execution workflow

---

## Google Doc Proposal Generator

**Purpose**: Client proposals from templates

**Quick Commands**:
- `Create proposal from last meeting`
- `Generate SOW for [client name]`
- `Create follow-up document for [meeting]`
- `Use template to create proposal`

**Tools Used**: Google Drive, Fathom

**Key Features**:
- Template-based generation
- Meeting transcript integration
- PDF proposal incorporation
- Automatic document creation
- Client-specific customization

---

## Business Performance Looker

**Purpose**: Business metrics and analytics

**Quick Commands**:
- `Show me this month's revenue`
- `What's our consultant utilization?`
- `Analyze customer lifecycle`
- `What's our P&L this quarter?`
- `Show website traffic trends`

**Tools Used**: Looker

**Key Features**:
- Analytics model queries
- Business Operations explore
- Finance explore (P&L)
- Web Analytics explore
- Custom metric analysis

---

## Jira Cycle Time Analysis

**Purpose**: Development productivity metrics

**Quick Commands**:
- `Analyze cycle times for project [name]`
- `Show sprint velocity trends`
- `What's our average cycle time?`
- `Identify development bottlenecks`

**Tools Used**: Looker, Jira (optional)

**Key Features**:
- Statistical cycle time analysis
- Velocity tracking
- Bottleneck identification
- Sprint context integration
- Team productivity metrics

---

## dbt Development

**Purpose**: Code quality validation

**Quick Commands**:
- `Review this dbt model`
- `Validate dbt code quality`
- `Check dbt naming conventions`
- `Analyze this transformation`

**Tools Used**: None (code analysis)

**Key Features**:
- Automatic activation
- Naming convention validation
- SQL structure checking
- Testing coverage verification
- Documentation validation
- sqlfluff integration

---

## Common Workflows

### Morning Routine
1. `Give me my daily briefing` (Daily Briefing)
2. `What's our aged debtors position?` (Xero Aged Debtors)
3. Review any follow-ups needed

### Weekly Financial Review
1. `Show me outstanding invoices` (Xero Aged Debtors)
2. `Show me this week's revenue` (Business Performance Looker)
3. `Guide me through weekly reconciliation` (Xero Bookkeeping)

### Client Onboarding
1. `Create proposal from last meeting` (Proposal Generator)
2. After deal closes: `Create Harvest project for [client]` (Harvest Creator)
3. Track progress: `Show project status` (Business Performance Looker)

### Month-End Close
1. `What are the month-end procedures?` (Xero Bookkeeping)
2. `Show me this month's P&L` (Business Performance Looker)
3. `What's our aged debtors position?` (Xero Aged Debtors)

### Development Review
1. `Review this dbt model` (dbt Development)
2. `Analyze cycle times for sprint` (Jira Cycle Time)
3. Address any code quality issues

---

## Tips for Best Results

### Be Specific
❌ "Show me data"
✅ "Show me outstanding invoices from the last 30 days"

### Provide Context
❌ "Create a project"
✅ "Create a Harvest project for the Power Digital deal"

### Use Natural Language
❌ "Execute daily-briefing skill"
✅ "Give me my daily briefing"

### Combine Skills
"Give me my daily briefing, then show me today's aged debtors"

### Ask for Clarification
If a skill needs more info, it will ask. Provide details when prompted.

---

## Tool Requirements Quick Check

| Skill | Xero | Slack | Google | HubSpot | Harvest | Looker | Fathom | Jira |
|-------|------|-------|--------|---------|---------|--------|--------|------|
| Daily Briefing | | ✓ | ✓ | | | | ✓ | |
| Xero Aged Debtors | ✓ | | | | | | | |
| Xero Bookkeeping | ✓ | | | | | | | |
| Harvest Creator | | | | ✓ | ✓ | | | |
| Proposal Generator | | | ✓ | | | | ✓ | |
| Business Looker | | | | | | ✓ | | |
| Jira Cycle Time | | | | | | ✓ | | (✓) |
| dbt Development | | | | | | | | |

✓ = Required
(✓) = Optional

---

## Troubleshooting Quick Fixes

### Skill Not Working
1. Check tool connections (Settings > Integrations)
2. Start new conversation
3. Use explicit trigger phrase

### No Data Returned
1. Verify data exists in source tool
2. Check date range in query
3. Confirm permissions in integrated tool

### Error Message
1. Note exact error text
2. Try simpler version of command
3. Check tool status/limits

---

## Getting More Help

- **Detailed Documentation**: See README.md
- **Installation Issues**: See INSTALLATION.md
- **Skill-Specific Help**: Check individual skill folders
- **Internal Support**: Contact Rittman Analytics team

---

**Last Updated**: November 2025
