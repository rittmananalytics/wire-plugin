// Session context and the status line (wire#270 D2, D6): the active release
// resolved once at session start, a status-line entry, one session-scoped
// system-prompt section carrying the release's decisions, and the context
// percentage with one toast at 85 percent. Replaces the UserPromptSubmit
// settings hook /wire:new installed (TEMPLATES/wire-session-check.sh) and
// TEMPLATES/wire-statusline.sh.

import type { WireActiveRelease, WireContextCache } from '../types'
import { WIRE_VERSION } from './constants'
import { type Options, exists, frameworkFile, gitBranch, isOn, listReleases, mtimeOf, readText, run1, sessionIdOf, toast } from './host'
const ACTIVE = { plugin: 'wire', key: 'active' } as const
const CONTEXT = { plugin: 'wire', key: 'context' } as const
const CONTEXT_PERCENT = { plugin: 'wire', key: 'contextPercent' } as const
const CONTEXT_WARNED = { plugin: 'wire', key: 'contextWarned' } as const

async function activeOf($: any): Promise<WireActiveRelease | null> {
  const { value } = await $.state.get(ACTIVE)
  return value ?? null
}
import {
  approvedCount, artifactStatesOf, businessRulesSummary, claimOf, frontMatterOf, openIterationsOf,
  orchestrationModeOf, parkedDecisionsOf, releaseContext, resolveActiveRelease, rulingsOf, scalarOf,
  sessionLine, statusLine,
} from './release'

const DAY_MS = 24 * 60 * 60_000
const CONTEXT_WARN_AT = 85

export async function resolveActive($: any, cwd: string): Promise<WireActiveRelease> {
  const releases = await listReleases($, cwd)
  const now = await $.clock.now()
  const infos = releases.map(r => ({
    folder: r.folder,
    claimedBranch: r.statusText ? claimOf(frontMatterOf(r.statusText).front)?.branch || null : null,
    daysSinceWrite: r.mtime > 0 ? (now - r.mtime) / DAY_MS : null,
  }))
  const branch = await gitBranch($, cwd)
  const r = resolveActiveRelease(infos, null, branch || null)
  const contextMd = await readText($, `${cwd}/.wire/engagement/context.md`)
  const clientName = contextMd ? scalarOf(frontMatterOf(contextMd).front || contextMd, 'client_name') ?? '' : ''
  return { resolution: r.resolution, release: r.release, candidates: r.candidates, mode: orchestrationModeOf(contextMd), clientName }
}

type Snapshot = {
  active: WireActiveRelease
  front: string
  body: string
  projectType: string | null
  approved: number
  parked: ReturnType<typeof parkedDecisionsOf>
  claimUser: string | null
}

async function snapshot($: any, cwd: string, active: WireActiveRelease): Promise<Snapshot> {
  const text = active.release ? await readText($, `${cwd}/.wire/releases/${active.release}/status.md`) : null
  const { front, body } = frontMatterOf(text ?? '')
  return {
    active, front, body,
    projectType: scalarOf(front, 'project_type') ?? scalarOf(front, 'release_type'),
    approved: approvedCount(artifactStatesOf(front)),
    parked: parkedDecisionsOf(front),
    claimUser: claimOf(front)?.user ?? null,
  }
}

/** Re-reads the active release and pins the status line. */
export async function refreshStatus($: any): Promise<void> {
  const active = await activeOf($)
  if (!active) {
    return
  }
  const cwd = await $.session.cwd()
  const s = await snapshot($, cwd, active)
  const { value: percent } = await $.state.get(CONTEXT_PERCENT)
  try {
    $.ui.status(statusLine({
      version: WIRE_VERSION, release: active.release, candidates: active.candidates, projectType: s.projectType,
      approved: s.approved, parked: s.parked.length, claimUser: s.claimUser,
      contextPercent: typeof percent === 'number' && percent > 0 ? percent : null,
    }))
  } catch {
    // no surface
  }
}

/** The next command the release can run, from wire_gate.py; null when unknown. */
export async function nextActionOf($: any, cwd: string, release: string): Promise<string | null> {
  const script = await frameworkFile($, 'scripts/wire_gate.py')
  if (!script) {
    return null
  }
  const out = await run1($, ['python3', script, 'next', '--repo', cwd, '--release', release], cwd, 20_000)
  try {
    const j = JSON.parse(out)
    return typeof j.next === 'string' ? j.next : null
  } catch {
    return null
  }
}

async function composeSection($: any, options: Options, cwd: string, active: WireActiveRelease): Promise<string> {
  const release = active.release
  const statusPath = release ? `${cwd}/.wire/releases/${release}/status.md` : ''
  const decisionsPath = release ? `${cwd}/.wire/releases/${release}/decisions.md` : ''
  const rulesPath = release ? `${cwd}/.wire/releases/${release}/artifacts/business_rules.yaml` : ''
  const mtimes = release ? [await mtimeOf($, statusPath), await mtimeOf($, decisionsPath), await mtimeOf($, rulesPath)] : [0, 0, 0]
  const { value: cached } = await $.state.get(CONTEXT)
  const hit = cached as WireContextCache | null
  if (hit && hit.release === release && hit.mtimes.join(',') === mtimes.join(',')) {
    return hit.text
  }
  const releases = await listReleases($, cwd)
  const s = await snapshot($, cwd, active)
  const lines = [sessionLine({
    clientName: active.clientName, release, candidates: active.candidates, projectType: s.projectType,
    approved: s.approved, parked: s.parked, mode: active.mode, releaseCount: releases.length,
  })]
  if (release) {
    const now = await $.clock.now()
    lines.push('', releaseContext({
      release,
      projectType: s.projectType,
      profile: scalarOf(s.front, 'build_profile') ?? scalarOf(s.front, 'discovery_profile') ?? scalarOf(s.front, 'migration_profile'),
      phase: scalarOf(s.front, 'current_phase'),
      nextAction: await nextActionOf($, cwd, release),
      parked: s.parked,
      rulings: rulingsOf(await readText($, decisionsPath)),
      rules: businessRulesSummary(await readText($, rulesPath), new Date(now).toISOString()),
      iterations: openIterationsOf(s.body),
      claim: claimOf(s.front),
      mode: active.mode,
      maxLines: typeof options.contextLines === 'number' && options.contextLines > 0 ? options.contextLines : 60,
    }))
  }
  const text = lines.join('\n')
  await $.state.set(CONTEXT, { text, mtimes, release } satisfies WireContextCache)
  return text
}

async function writeModRecord($: any, cwd: string, active: WireActiveRelease): Promise<void> {
  // /wire:start reads this to say whether the mod is loaded (wire#270 D8).
  try {
    const now = await $.clock.now()
    await $.fs.write(`${cwd}/.wire/local/mod.json`, JSON.stringify({
      version: WIRE_VERSION, session_id: await sessionIdOf($), loaded_at: new Date(now).toISOString(),
      release: active.release, mode: active.mode,
    }))
  } catch {
    // .wire/local may not exist; /wire:start then reports the mod as not seen
  }
}

/** session.start, after the engine's own: resolve the release, pin the status line, write the mod record, suggest the next command. */
export async function startContext($: any, options: Options, cwd: string): Promise<void> {
  if (!(await exists($, `${cwd}/.wire`))) {
    return
  }
  const active = await resolveActive($, cwd)
  await $.state.set(ACTIVE, active)
  await refreshStatus($)
  await writeModRecord($, cwd, active)
  if (active.release && isOn(options.context, await $.env.get('WIRE_CONTEXT'))) {
    const nextAction = await nextActionOf($, cwd, active.release)
    if (nextAction) {
      try {
        await $.prompt.suggest({ text: nextAction })
      } catch {
        // no prompt box (headless)
      }
    }
  }
}

/** prompt.compose: the engine's sections plus one session-scoped Wire section. */
export async function composePrompt($: any, options: Options, result: any): Promise<any> {
  if (!isOn(options.context, await $.env.get('WIRE_CONTEXT'))) {
    return result
  }
  const active = await activeOf($)
  if (!active) {
    return result
  }
  const cwd = await $.session.cwd()
  const text = await composeSection($, options, cwd, active)
  return { ...result, sections: [...(result?.sections ?? []), { id: 'wire:release', text, scope: 'session' }] }
}

/** session.measure: keep the percentage, refresh the status line, toast once at 85 percent. */
export async function measureContext($: any, e: any): Promise<void> {
  const percent = e?.context?.percent
  if (typeof percent !== 'number') {
    return
  }
  await $.state.set(CONTEXT_PERCENT, percent)
  await refreshStatus($)
  const { value: warned } = await $.state.get(CONTEXT_WARNED)
  if (percent >= CONTEXT_WARN_AT && warned !== true) {
    await $.state.set(CONTEXT_WARNED, true)
    toast($, `Context at ${percent}%. /wire-handoff writes a handoff file for the next session; /compact summarises in place.`)
  }
}

/** After a write tool ran: a changed status.md moves the status line. */
export async function afterStatusWrite($: any, e: any, result: any): Promise<void> {
  if (/\/status\.md$/.test(String(e.file_path ?? '')) && !result?.deny) {
    await refreshStatus($)
  }
}
