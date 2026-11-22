---
wire_schema: "1.0"
command: lifecycle
artifact: archive
domain: archive
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Archive a completed release within the current engagement
argument-hint: <release-folder>

---

# Wire Archive Release Command

## Purpose

Move a completed release to an archive location within the current engagement, to keep the active release list small. Archived releases are excluded from `/wire:status` and `/wire:start` scans but remain accessible via `/wire:status --archived`.

Wire is one-engagement-per-repo: there is exactly one client per `.wire/` root, so "archiving" here means archiving one completed **release** (e.g. `01-discovery`) within the current engagement — not switching between sibling client projects, which is not a concept that exists in the current layout.

## Archive Convention

Archived releases move one level deeper, from:
```
.wire/releases/<release_folder>/
```
to:
```
.wire/releases/_archive/<release_folder>/
```

This means a plain `.wire/releases/*/status.md` glob (used by `/wire:status` and `/wire:start`) naturally excludes archived releases without needing an exclude-list, and `/wire:status --archived` globs `.wire/releases/_archive/*/status.md` specifically. `_archive` is not a valid release folder name (release folders are always `NN-name`), so it can never collide with a real release.

## Usage

```bash
/wire:archive 01-discovery
```

## Workflow

### Step 1: List Active Releases

**Process**:
1. Use Glob to find all active release folders: `.wire/releases/*/status.md`
2. Exclude any match under `.wire/releases/_archive/` (shouldn't normally match the glob above, but guard against it anyway)
3. If `$ARGUMENTS` is provided, match against known release folders
4. If no arguments, present selection

**If no releases found**:
```
No active releases found in `.wire/releases/`. Nothing to archive.
```

### Step 2: Select Release to Archive

**If argument provided**: Validate the folder exists under `.wire/releases/`

**If no argument**: Use `AskUserQuestion` to present release options:

```json
{
  "questions": [{
    "question": "Which release do you want to archive?",
    "header": "Archive",
    "options": [
      {"label": "01-discovery", "description": "discovery — Discovery (Shape Up)"},
      {"label": "02-full-platform", "description": "full_platform — Requirements"}
    ],
    "multiSelect": false
  }]
}
```

Build options dynamically from discovered releases (folder name plus `release_type` and `current_phase` from each `status.md`). Include up to 4 releases as options (AskUserQuestion limit). If more than 4 releases exist, list them all in chat first and ask the user to specify by name.

### Step 3: Confirm Archive

**Use AskUserQuestion** for confirmation:

```json
{
  "questions": [{
    "question": "Archive this release? It will be moved to .wire/releases/_archive/ and hidden from /wire:status and /wire:start.",
    "header": "Confirm",
    "options": [
      {"label": "Yes, archive it", "description": "Move release to .wire/releases/_archive/"},
      {"label": "Cancel", "description": "Keep the release active"}
    ],
    "multiSelect": false
  }]
}
```

If user selects "Cancel":
```
Archive cancelled. No changes were made.
```
And exit.

### Step 4: Move to Archive

**Process**:
1. Create archive directory if it doesn't exist:
   ```bash
   mkdir -p .wire/releases/_archive/
   ```
2. Move the release folder:
   ```bash
   git mv .wire/releases/{release_folder}/ .wire/releases/_archive/{release_folder}/
   ```

### Step 5: Confirm Archive

Output confirmation:

```
## Release Archived

**Moved:** `.wire/releases/{release_folder}/` → `.wire/releases/_archive/{release_folder}/`

The release won't appear in `/wire:status` or `/wire:start`.

To view archived releases: `/wire:status --archived`
```

## Edge Cases

### No Releases Exist

If no release folders are found:
```
No active releases found in `.wire/releases/`. Nothing to archive.
```

### Release Not Found

If the specified release doesn't exist:
```
Release "{release_folder}" not found in `.wire/releases/`.

Active releases:
[list active releases]
```

### Already Archived

If the release is already in `.wire/releases/_archive/`:
```
Release "{release_folder}" is already archived.
```

### Git Not Available

If `git mv` fails, fall back to a regular move:
```bash
mkdir -p .wire/releases/_archive/
mv .wire/releases/{release_folder}/ .wire/releases/_archive/{release_folder}/
```

## Output

This command:
- Moves `.wire/releases/{release_folder}/` to `.wire/releases/_archive/{release_folder}/`

Final output is a confirmation message.
