---
name: cowork-sales-enquiry-follow-up-email
description: >
  Drafts a follow-up email to a new sales prospect or existing client directly
  after an initial or catch-up meeting. Retrieves the meeting transcript from
  Fathom, checks Slack and Gmail for additional context, distinguishes between
  new prospects and existing clients, and produces a Gmail draft in Mark's
  natural voice ready to review and send. Use when the user says "draft a
  follow-up email", "write a follow-up to [company]", "send a follow-up after
  the meeting", or "email [prospect/client] after the call".
platform: cowork
connectors:
  required: [fathom, gmail]
  optional: [slack]
triggers:
  - "draft a follow-up email after a meeting"
  - "write a follow-up to [company/prospect name]"
  - "send a follow-up after the call"
  - "email [prospect] after the meeting"
  - "follow up on today's meeting"
---

# Sales Enquiry Follow-Up Email

Produces a Gmail draft follow-up after a first sales call or client catch-up.
Pulls the Fathom transcript for the meeting, cross-checks Slack and Gmail for
any surrounding context, then writes the email in Mark's natural voice before
saving it as a Gmail draft.

---

## Connector guard

Before proceeding, verify:
- **Fathom** is connected: call `Fathom:list_meetings` with a recent date.
  If it fails, ask the user to paste the transcript directly into the
  conversation instead.
- **Gmail** is connected: required to create the draft. If unavailable,
  output the email body in the chat so the user can copy it manually.
- **Slack** (optional): used for supplementary context only; skip gracefully
  if unavailable.

---

## Step 1 — Identify the meeting

Extract the company or prospect name from the user's request. If not given,
ask which meeting to follow up on.

Search Fathom for the most recent meeting involving that company:

```
Fathom:search_meetings
  search_term: [company or prospect name]
  limit: 5
```

Present the top results to the user if more than one match exists. Retrieve
the full transcript once the meeting is confirmed:

```
Fathom:get_meeting_transcript
  recording_id: [meeting id]
```

---

## Step 2 — Gather supplementary context

**Slack** — search the relevant client channel and any DMs for context from
the past 7 days:

```
Slack:search_public_and_private
  query: [company name]
  date_from: [7 days ago]
```

**Gmail** — search for any prior email thread with this company:

```
Gmail:search_threads
  query: [company email domain or name]
```

Use `Gmail:get_thread` on any relevant thread to read the content. Look for:
prior proposals or quotes, outstanding questions from the prospect, and any
commitments made before the call.

---

## Step 3 — Determine relationship type

From the Fathom transcript and any HubSpot or Harvest data available, determine:

- **New prospect**: first contact, no existing engagement
- **Existing client**: ongoing relationship — extension, upsell, or new sprint

This distinction changes the opening tone of the email. New prospects get a
warm introduction framing ("great to understand what you're looking to
achieve"). Existing clients get a continuity framing ("great to catch up and
build on the success we've been seeing to-date").

---

## Step 4 — Identify US/Canada locale

Check the prospect's location from the transcript, company website, or email
domain. If they are US- or Canada-based, write in US English. Otherwise use
British English throughout.

---

## Step 5 — Draft the email body

Write the email body — no subject line, no "Dear [Name]" salutation — working
through these sections in order:

**Opening** (2–3 sentences)
- New prospect: thank them for setting up the call; say it was great to meet
  them and understand more about what they're looking to achieve.
- Existing client: say it was good to catch up; frame the continued or widened
  engagement as the outcome that both sides hoped-for when the relationship
  first started, and that we'd very much like to build on the success we've
  been seeing to-date.

**Their situation** (overview paragraph + bullet list)
- One paragraph summarising their scenario as you understood it from the call.
- Bullet list: their goals and objectives for the engagement, any specific
  needs or details they shared, and the type of project engagement they
  envisaged.

**Our proposed solution** (overview paragraph + bullet list)
- One paragraph on what we'd propose at this point.
- Bullet list of components or elements. Do not mention prices, costs, or
  budget figures.

**Follow-up actions** (bullet list)
- Each action we committed to after the meeting, with the agreed-by date if
  stated on the call.

**Next meeting** (1–2 sentences)
- If a date was agreed, include it. If not, say we'll be back in contact once
  the agreed actions are completed.

**Close** (2 sentences)
- Thank them and say that if they have any questions in the meantime, just let
  you know and you can jump on a call to discuss if easier.
- Final line: "Thanks again for reaching out, and I'll be back in contact with
  the follow-ups shortly." For existing clients, swap "reaching out" for
  something appropriate to the context (e.g. "Thanks again for the time on
  [day/date]...").

---

## Voice and phrasing rules

Match Mark's natural voice. Do not produce generic consultancy or AI-flavoured
prose.

- First person for personal sentiment ("I'm glad to hear that...", "I'll come
  back to you once..."); "we" for firm-side actions ("we'd very much like to
  build on...").
- Direct address ("yourself and I", "you've got today") rather than abstract
  corporate phrasing.
- Hyphenate set phrases that function as a stable idiom: "hoped-for",
  "very-much", "to-date", "catch-up", "use-cases", "in-contact",
  "follow-up" (as noun).
- Do not hyphenate phrasal verbs: "build on", "follow up on", "step in".
- Vary bullet construction — mix gerunds, noun phrases, and verb-led items
  rather than forcing uniform parallel structure.

**Phrases to avoid — replace as shown:**

| Avoid | Use instead |
|-------|-------------|
| "It's encouraging that..." | "I'm glad to hear that..." |
| "That's exactly the foundation we hoped for..." | "This is the outcome that both yourself and I hoped-for when we first discussed this engagement..." |
| "Our proposed approach is..." | "What we'd propose at this point is..." |
| "Specifically:" as a structural marker | "In practical terms:" or omit |
| "We are delighted", "we look forward to" | Replace with a concrete observation from the actual conversation |

---

## Step 6 — Create the Gmail draft

Once the email body is written, save it as a Gmail draft:

```
Gmail:create_draft
  to: [prospect email address — ask if not found in transcript]
  subject: [derive from call context — e.g. "Following up on our call — [brief topic]"]
  body: [full email body]
```

Confirm to the user: "Draft saved to Gmail. Subject: '[subject]' — ready to
review and send."

If Gmail is unavailable, present the full email body in the chat so the user
can copy it.
