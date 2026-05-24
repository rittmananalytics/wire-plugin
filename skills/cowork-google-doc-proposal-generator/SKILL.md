---
name: cowork-google-doc-proposal-generator
description: >
  Generates a populated Google Doc SOW or proposal from a template by
  combining an uploaded PDF proposal and a Fathom meeting transcript.
  Extracts client details, scope, deliverables, timeline, and agreed actions
  from both sources, maps them to the template placeholders, and creates the
  document directly in Google Drive. Use when the user says "generate the SOW",
  "create a proposal doc from the meeting", "populate the SOW template",
  "draft the statement of work", or "create the engagement doc".
platform: cowork
connectors:
  required: [google-drive]
  optional: [fathom]
triggers:
  - "generate the SOW from the meeting"
  - "create a proposal doc"
  - "populate the SOW template"
  - "draft the statement of work after the call"
  - "create the engagement document from the proposal and transcript"
---

# Google Doc Proposal Generator

Produces a populated Google Doc SOW or proposal by reading an uploaded PDF
proposal and a Fathom meeting transcript, extracting structured data from both,
and writing it into a Google Drive template using placeholder replacement.

---

## Connector guard

Before proceeding, verify:
- **Google Drive** is connected: required to read the template and create the
  output document. Call `GoogleDrive:list_recent_files` to confirm. If
  unavailable, stop and ask the user to connect Google Drive in
  Settings → Connectors.
- **Fathom** (optional): used to pull the meeting transcript automatically.
  If unavailable, ask the user to paste the transcript into the conversation.

---

## Step 1 — Gather inputs

### PDF proposal

If the user has attached a PDF, read it directly — Claude can parse PDF content
natively from uploaded files. Extract:

- Client name, contact name, company
- Project name and scope summary
- Deliverables and milestones
- Budget or fee (if present)
- Timeline and key dates
- Payment terms and conditions

If no PDF is provided, ask the user to attach it or paste the relevant sections.

### Meeting transcript

If a Fathom meeting is available, search for the most recent meeting with this
client:

```
Fathom:search_meetings
  search_term: [client name]
  limit: 3
```

Retrieve the transcript once identified:

```
Fathom:get_meeting_transcript
  recording_id: [meeting id]
```

If Fathom is unavailable or the user prefers, accept the transcript pasted
directly into the conversation.

From the transcript extract:
- Confirmed scope changes or additions discussed on the call
- Budget figures mentioned or agreed
- Timeline confirmations or modifications
- Action items and owners
- Next meeting date (if set)
- Any concerns or objections raised and how they were addressed

---

## Step 2 — Load the template

Retrieve the SOW template from Google Drive. The default template is the
Rittman Analytics SOW template — search for it:

```
GoogleDrive:search_files
  query: "Rittman Analytics SOW template"
```

If a custom template is specified by the user, use that instead. Read the
template content:

```
GoogleDrive:read_file_content
  file_id: [template file id]
```

Identify all `{{placeholder}}` fields in the template. Common placeholders:

| Placeholder | Source |
|-------------|--------|
| `{{client_name}}` | PDF / transcript |
| `{{contact_name}}` | PDF / transcript |
| `{{project_name}}` | PDF / transcript |
| `{{project_scope}}` | PDF, refined by transcript |
| `{{deliverables}}` | PDF, refined by transcript |
| `{{timeline}}` | PDF, confirmed in transcript |
| `{{budget}}` | PDF, confirmed in transcript |
| `{{payment_terms}}` | PDF |
| `{{milestones}}` | PDF / transcript |
| `{{next_steps}}` | Transcript |
| `{{agreed_actions}}` | Transcript |
| `{{effective_date}}` | Today's date unless specified |

---

## Step 3 — Merge proposal and transcript data

Combine data from both sources, giving priority to values confirmed in the
transcript over those in the original proposal (the call may have modified
scope, timeline, or budget).

For each placeholder, record:
- **Value**: the content to insert
- **Source**: "PDF", "transcript", or "PDF (confirmed in transcript)"
- **Confidence**: whether the value is explicit or inferred

Flag any placeholder for which no value can be found — these will need manual
completion. Do not leave `{{placeholder}}` strings in the output document;
replace unfilled fields with `[TO COMPLETE: field name]`.

---

## Step 4 — Create the output document

Create a new Google Doc in Drive with the populated content:

```
GoogleDrive:create_file
  name: "[Client Name] — Statement of Work — [Today's date]"
  content: [populated template text]
  parent_folder: [ask user for destination folder, or use Drive root]
  mime_type: "application/vnd.google-apps.document"
```

If `create_file` is not available, copy the template and update the content:

```
GoogleDrive:copy_file
  file_id: [template file id]
  name: "[Client Name] — Statement of Work — [Today's date]"
```

Then update the copied document with the merged content.

---

## Step 5 — Quality check and report

Before presenting the output, verify:
- All required placeholders have been filled or explicitly flagged
- No `{{placeholder}}` strings remain in the document
- Client name, dates, and budget figures are consistent throughout
- Deliverables listed match what was confirmed in the transcript

Present a summary to the user:

```markdown
## SOW Generated

**Document**: [Google Drive link]
**Client**: [Client name]
**Created**: [Today's date]

### Fields populated ([N] of [total])
[List of filled fields with source]

### Fields requiring manual completion ([N])
[List of unfilled fields with notes on what to add]

### Key data from transcript that refined the proposal
[2–3 bullet points noting where transcript data changed or confirmed the PDF]
```

Share the Google Drive link so the user can open and review the document
directly.

---

## Template variants supported

- Statement of Work (SOW) — default
- Master Service Agreement (MSA)
- Project Charter
- Proposal Response

If the user specifies a variant, search Drive for the corresponding template
using `GoogleDrive:search_files` with the variant name.

---

## Error handling

**Missing required fields**: flag clearly in the output summary rather than
silently omitting — the user can complete them before sending.

**Unreadable PDF**: if Claude cannot parse the PDF natively, ask the user to
paste the key sections (scope, deliverables, budget, timeline) as text.

**Template not found in Drive**: ask the user to share the template link
directly, then use `GoogleDrive:get_file_metadata` to retrieve the file ID.

**Drive creation fails**: produce a formatted DOCX via the `docx` skill as
a fallback, and present it for download.
