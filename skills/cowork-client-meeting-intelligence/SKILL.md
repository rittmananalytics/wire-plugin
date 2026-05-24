---
name: cowork-client-meeting-intelligence
description: >
  Provides comprehensive 360-degree client intelligence by analysing Fathom
  meeting recordings (client-facing and internal), Gmail communications with
  client stakeholders, and Slack discussions in client-specific channels.
  Extracts themes, concerns, sentiment, and CEO-level insights across all
  communication channels. Use when the user asks to analyse or summarise client
  interactions, understand what's being discussed with a client, review recent
  client conversations, or identify action items from client interactions.
  Provides cross-referenced analysis of client sentiment, internal team
  concerns, and communication patterns.
platform: cowork
connectors:
  required: [fathom, gmail, slack]
  optional: []
triggers:
  - "analyse all communications with [client]"
  - "what have we been discussing with [client]?"
  - "give me the complete picture on [client]"
  - "summarise this week's [client] activity"
  - "what should I know about our [client] engagement?"
  - "are there any issues with the [client] project?"
  - "how is our communication with [client]?"
---

# Client Meeting Intelligence — Multi-Channel Edition

Provides comprehensive client intelligence by analysing multiple communication
channels for a specified client: Fathom meeting recordings (client-facing and
internal), Gmail email threads, and Slack client channels. Produces a
CEO-level intelligence report cross-referencing what the client sees externally
against what the team is discussing internally.

---

## Connector guard

Before proceeding, verify that the required connectors are reachable:
- **Fathom**: call `Fathom:list_meetings` with a recent date. If unavailable,
  proceed with Gmail and Slack only and note the gap.
- **Gmail**: call `Gmail:search_threads` with a test query. If unavailable,
  proceed with Fathom and Slack only.
- **Slack**: call `Slack:search_channels` with a test query. If unavailable,
  proceed with Fathom and Gmail only.

Note which sources are unavailable in the report header.

---

## Step 1 — Identify the client

Extract the client name from the user's request. If unclear, ask for
clarification. Derive:

| Variable | Derivation |
|----------|-----------|
| `CLIENT_NAME` | As stated by user (e.g. "Hunkemoller") |
| `CLIENT_DOMAIN` | Primary email domain (e.g. "hunkemoller.com") — infer or ask |
| `SLACK_SLUG` | Lowercase hyphenated (e.g. "hunkemoller" or "hkm") — used for `#clients-{slug}` and `#clients-{slug}-internal` |

---

## Step 2 — Calculate the time range

Use today's actual date (available from the system context or `date` command).
Count back 5 working days from today, excluding weekends. Do not hardcode any
date — always calculate from the current date at runtime.

---

## Step 3 — Retrieve client-facing meetings (Fathom)

```
Fathom:list_meetings
  created_after: [5 working days ago — ISO 8601]
  calendar_invitees_domains: [CLIENT_DOMAIN]
  limit: 50
```

For each meeting found, retrieve the full transcript:

```
Fathom:get_meeting_transcript
  recording_id: [id]
```

---

## Step 4 — Retrieve internal team meetings (Fathom)

```
Fathom:list_meetings
  created_after: [5 working days ago]
  meeting_type: "internal"
  limit: 50
```

Filter to meetings likely to contain client discussion:
- Titles containing: "Start the Week", "Start of the Week", the client name,
  or the client abbreviation
- Common patterns: "Delivery Team Meet", "[Client] Project Review",
  "[Client] Internal Demo"

Retrieve transcripts for matches and scan for substantial discussion of the
client — exclude meetings where the client is only briefly mentioned.

---

## Step 5 — Retrieve Gmail communications

Search for email threads involving the client domain over the past 5 working
days:

```
Gmail:search_threads
  query: "from:@[CLIENT_DOMAIN] OR to:@[CLIENT_DOMAIN] after:[date 5 working days ago in YYYY/MM/DD format]"
```

For each thread returned, read the full content:

```
Gmail:get_thread
  id: [thread id]
```

Include threads containing: strategic discussions or decisions, client
concerns or escalations, requests for changes, budget or timeline discussions,
feedback on deliverables, new stakeholder introductions.

Exclude: calendar invites, brief acknowledgements ("Thanks", "Got it"),
pure logistics, auto-generated notifications.

Categorise as: Client→Team, Team→Client, or Internal-about-client.

---

## Step 6 — Retrieve Slack channel discussions

Find the client channels:

```
Slack:search_channels
  query: [SLACK_SLUG]
```

Read the external client channel (what the client sees):

```
Slack:read_channel
  channel_id: [clients-{slug} channel id]
  oldest: [Unix timestamp 5 working days ago]
  limit: 100
```

Read the internal client channel (what the team says privately):

```
Slack:read_channel
  channel_id: [clients-{slug}-internal channel id]
  oldest: [same timestamp]
  limit: 100
```

For significant threaded discussions, use `Slack:read_thread` to get the full
conversation context.

---

## Step 7 — Analyse multi-channel intelligence

Analyse the collected data from all sources. Maintain a strict separation
between the external view (what the client sees) and the internal view (what
the team says privately), then cross-reference.

**Client-facing analysis** (meetings + Gmail to/from client + external Slack):
- Discussion themes grouped by topic
- Key client stakeholders and their individual sentiments
- Overall client sentiment: Positive / Neutral / Concerned / Critical
- Urgency level: Low / Medium / High / Critical
- Communication pattern observations (which channels they use for what)
- Response time analysis (how quickly does the team respond per channel)

**Internal team analysis** (internal meetings + Gmail internal + internal Slack):
- What the team is discussing privately about this engagement
- Delivery challenges, resource constraints, technical blockers
- Team sentiment and confidence level
- Information that is known internally but not communicated to the client

**Cross-referenced insights**:
- Where client perception and internal reality diverge
- Commitments made in meetings not followed up in writing
- Issues escalating from Slack → email → meetings
- Documentation gaps

---

## Step 8 — Produce the report

```markdown
# CLIENT INTELLIGENCE REPORT: [Client Name] — MULTI-CHANNEL ANALYSIS

**Analysis period**: [Start date] – [End date] (5 working days)
**Report generated**: [Today's date]
**Data sources**:
- Fathom: [N] client-facing meetings, [N] internal meetings
- Gmail: [N] significant threads
- Slack: #clients-[slug] (external) + #clients-[slug]-internal

---

## EXECUTIVE SUMMARY

**External (client) reality**: [2–3 sentences on what the client is
experiencing and communicating across all channels]

**Internal (team) reality**: [2–3 sentences on what the team is saying
privately — delivery challenges, confidence level, concerns]

**Communication health**: [1–2 sentences on response times, channel usage,
and any documentation gaps]

---

## CLIENT-FACING ANALYSIS

### Discussion themes
[Each theme as a section: what was discussed across meetings, email, and Slack;
how the topic evolved; what it signals]

### Key stakeholders
[Each named client stakeholder: concerns, communication style, sentiment,
decision-making authority]

### Sentiment analysis
**Overall**: [Positive/Neutral/Concerned/Critical]
**Trajectory**: [Improving/Stable/Deteriorating]
[Positive signals and warning signs per channel]

---

## INTERNAL TEAM ANALYSIS

### Internal discussion themes
[What the team is discussing privately, per channel]

### Internal sentiment
**Team confidence**: [High/Medium/Low/Critical]
[Strengths, challenges, and channel-specific observations]

---

## CROSS-REFERENCED INSIGHTS

| Topic | What client sees | What's really happening | Gap |
|-------|-----------------|------------------------|-----|
| [Topic] | [External view] | [Internal view] | [Analysis] |

---

## ACTION ITEMS

### Immediate
[Numbered list: issue, evidence, action, owner, urgency]

### Monitor
[Items requiring ongoing attention]

### Strategic
[Longer-term relationship or delivery interventions]

---

## COMMUNICATION INVENTORY

### Client-facing meetings ([N])
| Date | Title | Client attendees | Key topics |
|------|-------|-----------------|-----------|

### Internal meetings discussing client ([N])
| Date | Title | Key discussion points |
|------|-------|----------------------|

### Significant email threads ([N])
| Date | Direction | Subject | Summary |
|------|-----------|---------|---------|

### Slack summary
**#clients-[slug]**: [N] messages, [N] from client, [N] from team
**#clients-[slug]-internal**: [N] messages, key topics: [list]

---

## CEO PERSPECTIVE

[3–5 sentences synthesising all channels into a clear assessment: relationship
health, what requires the CEO's attention, and specific recommended actions.
Write as a practitioner, not a narrator — name the actual person, the actual
issue, the actual channel where it surfaced.]
```

---

## Error handling

| Error | Action |
|-------|--------|
| No client-facing meetings found | Check domain spelling; note in report and continue |
| Slack channel not found | Try abbreviation variants; skip gracefully if none found |
| Gmail returns no results | Note in report; check date format and domain spelling |
| Transcript unavailable for a meeting | Note which meetings lack transcripts; analyse available ones |
| Internal meeting has no client discussion | Filter it out |

---

## Confidentiality note

The internal analysis — internal meeting transcripts, internal Slack channel
content, internal email threads — is strictly for CEO/leadership use only.
Do not share the full report with client stakeholders.
