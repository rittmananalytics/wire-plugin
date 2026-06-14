---
sidebar_position: 14
title: Custom
---

# Custom Release

Use the Custom release type when an engagement has bespoke deliverables that don't map cleanly to any standard Wire release type — architecture advisory reports, technology decision logs, PoC productionisation blueprints, MCP/AI integration roadmaps, compliance reviews, or any fixed-scope engagement where the deliverables are defined by the SoW rather than a standard delivery pattern.

## When to use Custom instead of a standard type

- The primary deliverables are documents or advisory outputs (not data pipelines or dashboards)
- The engagement is time-boxed and advisory
- More than one standard release type would be needed and the combination feels awkward
- The SoW defines specific named deliverables with acceptance criteria that don't match Wire's standard artifact names

## How it works

When you select "Custom" in `/wire:new`, Wire immediately invokes `/wire:custom-release-define`, which:

1. **Reads your source documents** — SoW, kick-off notes, agreed delivery plan (PDF, Markdown, Google Drive, Confluence)
2. **Extracts deliverables** — names, descriptions, acceptance criteria, effort estimates, and timeline milestones
3. **Maps each deliverable** — scores it against existing Wire commands; uses standard commands where there's a strong match, proposes custom specs for the rest
4. **Shows a proposal table** — you can accept, swap, or rename any item before anything is written
5. **Generates fully-specified project-scoped specs** for each custom deliverable — complete generate/validate/review workflows derived from the SoW acceptance criteria
6. **Writes `.claude/commands/` wrappers** so each custom spec is invokable as a slash command

## Workflow

```
/wire:new                           # select "Custom" → triggers /wire:custom-release-define

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

A worked example of a Custom engagement — using a fictional client scenario with realistic command output, agent delegation, and reviewer decisions — is available in the [Tutorial: Custom](../tutorials/custom).

:::


## Standalone document analysis

You can analyse source documents before running `/wire:new`:

```
/wire:utils-doc-analyze path/to/SoW.pdf path/to/kickoff-notes.md
```

This shows the extracted deliverables table with Wire match scores and workflow notes, without writing any files.

## Tips

- Provide all three document types when available — SoW for acceptance criteria, kick-off notes for stakeholder context, and the delivery plan for timeline milestones
- If a deliverable's description is vague in the SoW, Wire will flag it and ask for clarification before generating the spec
- Custom specs live in `.wire/releases/[folder]/custom-commands/` and are the source of truth
