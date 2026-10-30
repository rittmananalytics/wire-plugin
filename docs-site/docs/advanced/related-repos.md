---
sidebar_position: 4
title: Related Repos
---

# Related Repos

A client's work is often spread across several repositories. One repository holds the Airflow DAGs that land the sources and schedule the runs; another holds the dbt project that models them; a third holds the LookML. Work in one of them often needs facts from another: which DAG writes the table a dbt source reads, what file format and schedule it uses, which models read a table a DAG is about to change.

Related repos let one Wire session read the client's other repositories. The engagement lists them once. A session can then look up code in them, read only, and cite what it read by repository and commit.

## What is it?

| Part | Where | Committed |
|---|---|---|
| The list of related repos | `related_repos:` in `.wire/engagement/context.md` | yes |
| Where your own clone of each one is | `.wire/local/repos.yml` | no (git-ignored) |
| The commit each refresh read | `.wire/local/repos_state.json` | no (git-ignored) |
| The command | `/wire:utils-repos` | |
| The script it runs | `scripts/related_repos.py` (plain Python and git, no AI call) | |

An entry looks like this:

```yaml
related_repos:
  - id: airflow
    github_url: https://github.com/<org>/<repo>
    default_branch: main
    role: orchestration
    paths: [dags_*/, plugins/]
    description: Airflow DAGs that land sources and schedule dbt runs
    lookup: on_request
```

`role` is one of `code`, `dbt`, `orchestration`, `ingestion`, `lookml`, `omni`, `infrastructure` or `other`. `paths` limits searches to where the relevant code is.

If your engagement already has `client_repo:` (a dedicated delivery repo pointing at one client code repo), that keeps working. It is read as one related repo with the id `client_repo` and the role `code`.

## How do I add a repo?

```
/wire:utils-repos add https://github.com/<org>/<repo> --id airflow --role orchestration --paths 'dags_*/,plugins/'
```

Wire shows the entry it would add to `context.md` and asks before writing. Commit the change so the rest of the team has the same list. `/wire:utils-repos remove <id>` takes an entry out the same way; it leaves any local copy alone.

`/wire:adopt` also proposes entries when it finds signs of other repositories: dbt sources whose tables are loaded by nothing in the repository, DAGs that call dbt, links to other repositories of the same organisation. Nothing is added without your confirmation.

## Where do the copies come from?

If you already have a clone, tell Wire where it is in `.wire/local/repos.yml`:

```yaml
airflow: ~/code/composer-dags
```

Otherwise `/wire:utils-repos refresh` clones the repository to `~/.wire/repos/<org>/<repo>/`. The clone is bare and blobless: no working files, and file contents are fetched only when a search reads them.

Wire uses your own git access. It never asks for a password or token and never stores one. If you cannot reach a repository, `refresh` says so and carries on with the others.

## The read-only rule

Wire never commits, pushes, branches, checks out or writes a file in a related repo. In your own clone, `refresh` runs `git fetch`, which moves only the remote-tracking branch (`origin/main`); your checked-out branch and any work in progress are left alone, and searches read `origin/main`, not your working files.

A change a related repo needs is a separate piece of work in that repository. `/wire:work` names it in the plan as a step for whoever owns that repository.

## Lookups and citations

```
/wire:utils-repos list                     each repo: role, commit, how old the fetch is, state
/wire:utils-repos refresh                  fetch the default branch of each one
/wire:utils-repos find orders_raw          search them all
/wire:utils-repos find orders_raw --repo airflow --path 'dags_*/**'
```

`find` searches each copy with `git grep` at the commit the last refresh recorded, and prints each hit with its citation:

```
airflow@1a2b3c4:dags_shop/load_orders.py:3  DESTINATION = "landing_shop.orders_raw"
```

Anything taken from a related repo is cited as `<id>@<short commit>:<path>`, in the session and in any artifact, iteration file or pull request that uses it. The citation names exactly what was read, so a reviewer can open the same file at the same commit.

## When does Wire look?

Only when you ask, or when a command offers a lookup and you accept. Wire does not search related repos by default.

- At the start of a session, the engagement context lists the related repos with their role, commit and fetch age, so the session knows they exist. It does not search them.
- `/wire:work` reads the ticket. When the ticket names a source, table, model or DAG, it looks for related repos whose role matches. For a repo with `lookup: offer` it offers the lookup; for a repo with `lookup: on_request` (the default) it only names the repo. Accepted results go in the iteration file with their citations and into the pull request body.

The `lookup` setting on each entry is `on_request` by default. Set it to `offer` for the repos you want `/wire:work` to offer. `auto` is reserved for a later release.

## An example: a dbt ticket that needs the Airflow repo

The engagement works in the dbt repository. The Airflow repository that lands the sources is listed as a related repo with `lookup: offer`.

| You say | Wire does |
|---|---|
| (session start) | Lists the related repos: `airflow`, role `orchestration`, its commit and when it was last fetched |
| "Pick up OPS-210: add a staging model for the new purchase order lines source." | Reads the ticket and the release. The ticket names the landing table `landing_shop.po_lines`. Because `airflow` has a matching role and `lookup: offer`, Wire offers to look it up there |
| "Yes." | Runs `/wire:utils-repos find po_lines --repo airflow`. Finds the DAG config that writes the table and the load SQL, with the column list and the daily schedule. Records both hits with their citations in the ticket's iteration file, then plans the staging model from them |
| (later) | The pull request body carries the same citations, so the reviewer can open the DAG file at the commit Wire read |

If the lookup shows the Airflow side needs a change too, Wire does not make it. It adds a step to the plan for whoever owns the Airflow repository, and that change is a separate ticket there.

To refresh the copies before a lookup, say "refresh the related repos" or run `/wire:utils-repos refresh`. `/wire:utils-repos check` reports any entry that is badly formed: a missing or repeated id, a missing URL, a URL holding a credential, or an unknown role or field. `list` shows which repos are unreachable or have no local copy yet.

## What stays private?

The list of related repos is client data, kept in the client's repository. Nothing about it ships in Wire. The local files under `.wire/local/` are personal and git-ignored; `/wire:new` and `/wire:adopt` add the ignore line.
