---
sidebar_position: 9
title: Enablement
---

# Enablement Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director).

:::


Sometimes the platform is already built and running, and what remains is to teach people to use it and to write down how it works. Use this release type when an existing platform needs training and documentation, either as a standalone release or as the final phase of a delivery that was not originally run through the Wire Framework.

**In-scope artifacts**: `training`, `documentation`

## Workflow

At a high level, the release captures the training audience first and then produces the two artifacts in turn:

```
/wire:new                                         # release_type: enablement

/wire:requirements-generate <release-folder>      # Capture training audience and learning objectives

/wire:training-generate <release-folder>
/wire:training-validate <release-folder>
/wire:training-review <release-folder>

/wire:documentation-generate <release-folder>
/wire:documentation-validate <release-folder>
/wire:documentation-review <release-folder>

/wire:archive <release-folder>
```

:::info[Tutorial available]

A worked example of an Enablement engagement, using a fictional client scenario with realistic command output, agent delegation and reviewer decisions, is available in the [Tutorial: Enablement](../tutorials/enablement).

:::


**Tips**:
- Add any existing technical documentation, data dictionaries or architecture diagrams to `requirements/`, and the AI will use them as the basis for the generated materials
- Add the client stakeholder list (names, roles, technical levels) so that the training materials can be calibrated to the people who will attend
