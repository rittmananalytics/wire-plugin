---
wire_schema: "1.0"
command: generate
artifact: business_rules
domain: discovery
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - dashboard_extension
  - pipeline_only
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: domain
      description: "--domain <name> limits the run to one business domain. Defaults to the release's domain when status.md names one."
    - name: import
      description: "--import <path> reads exported SQL or model text from a system Wire cannot read (SAP BW, Hana, SAC, Looker Studio). Repeatable."
produces:
  - type: document
    path: "artifacts/business_rules.md"
    description: "Business rules register for the domain in scope"
  - type: document
    path: "artifacts/business_rules.yaml"
    description: "Machine-readable register, read by design, testing and validate commands"
preconditions: dynamic
auto_validate: true
valid_next:
  - validate
delegates_to:
  - utils/definition_extract
  - utils/precondition_gate
  - utils/stale_artifact_check
  - utils/meeting_context
  - utils/reference_legibility
description: Discover, define and agree the business rules for one domain, from legacy systems and from the people who own the definitions, before design starts
argument-hint: <release-folder> [--domain <name>] [--import <path>]
---

# Business Rules — Generate

Follow `specs/utils/stale_artifact_check.md` with `artifact_id: business_rules` and `artifact_file_path: artifacts/business_rules.md` before proceeding.

---

## Purpose

Wire has no step that establishes what a metric means before the build starts.
`requirements-generate` reads documents. `workshops-generate` runs after
requirements and only resolves clarification markers already written into the
requirements document. Neither looks at the data, and neither looks at the
competing definitions sitting in the legacy systems.

So a definition disagreement has no artifact to surface in, and the first place it
can appear is a number that does not tie in QA.

The worked example this exists for: a requirements document asked for "Gross Sales
Order Online" and a channel breakdown including the in-store order channel, and
listed "standardised metric definitions" as a success factor. It never said whether
in-store orders were inside the figure, or whether returns were deducted. Eleven
months later the number did not match the legacy dashboard. Nobody had been wrong;
nobody had been asked.

This command runs first in a release and produces one register for the domain in
scope. It reads the legacy systems, and it asks the people who know.

## What makes this different from an inventory

A command that inventories existing definitions cannot record the absence of one.
That is why the register has an `unknown` status and why `unknown` is not a
failure. The register's job is as much to say "nobody has decided whether in-store
orders count" as it is to say what gross sales is.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/status.md`

**Optional, and used when present**:
- The client's dbt project, LookML project, and `schema.yml` measures
- `--import <path>` exports from systems Wire cannot read
- `requirements/requirements_specification.md` or `planning/requirements_matrix.md` — every metric named there without a rule becomes an open item
- `artifacts/business_rules.yaml` from an earlier domain's run — the register accumulates across runs, one domain at a time
- Fathom transcripts via `specs/utils/meeting_context.md`

## Workflow

### Step 1: Pre-flight and scope

1. Resolve `$ARGUMENTS`. Read `status.md`.
2. Follow `specs/utils/precondition_gate.md`.
3. Resolve the domain: `--domain`, else the release's domain from `status.md`, else
   ask. **Do not run without a domain.** A register that tries to cover everything
   at once goes stale before it is agreed, which is how the last one ended up empty.

### Step 2: Extract from the systems

Follow `specs/utils/definition_extract.md`. It carries the enumeration across dbt,
LookML and `schema.yml`, the conflict taxonomy, and the `--import` intake for
unreachable systems with its mandatory `export_date` and `exported_by`.

Each definition found becomes a `variant` on a rule. Two variants of the same
business concept make the rule `disputed` before anyone has argued about it.

### Step 3: Read the requirements for named-but-undefined metrics

Every metric named in the requirements that has no variant from Step 2 becomes a
rule with status `unknown`. This is the step that would have caught the worked
example: "Gross Sales Order Online" was named, and no system definition of it
agreed with another.

### Step 4: Ask the people

A working session on one domain, with the people who own the numbers. Reuse the
interview machinery: follow `specs/sop_discovery/stakeholder_interview/generate.md`
in `--workshop` mode where the release is running a discovery, or run it as a
plain working session where it is not.

The session's output is not general context. It is, per rule:

1. Which variant is right, or that a new definition is needed
2. Who says so, by name
3. What the rule does with the awkward cases: returns, cancellations, in-store
   orders, currency, partial refunds, the remainder that fits nowhere

Where the room cannot settle it, the rule stays `disputed` and names who will.
Recording a real disagreement is a success for this command.

### Step 5: Write the register

Write `artifacts/business_rules.md` for people and `artifacts/business_rules.yaml`
for machines. One entry per rule:

```yaml
- id: BR-1
  name: "Gross Sales"
  domain: commerce
  statement: "Total order value before deductions, for the reporting period."
  status: disputed            # agreed | disputed | assumed | unknown
  variants:
    - source: looker_legacy
      object: "store_reports/views/sales.view.lkml:142"
      expression: "SUM(${TABLE}.gross_amount)"
    - source: sap_bw
      object: "exported/ZSD_GROSS_SALES.sql (manual export 2026-08-14)"
      expression: "SUM(NETWR) WHERE VBTYP NOT IN ('H','K')"
      export_date: 2026-08-14
      exported_by: "A. Consultant"
  disagreement: "Whether the in-store order channel is included, and whether returns are deducted."
  decision: null
  approver: null
  agreed_date: null
  confirm_by: null
  confirmer: null
  implemented_by: []
  check: null
```

Field rules:

| Field | Rule |
|---|---|
| `id` | `BR-n`, stable for the life of the register. Never renumbered: the build cites these |
| `statement` | The rule in plain words, readable by whoever approves it |
| `status` | One of the four below |
| `variants[]` | Every competing definition, each with `source` and `object`. **A variant with no `object` does not enter the register** |
| `disagreement` | What the variants actually differ on, stated explicitly. Not "definitions vary" |
| `decision` | The chosen definition, once made |
| `approver`, `agreed_date` | A named person and a date. Required for `agreed` |
| `confirmer`, `confirm_by` | Required for `assumed`. Assumptions expire |
| `implemented_by[]` | dbt models and LookML measures carrying this rule's id |
| `check` | The query that proves it, generated in Step 7 |

### Step 6: The four statuses

| Status | Meaning |
|---|---|
| `agreed` | A decision with a named approver and a date |
| `disputed` | Two or more variants, no decision yet. Named in the review as an open item |
| `assumed` | Chosen without confirmation. Carries a confirmer and a date |
| `unknown` | Nobody has decided and no variant is authoritative |

`unknown` is a legitimate resting state and never a validate failure on its own.
It is the record of an unknown-unknown, and recording it is the point. A register
that can only hold what is already known stays empty, which is exactly what
happened to the last one.

### Step 7: Generate the reconciliation checks

For every rule with a legacy variant, generate the query that compares both
readings against the legacy source, through the existing
`specs/migration/equivalency/validate.md` machinery. Write it to
`checks/br_<n>_<slug>.sql` and record the path in `check`.

Run it now, not after the build. A disputed gross sales rule produces a query on
day one that shows which reading matches the legacy dashboard, which is often
enough to settle the dispute without a meeting.

### Step 8: Reference legibility

Follow `specs/utils/reference_legibility.md`. `BR-n` codes are cited by design,
dbt and testing artifacts, so they are expanded at first mention and carry a
Reference key table.

### Step 9: Status and log

Update `status.md`:

```yaml
business_rules:
  generate: complete
  validate: not_started
  review: not_started
  file: artifacts/business_rules.md
  domains_covered: [commerce]
  generated_date: [today]
```

`domains_covered` accumulates. A later run on another domain appends to it and to
the register rather than replacing either.

Follow `specs/utils/execution_log.md`.

## Output

`artifacts/business_rules.md`, `artifacts/business_rules.yaml`, and
`checks/br_*.sql`.
