---
sidebar_position: 5
title: "Running Discovery"
---

# Running Discovery

Every Friday afternoon the billing administrator at Thornfield Private Healthcare sits down with two screens open, Stripe on one and Cliniko on the other, and reconciles the week's charges against the week's invoices by hand. About a third of the time the customer ID on the Stripe side matches nothing on the Cliniko side and she has to work out who the patient was from the amount and the date. Nobody has ever agreed what counts as a write-off as opposed to a pending reconciliation, so she made up a definition two years ago and has used it ever since. Meanwhile the Clinical Operations Director is being asked by the board for patient volume and revenue figures she cannot produce with any confidence, and she knows that two earlier attempts to build a reporting platform foundered on the question of patient identifiers before they produced anything.

This is what the start of most discovery engagements looks like: several systems that do not talk to each other, a handful of people each carrying part of the picture in their heads, a constraint everybody knows about but nobody has written down, and a sponsor who needs a diagnosis she can defend before she commits to a build. Wouldn't it be better if the interviews, the diagnosis and the roadmap were all produced to one method, so that every finding could be traced back to the words of the person who said it, and so that the sponsor's sign-off was a matter of record rather than of memory?

A "discovery" release is how Wire does that. It follows Rittman Analytics' standard discovery method and produces no code at all: what it produces is an agreed picture of where the client is, an analysis of why and a roadmap for getting somewhere better that the sponsor has signed off on a live call. It has two routes, and Wire asks you which at setup. The "diagnostic" route produces three analyses of the client's situation and ends with a findings playback that the sponsor signs off. The "modelling-led" route replaces the analyses with an appraisal of the current platform and an enterprise data model that the sponsor signs off instead, and it suits a client who already knows what is wrong and wants the target designed. Thornfield takes the diagnostic route.

In this chapter we will follow the discovery across ten days, from the engagement brief through seven stakeholder interviews to the requirements matrix, the three analyses, the playback and the roadmap, and we will finish by setting up the build release that the roadmap scopes. We will pay particular attention to the two places where Wire is working from recordings rather than documents, and to the one gate in the whole release that neither you nor Wire can open. Let's start with what you need before you begin.

## Before You Begin

You will need the signed statement of work in the `docs` folder of a new repository, and you will need the client's briefing call to have been recorded, since Wire reads it alongside the statement of work when it drafts the brief. You will need to know who the sponsor is (at Thornfield, the Clinical Operations Director, Rebecca Forsyth), and you will need to be able to record each stakeholder interview as you conduct it, because Wire writes the interviews up from the recordings. The one constraint known before the work starts, that no patient identifiers (NHS number, full name or date of birth) may appear in any analytics layer, should be in the statement of work.

At a high level, the release runs through seven stages:

1. Draft and approve the engagement brief.
2. Map the stakeholders and book the interviews.
3. Conduct the interviews and have Wire write them up.
4. Consolidate the write-ups into a requirements matrix.
5. Produce the three analyses.
6. Present the findings playback and record the sponsor's confirmations.
7. Produce the roadmap and set up Release 1.

Let's now take a look at each of these in turn.

## Stage 1: The Brief

| You say | Wire replies |
|---|---|
| "New engagement for Thornfield Private Healthcare, a discovery. Statement of work in the docs folder. The briefing call with the sponsor was recorded on Tuesday. Stop at every decision." | "This reads as a discovery release. It has two routes: diagnostic (three analyses, then a findings playback, then the roadmap) or modelling-led (a current-state appraisal and an enterprise data model, with the roadmap signed off at the playback). The statement of work describes the analyses and the playback, so I propose diagnostic. Client: Thornfield Private Healthcare. Release: Discovery. Which email domain do the client's people use?" |
| "thornfieldhealth.co.uk. Diagnostic. Confirm." | "Engagement set up. Drafting the engagement brief from the statement of work and Tuesday's recording.<br/><br/>Ran: `/wire:new`. Running: `/wire:engagement-brief-generate 01-discovery`" |
| *(later)* | "Engagement brief drafted: objectives, the six named stakeholders, the three systems and one known constraint recorded from the statement of work and confirmed in the recording: no patient identifiers in the analytics layer. Rebecca Forsyth said on the call that this is 'non-negotiable, and it has stopped two previous attempts'. All checks pass. Approve now, changes or park?<br/><br/>Ran: `/wire:engagement-brief-generate 01-discovery`, `/wire:engagement-brief-validate 01-discovery`" |
| "Approve." | "Approved. Drafting the stakeholder map.<br/><br/>Ran: `/wire:engagement-brief-review 01-discovery`. Running: `/wire:stakeholder-map-generate 01-discovery`" |

Wire read the recording as well as the statement of work, and the constraint it recorded carries the sponsor's own words, which is worth far more in a later argument than a paraphrase.

## Stage 2: The Stakeholders

| You say | Wire replies |
|---|---|
| *(later)* | "Stakeholder map drafted: six people, each with role, what they care about, priority for interviewing and who books the interview. I have added a seventh: the recording mentions a practice manager at the Bath clinic who owns the appointment data, and nobody else does. Approve now, changes or park?<br/><br/>Ran: `/wire:stakeholder-map-generate 01-discovery`, `/wire:stakeholder-map-validate 01-discovery`" |
| "Keep the seventh. Approve. I'll book the interviews for next week." | "Approved. Seven interviews to write up once they have happened. Nothing else can start until then.<br/><br/>Ran: `/wire:stakeholder-map-review 01-discovery`" |

The seventh stakeholder is a small example of something you will come to rely on. Wire found a person the statement of work had missed, because the recording mentioned her, and it proposed adding her rather than either ignoring her or quietly adding her itself. As a rule, anything Wire is not sure about becomes a proposal to you, and anything it is sure about it does and tells you.

## Stage 3: The Interviews

You conduct the interviews yourself, over three days, and record each one; Wire's part is the write-up. Every point in a write-up is tagged four ways, which is the discipline that makes the later analyses possible: which area of the business it belongs to; what kind of point it is (a pain, a requirement, a measure, a risk or something that already exists); which rung of the analytics ladder it sits on, from collecting data at the bottom to predicting with it at the top; and whether the underlying cause is people, process or technology. Where Wire is unsure of a tag it marks it with a question mark for you to confirm rather than guessing, because a guessed tag is a guessed diagnosis.

| You say | Wire replies |
|---|---|
| "Write up Mark Whitfield's interview from Monday's recording. He's the billing administrator." | "Write-up done: six points, each tagged four ways. Two to show you. Billing, a pain, at the cleaning rung, a process cause: 'I reconcile Stripe charges against Cliniko invoices by hand every Friday, and about a third of the time the customer ID doesn't match anything on the Cliniko side.' Billing, a measure, at the defining rung, a people cause: 'Nobody has agreed what counts as a write-off versus a pending reconciliation. I made up my own definition two years ago and nobody's corrected me.' No uncertain tags.<br/><br/>Ran: `/wire:stakeholder-interview-generate 01-discovery`" |
| "Now Susan Idowu, IT manager, Monday afternoon's recording." | "Write-up done: five points. The constraint from the brief comes up again, in her words: 'Cliniko and HubSpot both hold NHS number and full name. If any of that ends up in a dashboard, that's a breach, full stop.' Tagged as governance, a risk, cleaning rung, process cause. No uncertain tags.<br/><br/>Ran: `/wire:stakeholder-interview-generate 01-discovery`" |
| *(the remaining five, over three days)* | *(a write-up each)* |
| "That's all seven. Check them." | "Checked all seven write-ups. 33 points in total. One problem: Daniel Osei's third point has no rung on the analytics ladder. One uncertain tag: Priya Chandra's second point is marked process with a question mark. Coverage: every person on the stakeholder map has a write-up. The check fails until the missing tag is fixed.<br/><br/>Ran: `/wire:stakeholder-interview-validate 01-discovery` (fail)" |
| "Daniel's third point is the cleaning rung, appointment records get corrected after the fact. Priya's is process, confirmed." | "Both fixed. Checked again: 33 of 33 points fully tagged, coverage complete. Pass. Each write-up now needs an internal review, yours, not the client's. Approve all seven, or go through them one at a time?<br/><br/>Ran: `/wire:stakeholder-interview-validate 01-discovery`" |
| "I've read them. Approve all seven." | "All seven approved under your name. The requirements matrix is released.<br/><br/>Ran: `/wire:stakeholder-interview-review 01-discovery`" |

:::note
The check will not pass with a tag missing, and this is deliberate rather than pedantic. The three analyses in Stage 5 are built by counting points by rung and by cause, so a single untagged point is a point that silently drops out of the diagnosis. Fix the tags as you go and the check becomes a formality.
:::

## Stage 4: The Requirements Matrix

| You say | Wire replies |
|---|---|
| "Build the requirements matrix." | "Requirements matrix drafted: 11 requirements, consolidated from 33 tagged points across seven people. Where two people said the same thing it is one row with both sources. Every row cites the words it came from. Every row has a priority (must, should, could, will not) and a phase. Six business areas are covered. All checks pass. Approve now, changes or park?<br/><br/>Ran: `/wire:requirements-matrix-generate 01-discovery`, `/wire:requirements-matrix-validate 01-discovery`" |
| "Approve." | "Approved. Producing the three analyses from the tagged points.<br/><br/>Ran: `/wire:requirements-matrix-review 01-discovery`. Running: `/wire:discovery-analyses-generate 01-discovery`" |

Every row in the matrix traces back to a quotation from a named person, so that when a requirement is challenged in the playback, as one usually is, the answer is not "we felt that" but "your billing administrator said this, on Monday, and here are her words".

## Stage 5: The Three Analyses

So what does the diagnosis actually consist of? Three analyses, each derived from the tags on the 33 points, and each answering a different question the sponsor will ask.

| You say | Wire replies |
|---|---|
| *(later)* | "Three analyses done. **Where the needs sit:** 21 of 33 points are at the two lowest rungs of the ladder, collecting and cleaning; nobody is asking for prediction yet. **People, process, technology:** the binding cause is process in 19 of 33 points; the technology is adequate. **Maturity:** Thornfield is pinned at the first stage, where numbers are assembled by hand and disputed. The analyses carry a vision statement and the initiatives that would move them. All checks pass. Approve now, changes or park?<br/><br/>Ran: `/wire:discovery-analyses-generate 01-discovery`, `/wire:discovery-analyses-validate 01-discovery`" |
| "Approve." | "Approved. Drafting the findings playback deck for the sponsor.<br/><br/>Ran: `/wire:discovery-analyses-review 01-discovery`. Running: `/wire:findings-playback-generate 01-discovery`" |

The first analysis tells the sponsor where on the analytics ladder her organisation's needs actually sit, which at Thornfield is firmly on the bottom two rungs, and therefore what kind of work will help (it is not, yet, machine learning). The second tells her whether the binding constraint is people, process or technology, and here it is process, which means that buying a new tool would not fix it. The third pins the organisation to a stage on a maturity curve, in language a board understands. Together they are the "why" behind the roadmap, and the sponsor will be asked to agree each of them on the record.

## Stage 6: The Playback, and the Gate Only the Sponsor Can Open

| You say | Wire replies |
|---|---|
| *(later)* | "Findings playback deck drafted: 38 slides. It opens with the scope and the method, presents the three analyses and states the vision: 'Thornfield will have one trusted number for patient volume and revenue, refreshed daily, with pseudonymised identifiers end to end, replacing two days of manual reconciliation with a dashboard the board can query directly.' All structural checks pass: slide count in range, every required section present, vision statement complete. Approve the deck for presenting now, or changes?<br/><br/>Ran: `/wire:findings-playback-generate 01-discovery`, `/wire:findings-playback-validate 01-discovery`" |
| "Approve. The playback is Thursday at two, with Rebecca." | "Approved. The playback itself is the sponsor's gate. After the session, tell me it has happened and I will read the recording and check the seven things she has to confirm." |

You present the deck to Rebecca Forsyth on Thursday, and the session is recorded. This is the most important gate in the whole release, and it is unlike every other gate you have seen so far, because it is not opened by your approval or by Wire's checks. It is opened by seven specific things the sponsor has to say, on the call, in her own words.

| You say | Wire replies |
|---|---|
| "Playback done. Rebecca was happy. Check the recording." | "Read the recording (52 minutes). Sponsor checklist, seven items, all confirmed on the call, each with her words: the maturity stage agreed ('It's not comfortable to hear, but yes, that's where we are'); the needs analysis agreed; the people, process, technology diagnosis agreed; the vision statement endorsed; the initiatives confirmed; a preferred delivery option named: Build ('We don't have anyone in-house who could pair on this. Build it, and make sure we can maintain it after'); no open conflicts. The playback is recorded as approved by Rebecca Forsyth, and the notes of the call are written up with all seven answers.<br/><br/>Ran: `/wire:findings-playback-review 01-discovery`" |

:::note
If any of the seven items had not been confirmed on the call, the playback would have stayed at "presented" rather than "approved", Wire would have told you which items were missing, and nothing downstream would have moved until a follow-up session with the sponsor had closed them. A sponsor who was "happy" but did not name a delivery option has not signed off, however the meeting felt at the time.
:::

## Stage 7: The Roadmap and Release 1

| You say | Wire replies |
|---|---|
| "Roadmap." | "Delivery roadmap drafted. Three delivery options side by side: Build (Rittman Analytics delivers everything), Pair (a client engineer pairs three to four days a week), Coach (the client's team delivers, with architecture and weekly coaching). Build is headlined, as Rebecca chose. Release 1 scope is the two must-have, phase-one rows: a single patient identity across Cliniko and Stripe, and pseudonymised ingestion that meets the constraint. Discovery exit checklist: ten of ten complete. All checks pass. Approve now, changes or park for the sponsor?<br/><br/>Ran: `/wire:delivery-roadmap-generate 01-discovery`, `/wire:delivery-roadmap-validate 01-discovery`" |
| "Park it. Rebecca signs it off Monday." | "Parked, waiting on Rebecca Forsyth.<br/><br/>Ran: `/wire:delivery-roadmap-review 01-discovery` (parked)" |
| *(Monday, open a session)* | "One decision is waiting: the delivery roadmap, parked for Rebecca Forsyth.<br/><br/>Ran: `/wire:start`" |
| "Signed off, Build confirmed. Set up Release 1." | "Roadmap approved under her name. Release 1 set up as a full platform build, named Thornfield Foundation Platform, in the same engagement, with its scope taken from the roadmap and a link back to this discovery. It is ready to start. The discovery is complete.<br/><br/>Ran: `/wire:delivery-roadmap-review 01-discovery`, `/wire:release-spawn 01-discovery`" |

The roadmap always presents the three ways Rittman Analytics can deliver the build, since the sponsor's choice between them is one of the seven things she confirms at the playback, and it scopes the first release from the must-have, phase-one rows of the matrix rather than from everything that was asked for. Setting up Release 1 from the roadmap carries that scope across, together with a link back to the discovery, so that when the build starts in a month's time the requirements it works from are the ones the sponsor signed.

## What You Should Now Have

| Produced | Detail |
|---|---|
| Engagement brief | Objectives, six then seven stakeholders, three systems, the identifier constraint on record in the sponsor's words |
| Stakeholder map | Seven people with role, priority and interview owner |
| Interview write-ups | Seven, 33 points, every point tagged four ways, checked and reviewed |
| Requirements matrix | 11 requirements, each traced to the words it came from, prioritised and phased |
| Three analyses | Where the needs sit, the binding cause, the maturity stage, with a vision statement |
| Findings playback | 38 slides, presented live; seven sponsor confirmations on record with quotations |
| Delivery roadmap | Build, Pair and Coach compared; Build chosen; Release 1 scoped |
| Release 1 | A full platform build, set up and linked to the discovery |

## What If Something Goes Wrong?

Two things go wrong on discoveries more often than anything else. The first is an interview that was not recorded, or whose recording is unusable, and here Wire will scaffold a blank write-up for you to complete from your notes, with the four-tag discipline still applied; the check treats it exactly like any other write-up. The second is a playback at which the sponsor agrees with everything except one item, most often the choice of delivery option, and here the release simply waits: Wire names the missing item, you book a short follow-up with the sponsor, and once she has confirmed it on a recorded call the gate opens as it would have on the day.

In the next chapter we stop and look underneath the three releases we have run so far, at the orchestration agent that was reading your messages, the lane agents that were doing the work and the commands they were running.
