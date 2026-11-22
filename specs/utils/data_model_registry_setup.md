---
wire_schema: "1.0"
command: utility
artifact: data_model_registry_setup
domain: utils
release_types: []
action_type: utility
logs_execution: false
description: Clone the private wire-data-model-registry repo to this machine, for RA staff with access
argument-hint: (no arguments - interactive)

---

# Data Model Registry Setup

## Purpose

One-time, per-machine setup for the optional data model registry feature used by `/wire:data_model-generate` and `/wire:data_model-validate` (see `wire/schemas/data-model-registry.md`). This is **not** part of the Wire plugin's bundled content — `rittmananalytics/wire-data-model-registry` is a private repo containing proprietary reference implementations generalized from real RA client engagements, and the plugin itself is public. Running this command clones it to your own machine using your own git credentials; it is not fetched or bundled any other way.

If you don't have access to the private repo, this command isn't for you — Wire works completely normally without it. `data_model-generate`/`data_model-validate` silently skip the canonical-vertical feature when the local copy isn't present; nothing else is affected.

## Usage

```bash
/wire:utils-data-model-registry-setup
```

Not scoped to a release or engagement — this sets up your machine once, and every engagement you work on afterward can use it.

## Workflow

### Step 1: Check for an existing local copy

```bash
ls ~/.wire/data-model-registry/.git 2>/dev/null
```

If present:
```
Data model registry already set up at ~/.wire/data-model-registry/.
Pull the latest? (yes / no)
```
- **yes** — `cd ~/.wire/data-model-registry && git pull`, report the result, stop.
- **no** — stop.

If absent, continue to Step 2.

### Step 1.5: The attempted marker (for other commands calling this non-interactively)

Some Wire commands (`/wire:new`, `/wire:autopilot`) attempt this setup automatically and silently when they're about to work on an artifact that could use the registry, rather than requiring a consultant to have run this command manually first. When invoked that way (no interactive session, not run directly by a person), skip Step 1's interactive prompt — if a local copy already exists, just proceed as normal; don't ask about pulling. After Step 3 completes (success or failure), always write:

```bash
mkdir -p ~/.wire
date -u +%Y-%m-%dT%H:%M:%SZ > ~/.wire/data_model_registry_setup_attempted
```

This marker means: "a clone was attempted on this machine, at this time — don't automatically re-attempt from an automated caller." It does not mean the clone succeeded. Automated callers check for this marker's existence before invoking this workflow at all, so they only ever attempt once per machine, not once per engagement or release. A person running this command directly and interactively should feel free to re-run it any time regardless of the marker — the marker only gates *automatic* invocation, never a consultant's own deliberate one.

### Step 2: Clone

Prefer the `gh` CLI — it uses whatever `gh auth login` token is already active, which works non-interactively and fails cleanly on an auth error. Plain `git clone` over HTTPS depends on a credential helper being separately configured (keychain, Git Credential Manager, a PAT) and, run non-interactively via this command, either hangs prompting for a username/password or fails outright if that isn't set up — so it's a fallback only.

```bash
mkdir -p ~/.wire
if command -v gh >/dev/null 2>&1; then
  gh repo clone rittmananalytics/wire-data-model-registry ~/.wire/data-model-registry
else
  git clone https://github.com/rittmananalytics/wire-data-model-registry.git ~/.wire/data-model-registry
fi
```

### Step 3: Handle the result

**If the clone succeeds**, report:
```
✅ Data model registry set up at ~/.wire/data-model-registry/.

/wire:data_model-generate and /wire:data_model-validate will now automatically check
this for a canonical vertical match on every engagement. This is advisory only — it
proposes, never forces, and any engagement can decline the match at generate time.
```

**If the clone fails** (403, 404, or any authentication/access error), report plainly — this is an expected, unremarkable outcome for anyone outside RA, not an error to troubleshoot:
```
Could not clone rittmananalytics/wire-data-model-registry — this is a private RA-internal
repo. If you're not sure you should have access, this command isn't relevant to you: Wire
works completely normally without it, this just skips the canonical-vertical proposal step
in data_model-generate/validate. If you believe you should have access, check with whoever
manages RA's GitHub org.
```

The one exception worth a distinct message: if `gh` isn't installed and the fallback `git clone` fails with a credential/authentication error specifically (not a 404), it may just mean git isn't authenticated yet rather than lacking access — mention that installing `gh` and running `gh auth login` is the fastest fix, then re-running this command.

Do not retry automatically beyond that one distinction, and do not treat a plain access-denied outcome as a bug — a failed clone here is a normal, expected outcome for the majority of people who might run this command.

**When invoked automatically** (not directly by a person — see Step 1.5), skip the messages above entirely. Write the attempted marker (Step 1.5) and, on success only, note it briefly and unobtrusively in the calling command's own output (e.g. one line: "Data model registry found — canonical-vertical matching available for this engagement"). On failure, say nothing at all — an automated attempt failing is not news to surface, since it's the default outcome for most people.

## Notes

- This is a personal, per-machine setup, not a framework-level sync. There's no pinned version — you get whatever's on the registry's `main` branch when you run this, and `git pull` to refresh whenever you like. Contrast with `wire/scripts/sync-data-model-registry.sh`, which is the *framework maintainers'* pinned, reviewed sync into the Wire repo's own `wire/data-model-registry/` (used only when developing Wire itself, not by consultants running engagements).
- `data_model-generate`/`validate` check `wire/data-model-registry/` first (present only inside the Wire framework source repo) and fall back to `~/.wire/data-model-registry/` (this command's output) — same two-tier "dev mode / personal setup" pattern `droughty-setup.md` uses for its own pinned version file.
