---
sidebar_position: 8
title: Extending Wire
---

# Extending Wire

Sooner or later an engagement will ask for something Wire does not yet do, whether that is a kind of release the existing definitions do not cover, an artifact nobody has written a spec for, a utility that only your team needs or a change to a template that every new engagement should pick up. Wire is designed to be extended in each of these directions, and new release types, new artifact types, new utility commands and project-specific customisations are all first-class. In this page we will look at each in turn, starting with the largest change, a new release type, and working down to the smallest, a template you override for a single engagement, before finishing with how you distribute your extensions to others.

## Adding a new release type

**Since v4.0.0**, a release type is a YAML file conforming to [`wire/schemas/release-type-schema.md`](https://github.com/rittmananalytics/wire/blob/main/wire/schemas/release-type-schema.md): phases, an ordered list of artifacts per phase (each with `id`, `command`, `depends_on`, `sequence`, `required`), plus the corresponding spec files. This is not something you edit directly in this repo, because `wire/release-types/*.yaml` and `wire/specs/**/*.md` are a synced, pinned mirror of the private `rittmananalytics/wire-process-registry` repo, which is branch-protected with mandatory review, and [The Process and Data Model Registries](./registries) explains why it is externalised this way and how the sync works.

If you are an RA maintainer adding a release type for real, there are five steps: you raise a pull request against the registry, write a spec file for each artifact, get the change reviewed and merged, sync it into this repo and rebuild the packages. Let's take those in more detail.

1. **Open a PR against `wire-process-registry`**, not this repo. Add the new `release-types/<name>.yaml` there, following the schema: phases, artifacts, `depends_on` edges and `sequence` for tie-breaking within a phase.
2. **Write a spec file per artifact** at `specs/<domain>/<artifact>/generate.md` (and `validate.md`/`review.md` where applicable) in the same registry repo, with `wire_schema` front-matter conforming to [`wire/schemas/command-schema.md`](https://github.com/rittmananalytics/wire/blob/main/wire/schemas/command-schema.md): `command`, `artifact`, `domain`, `release_types`, `action_type`, `preconditions` (a static list, or the `dynamic` sentinel if the correct precondition genuinely varies by release type), and so on.
3. **Get it reviewed and merged**, for which one approving review is required.
4. **Sync it into this repo**: `wire/scripts/sync-process-registry.sh` mirrors both directories and pins the resolved commit SHA.
5. **Build the packages**:

```bash
./wire/scripts/build-packages.sh
```

This bundles the newly synced `wire/release-types/*.yaml` and inlines the specs into `commands/*.md`/`.toml`, regenerating the Claude Code plugin and Gemini extension.

Once bundled, the [precondition gate](../getting-started/core-concepts#the-precondition-gate) and [Autopilot](./autopilot) both read the new YAML's `depends_on`/`sequence` graph automatically at runtime, and nothing else in the framework needs to know that a new release type exists.

## Writing a spec file

So what goes into a spec file? A spec file is a Markdown document that Claude reads as an instruction set for the command, and what it should specify depends on which of the three actions it describes.

**For generate specs:**
- The inputs to read (upstream artifacts, source files, MCP data)
- The output document structure (required sections and their content)
- Any code to generate (file names, content patterns)
- Fathom/meeting context to surface

**For validate specs:**
- The checks to run (automated tests, structural validation, code compilation)
- How to classify each check (blocking vs. advisory)
- The PASS/FAIL summary format

If the artifact's generate/validate logic embeds a deterministic decision rule (a classification scheme, a gating condition, a selection grammar), extract it into a Tier 1 behavioural test alongside the spec, and see [Testing Wire Itself](../reference/testing.md) for the pattern every release type follows.

**For review specs:**
- The document to present
- The context to gather (validation results, meeting transcripts, prior decisions)
- The questions to ask the reviewer
- How to record the decision

A minimal spec structure looks like this:

```markdown
# my_first_artifact - generate

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

Wire will pick it up automatically, and these commands are then available as:

```
/wire:custom-<command-name> <release-folder>
```

## Adding utility commands

Utility commands (prefixed `/wire:utils-`) are general-purpose commands not tied to a specific release type, and they live in `wire/specs/utils/`. As an example, the document analysis utility at `wire/specs/utils/doc_analyze.md` reads an arbitrary document and extracts Wire-relevant information from it (deliverables, stakeholders, constraints), and it is invoked as `/wire:utils-doc-analyze`.

## Customising the status template

The status report template is at `wire/TEMPLATES/status-template.md`, and to override it for a specific engagement you copy it to `.wire/releases/<release-folder>/status-template.md`, since Wire reads the local override first.

## Customising the CLAUDE.md template

When `/wire:new` creates a new engagement, it populates a `CLAUDE.md` file from the template at `wire/TEMPLATES/claude-md-template.md`, so if you want to change what Wire captures at setup for all new engagements, modify that template.

## Distributing your extensions

Finally, how do you share what you have built? Extensions to Wire can be distributed as separate plugins, and a Wire extension plugin follows the same structure as the core Wire plugin, with:
- Spec files in `specs/` (or your own equivalent directory)
- A `build-packages.sh`-style entry point that inlines specs into `commands/*.md`

Users install an extension plugin alongside the core Wire plugin:

```
/plugin install my-extension@my-org
/reload-plugins
```

Extension commands coexist with core Wire commands, and namespacing is by convention: use a prefix that distinguishes your extension from the core (e.g. `/wire:ext_mycompany_*`).
