---
sidebar_position: 7
title: Dashboard Extension
---

# Dashboard Extension Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director).

:::


When the semantic layer already holds the data and what the client wants is new dashboards on top of it, there is no model or pipeline work to do. Use this release type for that case, where you are adding dashboards to a semantic layer that is already in place.

**In-scope artifacts**: `requirements`, `mockups`, `dashboards`, `uat`

## Workflow

At a high level, the release runs as follows, with the business rules step optional and the rest in order:

```
/wire:new                                         # release_type: dashboard_extension

/wire:business-rules-generate <release-folder>     # Optional, new in 4.0
/wire:business-rules-validate <release-folder>
/wire:business-rules-review <release-folder>

/wire:requirements-generate <release-folder>      # Focus on dashboard/user requirements
/wire:requirements-validate <release-folder>
/wire:requirements-review <release-folder>

/wire:mockups-generate <release-folder>           # Wireframes for review with end users
/wire:mockups-review <release-folder>

/wire:dashboards-generate <release-folder>
/wire:dashboards-validate <release-folder>
/wire:dashboards-review <release-folder>

/wire:uat-generate <release-folder>
/wire:uat-review <release-folder>

/wire:archive <release-folder>
```

:::info[Tutorial available]

A worked example of a Dashboard Extension engagement, using a fictional client scenario with realistic command output, agent delegation and reviewer decisions, is available in the [Tutorial: Dashboard Extension](../tutorials/dashboard-extension).

:::


**Tips**:
- Add existing LookML view files to `requirements/` before generating dashboards, since the AI needs to know which dimensions and measures are available
- Screenshots of existing Looker explores also help

## Business rules discovery (optional first phase)

Before the design work begins, there is a question that is easy to skip and expensive to leave open: what do the numbers actually mean? New in 4.0, `/wire:business-rules-generate` runs before design and establishes this, one business domain at a time.

It reads the definitions that already exist, in dbt, in LookML and, through `--import`, from systems Wire cannot read such as SAP BW, Hana or SAC, and then asks the people who own the numbers to settle the ones that disagree. The output is a register with one entry per rule, holding every competing definition with the file it came from, what they disagree on, the decision, the named approver and a reconciliation query that runs at generate time rather than in QA.

A rule nobody has decided is recorded with status `unknown`, which passes validate. That is the point of it: a register has to be able to say "nobody has agreed whether in-store orders are in this figure", because that sentence is what stops the number being wrong nine months later.

**The gate is advisory.** ``mockups-generate`` warns when the register has not been reviewed, asks for a one-line reason, records it as an `advisory_skip` and proceeds. Skipping is a real choice; what matters is that the choice is visible.

Full reference: [Business rules discovery](../advanced/business-rules.md).
