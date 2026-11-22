---
wire_schema: "1.0"
command: generate
artifact: kickoff
domain: kickoff
release_types: []
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Generate client kick-off presentation deck from SoW and engagement context
argument-hint: "[release-folder]"

---

# Kickoff Deck — Generate

## Purpose

Builds a client kick-off presentation by populating the EDITMODE JSON block inside the deck HTML template. The primary source is the Statement of Work and engagement context created by `/wire:new`. If a release folder is specified, discovery artifacts from that release enrich the deck further.

Run immediately after `/wire:new` — no discovery or delivery artifacts are required for a first pass. Re-run at any time as more artifacts become available.

## Inputs

**Always required**:
- `.wire/engagement/context.md` — client name, engagement type, team members, SoW reference
- `wire/decks/kickoff/Project Kickoff.html` — blank template (installed with Wire)

**Optional — SoW (primary content source)**:
- `engagement/sow.md`, or a PDF referenced from `engagement/context.md`, or any file under `engagement/references/`

**Optional — release enrichment** (only if `<release-folder>` argument supplied). Sources depend on `release_type` in `.wire/releases/<release-folder>/status.md`:

For `discovery`:
- `.wire/releases/<release-folder>/planning/problem_definition.md`
- `.wire/releases/<release-folder>/planning/pitch.md`
- `.wire/releases/<release-folder>/planning/sprint_plan.md`

For `sop_discovery`:
- `.wire/releases/<release-folder>/planning/engagement_brief.md`
- `.wire/releases/<release-folder>/planning/stakeholder_map.md` (for the attendee list and named domain SMEs)

For all release types:
- `.wire/releases/<release-folder>/requirements/requirements_specification.md` (if present)
- `.wire/releases/<release-folder>/planning/pipeline_design.md` (if present)

## Workflow

### Step 1: Check prerequisites

1. Confirm `.wire/engagement/context.md` exists. If not: stop — "Run `/wire:new` first to initialise the engagement."

2. Locate the deck template. Check the following paths in order:
   a. `wire/decks/kickoff/Project Kickoff.html` — Wire source repo layout
   b. `decks/kickoff/Project Kickoff.html` — plugin installation layout (when installed via `/plugin install wire`)
   c. Run `find . -name "Project Kickoff.html" -path "*/kickoff/*" 2>/dev/null | head -1` to discover any other location

   If found at (b) or (c) but not (a), note the actual path and use it throughout the rest of the command in place of `wire/decks/kickoff/Project Kickoff.html`.

   If not found at any location: attempt to bootstrap by running:
   ```bash
   mkdir -p wire/decks/kickoff/assets
   ```
   Then instruct the user:
   > "The kickoff deck template could not be found. To install it, run:
   > `find ~/.claude -name 'Project Kickoff.html' 2>/dev/null`
   > If found, copy the `decks/kickoff/` folder from your Wire plugin installation to `wire/decks/kickoff/` in this directory.
   > If not found, pull the latest Wire plugin to get the template bundled with the plugin."
   Stop here.

3. If `<release-folder>` was supplied, confirm the folder exists at `.wire/releases/<release-folder>/`. If not: warn and continue without release enrichment.

4. **Ask the user about a title page image** — before reading any content, ask:
   > "Do you have an image you'd like to use as the title slide background? If so, please provide the file path (e.g. `/Users/you/photos/client-office.jpg`). Press Enter to skip and use the default RA background."

   If the user provides a path:
   - Verify the file exists.
   - Determine the output directory for the kickoff deck (see Step 6 for paths).
   - Copy the image into `$OUTPUT_DIR/kickoff/assets/` with a normalised filename: `title-photo.<original-extension>`.
   - Set `"titlePhoto": "kickoff/assets/title-photo.<ext>"` in the EDITMODE JSON.

   If the user skips: leave `"titlePhoto": ""` (the deck will use its built-in default background).

### Step 2: Read engagement context

Read `.wire/engagement/context.md`. Extract:

- `client_name` — formal client name for the title slide
- `engagement_type` — map to EDITMODE values:
  - `discovery` → `engagementType: "Discovery"` (discovery sprint kickoff mode)
  - any delivery type (`full_platform`, `pipeline_only`, `dbt_development`, `dashboard_first`, `dashboard_extension`) → `engagementType: "Project"`
- `team` or `presenters` — list of RA team members and roles presenting
- `start_date` or `engagement_date` — used as `engagementDate` (ISO format)
- `accent_color` — **ignore this field**. Always set `accentColor` to `#4F60FF` (RA indigo). The deck's `accentColor` overrides `--ra-indigo` across the entire design system (eyebrows, bullet dots, table headers, cards). Using a client's brand colour here replaces the RA design system; the RA indigo must be preserved.
- Any SoW file path referenced under `sow:` or `references:`

### Step 3: Read the Statement of Work

Look for a SoW in this order:
1. Path referenced in `engagement/context.md` under `sow:` or `references:`
2. `engagement/sow.md`
3. `engagement/references/sow.pdf` (or any PDF under `engagement/references/`)
4. Any `.md` file in `engagement/references/`

If found, extract:
- **Engagement objectives** — the headline goals the client wants to achieve. Synthesise as 3–5 bullet points describing current state and desired state. Use these for `slide4LeftCache` (current state) and `slide4RightCache` (desired state).
- **Headline metric** — any quantified business impact mentioned (cost saving, time reduction, risk reduction). Use for `slide5*` fields.
- **Proposed approach** — summarise as 3–5 outcome statements for `slide8Outcomes`.
- **Data sources / systems in scope** — list up to 4 distinct systems for `slide14Categories`. For each system, write a specific, actionable `needs` string describing exactly what access is required. Use the patterns below as a guide — match the type of system:
  - Database / data warehouse (Postgres, BigQuery, Snowflake, Redshift, SQL Server, etc.): "Login credentials and connection details — host, port, database name, and a read-only user account"
  - ETL / pipeline tool (Fivetran, Airbyte, Stitch, etc.): "Admin login and permission to view/edit connectors and destination configuration"
  - CRM / SaaS app (Salesforce, HubSpot, etc.): "Connected App or OAuth credentials with read-only API access to the relevant objects"
  - BI / reporting tool (Looker, Tableau, Power BI, etc.): "Viewer or developer login with access to the relevant content and underlying data source connections"
  - File storage / spreadsheets (Google Sheets, SharePoint, S3, etc.): "Service account or shared link with read access; bucket/folder path and any access keys if S3"
  - Adapt the pattern to the actual system — be specific about what the RA team will need on day one to begin the data audit.
- **Timeline / phases** — use to populate `slide12W1Focus` and `slide12W2Focus` if no sprint plan exists.
- **Team members named in the SoW** — supplement or replace the presenters list.

If no SoW is found, proceed in scaffold mode: all content fields remain as empty strings with a comment noting manual completion is required.

### Step 4: Enrich from release artifacts (if release-folder supplied)

If a release folder was specified, first read `.wire/releases/<release-folder>/status.md` and resolve `release_type`. Then enrich the deck content from the artifacts that match the release type. Both discovery flavours are supported; for delivery release types, only the cross-cutting fallbacks (requirements_specification, pipeline_design) apply.

---

#### For `release_type: discovery`

**From `problem_definition.md`** (if `problem_definition.review: complete`):
- `slide4Headline`: synthesise an 8–12 word headline naming the core friction from Section 3. Do not use the section heading verbatim.
- `slide4LeftCache`: current state — summarise Section 4 Impact table "Current State" column as 3–5 bullet points (HTML allowed; use `<strong>` for key terms).
- `slide4RightCache`: desired state — from Section 5 "What Solved Looks Like".
- `slide5*`: most impactful quantified metric from Section 4. Prefer cost, time savings, or risk. Format: `slide5Number` = the digit(s), `slide5Suffix` = unit symbol, `slide5Bold` = bold lead sentence, `slide5Tail` = supporting sentence.
- `slide6Problems` (exactly 8 entries): root causes from Sections 3 and 7. Generate 3–5 word headlines and 1–2 sentence details. Pad unused slots with `{"headline": "", "detail": ""}`. Set `slide6Count` to the number of non-empty entries.

**From `pitch.md`** (if `pitch.review: complete`):
- `slide8Outcomes` (exactly 5 entries): from Section 7 "Success Criteria". 3–5 word headline + 1–2 sentence detail per outcome. Pad to 5. Set `slide8Count`.

**From `sprint_plan.md`** (if `sprint_plan.review: complete`):
- `slide12W1Focus`: sprint goal for Sprint 1.
- `slide12W2Focus`: sprint goal for Sprint 2 (or "Continuous delivery and review" if single-sprint plan).
- `slide12W1Items` (exactly 6 strings): first 5 stories/epics from Sprint 1 — **cap at 5, never fill slot 6 with real content**. Pad slots 5 and 6 with `""`. Set `slide12W1Count` to the number of non-empty entries (max 5).
- `slide12W2Items` (exactly 6 strings): same from Sprint 2 — cap at 5. Pad slots 5 and 6 with `""`. Set `slide12W2Count` (max 5). The 6th slot exists to satisfy the fixed array length but must always be empty.

---

#### For `release_type: sop_discovery`

The SOP discovery kick-off is the playbook's Phase 1 meeting — its job is to align the sponsor and stakeholders on the discovery process about to run, not on a specific delivery scope. Enrichment is therefore lighter: there are no Shape Up artefacts yet, only the engagement brief and (optionally) the stakeholder map.

**From `engagement_brief.md`** (if `engagement_brief.review: complete`):
- `slide4Headline`: a 8–12 word headline naming the engagement's problem statement (from the Problem statement row in the brief). Do not use deliverable framing.
- `slide4LeftCache`: current-state context drawn from the "Known constraints" and "Known risks" rows — 3–5 bullets.
- `slide4RightCache`: desired-state framing drawn from the "Desired outcome" row plus the in-scope domain list.
- `slide5*`: most striking success-metric or named target from the "Success metrics" row.
- `slide6Problems` (exactly 8 entries): pre-discovery hypotheses — themes RA expects to investigate during interviews. Use the brief's "Known risks" and "Out-of-scope" rows for material. Pad unused slots.
- `slide8Outcomes` (exactly 5 entries): the standard SOP discovery exit deliverables — engagement brief, stakeholder interviews, requirements matrix, three analyses (Hierarchy/PPT/Maturity), Findings Playback deck. Use this to set the right expectation about what the sponsor will see at the end of the engagement.

**From `stakeholder_map.md`** (if `stakeholder_map.review: complete`):
- `slide12W1Focus`: "Stakeholder interviews — week 1" with the count of P0 interviews planned.
- `slide12W2Focus`: "Stakeholder interviews — week 2" with the count of P1 interviews planned.
- `slide12W1Items` (exactly 6): list of P0 stakeholder names with title. Cap at 5; pad slots 5 and 6 with `""`.
- `slide12W2Items` (exactly 6): list of P1 stakeholder names with title. Same cap and padding rules.

The intent: a SOP discovery kick-off should leave every stakeholder knowing whether they're being interviewed, by whom, in what week, and what the exit deliverable will be.

---

#### Cross-cutting fallbacks (all release types)

**From `requirements_specification.md`** (if present):
- `slide14Categories` (exactly 4 entries): data access requirements. For each system, write the `needs` field as a specific, actionable string (see the access patterns in Step 3 above — database, ETL tool, CRM, BI tool, file storage). Pad unused slots to 4 with `{"name":"","needs":""}`. Set `slide14Count`.

**From `pipeline_design.md`** (if present):
- `slide10MermaidCache`: raw Mermaid source (no fences). Set `slide10Direction` to `"TB"` if > 8 nodes, otherwise `"LR"`. Set `slide10Headline` and `slide10Prompt` from the document's purpose.
  **Mermaid label rules** — node labels must not contain `\n` escape sequences (they render as literal backslash-n in the diagram). Keep labels short (≤ 25 characters) and single-line. If a label needs a line break, use `<br/>` inside a quoted HTML label: `A["Line one<br/>Line two"]`. Never use `\n` in any Mermaid string.

Discovery artifact content overrides SoW-derived content for the same fields.

### Step 5: Assemble and validate the EDITMODE JSON

Build the complete JSON object. Validate before writing:

- `slide6Problems` is exactly 8 entries
- `slide8Outcomes` is exactly 5 entries
- `slide12W1Items` and `slide12W2Items` are exactly 6 entries each
- `slide14Categories` is exactly 4 entries
- Count fields do not exceed array length
- `slide12W1Count` and `slide12W2Count` are ≤ 5 (the 6th slot is always empty — the slide layout fits 5 items per column readably)
- `accentColor` is always `"#4F60FF"` (RA indigo). Never substitute a client brand colour here.
- `vignetteStrength` is an **integer 0–100** (the range slider unit). Default to `74`. Do not write a float like `0.5` — the JS divides by 100 at render time, so `0.5` renders as 0.5% opacity (invisible vignette).
- `titleVariant` is always `"pitch"` — this is the value that enables the full-bleed photo backdrop on the title slide. Do not use `"photo"` or any other value; the deck JS only recognises `"pitch"` as the photo variant.
- `slide10Direction` is `"LR"` or `"TB"` (or `""` if slide10 is empty)
- The full object parses as valid JSON (no trailing commas, no comments)
- **String values must not contain literal newlines** — multi-line bullet lists (e.g. `slide4LeftCache`, `slide4RightCache`) must have newlines escaped as `\n`. Literal newlines inside double-quoted JS strings cause a syntax error that silently prevents the entire deck from rendering. Serialise using `json.dumps()` or equivalent, never by hand-writing multi-line strings.

### Step 6: Write the output file

**If `.wire/releases/<release-folder>/artifacts/kickoff-deck.html` already exists**: read its EDITMODE block first and merge — preserve any fields manually set (e.g. `titlePhoto`, `accentColor`, `showPartnerBadge`, `presenters`) unless the new generated value is non-empty. This allows re-runs without losing manual edits.

Read `wire/decks/kickoff/Project Kickoff.html`. Locate the EDITMODE delimiters:
```
/*EDITMODE-BEGIN*/
...
/*EDITMODE-END*/
```

Replace the content between (and including) the delimiters with the new JSON. Write the result to:

- **Engagement-level run** (no release folder): `.wire/kickoff-deck.html`
- **Release-enriched run**: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`

Do not modify the template file at `wire/decks/kickoff/Project Kickoff.html`.

**MANDATORY: Copy support files into a `kickoff/` subdirectory.** The deck HTML references CSS, JS, fonts, and assets using relative paths. Without these files next to the HTML, the deck will render with no styling, no fonts, and no images. **You must run the following bash commands immediately after writing the HTML file — do not skip this step, do not ask the user to do it.**

Substitute the actual paths for `TEMPLATE_DIR` and `OUTPUT_DIR`:
- `TEMPLATE_DIR` = the directory where the template was found (Step 1): `wire/decks/kickoff/` (Wire source repo) or `decks/kickoff/` (plugin install)
- `OUTPUT_DIR` = the directory containing `kickoff-deck.html`

**Run these bash commands now:**
```bash
mkdir -p "$OUTPUT_DIR/kickoff"
cp "$TEMPLATE_DIR/colors_and_type.css"  "$OUTPUT_DIR/kickoff/"
cp "$TEMPLATE_DIR/deck.css"             "$OUTPUT_DIR/kickoff/"
cp "$TEMPLATE_DIR/deck-stage.js"        "$OUTPUT_DIR/kickoff/"
cp "$TEMPLATE_DIR/mermaid.min.js"       "$OUTPUT_DIR/kickoff/"
cp -r "$TEMPLATE_DIR/fonts"             "$OUTPUT_DIR/kickoff/"
cp -r "$TEMPLATE_DIR/assets"            "$OUTPUT_DIR/kickoff/"
```

After running those commands, rewrite all external file references in the output HTML. These substitutions are also mandatory — the HTML file still has the original relative paths from the template. Do all as simple string substitutions across the entire file:

| Find | Replace | Covers |
|------|---------|--------|
| `href="colors_and_type.css"` | `href="kickoff/colors_and_type.css"` | CSS link tag |
| `href="deck.css"` | `href="kickoff/deck.css"` | CSS link tag |
| `src="mermaid.min.js"` | `src="kickoff/mermaid.min.js"` | Script tag |
| `src="deck-stage.js"` | `src="kickoff/deck-stage.js"` | Script tag |
| `src="assets/` | `src="kickoff/assets/` | All `<img>` tags (logo, partner logos, title bg — 15+ occurrences) |
| `'assets/` | `'kickoff/assets/` | JavaScript string references to assets (fallback title photo path in JS) |
| `` `assets/team/ `` | `` `kickoff/assets/team/ `` | Backtick template literal in `checkPhoto()` — derives team headshot paths from presenter name slug; the `photo` field on presenter objects is ignored by the deck JS |

The resulting artifacts directory structure:
```
artifacts/
├── kickoff-deck.html        ← references kickoff/* for all external files
└── kickoff/
    ├── colors_and_type.css
    ├── deck.css
    ├── deck-stage.js
    ├── mermaid.min.js
    ├── fonts/
    │   └── GoogleSans-*.ttf
    └── assets/
        └── ...
```

**Verify the copy succeeded** by running:
```bash
ls "$OUTPUT_DIR/kickoff/colors_and_type.css" "$OUTPUT_DIR/kickoff/deck-stage.js" "$OUTPUT_DIR/kickoff/fonts/" "$OUTPUT_DIR/kickoff/assets/"
```
If any path is missing, copy it now before proceeding. Do not report success until all four exist.

### Step 7: Update status

**Engagement-level run**: add or update `kickoff_deck` in `.wire/engagement/context.md` (or a dedicated `kickoff_status.md` if context.md has no artifact section).

**Release-enriched run**: add or update in `.wire/releases/<release-folder>/status.md`:
```yaml
kickoff_deck:
  generate: "complete"
  validate: "not_started"
  review: "not_started"
  file: "artifacts/kickoff-deck.html"
  generated_date: "<today>"
```

### Step 8: Report output

Show the consultant:
- Output file path (absolute, so they can open it directly)
- Which slides have content and which are placeholders requiring manual completion
- If discovery artifacts were available but not yet approved (not `review: complete`), list them and note what they would have contributed
- Next step: "Run `/wire:kickoff-validate` to check the deck, or open the file in Chrome to preview."

## Edge cases

- **No SoW, no discovery artifacts**: proceed in scaffold mode. All content slides are empty. Output a clear list of every field that needs manual completion.
- **Engagement type is `discovery` but no `--discovery` flag**: automatically set `engagementType: "Discovery"` since `context.md` already signals this.
- **Re-run after discovery artifacts become available**: merge, preserving manual edits. Log which fields were updated from newly approved artifacts.
- **Pipeline design has Mermaid with > 8 nodes**: set `slide10Direction: "TB"` automatically.
- **Multiple SoW files found**: read all, merge the content, note in the report.
