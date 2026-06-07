---
name: wire-release
description: >
  Skill for releasing a new version of the Wire Framework. Activates whenever the user asks to
  create a release, bump the version, ship a new version, or says something like "release this as
  v3.8" or "create a new release". Covers the full release lifecycle: bump type selection,
  pre-release cleanup, documentation updates, Wire Studio and VSCode extension updates, plugin
  rebuild, remote pushes, PR creation, and merge.
triggers:
  - Creating a new Wire Framework release
  - Bumping the version number (patch, minor, or major)
  - Shipping or publishing a new version of the Wire plugin or extension
  - "Release this as vX.Y"
  - "Create a new release"
---

# Wire Release Skill

## When This Skill Activates

Activate when the user asks to:
- Release a new version of the Wire Framework
- Bump the version number (patch / minor / major)
- Ship, publish, or cut a new release
- Say "create a new release" or "make a release" in the context of this repo

---

## Overview

The Wire Framework is distributed as three packages built from a single repo
(`ra-claude-skills-repo`):

| Package | Remote repo | Version file |
|---------|------------|--------------|
| Claude Code plugin (`wire`) | `rittmananalytics/wire-plugin` | `wire/packaging/claude-plugin/.claude-plugin/plugin.json` |
| Gemini CLI extension | `rittmananalytics/wire-extension` | `wire/packaging/gemini-extension/gemini-extension.json` |
| Wire Work plugin | `rittmananalytics/wirework-plugin` | `wire/packaging/wirework-plugin/.claude-plugin/plugin.json` |

The VSCode extension (`wire-vscode/`) and Wire Studio (`wire-web-ui/`) live in the same repo but
are versioned independently. The build script is `wire/scripts/build-packages.sh`.
A release automation script exists at `wire/scripts/release.sh` — it handles patch bumps,
CHANGELOG, RELEASE_NOTES, USER_GUIDE, build, and remote pushes. This skill wraps and extends it.

---

## Step 0 — On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | wire-release | activated | Wire release process triggered |
```

If `.wire/execution_log.md` does not exist, create it with the standard header. If no `.wire/`
directory exists, skip this step.

---

## Step 1 — Establish the Release Scope

Ask the user (or infer from context) the following:

| Item | How to determine |
|------|-----------------|
| **Bump type** | Patch (`x.x.1`) for bug fixes and small features; minor (`x.1.0`) for significant new features or release types — use sparingly; major (`1.0.0`) for substantial rewrites — use very sparingly |
| **Release summary** | One sentence describing what this release contains |
| **New features** | Bulleted list of what's new, changed, or fixed |
| **New release types?** | If any new `/wire:new` release types were added, a walkthrough is needed in USER_GUIDE.md |
| **Wire Studio changes?** | Any UI, API, or schema changes requiring a wire-web-ui update |
| **VSCode extension changes?** | Any changes to wire-vscode requiring a version bump + rebuild |

If bump type cannot be inferred, ask before proceeding. Never guess between minor and major.

### Bump type reference

| Type | When | Example |
|------|------|---------|
| Patch `x.x.1` | Bug fixes, new skills, small command additions, doc improvements | 3.7.5 → 3.7.6 |
| Minor `x.1.0` | New release type, significant new command group, major UX overhaul | 3.7.5 → 3.8.0 |
| Major `1.0.0` | Architectural rewrite, breaking changes to spec format or command API | 3.7.5 → 4.0.0 |

---

## Step 2 — Pre-Release Cleanup

Before touching version numbers, clean the repo:

1. **Temporary files**: remove any `.tmp`, `.scratch`, `*-draft.*`, `*-wip.*` files committed to
   the repo root, `wire/`, `wire-web-ui/`, or `wire-vscode/`.

2. **Design and planning docs**: remove any internal design notes, spike docs, or exploration
   files that are not part of the published framework. Typical locations: `docs/` subdirectories,
   `wire/specs/` one-off files, `wire-web-ui/docs/` drafts. Confirm with the user before deleting
   anything that isn't clearly temporary.

3. **RA client-specific references**: scan for any files that contain actual client data, project
   IDs, or RA-internal credentials accidentally committed. Flag these to the user — do not delete
   silently. Check: `docs/`, `wire/skills/`, `wire/specs/`, `wire-web-ui/`.

4. **Stale references in SKILL.md files**: if any skills under `wire/skills/` reference a version
   number that predates this release, update them.

Do not delete anything without confirming with the user when in doubt.

---

## Step 3 — Documentation Updates

### 3a. CHANGELOG.md and RELEASE_NOTES.md

`release.sh` updates these automatically when invoked. If running manually:

- Add a new `## [x.y.z] - YYYY-MM-DD` block at the top of `CHANGELOG.md` (Keep a Changelog format).
- Sections: `### Added`, `### Changed`, `### Fixed`, `### Removed` — only include non-empty sections.
- Mirror the same content to `wire/docs/CHANGELOG.md` and `wire/docs/RELEASE_NOTES.md`.
- Update the root `RELEASE_NOTES.md` with the same block.

### 3b. USER_GUIDE.md

Update `USER_GUIDE.md` at the repo root:

1. Replace every occurrence of the old version number with the new version.
2. Update the "What's New" or "Latest Release" section at the top.
3. **If a new release type was added**: add a walkthrough section following the existing pattern
   (SOW setup → `/wire:new` → `/wire:autopilot` → key artifacts). Check existing walkthroughs for
   `agentic_data_stack` and `agentic_commerce` as templates.
4. If `WIRE_WORK_USER_GUIDE.md` exists and covers any changed features, update it too.

### 3c. README files

Update version references in:

- `README.md` (repo root) — installation command, version badge if present
- `wire/README.md` — version in plugin install instructions
- `wire-web-ui/README.md` — if Wire Studio version is also bumping
- `wire-vscode/README.md` — if VSCode extension version is bumping

Search for the old version string across all README files and replace it.

### 3d. QUICK-REFERENCE.md

If any new commands were added or removed, update `wire/skills/QUICK-REFERENCE.md` (and the root
`QUICK-REFERENCE.md` if it exists) to reflect the current command list.

---

## Step 4 — Wire Studio Updates (wire-web-ui)

If this release includes changes that affect Wire Studio:

1. Check whether any new Wire commands, release types, or artifacts need to be reflected in:
   - `wire-web-ui/src/lib/artifacts.ts` — artifact catalog and dependency graph
   - `wire-web-ui/src/lib/wire-commands.ts` — 66 Wire command definitions
2. If a new release type was added, add its project type configuration to the artifact catalog.
3. Update any UI strings that reference the version number (e.g. about screens, footer text).
4. If the Prisma schema changed during this release, confirm `npx prisma db push` has been run and
   the migration is reflected in `prisma/schema.prisma`.
5. Run `npm run validate` from `wire-web-ui/` to confirm the build passes:
   ```bash
   cd wire-web-ui && npm run validate
   ```

Wire Studio's own version is in `wire-web-ui/package.json`. Bump it if substantive UI changes
were made — not required for every framework release.

---

## Step 5 — VSCode Extension Updates (wire-vscode)

If this release affects the VSCode extension:

1. Bump the version in `wire-vscode/package.json` to match or track the framework version.
2. Update `wire-vscode/README.md` with any new commands or features.
3. If the extension has a compiled output (`.vsix`), rebuild it:
   ```bash
   cd wire-vscode && npm run package
   ```
   This produces a `.vsix` file in `wire-vscode/`. Confirm the file is not committed to the repo
   (it should be in `.gitignore`); it is distributed separately.

---

## Step 6 — Update Skill Source Files

If any skills under `wire/skills/` were modified during this release:

1. Ensure changes are in the source directory (`wire/skills/<name>/SKILL.md`), not just in the
   plugin cache (`~/.claude/plugins/cache/`).
2. The build script (`build-packages.sh`) inlines skills into the distributed packages — source
   is authoritative.
3. For the `looker-dashboard-mockup` skill specifically, confirm the `references/design-system.md`
   and all four PNG assets (`looker_logo.png`, `icons.png`, `create_button.png`, `explore_icon.png`)
   are present in `wire/skills/looker-dashboard-mockup/references/`.

---

## Step 7 — Run the Release Script

For **patch bumps**, invoke the existing release automation:

```bash
bash wire/scripts/release.sh
```

The script prompts for a one-line release summary and a feature list, then:
1. Bumps the patch version across all version files
2. Updates CHANGELOG, RELEASE_NOTES, and wire/docs equivalents
3. Updates USER_GUIDE.md version reference
4. Commits and pushes to origin
5. Builds plugin/extension packages via `build-packages.sh`
6. Pushes the Claude plugin to `rittmananalytics/wire-plugin`
7. Pushes the Gemini extension to `rittmananalytics/wire-extension`
8. Updates Wire Studio and VSCode extension READMEs
9. Raises a PR

Use `--dry-run` to preview changes without writing:
```bash
bash wire/scripts/release.sh --dry-run
```

Use `--no-push` to run locally without remote pushes:
```bash
bash wire/scripts/release.sh --no-push
```

### For minor or major bumps

`release.sh` only increments the patch component. For minor or major bumps, manually set the
version first, then invoke the script with `--no-bump` or edit the version files directly:

**Version files to update manually for minor/major:**

```
wire/packaging/claude-plugin/.claude-plugin/plugin.json   → "version" field
wire/packaging/gemini-extension/gemini-extension.json     → "version" field
wire/packaging/wirework-plugin/.claude-plugin/plugin.json → "version" field
wire-vscode/package.json                                   → "version" field (if bumping)
wire-web-ui/package.json                                   → "version" field (if bumping)
```

After manually setting versions, run `build-packages.sh` directly:
```bash
bash wire/scripts/build-packages.sh
```

Then commit, push, and raise the PR manually (see Step 8).

---

## Step 8 — Commit, Push, PR, and Merge

If not handled by `release.sh`:

```bash
# Stage all changes
git add -A

# Commit
git commit -m "release: vX.Y.Z — <one-line summary>"

# Push to origin
git push origin HEAD

# Raise PR (gh CLI)
gh pr create \
  --title "Release vX.Y.Z — <one-line summary>" \
  --body "## Changes\n- <feature list>\n\n## Checklist\n- [ ] CHANGELOG updated\n- [ ] USER_GUIDE updated\n- [ ] Packages built\n- [ ] Remote plugin repos updated"

# Merge (once CI passes)
gh pr merge --merge --delete-branch
```

Confirm with the user before running `gh pr merge` — do not merge autonomously unless explicitly
asked to do so.

---

## Step 9 — Post-Release Verification

After the release completes, verify:

1. `plugin.json` version matches the intended release version:
   ```bash
   cat wire/packaging/claude-plugin/.claude-plugin/plugin.json | grep version
   ```
2. The Claude plugin remote repo (`rittmananalytics/wire-plugin`) has the new version committed.
3. The Gemini extension remote repo (`rittmananalytics/wire-extension`) has the new version.
4. CHANGELOG.md top entry matches the new version and today's date.
5. USER_GUIDE.md no longer references the old version number.

Report the results as a brief checklist with pass/fail for each item.

---

## Checklist Summary

Run through this before declaring the release complete:

```
Pre-release
[ ] Temporary files removed
[ ] Design/planning docs removed or archived
[ ] No RA client-specific references in published files
[ ] Stale version references in SKILL.md files updated

Documentation
[ ] CHANGELOG.md updated (new block at top)
[ ] RELEASE_NOTES.md updated
[ ] wire/docs/CHANGELOG.md and RELEASE_NOTES.md mirrored
[ ] USER_GUIDE.md version bumped, new features documented
[ ] New release type walkthrough added (if applicable)
[ ] WIRE_WORK_USER_GUIDE.md updated (if applicable)
[ ] README.md, wire/README.md version references updated
[ ] QUICK-REFERENCE.md updated (if commands added/removed)

Wire Studio
[ ] artifacts.ts updated for new release types (if applicable)
[ ] wire-commands.ts updated (if applicable)
[ ] npm run validate passes

VSCode Extension
[ ] package.json version bumped (if applicable)
[ ] .vsix rebuilt (if applicable)

Build and Publish
[ ] build-packages.sh completed without errors
[ ] Claude plugin pushed to rittmananalytics/wire-plugin
[ ] Gemini extension pushed to rittmananalytics/wire-extension
[ ] Wire Work plugin pushed to rittmananalytics/wirework-plugin

Git
[ ] Committed with "release: vX.Y.Z — <summary>" message
[ ] Pushed to origin
[ ] PR raised
[ ] PR merged (with user confirmation)

Post-release
[ ] plugin.json version confirmed correct
[ ] Remote plugin repos confirmed updated
[ ] CHANGELOG top entry correct
```
