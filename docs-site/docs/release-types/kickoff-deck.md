---
sidebar_position: 3
title: Client Kick-off Deck
---

# Generating a Client Kick-off Deck

The Wire Framework can generate a branded, client-specific kick-off presentation deck in HTML (exportable to PDF via headless Chrome). This works immediately after `/wire:new` — the primary source is the Statement of Work.

## Workflow

```
# Right after /wire:new (just SoW):
/wire:kickoff-generate

# Or after discovery artifacts are approved (enriched deck):
/wire:kickoff-generate 01-discovery

# Validate structure and content:
/wire:kickoff-validate

# Internal review, then PDF export instructions on approval:
/wire:kickoff-review
```

## Slide-by-slide content sources

| Slide | Content | Source |
|-------|---------|--------|
| 01 — Title | Client name, date, engagement type, presenters | `context.md` |
| 04 — Diagnosis | Current state / desired state narrative | SoW objectives, or `problem_definition.md` |
| 05 — Big number | Headline metric | SoW impact figures |
| 07 — Problems grid | Up to 8 root causes | SoW, or `problem_definition.md` |
| 09 — Outcomes | Up to 5 success criteria | SoW approach, or `pitch.md` |
| 11 — Architecture | Mermaid diagram | `pipeline_design.md` (if present) |
| 13 — Two-week timeline | Sprint goals and stories | SoW timeline, or `sprint_plan.md` |
| 15 — Access requirements | Up to 4 data systems | SoW data sources |
| 16 — Team | Presenter names and roles | `context.md` / SoW |

## PDF export

After the deck is reviewed and approved:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless \
  --print-to-pdf="kickoff.pdf" \
  --print-to-pdf-no-header \
  "file://$PWD/.wire/kickoff-deck.html"
```

If the Mermaid architecture diagram appears blank in the PDF, add `--virtual-time-budget=5000`.

## Re-running and manual edits

The generate command is safe to re-run. On re-run it merges generated values with any manual edits you have made directly to the EDITMODE block — fields like `titlePhoto`, `accentColor`, and `showPartnerBadge` are preserved unless a new generated value is available.
