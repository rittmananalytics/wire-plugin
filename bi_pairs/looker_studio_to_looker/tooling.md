# Looker Studio to Looker: tooling

Experimental.

## Setup

Everything the Looker Studio to Omni pair needs for the capture (`wire/bi_pairs/looker_studio_to_omni/tooling.md`: Chrome, Playwright, a signed-in Google profile, recorded client consent), plus Looker API credentials or the Looker MCP, and the client's LookML repo. `sqlglot` (`python3 -m pip install sqlglot`) rewrites division inside larger formulas; without it, only a single top-level `a / b` is rewritten.

## Converter

```bash
python3 scripts/ls_to_lookml.py convert --reports <report.json> [...] --out <batch> \
  [--catalogue metric_catalogue.json] --namespace <client slug> --model <model> --connection <connection> \
  [--include-root <folder>]
python3 scripts/ls_to_lookml.py lint <batch>
```

`parity_map.json` in the output links each chart to its element and maps each recording column to its Looker field, for the parity contracts.

## Limitations

- Experimental: run end to end once on two reports (BigQuery table, custom SQL and Looker connector data sources). Not on a client estate, report families, community connectors or blends.
- Blends, data sources Looker cannot read and unsupported formula functions are not converted.
- The date range control's default is not in the capture: set it by hand (the chart recordings show the range at capture time).
- A chart's range "to today" becomes Looker's nearest filter, which also takes in the rest of the current month: Looker's "to now" form generates SQL BigQuery rejects.
- A breakdown chart in Looker Studio draws only its top series; Looker draws every series.
- Data type, aggregation and date codes not listed in `property_mapping.md` are kept raw and listed.
