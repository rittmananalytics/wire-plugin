# BI pair: Looker to Omni

Translation guide, property mappings, feature-detection patterns, content mapping, tooling notes and worked examples for migrating a Looker reporting layer to Omni on the same warehouse. Used by the `bi_migration` release type (wire#258): `/wire:looker-audit-generate` classifies with `feature_detection.md`, `/wire:omni-model-generate` runs the converter and reads `translation_guide.md`, `/wire:omni-content-generate` reads `content_mapping.md` and `tooling.md`.

Sibling of `wire/platform_pairs/` (warehouse pairs). Same layout, same override mechanism, different subject: here the warehouse does not move; the semantic model and the content do.

## Files

| File | Content |
|---|---|
| `translation_guide.md` | One row per LookML construct: Omni construct, class (`mechanical`, `assisted`, `redesign`), notes. The converter implements every `mechanical` and `assisted` row and refuses every `redesign` row into `needs_human.json`. |
| `property_mapping.md` | Value tables: `value_format_name` and `value_format` to Omni `format`; LookML timeframes to Omni timeframes; measure types to `aggregate_type`; join relationship and type; LookML filter expressions to Omni filter operators. |
| `feature_detection.md` | Regex patterns the audit applies to `.lkml` files to find Liquid, parameters, PDTs, access filters, refinements and other constructs that decide a row's class. |
| `content_mapping.md` | Looker dashboards, Looks and tiles to Omni documents: tile types to `chartType`, dashboard filters to controls, `listen` maps to control maps, what stays manual. |
| `tooling.md` | Omni's dashboard migration skill and scripts, the Omni CLI branch workflow, `omni-sync`, and how partner converters fit as an optional first pass. |
| `omni_patterns.md` | Omni-side idioms for `needs_human` and `redesign` items, sourced from Omni's community Patterns category: mustache replacements for common Liquid uses, filtered-measure and control patterns for parameter-driven tiles, merged-results alternatives, navigation and theme recipes. Read by the agent when working `needs_human.json`; never implemented by the converter. |
| `examples/` | Six before-and-after pairs. Each `after/` directory is exactly what the converter emits for its `before/` directory, and the test suite checks that on every run. |

## The converter

`wire/scripts/lookml_to_omni.py` is the deterministic core of `/wire:omni-model-generate`. Same input, identical output, no AI call.

```
python3 scripts/lookml_to_omni.py --lookml <lookml dir> --out <omni model dir> \
    [--views a,b] [--explores e1,e2] [--overrides <dir>] [--report needs_human.json] [--default-schema SCHEMA] [--project NAME]
```

Output is an Omni model repo layout: `<SCHEMA>/<view>.view`, `<explore>.topic`, `relationships.yaml`, plus `needs_human.json` (every construct the script did not, or could not, translate, with its class and reason) and `conversion_summary.json` (counts per construct and class, and the converter version). Beside them it writes its intermediate representation, `ir/views/<view>.json` and `ir/topics/<topic>.json` (every field with its identity `looker:<project>:field:<view>:<field>`, class, references, emitted body and typed unsupported constructs, whether or not it was emitted), and `dependencies.jsonl` (view contains field, field references field, topic base_view, joins and join_on edges). The audit writes the content half of the same graph with the same identities.

The agent's job is what the script cannot decide: topic design, naming, and what to do with each `needs_human` item. The agent never hand-writes what the script emits.

## Three classes, and what they mean for the agent

| Class | Converter | Agent |
|---|---|---|
| `mechanical` | Emits it. No `needs_human` entry. | Nothing. |
| `assisted` | Emits a best effort and a `needs_human` entry. Where a wrong emission would silently change a number (an untranslatable measure filter, a topic default filter), it emits nothing and says so. | Confirms or writes the Omni form by hand before the batch is validated. |
| `redesign` | Emits nothing. Records the Omni alternative. | Applies the plan's ruling (rebuild, dbt model, dashboard control) or parks a decision for the release director. |

## Engagement overrides

Drop an engagement-specific `property_mapping.yml` into `.wire/engagement/bi_pair_overrides/looker_to_omni/` to extend or override the value tables:

```yaml
value_format_name:
  gbp_rounded: gbpcurrency_0
value_format:
  "£#,##0.0": gbpcurrency_1
timeframes:
  week_of_year: null        # null = drop the timeframe with a needs_human entry
```

Pass the directory with `--overrides`. Overrides win where they name the same key and supplement where they add one. Prose overrides for the guide itself belong in the engagement's `bi_pair_overrides/looker_to_omni/translation_guide.md`, read by the agent, not the script.

## What this pair does not cover

- Liquid. There is no Liquid-to-Mustache translator; Liquid is `redesign`. For the common uses (condition defaults, `_in_query`, parameter-driven grain and windows), `omni_patterns.md` documents the Omni idiom the agent rebuilds by hand.
- Styling, text and markdown tiles. Listed for hand finishing by `omni-content`.
- Looker users and permissions beyond groups and user attributes.
- Other pairs. The release type is built for them; only `looker_to_omni` ships in 4.0.0.
