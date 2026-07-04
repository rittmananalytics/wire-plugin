# SMML schema reference

The SMML (Semantic Modeler Markup Language) object model for Oracle Analytics
Cloud, as actually validated against a real, OAC-imported semantic model
(`eyelit_smml`, built from the `eyelit-dbt` project) and Oracle's own schema
reference (*SMML Schema Reference for Oracle Analytics Cloud*, F38574-15,
June 2026 — 64pp). Every section below is tagged **[ground truth]** (confirmed
against the real exported model), **[F38574-15]** (confirmed only against
Oracle's schema doc, not yet seen in a real export), or **[gap]** (neither
source pins it down — treat as best-effort).

Where the two sources agree, this file states the shape once. Where the PDF
documents something the real export never exercised (hierarchies, derived
measures, `LOOKUP` tables, parent-child hierarchies), that's flagged — don't
treat PDF-only content as equivalent in confidence to something a real OAC
import has actually round-tripped.

## The one rule that breaks everything if you miss it

**Every object is wrapped in a singular key matching its type.** A physical
table is not `{"name": "DIM_DATE", ...}`, it's:

```json
{ "physicalTable": { "name": "DIM_DATE", "sourceType": "TABLE", "physicalColumns": [ ... ] } }
```

Same for `database`, `schema`, `physicalTable` (base and alias), `businessModel`,
`logicalTable`, `subjectArea`, `presentationTable`, `hierarchy`,
`hierarchyLevel`. **[ground truth]**, confirmed independently by Rittman
Mead's own SMML write-up (`logicalTable` wrapper shown in a worked example).
A generator or validator that reads/writes flat objects (`obj["name"]`
instead of unwrapping the single top-level key first) is wrong.

## Folder layout — one JSON file per object **[ground truth, matches F38574-15]**

```
<model>/
  physical/
    <Database>.json
    <Database>/
      <Schema>.json
      <Schema>/
        <Physical Table>.json
        <Physical Table Alias>.json     # role-playing dimension — see modeling-patterns.md
  logical/
    <Business Model>.json
    <Business Model>/
      <Logical Table>.json              # one per role too — an alias gets its own logical table
  presentation/
    <Subject Area>.json
    <Subject Area>/
      <Presentation Table>.json
  variables/
    <Init Block>.json
    variables/<Variable>.json
```

Rules:
- `name` is required on every object; the file name matches the object name
  (unsupported characters replaced).
- Cross-file references use a **fully-qualified name**:
  `objecttype:fully.qualified.path.name`. Periods *inside* a name segment are
  escaped with `\.`. Example:
  `physicalColumn:Eyelit_ADW.CORIN_UAT2.DIM_DATE.DATE_KEY`.
- Attribute names are lowerCamelCase; booleans default to `false`.

## Physical layer

### `database` **[F38574-15 full property list; connectionPools/writeBackConfig ground-truth-shaped]**

```json
{ "database": {
    "name": "Eyelit_ADW",
    "databaseType": "ORACLE_ADW",
    "connectionPools": [ { "name": "New Connection Pool_1",
        "connection": "'system'.'CORIN_CC'",
        "remoteConnection": false, "maxConnections": 10,
        "requiresFullyQualifiedTableNames": true,
        "connectionTimeout": 5, "connectionTimeoutUnit": "MINUTES",
        "multithreaded": true, "supportParams": true, "isolationLevel": "default",
        "writeBackConfig": { "dbSupportsUnicode": false, "bulkInsertBufferSize": 10240,
                              "transactionBoundary": 1000, "tempTablePrefix": "TT" } } ],
    "virtualPrivateDatabase": false, "crmMetadataTables": false,
    "allowDirectDatabaseRequests": false, "allowPopulateQueries": false } }
```

Required: `name`, `databaseType`. Full `database` property list (F38574-15):
`name, description, tags[], databaseType, persistConnectionPool, connectionPools[],
featureOverrides[], queryLimits[], virtualPrivateDatabase, crmMetadataTables,
allowDirectDatabaseRequests, allowPopulateQueries`.

> **Note on the property named `requiresFullyQualifedTableNames` in some Oracle
> material**: the real export spells it correctly
> (`requiresFullyQualifiedTableNames`). Older prose in F38574-15 has a
> misspelling; trust the real export / this file's spelling.

There is **no `database.joins` property** — F38574-15's own prose lists one but
its JSON Schema for `database` doesn't define it. Physical joins live on
`physicalTable.joins` (below).

**`connectionPool`** full shape **[F38574-15]**: `name, description, connection
(req), remoteConnection, maxConnections, requiresFullyQualifiedTableNames,
connectionTimeout, connectionTimeoutUnit (WHEN_QUERY_COMPLETES|DAYS|HOURS|
MINUTES|SECONDS|NEVER), multithreaded, supportParams, isolationLevel (string),
runOnConnectScripts[], runBeforeQueryScripts[], runAfterQueryScripts[],
runOnDisconnectScripts[], writeBackConfig, permissions[]`.

**`schema`** / **`catalog`** — trivial: `{"schema": {"name": "CORIN_UAT2"}}`.
Both objects: `name (req), description, tags[], dynamicName`.

### `physicalTable` — base form **[ground truth + F38574-15]**

```json
{ "physicalTable": { "name": "DIM_DATE", "sourceType": "TABLE",
    "physicalColumns": [
      { "name": "DATE_KEY", "dataType": "DATETIME", "length": 0, "nullable": true },
      { "name": "YEAR", "dataType": "NUMERIC", "length": 0, "nullable": true },
      { "name": "IS_WEEKEND", "dataType": "CHAR", "length": 1, "nullable": true } ],
    "caching": { "enable": true, "expiryTime": 0 } } }
```

Full property list **[F38574-15]**: `name (req, pattern ^[^?*]+$), description,
tags[], sourceType (TABLE|STORED_PROCEDURE|SELECT), sourceTable, additionalKeys
([[string]]), joins[], dynamicName, sqlHints, caching, overrideSourceCacheSetting,
eventPollingFrequency, selectStatements[], physicalColumns[]`.

- `length` is **always present** on `physicalColumn` (`0` when not
  applicable), never omitted. **[ground truth]**
- `caching: {enable, expiryTime}` is present on every physical table.
  **[ground truth]**
- **`nullable` tracks the real column's `NOT NULL` constraint, not its
  semantic role.** A primary key can be `nullable: true` in the wire format
  (`DIM_DATE.DATE_KEY` is) and a foreign key can be `nullable: true` too
  (most FKs are). Don't derive `nullable` from `role`/`key`/`foreign_key` —
  there is no correlation. If you don't have a real NOT NULL source, default
  to `true`. **[ground truth]**

### `physicalTable` — alias form (role-playing dimension) **[ground truth + F38574-15]**

```json
{ "physicalTable": { "name": "DIM_ACCOUNT_DATE",
    "sourceTable": "physicalTable:Eyelit_ADW.CORIN_UAT2.DIM_DATE",
    "overrideSourceCacheSetting": false } }
```

An alias is a **distinct schema object** (`PhysicalTableAlias` in F38574-15):
`name (req), description, tags[], sourceTable (req), additionalKeys[],
caching, dynamicName, overrideSourceCacheSetting`. It **never has its own
`physicalColumns`** — columns are inherited from `sourceTable` and can't be
added/removed/modified on the alias. See `modeling-patterns.md` for when and
how to build one (multiple FKs on one fact pointing at the same dimension).

### `physicalColumn` **[ground truth + F38574-15]**

```json
{ "name": "DATE_KEY", "dataType": "DATETIME", "length": 0, "nullable": true }
```
`name (req), description, dataType, length (0–2147483647), nullable`.

### `physicalTable.joins` **[ground truth for the condition-based branch; F38574-15 for the expression-based branch and shared enums]**

Two branches, selected by `useJoinExpression`:

```json
{ "rightTable": "physicalTable:Eyelit_ADW.CORIN_UAT2.DIM_ACCOUNT_DATE",
  "useJoinExpression": false,
  "joinConditions": [ { "leftColumn": "physicalColumn:Eyelit_ADW.CORIN_UAT2.FACT_ATTENDANCE_LOG.ACCOUNT_DATE_KEY",
                         "rightColumn": "physicalColumn:Eyelit_ADW.CORIN_UAT2.DIM_ACCOUNT_DATE.DATE_KEY" } ],
  "joinType": "INNER", "cardinality": "MANY_TO_ONE" }
```

`useJoinExpression: true` switches to an expression instead of
`joinConditions` **[F38574-15, Ch.1 example]**:
```json
{ "rightTable": "physicalTable:...",
  "useJoinExpression": true,
  "physicalExpression": { "expressionTemplate": "TIMESTAMPDIFF(SQL_TSI_DAY, %1, %2)",
                           "expressionObjects": ["physicalColumn:...Order_Day_Dt", "physicalColumn:...Ship_Day_Dt"] },
  "joinType": "INNER", "cardinality": "MANY_TO_ONE" }
```
Use the expression form only when the join key isn't a plain equality (a
computed/derived join condition); default to `joinConditions` otherwise.

`joinType` always present, `cardinality` always present in the condition-based
form. Fact-to-dimension joins are always `MANY_TO_ONE` with the fact on the
many side — see `modeling-patterns.md` §5.

## Logical layer

### `businessModel` **[ground truth]**

```json
{ "businessModel": { "name": "MES", "disable": false } }
```
The business model name is **unrelated to `subjectArea`/`subject_area`
values** — it's the name of the whole semantic model, one per OAC model.
Don't conflate it with a dbt `meta.oac.subject_area` tag.

### `logicalTable` **[ground truth + F38574-15]**

```json
{ "logicalTable": { "name": "DIM_DATE", "type": "DIMENSION",
    "primaryKey": ["DATE_KEY"],
    "logicalColumns": [ ... ],
    "logicalTableSources": [ { "name": "DIM_DATE", "disable": false,
        "tableMapping": { "tables": ["physicalTable:Eyelit_ADW.CORIN_UAT2.DIM_DATE"] },
        "combineWithOtherFragments": false, "enableFragmentSelection": false, "distinctValues": false } ] } }
```

`type` **[ground truth]** is uppercase: `FACT` / `DIMENSION`. F38574-15 adds a
third value, `LOOKUP` **[F38574-15 only — never seen in a real export]**.

Full property list **[F38574-15]**: `name (req), description, tags[], type
(req), primaryKey[], logicalColumns[], logicalTableSources[], joins[],
hierarchyType, levelBasedHierarchy, parentChildHierarchy, dataFilters[]`.

**Naming**: logical table and column names are **the same UPPER_SNAKE string
as the physical relation/column they map to** (`DIM_DATE`, `DATE_KEY`,
`MONTH_NAME`) — not the lowercase dbt model/column name, and not the friendly
`meta.oac.label` value (that only ever shows up at the presentation layer).
**[ground truth]**

**Fact tables should not have a `primaryKey`** — Oracle explicitly recommends
against it except when a client tool needs to send keyed logical queries, in
which case the key must also be exposed in the presentation layer.
**[F38574-15 building guide, Ch.10]**. Dimensions always need one, and
business keys are preferred over surrogate keys at this layer.

### `logicalColumn` / `logicalColumnSource` **[ground truth for PHYSICAL_COLUMNS branch, F38574-15 for LOGICAL_COLUMNS branch]**

```json
{ "name": "DATE_KEY", "dataType": "DATETIME", "writeable": false,
  "logicalColumnSource": { "derivedFrom": "PHYSICAL_COLUMNS",
    "physicalMappings": [ { "logicalTableSource": "DIM_DATE",
        "physicalExpression": { "expressionTemplate": "%1",
          "expressionObjects": ["physicalColumn:Eyelit_ADW.CORIN_UAT2.DIM_DATE.DATE_KEY"] } } ] } }
```

`derivedFrom: "PHYSICAL_COLUMNS"` and `writeable: false` are **required on
every ordinary column** — not optional decoration. **[ground truth]**
`logicalTableSource` inside `physicalMappings` is a **plain name matching the
physical table's own name** (`"DIM_DATE"`), not a synthesized `_src` suffix.

Full `logicalColumn` list **[F38574-15]**: `name (req), description, dataType,
sortBy, descriptorColumn, writeable, logicalColumnSource (req), aggregation,
dataFilters[], logicalLevel`.

`logicalColumnSource` full shape **[F38574-15]**: `derivedFrom
(PHYSICAL_COLUMNS|LOGICAL_COLUMNS, req), physicalMappings[], logicalExpression`
— `logicalExpression` is used instead of `physicalMappings` when
`derivedFrom = LOGICAL_COLUMNS` (calculated/derived measures — see below).

**Measures** — matches ground truth exactly:
```json
"aggregation": { "rule": "SUM" }
```

### Derived / calculated measures **[F38574-15 only — never built in the ground-truth export; see modeling-patterns.md for how to use this correctly]**

```json
{ "name": "Actual Unit Price", "dataType": "NUMERIC",
  "logicalColumnSource": { "derivedFrom": "LOGICAL_COLUMNS",
    "logicalExpression": { "expressionTemplate": "%1 / %2",
      "expressionObjects": [ "logicalColumn:MES.FACT_SALES.REVENUE",
                              "logicalColumn:MES.FACT_SALES.BILLED_QUANTITY" ] } } }
```
Both operands are **already-aggregated `logicalColumn`s** (each has its own
`aggregation.rule`), not raw physical columns — the division happens
post-aggregation (ratio-of-sums, correct at any grain). Don't wrap `SUM()`
inside the expression template; set `aggregation.rule` on each operand
instead and divide the two logical columns directly. The query engine
auto-guards divide-by-zero in the generated SQL.

### `logicalTableSource` **[ground truth + F38574-15]**

Full shape: `name (req), description, disable, priority, tableMapping (req),
dataGranularity[], dataFragmentation, combineWithOtherFragments,
enableFragmentSelection, dataFilter, distinctValues`.
`tableMapping`: `{tables[], logicalTableSourceJoins[]}`.
`logicalTableSourceJoin`: `{leftTable (req), rightTable (req), joinType, disable}`.

### `logicalTable.joins` — fact → dimension **[ground truth + F38574-15]**

```json
{ "rightTable": "logicalTable:MES.DIM_TEAMS", "joinType": "INNER",
  "cardinality": "MANY_TO_ONE", "drivingTable": "None" }
```

`joinType` and `drivingTable` are **always present** — `drivingTable` is the
**literal string `"None"`**, not JSON `null`, when there isn't one; it's
typed as a plain string field (`rawType: table`), so that's just the sentinel
value observed, not a special construct. Only emit these joins from **fact**
logical tables outward to dimensions — a `foreign_key` column declared on a
*dimension* (a snowflake FK) does not automatically become a join; see
`modeling-patterns.md` §5 on keeping the business model a strict star.

`Join` object: `rightTable (req), joinType, cardinality, drivingTable`.

Full `Cardinality` enum **[F38574-15]**: `ONE_TO_ONE, ZERO_OR_ONE_TO_ONE,
ONE_TO_ZERO_OR_ONE, ZERO_OR_ONE_TO_ZERO_OR_ONE, ONE_TO_MANY,
ZERO_OR_ONE_TO_MANY, MANY_TO_ONE, MANY_TO_ZERO_OR_ONE, MANY_TO_MANY, UNKNOWN`.

Full `JoinType` enum **[F38574-15]**: `INNER, LEFT_OUTER, RIGHT_OUTER,
FULL_OUTER, FULL_OUTER_STITCH`. Outer joins are always defined at the logical
layer (physical joins carry no inner/outer semantics) — use sparingly, and
model an outer-joined dimension as a *separate* logical dimension rather than
forcing every consumer through an outer join by default.

## Hierarchies **[F38574-15 only — the one ground-truth dimension that declared a hierarchy (`dim_date`) shipped without building one; treat this whole section as unvalidated against a real import]**

### `levelBasedHierarchy` (on `logicalTable`)

```json
{ "logicalLevels": [ "LogicalLevel", "..." ],
  "logicalHierarchies": [ { "name": "Calendar", "levels": ["Grand Total", "Year", "Quarter", "Month", "Day"] } ],
  "defaultRootLevel": "Grand Total", "ragged": false, "skipped": false }
```
Required: `logicalLevels`, `logicalHierarchies`. `logicalLevels` holds the
*full* level definitions (below); `logicalHierarchies[].levels` is a plain
array of level-name strings, top (root) to bottom (leaf) — a dimension can
define one set of levels and multiple named drill hierarchies that reorder or
subset them (e.g. Calendar vs Fiscal).

### `logicalLevel`

```json
{ "name": "Day", "primaryKey": ["DATE_KEY"], "displayKey": "FULL_DATE",
  "chronologicalKey": ["DATE_KEY"], "numberOfElements": 3650 }
```
Full shape: `name (req), grandTotalLevel, displayKey (string), preferredDrillPath[],
primaryKey[], additionalKeys[], parentKey, chronologicalKey[], disableAggregateToHigherLevel,
numberOfElements`.

- Exactly one level per hierarchy is the **Grand Total**: `grandTotalLevel: true`,
  no key, `numberOfElements: 1`. Defining it auto-flags "supports rollup" on
  every other level. A Grand-Total-level measure ignores filters *on that
  dimension* but still respects filters on other dimensions — the mechanism
  behind share-of-total measures.
- `chronologicalKey` is an **array**, and belongs to a **`LogicalLevel`**, not
  the hierarchy or table. If the hierarchy's type is Time, every non-Grand-Total
  level needs its own `chronologicalKey` (the columns that sort that level's
  members oldest→newest), not just the leaf level — `(Year, Quarter)` ordering
  must sort correctly via a plain `ORDER BY` on the key.
- `displayKey` is typed as a single **string**, not an array, despite the
  prose ("column(s) used for display") suggesting otherwise.
- No documented per-level "skip" flag — skip-level behavior is a whole-hierarchy
  `skipped: true` on `levelBasedHierarchy`; ditto `ragged: true` for
  unbalanced hierarchies (some branches don't reach the deepest level).

### `logicalHierarchy`
`{ name (req), description, levels[] (req) }` — `levels` = ordered level-name strings.

### Parent-child hierarchies **[F38574-15 only]**

```json
{ "parentChildHierarchy": { "name": "Org Chart",
    "logicalLevels": [ "LogicalLevel", "..." ],
    "relationshipTables": [ { "logicalTableSource": "EMP_HIER_SRC",
        "table": "logicalTable:MES.EMP_RELATIONSHIP", "memberKey": "EMPLOYEE_ID",
        "parentKey": "MANAGER_ID", "distance": "DISTANCE", "leafNodeIdentifier": "IS_LEAF" } ] } }
```
Required on the hierarchy: `name`, `logicalLevels`, `relationshiptables`. All
five fields on `relationshipTable` are required. The relationship table has 4
physical columns: member id, ancestor/parent id, distance (levels between
them), leaf flag — generated once via "Generate Relationship Table" and
reloaded (full reload, not incremental) whenever the dimension changes.

## Presentation layer

### `subjectArea` **[ground truth + F38574-15]**

```json
{ "subjectArea": { "name": "Attendance", "sourceBusinessModel": "businessModel:MES",
    "tableOrder": [ { "name": "presentationTable:Attendance.Attendance Fact", "children": [] } ] } }
```
`name (req), description, tags[], sourceBusinessModel (req), implicitFactColumn,
alternateNames[], hideIfTrue, tableOrder[], permissions[], localization`.

`tableOrder` entries are `{name (req), children[]}` — **not bare FQN
strings** — and `children` is recursive, so tables can be nested into
folder-like groupings in the presentation tree. **[F38574-15 adds the
`children` nesting `eyelit_smml` never used; the `{name: fqn}` wrapper itself
is ground-truth-confirmed]**

A subject area draws from exactly **one business model**. `implicitFactColumn`
matters once a subject area spans more than one fact table — see
`modeling-patterns.md` §4 for the chasm-trap it prevents.

### `presentationTable` / `presentationColumn` **[ground truth for the base shape; F38574-15 for the full property list]**

```json
{ "presentationTable": { "name": "Attendance Fact",
    "presentationColumns": [
      { "name": "Account Date Key", "sourceLogicalColumn": "logicalColumn:MES.FACT_ATTENDANCE_LOG.ACCOUNT_DATE_KEY" } ] } }
```

`presentationTable`: `name (req), description, tags[], alternateNames[],
hideIfTrue, presentationColumns[], hierarchies[], permissions[], dataFilters[],
localization`.
`presentationColumn`: `name (req), description, tags[], sourceLogicalColumn,
alternateNames[], hideIfTrue, permissions[], dataFilters[], localization`.

- **Presentation names are friendly and human-chosen**, diverging from the
  underlying logical/physical name (`Attendance Fact`, not `FACT_ATTENDANCE_LOG`;
  `Clock In Dates`, not `DIM_CLOCK_IN_DATE`). There's no dbt-native source for
  this — see the `presentation_name` / `label` conventions in the sibling
  `dbt-to-smml` skill. **[ground truth]**
- **Degenerate/FK id columns are not hidden by default** — every FK and
  degenerate column in the real export is present in the presentation layer.
  **[ground truth]**
- **No `dataType` on presentation columns** — type is inherited from
  `sourceLogicalColumn`. **[F38574-15]**
- **No boolean visibility flag.** Visibility is controlled only by
  `hideIfTrue` (an `Expression`: `expressionTemplate` + `expressionObjects[]`),
  evaluated at runtime — same construct as join/derived-measure expressions.
  A hidden object is still directly queryable; hiding is UI-only, not
  security. **[F38574-15]**
- **No reordering property** beyond array position; `alternateNames[]` covers
  renames (old names survive as synonyms so existing reports don't break) —
  set these only once the logical model has stabilized. **[F38574-15]**

### `hierarchy` / `hierarchyLevel` (presentation layer) **[F38574-15 only]**

```json
{ "hierarchy": { "name": "Calendar", "sourceLogicalTable": "logicalTable:MES.DIM_DATE",
    "levels": [ { "hierarchyLevel": { "name": "Year", "sourceLogicalLevel": "Year" } } ] } }
```
A presentation hierarchy is always **nested inside a presentation table**
(unlike a logical dimension, which sits as a peer to tables). If a logical
dimension carries more than one named `logicalHierarchy` (e.g. Calendar vs
Fiscal), each becomes its own separate presentation `hierarchy`.

## Enums

### `DataType` — full list **[F38574-15]**

```
BINARY, BIT, BOOLEAN, CHAR, DATE, DATETIME, DOUBLE, FLOAT, NUMBER, INT,
INTERVAL, LONGVARBINARY, LONGVARCHAR, NUMERIC, OBJECT, SMALLINT, SMALUINT,
TIME, TIMESTAMP, TINYINT, TINYUINT, UINT, UNKNOWN, VARBINARY, VARCHAR
```
(`SMALUINT` is the schema's actual spelling, not a typo.) Ground truth's
observed subset — `DATETIME, NUMERIC, VARCHAR, CHAR, TIMESTAMP` — is fully
contained in this list.

### `DatabaseType` — use the JSON Schema enum, not Oracle's own prose list **[F38574-15 — the PDF itself has two conflicting lists]**

```
ORACLE_DATABASE, ORACLE_ADW, SQL_SERVER, TERADATA, INFORMIX, DB2, SYBASE_ASE,
SYBASE_IQ, MYSQL, IMPALA, APACHE_SPARK, REDSHIFT, MONGO_DB, SNOWFLAKE,
MONETDB, DEFAULT
```
`ORACLE_ADW` (Autonomous Data Warehouse) is the value ground truth actually
uses; `ORACLE_DATABASE` covers on-prem/regular Oracle. There is no separate
`ORACLE_ATP` value — use `ORACLE_ADW` or `ORACLE_DATABASE`.

### `AggregationRule` — top-level `aggregation.rule` **[F38574-15 — note the asymmetry with the dimension-based variant]**

```
NONE, SUM, AVG, COUNT, COUNT_DISTINCT, MAX, FIRST, LAST, MEDIAN,
STD_DEV, STD_DEV_POP, EVALUATE_AGGR, BASED_ON_DIMENSION
```
**`MIN` is not in this list.** It only exists on the dimension-based variant
below — this is a genuine schema asymmetry, confirmed twice in F38574-15, not
an omission.

### `AggregationRuleBasedOnDimension` — for `dimensionBasedRule.rule` **[F38574-15]**

```
NONE, SUM, AVG, COUNT, COUNT_DISTINCT, MAX, MIN, FIRST, LAST, MEDIAN,
STD_DEV, STD_DEV_POP, EVALUATE_AGGR, EXPRESSION
```
`dimensionBasedRule: {dimension (req), rule (req), aggregateExpression}` — the
semi-additive-measure mechanism (e.g. `{dimension: "Time", rule: "LAST"}` for
an ending balance that sums normally but takes the last period's value over
time).

### `DerivedFrom` **[F38574-15]**: `PHYSICAL_COLUMNS, LOGICAL_COLUMNS`

## Common constructs

`Expression`: `{expressionTemplate, expressionObjects[]}` — `%1`, `%2`… in the
template bind to objects in order, by position. Used for physical/logical
joins (expression form), derived measures, and `hideIfTrue`.

## Open gaps — don't trust these without checking a real OAC import first

- The exact field names on the **condition-based** physical join
  (`useJoinExpression`/`joinConditions`) are ground-truth-confirmed but not
  independently corroborated by F38574-15's own printed `physicalTable`
  schema fragment, which is incomplete on this point.
- **Hierarchies** (level-based, time, parent-child) — F38574-15 only; zero
  real-world confirmation.
- **Derived/calculated measures** (`LOGICAL_COLUMNS` branch) — F38574-15 only.
- **Degenerate dimensions** have no dedicated SMML construct in either
  source — model them as plain, non-aggregated attribute columns directly on
  the fact logical table (see `modeling-patterns.md` §6).
