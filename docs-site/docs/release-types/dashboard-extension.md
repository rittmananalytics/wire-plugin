---
sidebar_position: 7
title: Dashboard Extension
---

# Dashboard Extension Release

Use this when the semantic layer already has the data, and you're adding new dashboards on top.

**In-scope artifacts**: `requirements`, `mockups`, `dashboards`, `uat`

## Workflow

```
/wire:new                                         # release_type: dashboard_extension

/wire:requirements-generate <release-folder>      # Focus on dashboard/user requirements
/wire:requirements-validate <release-folder>
/wire:requirements-review <release-folder>

/wire:mockups-generate <release-folder>           # Wireframes for review with end users
/wire:mockups-review <release-folder>

/wire:dashboards-generate <release-folder>
/wire:dashboards-validate <release-folder>
/wire:dashboards-review <release-folder>

/wire:uat-generate <release-folder>
/wire:uat-review <release-folder>

/wire:archive <release-folder>
```

**Tips**:
- Add existing LookML view files to `requirements/` before generating dashboards — the AI needs to know which dimensions and measures are available
- Screenshots of existing Looker explores also help
