---
description: Shared convention — reference codes expanded at first mention, cross-document codes resolved in a Reference key table, enforced by the reference_legibility validate check
---

# Reference Legibility Convention

## Purpose

Wire artifacts mint reference codes (`FR-1`, `D3`, `PD-2`, sprint-story codes) and cite them across document boundaries: sprint plans cite release-brief deliverable numbers, conceptual models cite functional requirement codes. A reader who opens one artifact cold must be able to resolve every code it contains without opening another file.

This spec defines two authoring rules for generate commands, the canonical Reference key table format, and the deterministic `reference_legibility` check that validate commands run.

Codes stay valid as cross-references. The convention never removes a code; it makes sure no reader has to decode one.

## Recognized code families

| Pattern | Family | Minted by |
|---------|--------|-----------|
| `FR-<n>` | Functional requirement | `/wire:requirements-generate` (Section 4 headings) |
| `NFR-<n>` | Non-functional requirement | `/wire:requirements-generate` (Section 5 headings) |
| `D<n>` | Deliverable | `/wire:requirements-generate` (Section 9 table), `/wire:release-brief-generate` (Section 3 table) |
| `PD-<n>` | Design decision | `/wire:pipeline_design-generate` (bold-title decision records) |
| `A<n>` | Assumption | `/wire:release-brief-generate` (Section 6 table) |
| `E<n>` | Epic | No template minting site (see below) |
| `S<n>.<n>` | Sprint story | No template minting site (see below) |

All matches are word-bounded: `D1` matches; `3D1` and `D1x` do not. Release types may extend this table; any extension must state the minting artifact.

`E<n>` and `S<n>.<n>` are consultant shorthand: the sprint plan template heads epics as `Epic N` and its story rows are free text, so neither family has a framework minting site today. The check still recognises them so that a hand-written `E1` or `S1.1` is caught: it passes only through a first-use inline expansion, a Reference key row, or a minting-shaped heading or table row the consultant wrote themselves. If a template change ever mints these codes, update the table row above to name the minting artifact.

## Rule 1 — First-mention expansion

The first mention of any code in a document carries its plain-language meaning at the point of use. Three forms count as an expansion:

1. **Minting site** (the document defines the code itself):
   - a heading of the form `### FR-1: Ingest Substack exports` (heading text is `CODE:` or `CODE —` followed by the name), or
   - a table row whose first cell is the code and whose second cell is the name (e.g. the deliverables table `| D1 | Operating-cost model | ... |`), or
   - a bold title line `**PD-1: Pipeline Replication Tool**` (decision-record form).
2. **Inline expansion**: the meaning followed by the code in parentheses — "the operating-cost deliverable (D6)" — or the code immediately followed by its meaning in parentheses — "D6 (the operating-cost deliverable)".
3. **Reference key row** (Rule 2 below).

A minting site or Reference key row anywhere in the document resolves the code for the whole document. An inline expansion resolves the code only if it occurs at the code's **first** mention; expanding a code after it has already appeared bare does not pass.

Range mentions (`D1–D3`, "FR-1 through FR-4") count both endpoints as mentions; codes strictly inside the range are not mentions.

## Rule 2 — Cross-document Reference key

Any document that cites codes defined in *other* artifacts includes a **Reference key** section, canonically:

```markdown
## Reference key

Codes used in this document that are defined in other artifacts:

| Code | Meaning | Defined in |
|------|---------|------------|
| D1 | Operating-cost model | planning/release_brief.md |
| FR-3 | Ingest Substack exports | requirements/requirements_specification.md |
```

Requirements on the table:

- **Code**: exactly the code as used in the body.
- **Meaning**: the plain-language name from the defining document, non-empty.
- **Defined in**: the path of the defining document relative to the release or project root (the same root the citing document lives under), non-empty.

Place the section near the top of the document (after the title block) or immediately before the first section that uses foreign codes. Omit the section entirely when the document cites no foreign codes.

## The `reference_legibility` validate check

Every validate command whose artifact is a generated Markdown document runs this check alongside its existing checklist. It is deterministic — no judgement calls:

1. Remove fenced code blocks (``` ... ```) from the document. Everything else, including tables and headings, is scanned.
2. Collect every word-bounded occurrence of the recognized code patterns, in document order.
3. Classify definition sites per Rule 1 form 1 and Reference key rows per Rule 2. Occurrences inside a minting site or inside the Reference key table are definitions, not uses.
4. A code **passes** if it has a minting site, or a Reference key row with non-empty Meaning and Defined-in cells, or its first use is an inline expansion (Rule 1 form 2).
5. A code **fails** otherwise. A Reference key row with an empty Meaning or Defined-in cell does not resolve its code.

**Result line** (use exactly this shape in the validation report):

```
✓ reference_legibility: all 14 codes defined at first use or in the Reference key
```

on failure:

```
✗ reference_legibility: 2 of 14 codes unresolved — D3, FR-7 (no first-use expansion, no Reference key row)
```

Severity: **Major**. Offending codes are listed by name; remediation is either an inline expansion at first use or a Reference key row.

The check is code-driven: a document that uses no recognized codes passes trivially. Occurrences inside inline code spans (`` `FR-2` ``) are out of scope for this check — the spec takes no position on whether backticked codes are uses or literals; validators do not fail a document on backticked occurrences alone.

## Where this is wired in

Generate commands that mint or cite codes follow Rules 1–2 and include the Reference key section in their output templates when foreign codes are cited:

- `specs/requirements/generate.md` (mints FR/NFR/D)
- `specs/discovery/release_brief/generate.md` (mints D/A)
- `specs/discovery/sprint_plan/generate.md` (cites release-brief D-numbers)
- `specs/design/conceptual_model/generate.md` (cites FR codes)
- `specs/design/pipeline_design/generate.md` (mints PD)

Validate commands running the check:

- `specs/requirements/validate.md`
- `specs/discovery/problem_definition/validate.md`
- `specs/discovery/pitch/validate.md`
- `specs/discovery/release_brief/validate.md`
- `specs/discovery/sprint_plan/validate.md`
- `specs/design/conceptual_model/validate.md`
- `specs/design/data_model/validate.md`
- `specs/design/pipeline_design/validate.md`

The convention is normative for every generated Markdown artifact, not just the list above. A new document-producing command adopts it by referencing this spec; a validate command adopts the check by adding one checklist entry pointing here.

The deterministic check logic is tested at `wire/tests/utils/validate_reference_legibility.py` against fixture documents — change the algorithm here and the fixtures there together.
