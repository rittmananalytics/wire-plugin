---
description: Internal utility — tune and gate Omni AI answer quality during enablement, driving the upstream omni-ai-optimizer and omni-ai-eval skills against a real-question test set
---

# Omni AI Answer Quality

## Purpose

Omni's AI assistant answers only as well as the semantic model describes the data. This utility is the enablement-phase workflow that tunes the model's AI surface and gates the result against a set of real user questions. It operationalises Omni's own guidance (community.omni.co/t/improving-ai-answer-quality-a-practical-guide/356 and docs.omni.co/docs/ai/optimize-models, read 2026-09-06) as a repeatable Wire step.

Used by `training-generate` on engagements whose BI tool is Omni (a `bi_migration` release with `bi_pair: looker_to_omni`, or any release with `reporting_tool: omni`). Drives the upstream **omni-ai-optimizer** and **omni-ai-eval** skills from `exploreomni/omni-agent-skills` (see `wire/skills/omni/SKILL.md`); everything here is model YAML and admin surfaces those skills already cover.

## Inputs

- The Omni model (on `main`, post-cutover for a migration — never on the migration branch).
- 10 to 20 real user questions with their expected answers, gathered from the client during training scoping. Fewer than 10 is insufficient to gate on; more than 20 is fine.

## Workflow

### Step 1: Scope the topics

Review each topic the client's users will ask against. A topic should be subject-specific: focused field set, only the joins the subject needs, default filters applied, permissions set. An "everything" topic is the first cause of wrong-dataset answers; propose splits before tuning fields.

### Step 2: Tune the field surface

For every field in the scoped topics:

- **Labels** in plain language (`Number of Schedules`, not `scheduled_task_id_count_distinct`).
- **Descriptions** on every non-obvious field. Where the engagement's dbt layer carries descriptions (including Droughty-generated ones), import them through Omni's dbt integration (docs.omni.co/docs/integrations/dbt) rather than retyping.
- **`all_values`** on fields whose stored values differ from user language (`CA` vs `California`).
- **Synonyms** where users' words differ from the label, and to disambiguate similar fields.
- **`ai_context`** on the topic: what the dataset is for, the business terminology, and when it applies over neighbouring topics.

All changes are model YAML through `omni-model-builder`, validated before use.

### Step 3: Run the question set

Ask each question through Omni's AI surface (workbook query helper, or `omni-ai-eval` where installed). Classify each answer with exactly one outcome:

| Outcome | Meaning |
|---|---|
| `correct` | Right answer from the right topic and fields |
| `wrong_field` | Right topic, wrong field, filter or aggregation chosen |
| `wrong_data` | Answered from the wrong topic or dataset entirely |
| `refused` | No answer produced |

Record every question, its outcome, and (for non-correct outcomes) the observed failure in the enablement artifact's AI-quality section.

### Step 4: Apply the gate

The verdict is deterministic from the outcome counts:

1. Fewer than 10 questions asked: `INSUFFICIENT` — gather more questions; do not gate.
2. Any `wrong_data` outcome: `FAIL` — a wrong-dataset answer is silently misleading and blocks sign-off regardless of the overall rate.
3. Otherwise, `correct / total >= 0.8`: `PASS`.
4. Otherwise: `ITERATE` — return to Steps 1 and 2 for the failing questions, then re-run Step 3. There is no round limit; each round's outcomes are appended, never overwritten.

`PASS` is recorded in the enablement artifact and `status.md`. `FAIL` and `ITERATE` list the failing questions and the tuning applied in response.

### Step 5: Leave the loop running

Hand the client the maintenance habit, not just the tuned state: review Omni's AI prompt logs periodically for repeated corrections and unanswered phrasings, and fold what they show into labels, synonyms and `ai_context`. Note this in the training materials.

## Rules

1. **Never gate on invented questions.** The question set comes from the client's real usage or stakeholders; a set the consultant wrote to pass proves nothing.
2. **Classify from evidence.** An outcome is assigned from the observed answer against the expected one, never from how the answer reads.
3. **Model changes go through the model workflow** — branch, validate, merge per the engagement's rules; this utility never edits `main` directly during a migration.
