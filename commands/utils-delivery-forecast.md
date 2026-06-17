---
description: Calculate % delivered and ETA per release using checklist, Jira, Harvest and Fathom velocity, compared against contractual dates
argument-hint: <client-name> [--release <folder>]
---

# Calculate % delivered and ETA per release using checklist, Jira, Harvest and Fathom velocity, compared against contractual dates

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Calculate % delivered and ETA per release using checklist, Jira, Harvest, and Fathom velocity data, compared against contractual dates from HubSpot or the SOW
argument-hint: <client-name> [--release <release-folder>]
---

# Delivery Forecast Utility

## Purpose

Produce a per-release delivery forecast for an in-flight engagement: what percentage of scope has been delivered, how fast the team is moving, when each release is likely to complete at current velocity, and whether that ETA is ahead of or behind the contractual date.

This utility is called automatically by `/wire:adopt` (Phase 3) and can be invoked standalone for any active Wire engagement. It degrades gracefully — a useful forecast is produced even when only one or two data sources are available.

## Usage

```bash
/wire:utils-delivery-forecast <client-name>              # all releases for client
/wire:utils-delivery-forecast <client-name> --release 02 # single release
```

Can also be called internally by `/wire:adopt` or the `client-delivery-status-report` skill, which pass pre-fetched source data rather than re-querying.

## Prerequisites

- A `.wire/releases/` folder with at least one `status.md` file, **or**
- A `ClientContext` object passed from `utils/client_context` (when called from another command)
- At least one of: Jira, Harvest, or Fathom accessible. All are optional — the checklist alone is sufficient for a low-confidence forecast.

---

## Inputs

When called internally (from `/wire:adopt` or the delivery status skill), the following are passed in rather than re-fetched:

```
ForecastInput {
  client_name: string
  today: ISO-8601 date
  releases: [                         # from repo scan (Agent E in adopt)
    {
      release_id: string              # e.g. "02"
      release_folder: string          # e.g. "02-customer-resolution"
      release_name: string
      release_type: string
      status_md_path: string
      status_md_content: string       # raw content of status.md
      brief_md_content: string | null
      start_date: date | null
    }
  ]
  client_context: ClientContext | null   # from utils/client_context if already fetched
}
```

When called standalone, the utility reads `.wire/` directly and calls `utils/client_context` for external source data.

---

## Workflow

### Step 1: Read Release Status Files

For each release in `.wire/releases/`:

**1a. Checklist completion** — parse the `status.md` Deliverables section:
- Count items marked `[x]` as **done**
- Count items marked `[ ]` as **remaining**
- Separate Must-Have and Nice-to-Have (treat Nice-to-Have at half weight in the denominator)
- Record: `checklist_done`, `checklist_remaining`, `checklist_pct` (integer 0–100)

**1b. Session count** — count rows in the Session History table. Zero sessions = engagement not yet active for this release.

**1c. Blocker list** — extract all open blockers from the Blockers & Risks table (status = "Open" or "In Progress").

**1d. Wire status** — read the YAML frontmatter `status` field: `not_started`, `draft`, `active`, `completed`, `blocked`.

**1e. Contractual date — in-repo sources** — search for date patterns in:
  - `brief.md`: lines containing "end date", "due", "by", "complete by", "target", "deadline", "close"
  - `status.md` YAML: any field named `target_date`, `close_date`, `due_date`, `expected_end`
  - `engagement/context.md`: same patterns

Store as `contractual_date_local` with source label.

---

### Step 2: External Source Data

If `ClientContext` was passed in, use its data directly (skip re-querying). Otherwise query each source.

#### 2a. HubSpot — Contractual Date

From the HubSpot deal:
- `close_date`: the deal close date. **This is the primary contractual date signal** — it represents the agreed delivery date as recorded in CRM.
- `deal_stage`: if "Closed Won" or "Closed Lost", the deal is complete commercially; delivery may still be ongoing.
- `deal_value`: used to contextualise scope (a £200k deal has different expectations than a £20k one).

If multiple deals exist for the client, use the most recently modified active deal. Store `contractual_date_hubspot`.

**Contractual date priority**: HubSpot `close_date` > local brief.md date > engagement/context.md date > null.

#### 2b. Harvest — Burn Rate

For each release, attempt to match to a Harvest task or project:
- Match Harvest task names to release names (fuzzy: "Customer Resolution" matches release `02-customer-resolution`)
- If no task-level match, use project-level totals

For the matched Harvest data:
- `budget_hours`: total budgeted hours for this phase
- `logged_hours`: total hours logged to date
- `harvest_pct`: `min(100, round(logged_hours / budget_hours * 100))` (cap at 100 if over-budget, but flag overrun separately)
- `last_entry_date`: date of most recent time entry
- `hours_per_week`: `logged_hours / weeks_elapsed` where `weeks_elapsed = (today - first_entry_date).days / 7`
- `estimated_hours_remaining`: `max(0, budget_hours - logged_hours)`

If Harvest unavailable or no match: `harvest_data: null`.

#### 2c. Jira — Issue Completion

For each release, look for Jira issues with:
- Epic label or summary matching the release name
- Or filter by label: `release-[release_id]` or `sprint-[N]`

Count issues by status category:
- `jira_done`: count of issues in "Done" category
- `jira_open`: count of issues in "To Do" + "In Progress"
- `jira_total`: `jira_done + jira_open`
- `jira_pct`: `round(jira_done / jira_total * 100)` if total > 0

If Jira unavailable or no issues found for this release: `jira_data: null`.

#### 2d. Fathom — Sprint Velocity

Parse sprint velocity from Fathom call summaries (sprint changeover / sprint planning calls):

For each sprint changeover call found:
- Extract: sprint number, points committed, points delivered
- Calculate `velocity`: points delivered per sprint
- Record sprint length in days (look for "2-week sprint", "1-week", "3-week" in summaries)

Compute:
- `sprint_length_days`: from call summaries (default 14 if not stated)
- `velocity_history`: list of `{sprint_number, points_delivered}` for last 3 sprints
- `avg_velocity`: mean of last 3 sprints (or last 1–2 if fewer available)
- `last_sprint_velocity`: most recent sprint's delivered points
- `velocity_trend`: `"improving"` if last > avg, `"declining"` if last < avg × 0.8, else `"stable"`

If no sprint data found in Fathom: `velocity_data: null`.

**Finding remaining story points**: Search status.md and Jira for story point estimates on open items. If none found, estimate from open deliverable count × average points per deliverable (default: 3 points per deliverable item).

---

### Step 3: Calculate % Delivered per Release

Combine available data sources using weighted averaging:

| Source | Weight | Used when |
|--------|--------|-----------|
| Checklist | 0.40 | Always (if status.md has deliverables) |
| Jira issues | 0.35 | Jira data available and ≥5 issues found |
| Harvest hours | 0.25 | Harvest data available for this release |

If a source is unavailable, redistribute its weight proportionally across available sources.

**Special cases:**
- If `status_md.status == "completed"`: set `pct_delivered = 100`, skip calculation.
- If `checklist_done == 0` and `session_count == 0`: set `pct_delivered = 0` (not yet started).
- If Harvest shows `logged_hours > budget_hours`: flag overrun separately; cap harvest_pct at 100 for the composite.
- If checklist has zero items (status.md has no deliverables section): fall back to Jira-only or Harvest-only with a low-confidence flag.

Record: `pct_delivered` (integer), `pct_breakdown` (one value per source used), `composite_method` (description of what was combined).

---

### Step 4: Calculate Velocity and ETA

For each incomplete release (pct_delivered < 100):

#### 4a. Remaining work estimate

```
remaining_deliverables = checklist_remaining (from Step 1a)
remaining_jira_issues  = jira_open (from Step 2c, or null)
estimated_hours_left   = max(0, budget_hours - logged_hours) (from Step 2b, or null)
```

If Fathom velocity available:
```
remaining_story_points = remaining_deliverables × avg_points_per_deliverable
                       (or from Jira if story points are tracked)
sprint_equivalent      = remaining_story_points / avg_velocity
```

#### 4b. ETA — velocity-based (highest confidence when available)

```
if avg_velocity > 0 and sprint_length_days known:
  days_to_complete = sprint_equivalent × sprint_length_days
  eta_velocity     = today + days_to_complete days
```

#### 4c. ETA — burn-rate-based (from Harvest)

```
if hours_per_week > 0 and estimated_hours_left is known:
  weeks_remaining  = estimated_hours_left / hours_per_week
  eta_burn_rate    = today + weeks_remaining × 7 days
```

#### 4d. ETA — checklist extrapolation (fallback, always calculable)

```
if pct_delivered > 0 and start_date known:
  weeks_elapsed       = (today - start_date).days / 7
  implied_total_weeks = weeks_elapsed / (pct_delivered / 100)
  eta_checklist       = start_date + implied_total_weeks × 7 days
```

If `start_date` unknown, use date of first session in Session History instead.

#### 4e. Recommended ETA

Select the most conservative (latest) ETA from available methods, unless one method is clearly an outlier (> 2× others — discard it and take the median).

State which method drove the recommended ETA.

#### 4f. Confidence classification

| Confidence | Criteria |
|------------|----------|
| `high` | Fathom velocity (≥2 sprints) + Harvest burn rate both available |
| `medium` | One of velocity or burn rate available, plus checklist |
| `low` | Checklist extrapolation only, or fewer than 2 sprints of velocity data |

---

### Step 5: Compare Against Contractual Date

```
contractual_date = hubspot_close_date ?? local_brief_date ?? null
days_delta       = (eta_recommended - contractual_date).days  # positive = late
```

**Status classification:**

| Status | Criteria | Icon |
|--------|----------|------|
| `complete` | pct_delivered = 100 or Wire status = completed | ✅ |
| `not_started` | pct_delivered = 0 and session_count = 0 | ⬜ |
| `on_track` | ETA ≤ contractual + 14 days (2-week tolerance) | 🟢 |
| `at_risk` | ETA is 15–42 days past contractual | 🟡 |
| `overdue` | ETA > 42 days past contractual, or contractual date already passed by >14 days | 🔴 |
| `blocked` | Open blocker with no resolution path and >7 days since last session | 🚫 |
| `no_date` | No contractual date found — show ETA only, no comparison | ⚪ |

If `contractual_date` is null: report ETA without comparison, classify as `no_date`.

---

### Step 6: Assemble and Return Forecast Object

```
DeliveryForecast {
  generated_at: ISO-8601 timestamp
  client_name: string
  releases: [
    {
      release_id: string
      release_name: string
      release_type: string
      wire_status: string                 # from status.md YAML
      pct_delivered: integer              # 0–100
      pct_breakdown: {
        checklist: integer | null
        jira: integer | null
        harvest: integer | null
        method: string                    # e.g. "checklist 40% + jira 60%"
      }
      velocity: {
        sprint_length_days: integer | null
        avg_velocity: number | null       # story points per sprint
        last_sprint_velocity: number | null
        trend: "improving" | "stable" | "declining" | "insufficient_data"
        sprints_of_data: integer          # 0 if no Fathom data
      }
      remaining_work: {
        open_deliverables: integer
        open_jira_issues: integer | null
        estimated_hours_remaining: number | null
        sprint_equivalent: number | null  # null if no velocity data
      }
      eta: {
        velocity_based: date | null
        burn_rate_based: date | null
        checklist_based: date | null
        recommended: date | null
        method: string                    # which method drove recommended
        confidence: "high" | "medium" | "low"
        confidence_reason: string
      }
      contractual_date: date | null
      contractual_source: string | null   # "hubspot", "brief.md", "context.md"
      days_to_eta: integer | null         # from today; negative if in the past
      days_delta: integer | null          # eta - contractual; positive = late
      status: "complete" | "on_track" | "at_risk" | "overdue" | "not_started" | "blocked" | "no_date"
      blockers: string[]
      overrun_flag: boolean               # true if logged_hours > budget_hours
    }
  ]
  portfolio: {
    total_releases: integer
    complete: integer
    on_track: integer
    at_risk: integer
    overdue: integer
    not_started: integer
    blocked: integer
    overall_pct_delivered: number         # weighted mean across releases
    earliest_at_risk_date: date | null    # soonest overdue contractual date
  }
}
```

---

### Step 7: Output (when called standalone)

When invoked directly via `/wire:utils-delivery-forecast`, render a markdown report:

```markdown
## Delivery Forecast — [client_name]
Generated: [timestamp] | Confidence: [overall]

### Portfolio Summary
[overall_pct_delivered]% delivered across [N] releases

| Status | Count |
|--------|-------|
| ✅ Complete | N |
| 🟢 On Track | N |
| 🟡 At Risk | N |
| 🔴 Overdue | N |
| 🚫 Blocked | N |
| ⬜ Not Started | N |

---

### Per-Release Forecast

| Release | % Done | ETA | Contractual | Delta | Status | Confidence |
|---------|--------|-----|-------------|-------|--------|------------|
| [name] | [N]% | [date] | [date] | [+/-N days] | [icon] | [h/m/l] |
| ... | | | | | | |

---

### [Release Name] — Detail

**Progress**: [N]% delivered
- Checklist: [N]% ([done]/[total] must-have items complete)
- Jira: [N]% ([done]/[total] issues closed)  ← omit if unavailable
- Harvest: [N]% ([N]h of [N]h budget consumed) ← omit if unavailable

**Remaining work**: [N] deliverables open, ~[N] sprint-equivalents
**ETA**: [date] ([method], [confidence] confidence)
**Contractual date**: [date] (source: [HubSpot/brief.md/not found])
**Delta**: [on track by N days / at risk by N days / overdue by N days]

**Velocity** (from Fathom): [avg] points/sprint over [N] sprints — [trend]  ← omit if no data

**Open blockers**:
- [blocker text]

---
[repeat per release]
```

When called from another command (not standalone), return the `DeliveryForecast` object directly without rendering.

---

## Fail-Safe Behaviour

If all external sources fail and no status.md files contain a deliverables section:

```
⚠️ Delivery forecast: insufficient data.
  status.md files present but no deliverables checklist found.
  Configure Jira, Harvest, or Fathom MCP servers for a higher-confidence forecast.
```

Return a `DeliveryForecast` object with all releases showing `pct_delivered: null`, `eta: null`, `status: "insufficient_data"`.

The calling command (e.g. `/wire:adopt`) must handle this gracefully — include a note in the assessment that the forecast could not be computed rather than blocking the rest of the output.

Execute the complete workflow as specified above.
