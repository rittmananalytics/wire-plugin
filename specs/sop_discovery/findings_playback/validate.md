---
wire_schema: "1.0"
command: validate
artifact: findings_playback
domain: sop_discovery
release_types:
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: findings_playback
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the Findings Playback deck — structure, placeholder fill rate, TODO regions, deliverability

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Findings Playback Deck — Validate

## Purpose

Checks the generated Findings Playback deck before the sponsor meeting:
- All required placeholders filled
- TODO chart/word-cloud regions populated (or explicitly deferred to in-meeting edit)
- Slide ordering matches the canonical structure
- Assets and fonts present and loadable
- File opens in a browser without console errors

## Inputs

- `.wire/releases/$ARGUMENTS/playback/findings_playback.html`
- `wire/decks/findings_playback/Findings Playback.html` (reference template)

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read the generated deck. If missing: "Run `/wire:findings-playback-generate $ARGUMENTS` first."

### Step 2: Structure checks

Parse the deck. For every `<section data-label="...">`:
- [ ] Slide ordering: numeric prefix (01, 02, ...) is contiguous (no gaps unless a section was explicitly excluded in generate)
- [ ] Total slide count between 28 and 60 (canonical range is 30–55; tolerance buffer)
- [ ] Cover slide (label starts with "01") present
- [ ] Section divider for Scope & Discovery Process present
- [ ] Three lens introduction slides present (Hierarchy of Needs, PPT framework, Maturity curve)
- [ ] Current State section divider present
- [ ] Vision Statement slide present
- [ ] At least one per-axis section present (Process / People / Technology) — order by largest count first per playbook

### Step 3: Placeholder fill check

For every `<span class="ph">&lt;&lt;variable_name&gt;&gt;</span>` still in the deck:
- [ ] Flag every unfilled placeholder with its slide number and variable name

Categorise:
- **Critical unfilled** — placeholders on Cover, Team intro, Scope & Objectives, Vision Statement, per-axis Summary slides. These MUST be filled before the sponsor sees the deck.
- **Optional unfilled** — placeholders on slides marked as optional (concept explainer, tool replacement, product spotlights). OK to leave if the slide will be excluded; otherwise must fill.

### Step 4: TODO region check

Search for `<!-- TODO Lead Consultant: ... -->` comments:
- [ ] Each TODO region has either: (a) been replaced with the actual data, or (b) been confirmed as "fill live in playback edit-mode" by the consultant. Surface every remaining TODO with slide number.

### Step 5: Asset loadability

- [ ] `assets/logo-black-blue.svg` exists at the deck-relative path
- [ ] `assets/logo-white-blue.svg` exists
- [ ] `assets/hierarchy-of-needs.png` exists
- [ ] `assets/ppt-venn.svg` exists
- [ ] `assets/maturity-curve.png` exists
- [ ] `colors_and_type.css` exists
- [ ] `deck-stage.js` exists
- [ ] `fonts/` directory present with at least Beatrice-Regular.woff2 and GoogleSans-Regular.ttf

### Step 6: Vision Statement check

- [ ] Slide labelled "Vision Statement" (or similar) contains two paragraphs
- [ ] Each paragraph has at least one `<strong>` bolded phrase (the load-bearing language)
- [ ] Vision Statement matches the Vision Statement excerpt recorded in `status.md → sponsor_validation.vision_statement_excerpt` (or that field is still null — flag a WARNING to set it before review)

### Step 7: Optional smoke test

If `--browser` flag is passed, the validator should open the deck in a headless browser and check for:
- No JavaScript console errors during initial render
- Every slide section visible (no `display: none` regression)
- Font load succeeds

This is opt-in and only runs if a browser engine is available. Without `--browser`, skip with a note "Smoke test skipped — pass --browser to enable".

### Step 8: Produce report

**Output**: `.wire/releases/$ARGUMENTS/playback/findings_playback_validation.md`

```markdown
# Findings Playback Deck Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}
**Deck**: playback/findings_playback.html

## Result: PASS / FAIL / PASS WITH WARNINGS

## Structure

| Check | Result | Note |
|---|---|---|
| Slide count in [28, 60] | ✅ | 42 slides |
| Slide ordering contiguous | ✅ | |
| Required canonical sections present | ✅ | |

## Placeholders

| Category | Count remaining |
|---|---|
| Critical unfilled | 3 |
| Optional unfilled | 7 (slides marked for exclusion) |

### Critical unfilled (must fix)
- Slide 04 — `presenter_title`
- Slide 14 — `vision statement paragraph 2`
- Slide 18 — `process headline`

## TODO regions

- Slide 10 — Hierarchy chart counts
- Slide 11 — PPT chart counts
- Slide 16 — Process word cloud
- Slide 22 — People word cloud
- Slide 28 — Technology word cloud

## Asset loadability

| Asset | Status |
|---|---|
| logo-black-blue.svg | ✅ |
| logo-white-blue.svg | ✅ |
| ... | ... |

## Vision Statement

- Two paragraphs: ✅
- Bold phrases: ✅
- Matches `sponsor_validation.vision_statement_excerpt`: ⚠️ field still null — set it before review

## Next Steps

[If PASS]:
Hold the playback meeting and run the review:
/wire:findings-playback-review $ARGUMENTS

[If FAIL]:
Fix unfilled placeholders and TODO regions, then re-validate.
```

### Step 9: Update status

```yaml
artifacts:
  findings_playback:
    validate: complete   # or "failed"
```

### Step 10: Output summary

Show: critical-unfilled count, TODO count, top issue.

## Output Files

- `.wire/releases/$ARGUMENTS/playback/findings_playback_validation.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


---

## Profile-aware checks

Read `discovery_profile` from `status.md` before running the checks below.

**Check: the right deck was built**
The deck's template matches the profile. A `modelling_led` release carrying the
diagnostic deck is FAIL, reason `wrong_deck_template` — it is the failure mode
this profile exists to prevent, and it produces a deck of empty analysis slides.

**Check: every substantive slide has a backing artifact**
For each content slide, the artifact it renders from exists and is
`review: approved`. A slide rendering from an unapproved artifact is FAIL, naming
both. A slide rendering from nothing is FAIL, reason `unbacked_slide`.

**Check: the sign-off checklist matches the profile**
Under `modelling_led`, the checklist has the five items in the generate spec's
table and no items from the canonical vocabulary. A maturity pin or PPT item
present under this profile is FAIL, reason `checklist_profile_mismatch`.

**Check: omissions are declared**
Every optional artifact the release did not run appears on the sign-off slide as
`not applicable` with a reason. An omitted section with no declaration is FAIL:
the sponsor must be able to see what was not produced.

**Check: roadmap precedes the playback under `modelling_led`**
`artifacts.delivery_roadmap.review` is `approved`. Under this profile the roadmap
is part of what is being signed off, so a playback built without it is FAIL,
reason `roadmap_not_ready`.

Under `diagnostic` this check is SKIP with the reason, since the ordering is
reversed there by design.

**Check: appraisal gaps are carried, not filtered**
Every entry in `current_state_appraisal.md` Section 10's first list appears on the
current-state slides. A gap present in the appraisal and absent from the deck is
FAIL, named. A deck that quietly drops what we do not know is the one output that
would make the appraisal's honesty pointless.
