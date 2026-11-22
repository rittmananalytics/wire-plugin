---
wire_schema: "1.0"
command: generate
artifact: pitch
domain: discovery
release_types:
  - discovery_shape_up
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: problem_definition
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate a Shape Up pitch document from the approved problem definition

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Pitch Generate Command

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Generates a 10-section Shape Up pitch document from the approved problem definition. The pitch is the core planning artefact of a discovery release — it frames the problem, proposes a shaped (rough but solved) solution, defines the appetite, identifies rabbit holes to avoid, and makes the case for why this is worth betting on now.

A pitch is NOT a requirements specification. It uses fat-marker sketches and rough concepts, not pixel-perfect designs. It leaves room for implementation decisions. It is meant to be good enough to bet on — not complete enough to build from.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/problem_definition.md` — must be reviewed and approved

**Helpful**:
- `engagement/context.md` — client background, engagement objectives
- `engagement/sow.md` — budget context, appetite clues

## Workflow

### Step 1: Locate the Release and Read Problem Definition

1. Resolve release folder from `$ARGUMENTS`
2. Read `planning/problem_definition.md` — verify it exists and has been through review (check status.md)
3. If problem definition is not yet approved, output:
   ```
   Problem definition must be reviewed before generating a pitch.
   Run /wire:problem-definition-review [folder] first.
   ```

### Step 2: Determine Appetite

The appetite is the most important constraint in the pitch. It defines the time budget — and therefore shapes what solution is worth building.

Ask directly in chat:
```
What is the appetite for this release?
- Small batch (1–2 weeks): tight scope, a quick win or focused improvement
- Big batch (6 weeks): significant new capability or complex problem

Which fits? (small/big)
```

Wait for user response.

If the SOW or engagement context has a timeline, suggest that as the default.

### Step 3: Facilitate Solution Shaping

The pitch must contain a shaped solution — rough but solved. Guide the user through the key shaping decisions:

**Q1:**
```
What is the core element of the solution — the one thing that, if done, solves the problem?
(Describe it in 2–3 sentences. No need for technical specifics — sketch the idea.)
```

**Q2:**
```
What is the simplest version of this that would still solve the problem?
(The "fat marker" version — what gets cut to the bone but still works?)
```

**Q3:**
```
What are the rabbit holes — the parts that look straightforward but could take forever?
(List 2–3 specific things you want to explicitly avoid or timebox.)
```

**Q4:**
```
What are the hard no-gos — things this solution will NOT do?
(Boundaries that must not move, even if stakeholders ask for them.)
```

If source material already answers some of these, pre-populate and ask for confirmation.

### Step 4: Generate the Pitch Document

**Output location**: `.wire/releases/$ARGUMENTS/planning/pitch.md`

**Document structure**:

```markdown
# Pitch: [Engagement Name / Release Name]

**Release**: [release_folder]
**Client**: [client_name]
**Date**: [generation_date]
**Appetite**: [Small batch — 1–2 weeks | Big batch — 6 weeks]
**Version**: 1.0

---

## 1. Problem

[2–3 paragraph summary of the problem from the problem definition. Written for a decision-maker who hasn't read the full problem definition. Include who has the problem, what they can't do today, and what it costs them.]

## 2. Appetite

**[Small batch — 1–2 weeks | Big batch — 6 weeks]**

[Why this appetite is appropriate. What it means for scope. What is explicitly NOT included because of the appetite constraint.]

## 3. Solution Sketch

[2–4 paragraphs describing the shaped solution. Fat-marker level — not implementation design. Describe the key user-facing behaviour or system behaviour that solves the problem. Use simple diagrams (ASCII or Mermaid) where helpful.]

**Core interaction / key behaviour**:
[One concrete example of how the solution works for the user. A scenario or story.]

## 4. Rabbit Holes

[Specific things that look simple but could expand indefinitely. Name them explicitly so the team knows to timebox or cut them.]

- **[Rabbit hole 1]**: [Why it's dangerous and what the boundary is]
- **[Rabbit hole 2]**: [Why it's dangerous and what the boundary is]

## 5. No-gos

Things this release will NOT do:

- [Hard no-go 1]
- [Hard no-go 2]
- [Hard no-go 3]

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [risk] | High/Med/Low | High/Med/Low | [mitigation] |

## 7. Success Criteria

How we will know this release has solved the problem:

- [ ] [Measurable outcome 1 — tied directly to the problem definition]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]

## 8. Downstream Releases

[If this discovery release will spawn delivery releases, list the likely release types and names here. These will be formalised in the release brief.]

| Likely Release | Type | Rough Scope |
|----------------|------|-------------|
| [name] | [full_platform / pipeline_only / dbt_development / etc.] | [1-line description] |

## 9. Timeline

| Milestone | Target |
|-----------|--------|
| Problem definition approved | [date] |
| Pitch approved | [date] |
| Release brief signed off | [date] |
| Sprint plan confirmed | [date] |
| First delivery release start | [date] |

## 10. The Bet

[1–2 paragraphs: why this is worth betting [appetite] on now. What is the cost of NOT doing it. What opportunity or risk it addresses. This is the closing argument for the pitch — it should make the decision feel obvious.]
```

### Step 5: Update Release Status

```yaml
pitch:
  generate: "complete"
  validate: "not_started"
  review: "not_started"
  file: "planning/pitch.md"
  generated_date: [today's date]
```

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `pitch`
- `artifact_name`: `Shape Up Pitch`
- `file_path`: `.wire/releases/[release_folder]/artifacts/pitch.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 7: Confirm and Suggest Next Steps

```
## Pitch Generated

File: .wire/releases/[folder]/planning/pitch.md
Appetite: [Small batch / Big batch]

### Next Steps

1. Validate the pitch:
   /wire:pitch-validate [folder]

2. Review with stakeholders (decision-makers who will approve the bet):
   /wire:pitch-review [folder]

3. When approved, formalise as a release brief:
   /wire:release-brief-generate [folder]
```

## Output Files

- `.wire/releases/[folder]/planning/pitch.md`
- Updated `.wire/releases/[folder]/status.md`
