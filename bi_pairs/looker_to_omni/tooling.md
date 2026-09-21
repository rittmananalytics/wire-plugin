# Looker to Omni: tooling

What exists outside Wire, what Wire uses from it, and where each piece fits in the release.

## Omni agent skills (required)

`exploreomni/omni-agent-skills`, Apache 2.0. Install once per machine:

```
/plugin marketplace add exploreomni/omni-agent-skills
/plugin install omni-analytics@omni-analytics
```

Gemini CLI and other agents: `npx skills add exploreomni/omni-agent-skills`. Wire's `omni` skill (`wire/skills/omni/SKILL.md`) wraps the package and documents the connection step.

| Skill | Used by |
|---|---|
| `omni-model-builder` | `omni-target-setup` (branch, schema refresh), `omni-model-generate` (`yaml-create`, `yaml-get`), `omni-model-validate` (`omni models validate`) |
| `omni-model-explorer` | `omni_audit` on a brownfield target; `omni-content-validate` field existence checks |
| `omni-content-builder` | `omni-content-generate` (`omni documents v2-create`, `v2-patch-draft`, `v2-publish-draft`) |
| `omni-content-explorer` | `omni_audit`; folder checks |
| `omni-query` | `bi-equivalency-validate` (`omni query run` with `branchId`) |
| `omni-admin` | `omni-target-setup` (groups, user attributes, permissions), `cutover` (access switch, schedules) |
| `omni-ai-optimizer`, `omni-ai-eval` | Post-cutover enablement, not migration |

## Omni CLI (required)

Source: https://github.com/exploreomni/cli. On a Claude Code machine the simplest install is the prompt "Install the Omni CLI from https://github.com/exploreomni/cli"; verify with `omni --version`.

Authenticated through a named profile (`omni config use <profile>`) or `OMNI_BASE_URL` plus `OMNI_API_TOKEN`. The migration never writes to the production model: everything goes to the branch created by `omni-target-setup`, and merging (`omni models merge-branch`, or `omni models commit` for a git-connected model) happens only on the release director's ruling at cutover.

`omni-sync` (Omni's local development package) streams validation errors while editing model YAML locally. Useful during a batch's `needs_human` work; not required.

## Omni's Looker dashboard migration skill (optional, recommended for content)

Omni documents a `looker-to-omni-dashboard` agent skill with two scripts, `looker_dashboard_inspect.py` and `omni_dashboard_builder.py`, at `docs.omni.co/guides/migrations/looker-to-omni-skill`. It migrates one dashboard at a time: reads the dashboard from the Looker API, maps fields to the Omni model, generates a `build_<name>()` function and creates the document.

How `omni-content-generate` uses it: as the write mechanism for a planned dashboard, after Wire's plan step has mapped fields and decided the skipped tiles. The skill assumes the Omni model already has every field, which the model phase guarantees. The skill skips text and markdown tiles, table calculations referencing runtime values, and styling, which matches Wire's skipped-tile reasons.

Obtain the scripts from Omni's docs appendix at the time of the engagement; they are not vendored here. Record the version used in `omni_content.md`.

Two things to know before using the builder (read 2026-09-04):

- It creates documents through the stable `POST /v1/documents` endpoint and then applies layout, filter wiring and visualisation config through an export and import cycle on `/api/unstable/` endpoints. The guide itself says future versions should move to the v2 documents API, which supports layout (`containers`) and filters (`controls`) natively. Wire's `omni-content-generate` writes through `omni documents v2-create` for that reason; the builder is an optional write mechanism for engagements that already have it working.
- Its `delete_existing_by_name()` deletes every accessible document with a matching name, in any folder, before recreating. Wire never uses that path: the content manifest's `target_identifier` is the only handle, and a re-run patches or recreates by identifier, never by title.

Its `looker_dashboard_inspect.py` is a good shape for the content half of `looker-audit-generate`: `sdk.dashboard`, `sdk.dashboard_dashboard_filters`, `sdk.dashboard_dashboard_elements`, output sorted by layout position with fields, filters, sorts, pivots, dynamic fields, hidden fields and the filter-listen map per tile.

`omni-sync` (`npm install -g @omni-co/model-local-editor`; `omni-sync init <model_id> --branch <name> --create-branch`, `omni-sync start <model_id>`) watches local model YAML, pushes to the branch and streams validation errors. Useful during a batch's `needs_human` work.

## Omni's inventory tooling and converter (confirm before relying on it)

Omni's migration guide names a "LookML converter" (explores to topics), an asset inventory export, a Modeling Agent and a Workbook Agent. None of them appear in Omni's migration documentation. Before a `bi_migration` engagement, ask Omni whether partners can use the converter and the inventory export. If yes, record them here for that engagement (`bi_pair_overrides/looker_to_omni/tooling.md`) and use the converter as a first pass the way `bqms_first_pass.md` treats the BigQuery Migration Service: Omni's output first, Wire's converter and `needs_human` list to finish and to check.

## Partner converters (optional)

Tasman's LookML to Omni YAML converter (proprietary) reports 30 seconds per view against 30 to 45 minutes by hand, and covers field-level property mapping and parameters to templated filters. If a client has access, treat it the same way: first pass, then Wire's converter run on the same input to produce the `needs_human` list and the lint.

## Looker side

| Need | Tool |
|---|---|
| LookML | The client's LookML repo, cloned locally (`bi_migration.lookml_repo_path`) |
| Dashboards, Looks, tiles, folders, users, groups | Looker API 4.0 (`LOOKERSDK_BASE_URL`, `LOOKERSDK_CLIENT_ID`, `LOOKERSDK_CLIENT_SECRET`) or the Looker MCP server |
| Usage (`views_90d`, `last_viewed`) | System Activity `history` explore; needs the `see_system_activity` permission |
| Source side of parity | `run_inline_query` on the tile's query, or the Looker MCP `query` tool |

## Wire side

| Piece | Path |
|---|---|
| Converter | `scripts/lookml_to_omni.py` in the installed plugin (`wire/scripts/` in the framework repo) |
| Parity comparator | `scripts/bi_parity.py`: one test contract, two result sets, one verdict document with an outcome (`PASS`, `FAIL`, `BLOCKED`, `INCONCLUSIVE`, `NOT_RUN`, `ACCEPTED_DIFFERENCE`) |
| Evidence fingerprints | `scripts/bi_evidence.py`: fingerprint over seven components; `invalidate` says which evidence a change stales |
| Pair files | `bi_pairs/looker_to_omni/` |
| Engagement overrides | `.wire/engagement/bi_pair_overrides/looker_to_omni/` |
| Tests | `wire/tests/bi_migration/` |
