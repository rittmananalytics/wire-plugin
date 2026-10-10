# Tableau to Looker: feature detection

Experimental. Where each construct lives in `.twb` and `.tds` XML, and the pattern that decides its class. `twb_to_lookml.py` stops with an error on XML it cannot parse rather than writing a partial result.

| Construct | XML or pattern | Class |
|---|---|---|
| Parameters | `datasource[@name='Parameters']/column` with `param-domain-type` | assisted |
| Embedded data source | `datasources/datasource` with `connection[@class='federated']` | from its parts |
| Published data source reference | `connection[@class='sqlproxy']` with `dbname` | mechanical |
| Warehouse connection | `named-connections/named-connection/connection` (`class`, `project`, `schema`, `server`) | |
| Table relation | `relation[@type='table']` | mechanical |
| Custom SQL | `relation[@type='text']` (SQL as element text) | assisted |
| Physical join | `relation[@type='join']` with `clause/expression[@op='=']` | assisted |
| Logical relationships | `object-graph/relationships/relationship` with `first-end-point` and `second-end-point` `unique-key` | assisted |
| Columns | `connection/metadata-records/metadata-record[@class='column']` (`remote-name`, `local-name`, `parent-name`, `local-type`, `aggregation`), mapped by `cols/map` | mechanical |
| Caption, hidden, format overrides | `datasource/column` with the same `name` | |
| Calculation | `column/calculation[@class='tableau']/@formula` | by formula |
| LOD | formula matches `\{\s*(FIXED\|INCLUDE\|EXCLUDE)\b` | redesign |
| Table calculation | formula calls `WINDOW_*`, `RUNNING_*`, `INDEX`, `RANK*`, `LOOKUP`, `FIRST`, `LAST`, `SIZE`, `TOTAL`, `PREVIOUS_VALUE` | redesign |
| Aggregate calculation | formula calls `SUM`, `AVG`, `MIN`, `MAX`, `COUNTD`, `COUNT`, `MEDIAN`, `ATTR` | assisted |
| Parameter reference | `[Parameters].[...]` in a formula | assisted |
| Group | `calculation[@class='categorical-bin']` with `bin/value` | assisted |
| Bin | `calculation[@class='bin']` with `size`, or `size-parameter` (sized by a parameter); its `formula` may name a calculated field | assisted |
| Set | `datasource/group` | assisted |
| Extract | `datasource/extract[@enabled='true']` (refresh time in `connection/@update-time`), or a `hyper` connection with no `extract` element (extract-only data: the file is the only copy) | redesign |
| File source | named connection class `excel-direct`, `textscan`, `google-sheets` and other file classes; `filename` is part of the table identity | redesign |
| Relations (2020.2+) | `connection/relation[@type='collection']` holding one `relation` per table; `object-graph/objects/object` names each table's relation (its `caption` is a label and can differ); `relationships/relationship` joins objects by `object-id` | assisted |
| Worksheet | `worksheets/worksheet` with `table/view/datasources`, `datasource-dependencies/column-instance`, `rows`, `cols`, `encodings`, `filter`, `sort`, `panes/pane/mark/@class` | |
| Blend | a worksheet whose `view/datasources` lists two or more data sources (other than Parameters) | redesign |
| Dashboard | `dashboards/dashboard` (`size/@maxwidth`, `@maxheight`), zones with `x`, `y`, `w`, `h` in units of 100,000 | |
| Zone kinds | `zone/@type-v2`: absent or a sheet `name` (sheet), `text`, `filter` (with `param`), `bitmap`, `web`, `layout-*` (containers, walked) | |
| Device layout | `dashboard/devicelayouts/devicelayout` | drop |
| Story | `dashboard[@type='storyboard']` | drop |
| Action | `actions/action` with `command/@command` (`tsc:tsl-filter` is a filter action) | assisted |
| Packaged workbook | `.twbx` or `.tdsx`: a zip with the `.twb` or `.tds` at the top level | unpacked |
