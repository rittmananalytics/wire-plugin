# Worked examples

Each example shows a Looker Studio construct as it appears in `report.json` (`before.json`) and the Omni model or tile it becomes (`after.yaml`), with the reasoning in `notes.md`. Field and table names are fictional (Halcyon Outdoor, the test fixture client). These are agent-authored outputs, not script output: this pair has no converter, so the examples show the rule, not a byte-for-byte target.

| Example | Shows |
|---|---|
| `01_chart_level_ratio` | A chart-level CTR formula, ruled in the metric catalogue, becomes one Omni measure |
| `02_blend_to_join` | A two-input full outer blend on date becomes a modelled join at daily grain |
| `03_sum_of_ratio` | A scorecard that sums a per-row ratio is rebuilt as a ratio of totals, and recorded as an accepted difference |
