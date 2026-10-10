# Looker Studio to Omni

The second pair for the `bi_migration` release type (`bi_pair: looker_studio_to_omni`, added in 4.2.2, wire#278). It moves Looker Studio (formerly Data Studio) reports to Omni.

> **Experimental.** This pair reads undocumented Looker Studio endpoints. Capture, extraction, cataloguing and the metric catalogue have been run on real client reports; the model, content and parity steps have been tested on fixtures only and not yet run end to end into Omni on a client estate. Review every output before presenting it to a client.

## How this pair differs from Looker to Omni

Looker has a semantic model (LookML) that a script can convert. Looker Studio does not: each report's data sources and charts carry their own formulas. So this pair does not convert a model. It does three things instead:

1. **Captures the estate** from the Looker Studio editor: report definitions, layout, data sources, calculated fields and the values each chart showed. There is no supported API for report definitions.
2. **Builds a metric catalogue** that groups every calculated field by metric name, flags copies, aliases and conflicts, and asks the client to rule on one definition per metric.
3. **Builds the Omni model from the warehouse**, not from the reports: from existing modelled tables, or from a linked `dbt_development` release when the warehouse has no model for a subject area. Each ruled metric becomes one Omni measure.

## Files

| File | What it holds |
|---|---|
| `translation_guide.md` | Evidence routes, translation classes, formula normalisation, metric catalogue classes |
| `property_mapping.md` | Enum codes (confirmed and unconfirmed), connector types, field kinds |
| `feature_detection.md` | Where each construct lives in the captured responses |
| `content_mapping.md` | Component types to Omni charts, layout to the 24-column grid, controls, text, report families |
| `tooling.md` | Setup, sign-in, access requests, data handling, the six scripts |
| `examples/` | Worked examples: one chart-level ratio, one blend, one sum-of-ratio correction |

Engagement overrides go in `.wire/engagement/bi_pair_overrides/looker_studio_to_omni/`, layered over these files.

## Scripts

All six are deterministic and make no AI call. The agent reads their output; it never hand-writes it.

| Script | Purpose |
|---|---|
| `wire/scripts/looker_studio_capture.py` | Routes B and C: headed Chrome capture of definitions and chart data |
| `wire/scripts/looker_studio_extract.py` | Capture in, `report.json` and `report.md` out |
| `wire/scripts/looker_studio_parity.py` | Route C recordings to parity contracts for `bi_parity.py` |
| `wire/scripts/looker_studio_jobs.py` | Route A: BigQuery job history, linked to charts |
| `wire/scripts/looker_studio_catalog.py` | Content and data source catalogs with translation classes |
| `wire/scripts/looker_studio_metrics.py` | Metric catalogue: grouping, normalisation, candidate classes, findings |

Tests: `wire/tests/bi_migration/validate_looker_studio_{extract,catalog,metrics,evidence}.py`, on a fictional fixture report.

## Limitations

See `tooling.md`, section "Limitations", and the docs site page `tutorials/looker-studio-to-omni.md`.
