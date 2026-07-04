---
name: wire-release
description: >
  Skill for releasing a new version of the Wire Framework. Activates whenever the user asks to
  create a release, bump the version, ship a new version, or says something like "release this as
  v3.8" or "create a new release". Covers the full release lifecycle: bump type selection,
  pre-release cleanup, documentation updates, VSCode extension updates, plugin
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

The VSCode extension (`wire-vscode/`) lives in the same repo but
is versioned independently. The build script is `wire/scripts/build-packages.sh`.
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
   the repo root, `wire/`, or `wire-vscode/`.

2. **Design and planning docs**: remove any internal design notes, spike docs, or exploration
   files that are not part of the published framework. Typical locations: `docs/` subdirectories,
   `wire/specs/` one-off files. Confirm with the user before deleting
   anything that isn't clearly temporary.

3. **RA client-specific references**: scan for any files that contain actual client data, project
   IDs, or RA-internal credentials accidentally committed. Flag these to the user — do not delete
   silently. Check: `docs/`, `wire/skills/`, `wire/specs/`.

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
- **`docs-site/docs/reference/release-notes.md`** — this is the Docusaurus release-history page and is **hand-maintained**; `release.sh` does NOT update it and it is not part of the Step 3e USER_GUIDE→page mapping. On **every** release, prepend a new `## vX.Y.Z — <title>` section at the top (immediately after the intro `---` divider, before the previous top entry), matching the existing style: a `**Released**: <Month Year>` line followed by prose paragraphs with bolded lead-ins per change. Derive the content from the `RELEASE_NOTES.md` overview, but keep it client-neutral — no client or engagement names. Skipping this is the easy step to miss: the page silently falls a version behind.

### 3b. USER_GUIDE.md

Update `USER_GUIDE.md` at the repo root:

1. Replace every occurrence of the old version number with the new version.
2. Update the "What's New" or "Latest Release" section at the top.
3. **If a new release type was added**: add a walkthrough section following the existing pattern
   (SOW setup → `/wire:new` → `/wire:autopilot` → key artifacts). Check the existing `agentic_data_stack`
   walkthrough as a template.
4. If `WIRE_WORK_USER_GUIDE.md` exists and covers any changed features, update it too.

### 3c. README files

Three files carry a version string in their title heading and **must be updated on every release**, unconditionally:

| File | What to update |
|------|----------------|
| `README.md` (repo root) | `# Wire Framework vX.Y.Z` heading |
| `wire/README.md` | `# Wire Framework vX.Y.Z` heading |
| `USER_GUIDE.md` | `**Version**: X.Y.Z` header line (also covered in 3b, but confirm here) |

Verify every target before editing:

```bash
grep -n "Wire Framework v\|\*\*Version\*\*" README.md wire/README.md USER_GUIDE.md
```

Replace every hit.

Also update if applicable:
- `wire-vscode/README.md` — if the VSCode extension version is bumping

### 3d. QUICK-REFERENCE.md and the skills reference

If any new commands were added or removed, update `wire/skills/QUICK-REFERENCE.md` (and the root
`QUICK-REFERENCE.md` if it exists) to reflect the current command list.

**If any skill was added or removed under `wire/skills/`**, update `docs-site/docs/reference/skills.md`
to match. This page is **hand-maintained** — it is not generated from `wire/skills/` and is not part
of the Step 3e USER_GUIDE→page mapping, so a new skill silently goes missing from it otherwise (the
`metabase` skill was missed this way). Add a `### \`<skill-name>\`` entry under the appropriate section
(matching the existing **Activates when** + description format), and create or rename a section heading
if the skill doesn't fit an existing one. Cross-check the file list:

```bash
diff <(ls -d wire/skills/*/ | xargs -n1 basename | sort) \
     <(grep -oE '^### `[a-z0-9-]+`' docs-site/docs/reference/skills.md | tr -d '#` ' | sort)
```

Reconcile any skill that appears in one list but not the other (some internal/meta skills may be
intentionally omitted — confirm rather than blindly adding).

### 3e. Docusaurus doc pages (docs-site/)

The `docs-site/docs/` directory contains 29 Markdown pages derived from `USER_GUIDE.md`. These are
served as the Wire Framework documentation site via Read the Docs from `rittmananalytics/wire-plugin`.
They must be kept in sync with `USER_GUIDE.md` on every release where the guide changes.

**Mapping — USER_GUIDE.md section → doc page:**

| Section | Doc page |
|---------|----------|
| 1–2: What Is Wire / The Problem It Solves | `docs-site/docs/intro.md` |
| 3: Engagements and Releases | `docs-site/docs/getting-started/engagements-releases.md` |
| 4: Release Types | `docs-site/docs/getting-started/release-types.md` |
| 5: Installation | `docs-site/docs/getting-started/installation.md` |
| 6: Core Concepts | `docs-site/docs/getting-started/core-concepts.md` |
| 7: Discovery (Shape Up) | `docs-site/docs/release-types/discovery-shape-up.md` |
| 8: Discovery (SOP) | `docs-site/docs/release-types/discovery-sop.md` |
| 9: Kick-off Deck | `docs-site/docs/release-types/kickoff-deck.md` |
| 10: Full Platform | `docs-site/docs/release-types/full-platform.md` |
| 11: Pipeline / dbt | `docs-site/docs/release-types/pipeline-dbt.md` |
| 12: dbt Development | `docs-site/docs/release-types/dbt-development.md` |
| 13: Dashboard Extension | `docs-site/docs/release-types/dashboard-extension.md` |
| 14: Dashboard First | `docs-site/docs/release-types/dashboard-first.md` |
| 15: Enablement | `docs-site/docs/release-types/enablement.md` |
| 16: Platform Migration | `docs-site/docs/release-types/platform-migration.md` |
| 17: Agentic Data Stack | `docs-site/docs/release-types/agentic-data-stack.md` |
| 18: Droughty | `docs-site/docs/release-types/droughty.md` |
| 19: Custom | `docs-site/docs/release-types/custom.md` |
| 20: Worked Example | `docs-site/docs/advanced/worked-example.md` |
| 21: Wire Autopilot | `docs-site/docs/advanced/autopilot.md` |
| 22: Wire Agents | `docs-site/docs/advanced/wire-agents.md` |
| 23: VS Code Extension | `docs-site/docs/advanced/vscode-extension.md` |
| 24: Issue Tracking | `docs-site/docs/advanced/issue-tracking.md` |
| 25: Document Store | `docs-site/docs/advanced/document-store.md` |
| 26: Extending Wire | `docs-site/docs/advanced/extending.md` |
| 27: FAQ | `docs-site/docs/reference/faq.md` |
| 28: Troubleshooting | `docs-site/docs/reference/troubleshooting.md` |
| 29: Management Commands | `docs-site/docs/reference/management-commands.md` |

**Process:**

1. Run `git diff HEAD -- USER_GUIDE.md` (or compare to the previous release tag) to identify which
   sections changed.

2. For each changed section, update the corresponding doc page(s) listed above. Match the existing
   style of that page — plain prose, no comment blocks, mermaid diagrams preserved.

3. If a **new section** was added to USER_GUIDE.md (e.g. a new release type):
   - Create a new doc page under the appropriate subdirectory
   - Add a frontmatter block: `---\nsidebar_position: N\ntitle: Page Title\n---`
   - Add the page to `docs-site/sidebars.js` in the correct category and position
   - Update `docs-site/docs/getting-started/release-types.md` to include the new type in the
     comparison table

4. If a **section was removed**, delete the corresponding doc page and remove it from `sidebars.js`.

5. Verify the site still builds:
   ```bash
   cd docs-site && npm run build
   ```
   Fix any broken sidebar references or mermaid syntax errors before proceeding.

6. Sync the updated `docs-site/` to the wire-plugin repo:
   ```bash
   rsync -av --exclude='node_modules' --exclude='.docusaurus' --exclude='build' \
     docs-site/ /path/to/wire-plugin/docs-site/
   ```
   Replace `/path/to/wire-plugin` with the actual local path to the `rittmananalytics/wire-plugin`
   clone. The wire-plugin repo already contains the `docs-site/` directory and `.readthedocs.yaml`.
   The rsync is sufficient — Read the Docs rebuilds automatically on the next push to wire-plugin.

---

## Step 4 — VSCode Extension Updates (wire-vscode)

If this release affects the VSCode extension:

The extension is **data-driven** — it reads the live `.wire/` structure and builds `/wire:<artifact>-<action>` command strings dynamically, so new Wire commands/release types surface automatically with **no code change**. Update the extension only when its own `src/` code changes (tree, command picker, status webview, MCP panel, workflow graph). A framework-only release does not require an extension rebuild; bump it solely for version alignment if you want.

When the extension does change:

1. Bump the version in `wire-vscode/package.json` to match or track the framework version.
2. Update `wire-vscode/README.md` with any new commands or features.
3. Compile and package the `.vsix`:
   ```bash
   cd wire-vscode && npm install && npm run compile
   npx @vscode/vsce package      # → wire-framework-<version>.vsix
   ```
   Note: there is **no** `npm run package` script — packaging is `vsce`, run via `npx @vscode/vsce` (it is not in `devDependencies`). The `.vsix` is gitignored; it is distributed, not committed.
4. Test locally: VS Code → "Extensions: Install from VSIX…", or `code --install-extension wire-framework-<version>.vsix`. Reload and check the Releases tree, the `⌘⇧W` command picker, and the status webview.
5. Publish to the Marketplace (requires a publisher PAT for `rittman-analytics`):
   ```bash
   npx @vscode/vsce publish      # vsce login rittman-analytics, or set VSCE_PAT
   ```
   If you also list on Open VSX: `npx ovsx publish`.
6. Commit the `package.json` / `README.md` / `src` changes — not the `.vsix`.

---

## Step 5 — Update Skill Source Files

If any skills under `wire/skills/` were modified during this release:

1. Ensure changes are in the source directory (`wire/skills/<name>/SKILL.md`), not just in the
   plugin cache (`~/.claude/plugins/cache/`).
2. The build script (`build-packages.sh`) inlines skills into the distributed packages — source
   is authoritative.
3. For the `looker-dashboard-mockup` skill specifically, confirm the `references/design-system.md`
   and all four PNG assets (`looker_logo.png`, `icons.png`, `create_button.png`, `explore_icon.png`)
   are present in `wire/skills/looker-dashboard-mockup/references/`.

---

## Step 6 — Run the Release Script

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
8. Updates the VSCode extension README
9. Raises a PR

Use `--dry-run` to preview changes without writing:
```bash
bash wire/scripts/release.sh --dry-run
```

Use `--no-push` to run locally without remote pushes:
```bash
bash wire/scripts/release.sh --no-push
```

Use `--push-only` to re-push the current dist to all plugin repos without bumping the version.
Run this after a post-release fix that updates `wire/dist/` but doesn't warrant a new version number:
```bash
bash wire/scripts/release.sh --push-only
```

### For minor or major bumps

`release.sh` only increments the patch component. For minor or major bumps, manually set the
version first, then invoke the script with `--no-bump` or edit the version files directly:

**Version files to update manually for minor/major:**

```
# Packaging manifests — "version" field
wire/packaging/claude-plugin/.claude-plugin/plugin.json
wire/packaging/gemini-extension/gemini-extension.json
wire/packaging/wirework-plugin/.claude-plugin/plugin.json

# Prose heading files — update version string in title/header line (REQUIRED every release)
README.md                   → # Wire Framework vX.Y.Z
wire/README.md              → # Wire Framework vX.Y.Z
USER_GUIDE.md               → **Version**: X.Y.Z

# package.json files (only if the component is bumping)
wire-vscode/package.json    → "version" field
```

The build script reads its version from `plugin.json` — it does NOT automatically rewrite
`wire/README.md`, `README.md`, or `USER_GUIDE.md`. Those three files
must be updated manually before every release commit.

After manually setting versions, run `build-packages.sh` directly:
```bash
bash wire/scripts/build-packages.sh
```

Then commit, push, and raise the PR manually (see Step 7).

---

## Step 7 — Commit, Push, PR, and Merge

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

## Step 8 — Post-Release Verification

After the release completes, verify:

1. `plugin.json` version matches the intended release version:
   ```bash
   cat wire/packaging/claude-plugin/.claude-plugin/plugin.json | grep version
   ```
2. The Claude plugin remote repo (`rittmananalytics/wire-plugin`) has the new version committed.
3. The Gemini extension remote repo (`rittmananalytics/wire-extension`) has the new version.
4. CHANGELOG.md top entry matches the new version and today's date.
5. **USER_GUIDE.md version** — check that the version header matches:
   ```bash
   grep "^\*\*Version\*\*" USER_GUIDE.md
   ```
6. **README.md (root) heading** — check the framework version heading:
   ```bash
   grep "^# Wire Framework v" README.md
   ```
7. **wire/README.md heading** — must also match:
   ```bash
   grep "^# Wire Framework v" wire/README.md
   ```
8. **Plugin repo README** — the `rittmananalytics/wire-plugin` repo must have a non-empty `README.md`.
   The build script generates this from the root `README.md`. If it's missing, run
   `bash wire/scripts/build-packages.sh` and re-push.
9. **Logo path in plugin repo** — the USER_GUIDE.md served from `rittmananalytics/wire-plugin` must
    reference `docs/images/wire_logo_transparent.png` (not `wire/docs/images/...`). Check the first
    line of `wire/dist/claude-plugin/USER_GUIDE.md`:
    ```bash
    head -1 wire/dist/claude-plugin/USER_GUIDE.md
    ```
    It must read `<img src="docs/images/wire_logo_transparent.png" ...>`.

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
[ ] USER_GUIDE.md version bumped (**Version**: line), new features documented
[ ] New release type walkthrough added (if applicable)
[ ] WIRE_WORK_USER_GUIDE.md updated (if applicable)
[ ] README.md (root) — # Wire Framework vX.Y.Z heading updated
[ ] wire/README.md — # Wire Framework vX.Y.Z heading updated
[ ] QUICK-REFERENCE.md updated (if commands added/removed)
[ ] docs-site/ doc pages updated for all changed USER_GUIDE.md sections
[ ] docs-site/docs/reference/release-notes.md — new vX.Y.Z block prepended (hand-maintained; release.sh does not touch it)
[ ] docs-site/docs/reference/skills.md — updated if any skill added/removed (hand-maintained; not generated from wire/skills/)
[ ] New doc page created and added to sidebars.js (if new release type added)
[ ] docs-site/ builds without errors (npm run build)
[ ] docs-site/ synced to wire-plugin repo (rsync)

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
[ ] USER_GUIDE.md **Version** header matches new version
[ ] README.md (root) # Wire Framework heading matches new version
[ ] wire/README.md # Wire Framework heading matches new version
[ ] wire-plugin repo has non-empty README.md
[ ] wire-plugin USER_GUIDE.md logo path is docs/images/wire_logo_transparent.png (not wire/docs/images/...)
[ ] wire-plugin docs-site/ updated (rsync completed, all changed sections reflected)
[ ] Remote plugin repos confirmed updated
[ ] CHANGELOG top entry correct
```
