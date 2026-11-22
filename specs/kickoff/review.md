---
wire_schema: "1.0"
command: review
artifact: kickoff
domain: kickoff
release_types: []
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: kickoff
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Review kick-off deck internally and record approval for PDF export
argument-hint: "[release-folder]"

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Kickoff Deck — Review

## Purpose

Conducts an internal review of the kick-off deck before it is presented to the client. Surfaces meeting context from Fathom (if available), collects reviewer feedback, records the review outcome, and on approval instructs the consultant how to export the PDF.

## Inputs

- Engagement-level: `.wire/kickoff-deck.html`
- Release-enriched: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`

`kickoff_deck.validate` must be `complete`. If not: stop — "Run `/wire:kickoff-validate` first."

## Workflow

### Step 1: Locate the deck file

Resolve in order:
1. If `<release-folder>` supplied: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`
2. Else: `.wire/kickoff-deck.html`

Read the EDITMODE block. Extract `clientName`, `engagementType`, and `presenters` for the review header.

### Step 2: Surface meeting context (Fathom)

Attempt to retrieve Fathom meeting context via the meeting context utility (`wire/specs/utils/meeting_context.md`). Search for recent meetings related to the kickoff or scoping discussion with this client.

If Fathom is available and meetings are found, surface:
- Any client-stated priorities or expectations from scoping calls
- Any concerns or preferences about the kick-off format
- Any changes to team composition or timeline mentioned since the SoW

If Fathom is unavailable, proceed without — note this in the review header.

### Step 3: Present the review summary

Display:

```
KICKOFF DECK INTERNAL REVIEW
Client: [clientName]
Engagement type: [engagementType]
Deck: [file path]
Presenters: [names and roles]

Slide-by-slide content summary:
  Slide 01 (Title):    [clientName] — [engagementDate]
  Slide 04 (Diagnosis): [first 80 chars of slide4LeftCache or "EMPTY"]
  Slide 05 (Metric):   [slide5Number][slide5Suffix] — [slide5Bold or "EMPTY"]
  Slide 07 (Problems): [slide6Count] problems
  Slide 09 (Outcomes): [slide8Count] outcomes
  Slide 11 (Architecture): [slide10Headline or "EMPTY"]
  Slide 13 (Timeline): W1 — [slide12W1Focus or "EMPTY"] / W2 — [slide12W2Focus or "EMPTY"]
  Slide 15 (Access):   [slide14Count] categories
  Slide 16 (Team):     [presenter count] presenter(s)

[Fathom context, if available]
```

### Step 4: Collect reviewer feedback

Ask:

```
Please review the deck at [file path] in your browser, then answer:

1. Are all slides accurate and complete?
2. Are there any content changes needed before presenting?
3. Is the presenter list correct?
4. Approved to export as PDF and present?

Enter feedback, or type "approved" to record approval.
```

### Step 5: Handle feedback

**If changes are needed**:
- Record the feedback verbatim
- Set `kickoff_deck.review: "in_progress"` in status
- Instruct consultant: "Update the EDITMODE block in [file path] using the tweaks panel or by editing the JSON directly, then re-run `/wire:kickoff-validate` and `/wire:kickoff-review`."

**If approved**:
- Set `kickoff_deck.review: "complete"` in status
- Record the reviewer name and date in status

### Step 6: PDF export instructions (on approval)

```
✅ KICKOFF DECK APPROVED

To export as PDF, run one of the following:

macOS (Google Chrome):
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless \
    --print-to-pdf="kickoff.pdf" \
    --print-to-pdf-no-header \
    "file://$PWD/[deck-path]"

macOS (Chromium via Homebrew):
  /opt/homebrew/bin/chromium \
    --headless \
    --print-to-pdf="kickoff.pdf" \
    --print-to-pdf-no-header \
    "file://$PWD/[deck-path]"

Linux / CI:
  chromium --headless --no-sandbox \
    --print-to-pdf="kickoff.pdf" \
    --print-to-pdf-no-header \
    "file://$PWD/[deck-path]"

If the architecture diagram (slide 11) appears blank in the PDF, add:
  --virtual-time-budget=5000

Fallback (interactive browser):
  Open [deck-path] in Chrome → Cmd+P (Mac) or Ctrl+P (Linux/Windows)
  → Destination: Save as PDF → Layout: Landscape → Margins: None → Background graphics: ON

The PDF will be saved to the current working directory. Move it alongside the HTML:
  mv kickoff.pdf [deck-dir]/kickoff-deck.pdf
```

### Step 7: Sync to issue tracker

If Jira or Linear are configured, update the kickoff_deck sub-issue/task to "Done".

## Status transitions

| Outcome | `review` field |
|---------|---------------|
| Changes requested | `in_progress` |
| Approved | `complete` |
