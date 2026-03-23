---
name: dignified-python
description: Production Python quality skill. Auto-activates when writing, reviewing, or refactoring Python code. Enforces modern type syntax, LBYL exception handling, pathlib for file operations, and clean module design. Particularly relevant for Dagster asset code, pipeline ingestion scripts, and utility code in Wire projects.
---

# Dignified Python Skill

## Purpose

This skill ensures Python code written in Wire projects meets production quality standards. It activates proactively when creating or reviewing Python files to enforce consistent patterns around types, error handling, file operations, and module structure.

## When This Skill Activates

**Keywords**: "python", "type hints", "pathlib", "exception", "LBYL", "EAFP", "click", "subprocess", "refactor this", "is this good python", "make this pythonic", "code review", "improve this code"

**Self-triggered**: when you are about to write or modify `.py` files in a Wire project, especially in `dagster_orchestration/`, `pipeline/`, or utility scripts.

---

## Core Standards

### 1. Type annotations

Use Python 3.10+ union syntax (`X | None` not `Optional[X]`). Annotate all function signatures:

```python
# ✅ Correct
def get_row_count(table: str, project_id: str | None = None) -> int:
    ...

# ❌ Old style
from typing import Optional
def get_row_count(table: str, project_id: Optional[str] = None) -> int:
    ...
```

Use `list[str]` not `List[str]`, `dict[str, int]` not `Dict[str, int]`.

### 2. LBYL (Look Before You Leap) exception handling

Check conditions before acting. Never use exceptions for control flow:

```python
# ✅ LBYL — check first
if "key" in data:
    value = data["key"]
else:
    value = default

# ❌ EAFP — exception as control flow
try:
    value = data["key"]
except KeyError:
    value = default
```

**When exceptions ARE appropriate**:
- At system boundaries (file I/O, network calls, external APIs) — wrap in try/except and convert to application errors
- Re-raising with context: `raise RuntimeError("...") from original_error`
- Third-party libraries that guarantee exceptions as their API (e.g. `requests.raise_for_status()`)

```python
# ✅ Exception at system boundary
def read_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config {path}") from e
```

### 3. Path operations — always use `pathlib.Path`

```python
# ✅ Correct
from pathlib import Path

config_path = Path("config") / "settings.json"
if config_path.exists():
    content = config_path.read_text(encoding="utf-8")

# ❌ Avoid
import os
config_path = os.path.join("config", "settings.json")
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        content = f.read()
```

Always:
- Check `.exists()` before `.resolve()` (`.resolve()` raises on non-existent paths in strict mode)
- Specify `encoding="utf-8"` explicitly on `.read_text()` / `.write_text()`
- Use `/` operator for path joining, not `os.path.join()`

### 4. Imports

Module-level absolute imports only. No relative imports except for `TYPE_CHECKING`:

```python
# ✅ Correct
from dagster import asset, AssetExecutionContext
from pathlib import Path

# ❌ Avoid
from .utils import helper          # relative import
from dagster import *              # wildcard import
```

Import order: stdlib → third-party → local. One blank line between each group.

### 5. Performance — properties and magic methods must be O(1)

Never do I/O, database calls, or heavy computation in `__init__`, `__repr__`, `@property`, or `__len__`. These are called implicitly and must be cheap.

### 6. Anti-patterns

| Anti-pattern | Correct approach |
|-------------|-----------------|
| `for i in range(len(items)):` | `for item in items:` or `for i, item in enumerate(items):` |
| Destructuring into single-use locals | Use the expression directly |
| More than 4 levels of indentation | Extract inner logic to a function |
| Backwards-compatibility `__all__` exports | Delete unused code outright |
| `print()` for logging | `logging.getLogger(__name__)` or `context.log.info()` in Dagster |

### 7. CLI code (Click)

```python
import sys
import click

@click.command()
@click.argument("project_path", type=click.Path(exists=True, path_type=Path))
@click.option("--verbose", is_flag=True)
def run(project_path: Path, verbose: bool) -> None:
    """Brief description of what the command does."""
    if not (project_path / "dbt_project.yml").exists():
        click.echo("Error: not a dbt project directory", err=True)
        raise SystemExit(1)
    click.echo(f"Running in {project_path}")
```

- Use `click.echo()` not `print()`
- Use `err=True` for error messages (writes to stderr)
- Use `raise SystemExit(1)` for error exits, not `sys.exit(1)` inside click commands
- Use `click.Path(path_type=Path)` to get `pathlib.Path` objects directly

### 8. Subprocess calls

```python
import subprocess
from pathlib import Path

def run_dbt(project_dir: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = ["dbt", *args]
    result = subprocess.run(
        cmd,
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,          # handle returncode manually
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"dbt command failed: {' '.join(cmd)}\n{result.stderr}"
        )
    return result
```

Always:
- Use `subprocess.run()` not `subprocess.call()` or `os.system()`
- Use `text=True` for string output (not bytes)
- Handle `returncode` explicitly — don't rely on `check=True` swallowing context
- Pass `cwd=` rather than `os.chdir()`
