---
sidebar_position: 5
title: VS Code Extension
---

# Wire VS Code Extension

If you spend your day in Visual Studio Code, switching to a terminal to check which artifacts are approved and which are waiting on a validation fix is a small but constant interruption. The Wire VS Code extension brings Wire status and artifact management into Visual Studio Code, providing a sidebar panel, inline artifact decorations and quick-run command shortcuts, so that you can see and drive a release without leaving your editor. In this page we will look at what the extension provides, how you install it, how the Wire Explorer and the command shortcuts work, how you set the active release, and what the extension settings and gutter decorations do.

## What the extension provides

- **Wire Explorer sidebar**: a tree view of all releases in the open workspace, showing phase, artifact status and the last-run command
- **Status bar indicator**: a compact status line showing the current engagement phase and last artifact state
- **Quick-run commands**: run any Wire command from the VS Code command palette (`Cmd+Shift+P` → `Wire: Run Command`)
- **Artifact preview**: click any artifact in the explorer to open it in a preview panel (read-only rendered Markdown)
- **Inline review decorations**: generated files are annotated with their Wire artifact status (Generated, Validated, Approved) in the editor gutter

## Installing the extension

The extension is published to the VS Code Marketplace as **Wire Framework**, and you install it from the command line with:

```bash
code --install-extension rittmananalytics.wire-framework
```

or by searching for "Wire Framework" in the Extensions panel.

### Prerequisites

Before installing, you will need:

- Claude Code CLI installed and on `$PATH`
- The Wire plugin installed in Claude Code (`/plugin install wire@rittman-analytics`)
- VS Code 1.80 or later

## Using the Wire Explorer

Open the Wire Explorer from the Activity Bar (the Wire icon), and the explorer shows each release in the workspace with its phases and artifacts:

```
WIRE FRAMEWORK
└── 20240115_barton_peveril_full_platform
    ├── Phase: Development
    ├── Requirements ✓ (all approved)
    ├── Design ✓ (all approved)
    └── Development
        ├── ingestion ✓ Approved
        ├── dbt-models (students) ✓ Approved
        ├── dbt-models (finance) ⚠ Validation failures
        └── dbt-models (attendance) - Not started
```

Click any artifact node to open the artifact document, and right-click for the context menu:
- **Run generate**: run the generate command for this artifact
- **Run validate**: run the validate command
- **Open review**: open the artifact for review in the Studio web panel
- **Copy command**: copy the full Wire command to the clipboard

## Running Wire commands from VS Code

There are three ways to run a command from the editor.

**Command palette**: `Cmd+Shift+P` → type "Wire" to see all Wire commands. Select a command and Wire will prompt for the release folder if it is not already set.

**Status bar**: click the Wire status bar item to open a quick-pick of available commands for the current release.

**Keyboard shortcut**: assign `wire.runLastCommand` to a keyboard shortcut to re-run the last Wire command without opening the palette.

## Setting the active release

If the workspace contains multiple Wire releases, you set the active release from the status bar:

```
Wire: 20240115_barton_peveril ▾
```

Click the status bar item to change the active release, and all quick-run commands run against the active release.

## Extension settings

Open VS Code settings (`Cmd+,`) and search for "Wire" to configure the following:

| Setting | Default | Description |
|---|---|---|
| `wire.claudeCodePath` | `claude` | Path to the Claude Code CLI binary |
| `wire.autoRefresh` | `true` | Auto-refresh the explorer after a command completes |
| `wire.showStatusBar` | `true` | Show the Wire status bar item |
| `wire.defaultRelease` | `` | Pin a specific release folder as default |
| `wire.artifactDecorations` | `true` | Show artifact status in the editor gutter |

## Artifact gutter decorations

When you open a file that is a Wire-generated artifact (identified by the Wire header comment), the extension adds a decoration in the gutter showing the artifact's current status, and hovering over the decoration shows the full status and the last action taken.

Files in a non-approved state show a yellow dot, approved files show a green dot and files with validation failures show a red dot.
