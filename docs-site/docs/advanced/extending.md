---
sidebar_position: 7
title: Extending Wire
---

# Extending Wire

Wire is designed to be extended — new release types, new artifact types, new utility commands, and project-specific customisations are all first-class.

## Adding a new release type

A release type is a named configuration in `wire/packaging/wire-plugin/WIRE_COMMANDS.md` (or its Gemini equivalent), with:
- A set of phases
- An ordered list of artifacts per phase
- Command mappings (`-generate`, `-validate`, `-review` per artifact)
- Corresponding spec files in `wire/specs/`

To add a release type:

1. **Define the phases and artifacts** in a new section of `WIRE_COMMANDS.md`:

```markdown
## Release type: my_release_type

### Phase 1 — Requirements
- my_first_artifact: generate, validate, review

### Phase 2 — Delivery
- my_second_artifact: generate, validate, review
```

2. **Write a spec file** for each artifact at `wire/specs/my_release_type/my_first_artifact.md`. The spec must define:
   - What upstream inputs this artifact reads
   - What the artifact produces (format, required sections)
   - Validation criteria (what PASS/FAIL looks like)
   - Review prompts (what questions to ask the reviewer)

3. **Register the artifact commands** — add entries to the commands section of `WIRE_COMMANDS.md`:

```markdown
/wire:my_first_artifact-generate
/wire:my_first_artifact-validate
/wire:my_first_artifact-review
```

4. **Build the packages**:

```bash
./wire/scripts/build-packages.sh
```

This regenerates the Claude Code plugin and Gemini extension from the source files.

## Writing a spec file

A spec file is a Markdown document that Claude reads as an instruction set for the command. It should specify:

**For generate specs:**
- The inputs to read (upstream artifacts, source files, MCP data)
- The output document structure (required sections and their content)
- Any code to generate (file names, content patterns)
- Fathom/meeting context to surface

**For validate specs:**
- The checks to run (automated tests, structural validation, code compilation)
- How to classify each check (blocking vs. advisory)
- The PASS/FAIL summary format

**For review specs:**
- The document to present
- The context to gather (validation results, meeting transcripts, prior decisions)
- The questions to ask the reviewer
- How to record the decision

A minimal spec structure:

```markdown
# my_first_artifact — generate

## Inputs
- Upstream: `problem_definition.md`
- Source: read `dbt_project.yml` from the project root

## Output: my_first_artifact.md

### Required sections
1. Executive Summary (3–5 sentences)
2. Scope table (source systems, included / excluded)
3. Open questions (any items requiring client clarification)

## Meeting context
Search Fathom for meetings in the last 30 days mentioning [client name].
Surface any decisions related to scope or data sources.

## Completion criteria
- All three required sections present
- No placeholder text remaining
- Open questions table has at least one entry OR an explicit "None" marker
```

## Adding a project-specific command

For a single engagement, you can add a custom command without modifying the shared Wire source. Place the spec at:

```
.wire/releases/<release-folder>/custom-commands/<command-name>.md
```

Wire will pick it up automatically. These commands are available as:

```
/wire:custom-<command-name> <release-folder>
```

## Adding utility commands

Utility commands (prefixed `/wire:utils-`) are general-purpose commands not tied to a specific release type. They live in `wire/specs/utils/`.

Example: the document analysis utility at `wire/specs/utils/doc_analyze.md` reads an arbitrary document and extracts Wire-relevant information from it (deliverables, stakeholders, constraints). It's invoked as `/wire:utils-doc-analyze`.

## Customising the status template

The status report template is at `wire/TEMPLATES/status-template.md`. Copy it to `.wire/releases/<release-folder>/status-template.md` to override it for a specific engagement. Wire reads the local override first.

## Customising the CLAUDE.md template

When `/wire:new` creates a new engagement, it populates a `CLAUDE.md` file from the template at `wire/TEMPLATES/claude-md-template.md`. Modify the template to change what Wire captures at setup for all new engagements.

## Distributing your extensions

Extensions to Wire can be distributed as separate plugins. A Wire extension plugin follows the same structure as the core Wire plugin, with:
- A `WIRE_COMMANDS.md` listing the new commands
- Spec files in `specs/`
- A `build-packages.sh` entry point

Users install an extension plugin alongside the core Wire plugin:

```
/plugin install my-extension@my-org
/reload-plugins
```

Extension commands coexist with core Wire commands. Namespacing is by convention — use a prefix that distinguishes your extension from the core (e.g. `/wire:ext_mycompany_*`).
