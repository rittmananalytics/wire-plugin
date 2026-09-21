# Findings Playback deck — `modelling_led` profile

The deck `findings-playback-generate` builds when `status.md` has
`discovery_profile: modelling_led`.

## Why a separate template

The `diagnostic` deck in `../findings_playback/` has the three analyses as its
spine: the Hierarchy of Needs bar chart, the People–Process–Technology bar chart,
the per-axis word clouds and quote slides, and the Maturity Curve pin. The
`modelling_led` profile switches `discovery_analyses` off, so those slides have no
content. A show/hide switch cannot fix that: over half the deck would be empty,
and the narrative that runs between the charts would not hold together.

## Slide order

Follows the three pillars. Authoritative definition is
`specs/sop_discovery/findings_playback/generate.md`, "The `modelling_led` deck".

| # | Slide group | Rendered from |
|---|---|---|
| 1 | Context and process | `engagement_brief.md`, the interview and workshop set |
| 2 | Current state, including the full Gaps list | `current_state_appraisal.md` Sections 1–10 |
| 3 | Business questions | `requirements_matrix.md`, `#question` rows |
| 4 | Conceptual model, with exclusions and why | `conceptual_model.md` |
| 5 | Logical model — the decisions, not the diagram | `logical_model.md` Sections 4, 6, 8 |
| 6 | Data flow, then one slide per platform layer | `pipeline_design.md` + its Section A |
| 7 | Roadmap — leadership view, then Release 1 | `delivery_roadmap.md` |
| 8 | What we are asking you to sign off | The five-item checklist |

A slide with no backing artifact is not generated, and the omission is listed on
slide 8.

## Styling

Shares the `diagnostic` deck's design system rather than defining a second one.
Take `colors_and_type.css`, `deck-stage.js`, `fonts/` and `assets/` from
`../findings_playback/`.

## Status of this template

The slide order, the source artifact per slide, and the sign-off checklist are
specified and enforced by `findings-playback-validate`. The HTML template itself
is not yet authored: the `diagnostic` deck came from a Claude Design handoff
bundle, and the equivalent visual pass for this profile is outstanding.

Until it lands, `findings-playback-generate` under `modelling_led` builds the deck
from the `diagnostic` deck's slide components — title, section divider, two-column
content, table, diagram-with-caption — dropping the chart and word-cloud
components, which have no data in this profile. That produces a correct and
presentable deck in the house style. It does not produce the bespoke layouts the
model and roadmap slides would benefit from.

`findings-playback-validate`'s `wrong_deck_template` check fires on a
`modelling_led` release that has been built from the `diagnostic` spine, so this
gap cannot pass silently as if it were the finished article.
