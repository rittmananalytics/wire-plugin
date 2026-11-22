---
wire_schema: "1.0"
command: utility
artifact: repos
domain: utils
release_types: []
action_type: utility
logs_execution: false
description: List the client's related repositories and look up code in them, read only, cited by repo and commit
argument-hint: "<list | refresh [<id>] | find <text> [--repo <id>] [--path <glob>] | add <github_url> --id <id> --role <role> | remove <id> | check>"

---

# Related Repos Command

## Purpose

A client's work often spans several repositories: an Airflow repo lands the
sources and schedules the runs, a dbt repo models them, a LookML repo serves
them. Work in one needs context from the others. This command lets a session
in one repository read the client's other repositories, read only, and cite
what it read by repo and commit (wire#381).

The engagement lists the related repos once, in the `related_repos:` block of
`.wire/engagement/context.md`. Where each person's copy is lives in
`.wire/local/repos.yml`, which is git-ignored. A repo with no local copy is
cloned blobless to `~/.wire/repos/<org>/<repo>/` with the person's own git
access. The schema is `wire/schemas/related-repos-schema.md`.

`client_repo:` keeps working: it is read as one entry, id `client_repo`, role
`code`.

## Usage

```bash
/wire:utils-repos list                                  # each repo: role, commit, fetch age, state
/wire:utils-repos refresh                               # clone or fetch every repo
/wire:utils-repos refresh airflow                       # one repo
/wire:utils-repos find orders_raw                       # search every repo at its recorded commit
/wire:utils-repos find orders_raw --repo airflow --path 'dags_*/**'
/wire:utils-repos add https://github.com/<org>/<repo> --id airflow --role orchestration --paths 'dags_*/,plugins/'
/wire:utils-repos remove airflow
/wire:utils-repos check                                 # check the list and the local file
```

Not scoped to a release. Run in the engagement repository.

## Workflow

Every step runs `python3 <wire>/scripts/related_repos.py <sub-command>` in the
engagement repository and shows its output. The script is plain Python and
git; it makes no AI call and no network call except `git clone` and
`git fetch`.

### list

Run `related_repos.py list`. Show its table: repo id, role, lookup setting,
short commit, fetch age, state (`ready`, `stale`, `unreachable`,
`not refreshed`, `not fetched`) and where the local copy is. `list` reads
only what is on disk.

If a repo is `not fetched` or older than a day, offer `refresh`. Do not run it
unasked.

### refresh

Run `related_repos.py refresh [<id>]`. For each repo it fetches the default
branch, or clones it the first time, and records the commit it read in
`.wire/local/repos_state.json`. Report one line per repo.

- **Unreachable:** say so with git's reason and carry on with the others. The
  usual cause is that the person has no access to that repository. Never ask
  for a password or token, never suggest putting one in the URL, and never
  store one. Point to `gh auth login` (or the person's own git setup) if the
  reason is an authentication error.
- **Stale:** the fetch failed but an earlier one worked. Lookups still read
  the earlier commit; say which.

### find

Run `related_repos.py find <text> [--repo <id>] [--path <glob>] [--regex]`.
It searches each local copy with `git grep` at the commit the last refresh
recorded, within the entry's `paths` unless `--path` is given, and prints one
line per hit: `<id>@<short commit>:<path>:<line>  <text>`.

Present the hits grouped by repo, with the citation for each. When you use a
finding in an answer, an artifact, an iteration file or a PR body, cite it as
`<id>@<short commit>:<path>`. To read a whole file a hit names, read it at the
same commit: `git -C <local copy> show <commit>:<path>`. Never read the
working tree of a person's clone: it may hold unfinished work on another
branch.

### add

1. Run `related_repos.py add <github_url> --id <id> --role <role> [--branch B]
   [--paths a,b] [--description T] [--lookup L]` without `--yes`. It shows the
   entry it would add as a diff of `context.md` and writes nothing. It refuses
   an id or URL already listed, and a URL with a user or token in it.
2. Ask: **Add / Change / Cancel**. Suggest a role from the repository's
   contents if the person did not give one (`dbt_project.yml`: `dbt`; a `dags`
   folder: `orchestration`; `*.lkml`: `lookml`).
3. On **Add**, run the same command with `--yes`, then commit
   `.wire/engagement/context.md` on the current branch
   (`specs/utils/commit.md`), message `repos: add <id>`.
4. Offer `refresh <id>`.

If the person already has a clone, offer to write its path to
`.wire/local/repos.yml` (`<id>: <path>`). That file is personal and is not
committed.

### remove

1. Run `related_repos.py remove <id>` without `--yes`: it shows the diff.
2. Ask: **Remove / Cancel**. On **Remove**, run it with `--yes` and commit
   `context.md`, message `repos: remove <id>`.
3. Any local copy is left where it is. Say where it is, so the person can
   delete it if they want to.

`client_repo` cannot be removed this way; it is edited by hand.

### check

Run `related_repos.py check`. It reports ids that are missing, malformed or
listed twice, unknown roles and lookup values, unknown fields, a URL listed
twice or holding a credential, lines in `.wire/local/repos.yml` for repos not
listed, and `.wire/local/` not being git-ignored. Exit 1 on any problem.
Offer to fix each one; fix none unasked.

## Rules

1. **Read only.** Never commit, push, check out, branch, merge, or write a
   file in a related repo, by script or by hand. A change a related repo needs
   is a separate piece of work in that repository: say what it is and where,
   and stop.
2. **On request.** Look in a related repo only when the person asks, or when
   a command offers a lookup and the person accepts. The `lookup` setting on
   an entry is `on_request` by default; `offer` lets commands offer; `auto` is
   reserved and treated as `offer`.
3. **Cite.** Every finding taken from a related repo carries its citation,
   `<id>@<short commit>:<path>`, wherever it is used.
4. **No credentials.** Git uses the person's own access. Nothing asks for,
   writes or stores a credential.
5. **Nothing private leaks.** The entries are client data in the client's
   repository.
6. Plain text, no emojis.

## Gemini CLI

The same spec and script. No change.
