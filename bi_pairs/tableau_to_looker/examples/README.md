# Worked examples

Each example is a hand-written Tableau workbook (`before/`) and the converter's output for it (`after/`): LookML views, the model file, any LookML dashboard, `needs_human.json`, `conversion_summary.json`, the IR and `dependencies.jsonl`. `wire/tests/bi_migration/validate_twb_to_lookml.py` round-trips every example byte for byte, so a converter change is a deliberate change to these files. The client (Halcyon) is fictional.

| Example | Shows |
|---|---|
| `01_single_table_sheet` | One table, one sheet: a view, an explore, a standalone worksheet listed for a Look |
| `02_joined_datasource` | A physical inner join: `relationship: many_to_one` proposed and listed for confirmation |
| `03_calculated_fields` | An aggregate ratio as a `type: number` measure; `IIF` and string concatenation as SQL |
| `04_lod_redesign` | A FIXED LOD and a calculation over it: neither emitted, both in needs_human |
| `05_parameter_and_actions` | A parameter as a LookML parameter with `{% parameter %}`; a quick filter with `listen`; a filter action listed |
| `06_dashboard_layout` | Zones on the 24-column newspaper grid; a text element; an image and a device layout dropped |

Regenerate after a deliberate converter change: `python3 wire/tests/bi_migration/validate_twb_to_lookml.py --update`, then review the diff.
