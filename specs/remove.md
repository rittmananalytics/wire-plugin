---
wire_schema: "1.0"
command: lifecycle
artifact: remove
domain: remove
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Remove an existing release from the current engagement, with confirmation
argument-hint: <release-folder>

---

# Wire Remove Release Command

## Purpose

Interactive workflow to remove an existing release from the current engagement. Handles issue-tracker cleanup notes and folder deletion with safety confirmations.

Wire is one-engagement-per-repo: there is exactly one client per `.wire/` root, so this command removes one **release folder** (e.g. `01-discovery`) under `.wire/releases/` — active or archived — not a whole client project.

## Workflow

### Step 1: List Existing Releases

**Process**:
1. Use Bash to find all existing release folders (active and archived):
   ```bash
   ls -d .wire/releases/*/ 2>/dev/null | grep -v '/_archive/$'
   ls -d .wire/releases/_archive/*/ 2>/dev/null
   ```
2. If no releases found (both empty), output message and exit:
   ```
   No releases found in `.wire/releases/`. Nothing to remove.
   ```
3. For each release folder found, note:
   - `release_folder`: the folder name (e.g. `01-discovery`)
   - whether it's active or under `_archive/`

4. For each release, read `.wire/releases/{release_folder}/status.md` (or `.wire/releases/_archive/{release_folder}/status.md` if archived) to get `release_type` and `current_phase`

### Step 2: Ask Which Release to Remove

**Use AskUserQuestion** to present release options:

```json
{
  "questions": [{
    "question": "Which release do you want to remove?",
    "header": "Select",
    "options": [
      {"label": "01-discovery", "description": "discovery — Discovery (Shape Up)"},
      {"label": "02-full-platform", "description": "full_platform — Requirements (archived)"}
    ],
    "multiSelect": false
  }]
}
```

Build options dynamically from discovered releases. Include up to 4 releases as options (AskUserQuestion limit). If more than 4 releases exist, list them all in chat first and ask the user to specify by name.

### Step 3: Show Deletion Preview & Confirm

**Process**:
1. Use `find .wire/releases/{release_folder}/ -type f` (or the `_archive/` path if archived) to list all files that will be deleted
2. Count files and subdirectories

**Display preview:**
```
## Deletion Preview

**Release:** {release_folder} ({release_type})
**Folder:** .wire/releases/{release_folder}/

### Contents to be deleted:
- status.md
- artifacts/ (X files)
- requirements/ (Y files)
- design/ (Z files)
- dev/ (W files)
- test/ (V files)
- deploy/ (U files)
- enablement/ (T files)

**Total:** N files will be permanently deleted
```

(List only the subfolders that actually exist for this release type — e.g. discovery releases have `artifacts/` and `planning/`, not `dev/`/`test/`/`deploy/`.)

**Use AskUserQuestion** for confirmation:

```json
{
  "questions": [{
    "question": "This action is IRREVERSIBLE. All release files will be permanently deleted. Proceed?",
    "header": "Confirm",
    "options": [
      {"label": "Yes, delete it", "description": "Permanently remove this release and all its files"},
      {"label": "Cancel", "description": "Keep the release, do not delete anything"}
    ],
    "multiSelect": false
  }]
}
```

If user selects "Cancel", output:
```
Removal cancelled. No changes were made.
```
And exit.

### Step 4: Delete Folder

**Bash command:**
```bash
rm -rf .wire/releases/{release_folder}/
```
(or `.wire/releases/_archive/{release_folder}/` if the release was archived)

Capture exit code. If non-zero, report error and suggest manual deletion.

### Step 5: Confirm Removal

Output confirmation:

```
## Release Removed Successfully

**Deleted:** .wire/releases/{release_folder}/

### Summary
- Removed {N} files

### Remaining Releases
Run `/wire:status` to see remaining releases in this engagement.
```

## Edge Cases

### No Releases Exist

If no release folders are found (active or archived):
```
No releases found in `.wire/releases/`. Nothing to remove.
```
Exit without further prompts.

### More Than 4 Releases

AskUserQuestion supports max 4 options. If more releases exist:
1. List all releases in chat with their folder names and types
2. Ask user to type the folder name directly:
   ```
   You have {N} releases. Please type the folder name of the release to remove (e.g., "01-discovery"):
   ```
3. Wait for text input, then continue to Step 3

### Removing the Only Release in the Engagement

If this is the last release under `.wire/releases/`, removing it leaves the engagement with no releases at all (`.wire/engagement/context.md` is untouched). Note this in the confirmation preview:
```
Note: this is the only release in this engagement. After removal, run /wire:new to add a new release.
```

### Permission Errors

If `rm -rf` fails:
1. Report the error message
2. Suggest manual deletion:
   ```
   Could not delete folder. Try manually:
   rm -rf .wire/releases/{release_folder}/
   ```

### User Cancels

If user selects "Cancel" at confirmation:
```
Removal cancelled. No changes were made.
```

## Output

This command:
- Deletes `.wire/releases/{release_folder}/` (or `.wire/releases/_archive/{release_folder}/`) directory and all contents

Final output is a confirmation message with summary.
