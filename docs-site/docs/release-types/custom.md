---
sidebar_position: 14
title: Custom
---

# Custom Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director).

:::


Not every engagement produces pipelines and dashboards. Some deliver an architecture advisory report, a technology decision log, a PoC productionisation blueprint, an MCP/AI integration roadmap or a compliance review, and in each case the deliverables are defined by the SoW rather than by a standard delivery pattern. Use the Custom release type for these engagements, where the bespoke deliverables do not map cleanly to any standard Wire release type and the scope is fixed by the SoW.

## When to use Custom instead of a standard type

- The primary deliverables are documents or advisory outputs (not data pipelines or dashboards)
- The engagement is time-boxed and advisory
- More than one standard release type would be needed and the combination feels awkward
- The SoW defines specific named deliverables with acceptance criteria that do not match Wire's standard artifact names

## How it works

So how does Wire run a release whose artifacts it has never seen before? When you select "Custom" in `/wire:new`, Wire immediately invokes `/wire:custom-define`, which:

1. **Reads your source documents**: the SoW, kick-off notes and agreed delivery plan (PDF, Markdown, Google Drive, Confluence)
2. **Extracts deliverables**: names, descriptions, acceptance criteria, effort estimates and timeline milestones
3. **Maps each deliverable**: scores it against existing Wire commands, uses standard commands where there is a strong match and proposes custom specs for the rest
4. **Shows a proposal table**: you can accept, swap or rename any item before anything is written
5. **Generates fully specified project-scoped specs** for each custom deliverable, with complete generate/validate/review workflows derived from the SoW acceptance criteria
6. **Writes `.claude/commands/` wrappers** so that each custom spec is invokable as a slash command

## Workflow

```
/wire:new                           # select "Custom" → triggers /wire:custom-define

# Wire prompts for source documents, then shows a proposal:
# ┌─────────────────────────────────────────────────────────────────┐
# │ Deliverable                        │ Handling   │ Command       │
# │ Target State Architecture Document │ Custom 🔧  │ /target-state-architecture-doc-generate │
# │ Decision Log                       │ Custom 🔧  │ /decision-log-generate                  │
# └─────────────────────────────────────────────────────────────────┘
# Accept or adjust, then Wire generates the specs and scaffolds the release.

# Custom commands are then available as slash commands:
/target-state-architecture-doc-generate <release-folder>
/target-state-architecture-doc-validate <release-folder>
/target-state-architecture-doc-review <release-folder>

/wire:archive <release-folder>
```

:::info[Tutorial available]

A worked example of a Custom engagement, using a fictional client scenario with realistic command output, agent delegation and reviewer decisions, is available in the [Tutorial: Custom](../tutorials/custom).

:::


## Standalone document analysis

You can also analyse the source documents before running `/wire:new`:

```
/wire:utils-doc-analyze path/to/SoW.pdf path/to/kickoff-notes.md
```

This shows the extracted deliverables table with Wire match scores and workflow notes, without writing any files.

## Tips

- Provide all three document types when they are available: the SoW for acceptance criteria, the kick-off notes for stakeholder context and the delivery plan for timeline milestones
- If a deliverable's description is vague in the SoW, Wire will flag it and ask for clarification before generating the spec
- Custom specs live in `.wire/releases/[folder]/custom-commands/` and are the source of truth
