// Session management (wire#270 D7, wire#43): the lane stall timer, the
// handoff template as compaction instructions, /wire-handoff through one
// $.model.fork, and the opt-in drift watch.

import type { WireActiveRelease, WireLane } from '../types'
import { type Options, appendNote, exists, frameworkFile, mtimeOf, readText, sessionIdOf, toast } from './host'
const ACTIVE = { plugin: 'wire', key: 'active' } as const
const LANES = { plugin: 'wire', key: 'lanes' } as const

async function activeOf($: any): Promise<WireActiveRelease | null> {
  const { value } = await $.state.get(ACTIVE)
  return value ?? null
}
async function lanesOf($: any): Promise<WireLane[]> {
  const { value } = await $.state.get(LANES)
  return Array.isArray(value) ? value : []
}
async function saveLanes($: any, lanes: WireLane[]): Promise<void> {
  await $.state.set(LANES, lanes)
}
import { sendEvent } from './telemetry'
const DRIFT = { plugin: 'wire', key: 'drift' } as const
const CONTEXT_PERCENT = { plugin: 'wire', key: 'contextPercent' } as const
const TURNS = { plugin: 'wire', key: 'turns' } as const

export const STALL_MINUTES = 30
export const STALL_CHECK_MS = 5 * 60_000
export const DRIFT_EVERY_TURNS = 8
export const DRIFT_FROM_PERCENT = 50

/** The handoff template shipped in TEMPLATES/handoff-template.md, or this copy when the file is not found. */
export const HANDOFF_FALLBACK = [
  'Write a Wire session handoff for the next session, as plain Markdown with these headings, each a short list:',
  '## What was built (files and artifacts, by release folder)',
  '## Rulings made (R-n ids and one line each; parked decisions still open)',
  '## State (status.md artifact states that changed; lanes and their state files; anything blocked and why)',
  '## Next command (the next Wire command in full, as it would be typed, and the stop point)',
  'Name every Wire command in full (/wire: prefix, release folder, flags). Do not invent work that did not happen.',
].join('\n')

export async function handoffTemplate($: any): Promise<string> {
  const path = await frameworkFile($, 'TEMPLATES/handoff-template.md')
  const text = path ? await readText($, path) : null
  return text?.trim() || HANDOFF_FALLBACK
}

/** Lanes past the stall threshold with no completion and not yet reported. */
export function stalledLanes(lanes: readonly WireLane[], mtimes: ReadonlyMap<string, number>, texts: ReadonlyMap<string, string | null>, now: number): WireLane[] {
  return lanes.filter(l => {
    if (l.stalledAt !== null) {
      return false
    }
    const file = l.stateFile ?? ''
    const text = texts.get(file) ?? null
    if (text && /^\s*(status|state)\s*:\s*complete\b/im.test(text)) {
      return false
    }
    const last = Math.max(mtimes.get(file) ?? 0, l.startedAt)
    return now - last > STALL_MINUTES * 60_000
  })
}

export function stallNote(lane: WireLane): string {
  return `Wire: lane "${lane.label}" has written nothing for ${STALL_MINUTES} minutes and is not complete${lane.stateFile ? ` (${lane.stateFile})` : ''}. Treat it as stalled: re-dispatch its remaining items to a new lane per the resume contract (specs/utils/director_operating_model.md).`
}

export function driftPrompt(decisionsMd: string | null, skill: string | null): string {
  return [
    'Wire drift check. Answer with the single word NONE, or with one line per contradiction.',
    'Which instructions in the recent turns contradict a ruling below, or a convention of the active Wire skill? Name the ruling id or the convention.',
    '',
    'Rulings (decisions.md):',
    (decisionsMd ?? '').trim() || '(none recorded)',
    skill ? `\nActive skill: ${skill}` : '',
  ].join('\n')
}

/** session.start: the handoff command and the stall timer. */
export async function startSession($: any): Promise<void> {
  await $.command.register({ name: 'wire-handoff', description: "Wire: write a session handoff (built, rulings, state, next command) to the release's lanes folder" })
  $.clock.every(STALL_CHECK_MS, async () => {
    try {
      await checkStalls($)
    } catch {
      // the timer is best effort
    }
  })
}

export async function checkStalls($: any): Promise<WireLane[]> {
  const lanes = await lanesOf($)
  if (lanes.length === 0) {
    return []
  }
  const now = await $.clock.now()
  const mtimes = new Map<string, number>()
  const texts = new Map<string, string | null>()
  for (const l of lanes) {
    if (l.stateFile) {
      mtimes.set(l.stateFile, await mtimeOf($, l.stateFile))
      texts.set(l.stateFile, await readText($, l.stateFile))
    }
  }
  const stalled = stalledLanes(lanes, mtimes, texts, now)
  for (const l of stalled) {
    toast($, `Lane "${l.label}" stalled: no state-file write for ${STALL_MINUTES} minutes.`)
    await appendNote($, stallNote(l))
  }
  if (stalled.length > 0) {
    await saveLanes($, lanes.map(l => (stalled.some(s => s.agentId === l.agentId) ? { ...l, stalledAt: now } : l)))
  }
  return stalled
}

/** session.compact on the main loop in a Wire repo: the handoff template joins the instructions. */
export async function onCompact($: any, e: any, next: any): Promise<any> {
  if (e.agentId) {
    return next(e)
  }
  const cwd = await $.session.cwd()
  if (!(await exists($, `${cwd}/.wire`))) {
    return next(e)
  }
  const template = await handoffTemplate($)
  const instructions = e.instructions ? `${e.instructions}\n\n${template}` : template
  return next({ ...e, instructions })
}

export async function handoffCommand($: any): Promise<{ text: string }> {
  const active = await activeOf($)
  const cwd = await $.session.cwd()
  if (!active?.release) {
    return { text: 'No active release to write a handoff for. Run /wire:start to pick one.' }
  }
  const reply = await $.model.fork({ prompt: await handoffTemplate($) })
  if (!reply?.isAnswered) {
    return { text: `No handoff written: ${reply?.reason ?? 'the model did not answer'}.` }
  }
  const sid = (await sessionIdOf($)) || 'session'
  const path = `${cwd}/.wire/releases/${active.release}/lanes/handoff-${sid}.md`
  const now = await $.clock.now()
  const header = `# Session handoff — ${active.release}\n\nSession: ${sid}\nWritten: ${new Date(now).toISOString()}\n\n`
  try {
    await $.fs.write(path, `${header}${reply.text.trim()}\n`)
  } catch {
    return { text: `Could not write ${path}. The handoff:\n\n${reply.text}` }
  }
  const u = reply.usage ?? {}
  const tokens = (u.input_tokens ?? 0) + (u.output_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0) + (u.cache_read_input_tokens ?? 0)
  return { text: `Handoff written to ${path} (${tokens} tokens, ${u.cache_read_input_tokens ?? 0} read from cache).` }
}

/** turn.complete on the main loop: the drift watch, opt-in, every eight turns once context passes 50 percent. */
export async function onMainTurnComplete($: any, options: Options): Promise<void> {
  const { value: turns } = await $.state.get(TURNS)
  const n = (typeof turns === 'number' ? turns : 0) + 1
  await $.state.set(TURNS, n)
  const watch = options.driftWatch === true || (await $.env.get('WIRE_DRIFT_WATCH')) === 'true'
  if (!watch || n % DRIFT_EVERY_TURNS !== 0) {
    return
  }
  const { value: percent } = await $.state.get(CONTEXT_PERCENT)
  if (typeof percent !== 'number' || percent < DRIFT_FROM_PERCENT) {
    return
  }
  const active = await activeOf($)
  if (!active?.release) {
    return
  }
  try {
    const cwd = await $.session.cwd()
    const decisions = await readText($, `${cwd}/.wire/releases/${active.release}/decisions.md`)
    const reply = await $.model.fork({ prompt: driftPrompt(decisions, null) })
    if (reply?.isAnswered && !/^\s*none\b/i.test(reply.text)) {
      const hit = reply.text.trim().split('\n')[0] ?? ''
      await $.state.set(DRIFT, hit)
      toast($, `Wire drift watch: ${hit}`)
      await sendEvent($, options, 'wire_drift_hit', { release: active.release, turn: n })
    }
  } catch {
    // the watch is advisory
  }
}
