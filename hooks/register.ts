// The Wire mod: Claude Code function hooks for the Wire plugin (wire#270).
//
// This file carries release 1 (4.1.0): telemetry and execution-log metrics,
// /wire-usage and /wire-studio. It replaced the UserPromptExpansion hook
// (wire-telemetry.sh) and the Stop hook (wire-metrics.sh + wire_metrics.py).
// The later releases are one file per concern under hooks/wire/, registered
// at the end of `register`:
//
// - context.ts  (D2, D6) the active release, the status line, the session
//                system-prompt section with the release's decisions, the
//                context percentage, the next-action suggestion
// - enforce.ts  (D5) the operating model's rules 1, 3 and 6, the budget
//                (lanes_max, warehouse_spend, build slot, spend ledger and
//                cap), the collision guard
// - lint.ts     (D6) convention lint on every write to a dbt, LookML, Cube,
//                dbt Charts or Airflow file
// - band.tsx    (D6) the commands band above the prompt, /wire-ran, the
//                rule-7 `Ran:` check
// - review.ts   (D7) /wire-approve, /wire-park, the hard gate with
//                --override-gate
// - session.ts  (D7) the lane stall timer, compaction instructions,
//                /wire-handoff, the opt-in drift watch
// - upgrade.ts  the safe /wire:upgrade steps applied at session start (the
//                4.0 session-check hook removed, short log headers extended)
//                and the releases that still need the full command
//
// - Telemetry: one `wire_command` event per Wire command, from the event that
//   ran it, so `invoked_by` comes from the engine (typed, orchestrator, lane,
//   autopilot, or studio for sessions Wire Studio opened), not from a scraped
//   prompt. Sent after the hook returns, so it never delays a command.
// - Metrics: each Wire command opens a run; every model request in its loop
//   adds its measured usage; when the loop's turn ends the run closes and the
//   mod fills that command's Duration / Tokens / Cost cells in
//   execution_log.md, or in a ticket's own run log
//   (iterations/<ticket>.execution_log.md, 4.2.0) when the command ran on a
//   ticket branch. A row an orchestrator writes later is filled when it is
//   written.
// - /wire-usage prints this session's runs, with no model turn.
// - /wire-studio start|restart|stop|status runs Wire Studio for the session's
//   repository as a detached local process (one per repository, ports
//   4800-4820), with no model turn.
//
// Off switches: the plugin's options (telemetry, metrics, enforce, context,
// lintOnWrite, driftWatch), or WIRE_TELEMETRY / WIRE_METRICS / WIRE_ENFORCE /
// WIRE_CONTEXT / WIRE_LINT = false and WIRE_DRIFT_WATCH = true. Refusals come
// only from enforce.ts and review.ts, only in orchestrated mode, and every
// one names the rule and what to do instead. Nothing here approves a call.

import type { Register } from 'claude-code'

import type { WireActiveRelease, WireLane, WireRun } from '../types'
import { blockedRowsOf, checkRanLine, ranCommand, registerBandCommand, renderBand } from './wire/band'
import { SEGMENT_IDENTIFY, SEGMENT_TRACK, SEGMENT_WRITE_KEY, WIRE_VERSION } from './wire/constants'
import { afterStatusWrite, composePrompt, measureContext, startContext } from './wire/context'
import { denyAgentCall, denyWrite, onAgentSpawn, onBash, onLaneTurnComplete, onWarehouseCall, warnCollision } from './wire/enforce'
import { type Options, toast } from './wire/host'
const NOT_RUN = { plugin: 'wire', key: 'notRun' } as const
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
import { afterWrite } from './wire/lint'
import { approveCommand, hardGate, parkCommand, registerReviewCommands } from './wire/review'
import { handoffCommand, onCompact, onMainTurnComplete, startSession } from './wire/session'
import { identityOf, post, sendEvent } from './wire/telemetry'
import { autoUpgrade } from './wire/upgrade'
import {
  addUsage,
  backfillLog,
  computeCost,
  emptyUsage,
  identifyBody,
  invokedBy,
  personaOf,
  isOn,
  logCommandOf,
  logRowResult,
  logStamp,
  parseStudioArgs,
  parseStudioRecord,
  releaseOf,
  restArgsOf,
  STUDIO_PORT_FIRST,
  STUDIO_PORT_LAST,
  studioStateName,
  type StudioRecord,
  totalTokens,
  trackBody,
  usageReport,
} from './wire/logic'

const RUNS = { plugin: 'wire', key: 'runs' } as const
const AUTOPILOT = { plugin: 'wire', key: 'autopilot' } as const
const STEP = { plugin: 'wire', key: 'stepUsage' } as const
const MAX_RUNS = 200
const LOG_WINDOW_MS = 30 * 60_000

async function runsOf($: any): Promise<WireRun[]> {
  const { value } = await $.state.get(RUNS)
  return Array.isArray(value) ? value : []
}

async function saveRuns($: any, runs: WireRun[]): Promise<void> {
  await $.state.set(RUNS, runs.slice(-MAX_RUNS))
}

async function run1($: any, argv: string[], cwd: string): Promise<string> {
  try {
    const r = await $.process.run(argv, { cwd, timeoutMs: 3000 })
    return r.exitCode === 0 ? String(r.stdout ?? '').trim() : ''
  } catch {
    return ''
  }
}

async function sendTrack($: any, run: WireRun): Promise<void> {
  const { identity, isNew } = await identityOf($)
  const timestamp = new Date(run.startedAt).toISOString().replace(/\.\d{3}Z$/, 'Z')
  if (isNew) {
    await post($, SEGMENT_IDENTIFY, identifyBody(SEGMENT_WRITE_KEY, identity.userId, {
      username: identity.username, hostname: identity.hostname, os: identity.os, version: WIRE_VERSION, timestamp,
    }))
  }
  let sessionId: string | null = null
  try {
    sessionId = await $.session.id()
  } catch {
    sessionId = null
  }
  await post($, SEGMENT_TRACK, trackBody(SEGMENT_WRITE_KEY, identity.userId, {
    command: run.command.replace(/^\/wire:/, ''),
    invokedBy: run.invokedBy,
    persona: run.persona ?? '',
    timestamp,
    release: run.release,
    sessionId,
    agentId: run.agentId,
    gitRepo: identity.gitRepo,
    gitBranch: identity.gitBranch,
    username: identity.username,
    hostname: identity.hostname,
    os: identity.os,
    version: WIRE_VERSION,
  }))
}

async function startRun($: any, options: Options, run: WireRun): Promise<void> {
  if (isOn(options.metrics, await $.env.get('WIRE_METRICS'))) {
    await saveRuns($, [...(await runsOf($)), run])
  }
  if (isOn(options.telemetry, await $.env.get('WIRE_TELEMETRY'))) {
    $.clock.after(0, () => {
      void sendTrack($, run)
    })
  }
}

// Usage goes to the run's own stepUsage member, never into `runs`: a request
// whose hook finishes after the turn has closed the run cannot overwrite it.
// A request made while no Wire run is open in its loop (an orchestrator
// planning before its first Skill call) is kept under `loose:<turnId>`, so the
// turn-end settlement does not charge it to a command.
async function addStepUsage($: any, agentId: string | null, turnId: string, usage: any): Promise<void> {
  if (!usage) {
    return
  }
  const runs = await runsOf($)
  const run = [...runs].reverse().find(r => r.endedAt === null && r.agentId === agentId)
  const id = run ? run.id : `loose:${turnId}`
  const { value } = await $.state.get({ ...STEP, id })
  const held = value ?? { usage: emptyUsage(), model: null }
  await $.state.set({ ...STEP, id }, {
    usage: addUsage(held.usage, usage),
    model: typeof usage.model === 'string' ? usage.model : held.model,
  })
}

// The loop's turn ended. Its open runs close with their recorded usage; the
// turn's own total (turn.complete's usage, every request of the turn) settles
// what the per-request records have not caught yet, such as the last request,
// whose hook may finish after this one: the remainder goes to the newest run.
async function closeRuns($: any, agentId: string | null, turnId: string, turnUsage: any): Promise<void> {
  const now = await $.clock.now()
  const runs = await runsOf($)
  const open = runs.map((r, i) => ({ r, i })).filter(({ r }) => r.endedAt === null && r.agentId === agentId)
  if (open.length === 0) {
    return
  }
  const recorded = []
  for (const { r } of open) {
    const { value } = await $.state.get({ ...STEP, id: r.id })
    recorded.push(value ?? { usage: emptyUsage(), model: null })
  }
  const { value: loose } = await $.state.get({ ...STEP, id: `loose:${turnId}` })
  const counted = recorded.reduce((sum, acc) => addUsage(sum, acc.usage), addUsage(emptyUsage(), loose?.usage))
  const total = turnUsage ? addUsage(emptyUsage(), turnUsage) : counted
  const remainder = {
    input_tokens: Math.max(0, total.input_tokens - counted.input_tokens),
    output_tokens: Math.max(0, total.output_tokens - counted.output_tokens),
    cache_creation_input_tokens: Math.max(0, total.cache_creation_input_tokens - counted.cache_creation_input_tokens),
    cache_read_input_tokens: Math.max(0, total.cache_read_input_tokens - counted.cache_read_input_tokens),
  }
  open.forEach(({ r, i }, k) => {
    const isNewest = k === open.length - 1
    const usage = isNewest ? addUsage(recorded[k]?.usage ?? emptyUsage(), remainder) : recorded[k]?.usage ?? emptyUsage()
    const model = recorded[k]?.model ?? (typeof turnUsage?.model === 'string' ? turnUsage.model : r.model)
    runs[i] = { ...r, endedAt: now, usage, model }
  })
  await saveRuns($, runs)
}

// The logs a run's row may be in, newest first: the release's execution log
// and, in a release built from tickets, each ticket's own run log
// (iterations/<ticket>.execution_log.md, specs/utils/ticket_delivery.md).
async function logsFor($: any, cwd: string, release: string | null): Promise<string[]> {
  const found: { path: string; mtime: number }[] = []
  const now = await $.clock.now()
  const add = async (path: string, windowed: boolean) => {
    try {
      const st = await $.fs.stat(path)
      if (!windowed || now - st.mtimeMs <= LOG_WINDOW_MS) {
        found.push({ path, mtime: st.mtimeMs })
      }
    } catch {
      // no such log
    }
  }
  const addRelease = async (dir: string, windowed: boolean) => {
    await add(`${dir}/execution_log.md`, windowed)
    try {
      for (const f of await $.fs.list(`${dir}/iterations`)) {
        if (f.kind === 'file' && f.name.endsWith('.execution_log.md')) {
          await add(`${dir}/iterations/${f.name}`, windowed)
        }
      }
    } catch {
      // no ticket run logs in this release
    }
  }
  const named = release ? `${cwd}/.wire/releases/${release}` : null
  let namedExists = false
  if (named) {
    try {
      namedExists = await $.fs.exists(`${named}/execution_log.md`) || await $.fs.exists(`${named}/iterations`)
    } catch {
      namedExists = false
    }
  }
  if (named && namedExists) {
    await addRelease(named, false)
  } else {
    try {
      for (const dir of await $.fs.list(`${cwd}/.wire/releases`)) {
        if (dir.kind === 'dir') {
          await addRelease(`${cwd}/.wire/releases/${dir.name}`, true)
        }
      }
    } catch {
      return []
    }
  }
  return found.sort((a, b) => b.mtime - a.mtime).map(f => f.path)
}

async function backfillPending($: any, options: Options): Promise<void> {
  if (!isOn(options.metrics, await $.env.get('WIRE_METRICS'))) {
    return
  }
  const runs = await runsOf($)
  const cwd = await $.session.cwd()
  let changed = false
  for (let i = 0; i < runs.length; i++) {
    const r = runs[i]
    if (!r || r.filled || r.endedAt === null || totalTokens(r.usage) === 0) {
      continue
    }
    for (const path of await logsFor($, cwd, r.release)) {
      let text: string
      try {
        text = String(await $.fs.read(path))
      } catch {
        continue
      }
      const updated = backfillLog(text, {
        command: r.command,
        usage: r.usage,
        model: r.model,
        durationSeconds: Math.round((r.endedAt - r.startedAt) / 1000),
        notBefore: logStamp(r.startedAt, 24 * 60).slice(0, 10),
      })
      if (updated !== null && updated !== text) {
        await $.fs.write(path, updated)
        runs[i] = { ...r, filled: true, result: logRowResult(updated, r.command) }
        changed = true
        break
      }
    }
  }
  if (changed) {
    await saveRuns($, runs)
  }
}

async function readText($: any, path: string): Promise<string | null> {
  try {
    return String(await $.fs.read(path))
  } catch {
    return null
  }
}

async function personaFor($: any, args: string): Promise<string> {
  const cwd = await $.session.cwd()
  const fileText = await readText($, `${cwd}/.wire/local/persona.yml`)
  const rosterText = await readText($, `${cwd}/.wire/engagement/team.yml`)
  const email = rosterText ? await run1($, ['git', 'config', '--get', 'user.email'], cwd) : ''
  return personaOf(args, await $.env.get('WIRE_PERSONA'), fileText, rosterText, email)
}

async function newRun($: any, id: string, command: string, args: string, agentId: string | null, by: WireRun['invokedBy']): Promise<WireRun> {
  const laneLabel = agentId ? (await lanesOf($)).find(l => l.agentId === agentId)?.label ?? null : null
  return {
    id, command, args: restArgsOf(args), release: releaseOf(args), agentId, invokedBy: by, persona: await personaFor($, args),
    startedAt: await $.clock.now(), endedAt: null, usage: emptyUsage(), model: null, filled: false, result: null, laneLabel,
  }
}

// Rule 7: the orchestrator's reply names every command it ran, in full.
async function checkRanLines($: any, options: Options, open: WireRun[], answer: string): Promise<void> {
  const missing = checkRanLine(open, answer)
  if (missing.length === 0) {
    return
  }
  const runs = await runsOf($)
  const ids = new Set(missing.map(m => m.id))
  await saveRuns($, runs.map(r => (ids.has(r.id) ? { ...r, ranLineMissing: true } : r)))
  toast($, `Rule 7: the reply ran ${missing.map(m => `${m.command}${m.release ? ` ${m.release}` : ''}`).join(', ')} and ended with no Ran: line naming it.`)
  for (const m of missing) {
    await sendEvent($, options, 'wire_ran_line_missing', { command: m.command.replace(/^\/wire:/, ''), release: m.release, invoked_by: m.invokedBy, agent_id: m.agentId })
  }
}

// The band's `Not run:` rows: the precondition gate's `blocked` rows in the active release's log.
async function refreshNotRun($: any): Promise<void> {
  const active = await activeOf($)
  if (!active?.release) {
    return
  }
  const cwd = await $.session.cwd()
  const text = await readText($, `${cwd}/.wire/releases/${active.release}/execution_log.md`)
  const { value } = await $.state.get(NOT_RUN)
  const rows = blockedRowsOf(text, logStamp(await $.clock.now(), 24 * 60).slice(0, 10))
  if (JSON.stringify(rows) !== JSON.stringify(value ?? [])) {
    await $.state.set(NOT_RUN, rows)
  }
}

async function studioScript($: any): Promise<string | null> {
  // Built plugin: studio/ at the plugin root. Source tree: wire/studio/.
  for (const path of [`${$.plugin.root}/studio/studio.py`, `${$.plugin.root}/../../studio/studio.py`]) {
    try {
      if (await $.fs.exists(path)) {
        return path
      }
    } catch {
      // try the next place
    }
  }
  return null
}

async function exitsZero($: any, argv: string[]): Promise<boolean> {
  try {
    return (await $.process.run(argv, { timeoutMs: 3000 })).exitCode === 0
  } catch {
    return false
  }
}

async function isServing($: any, port: number): Promise<boolean> {
  try {
    return (await $.http.fetch(`http://127.0.0.1:${port}/api/summary`)).ok === true
  } catch {
    return false
  }
}

async function studioPaths($: any, cwd: string): Promise<{ dir: string; state: string; log: string }> {
  const home = (await $.env.get('HOME')) ?? ''
  const dir = `${home}/.wire/studio`
  const name = studioStateName(cwd)
  return { dir, state: `${dir}/${name}`, log: `${dir}/${name.replace(/\.json$/, '.log')}` }
}

async function readStudio($: any, statePath: string): Promise<StudioRecord | null> {
  try {
    return parseStudioRecord(String(await $.fs.read(statePath)))
  } catch {
    return null
  }
}

async function studioUp($: any, rec: StudioRecord | null): Promise<boolean> {
  return !!rec && (await exitsZero($, ['kill', '-0', String(rec.pid)])) && (await isServing($, rec.port))
}

async function freePort($: any, wanted: number | null): Promise<number | null> {
  const ports = wanted ? [wanted] : Array.from({ length: STUDIO_PORT_LAST - STUDIO_PORT_FIRST + 1 }, (_, i) => STUDIO_PORT_FIRST + i)
  for (const port of ports) {
    const listening = await exitsZero($, ['lsof', '-nP', `-iTCP:${port}`, '-sTCP:LISTEN'])
    if (!listening && !(await isServing($, port))) {
      return port
    }
  }
  return null
}

async function startStudio($: any, cwd: string, wanted: number | null): Promise<string> {
  const paths = await studioPaths($, cwd)
  const running = await readStudio($, paths.state)
  if (await studioUp($, running)) {
    return `Wire Studio is already running for this repository: http://127.0.0.1:${running?.port}/`
  }
  if (!(await $.fs.exists(`${cwd}/.wire`))) {
    return `No .wire/ folder in ${cwd}. Start Claude Code in a Wire engagement repository, then run /wire-studio.`
  }
  const script = await studioScript($)
  if (!script) {
    return 'Wire Studio is not in this copy of the plugin (studio/studio.py). It ships from Wire 4.1.0.'
  }
  const port = await freePort($, wanted)
  if (!port) {
    return wanted
      ? `Port ${wanted} is in use. Run /wire-studio start --port <another port>.`
      : `Ports ${STUDIO_PORT_FIRST}-${STUDIO_PORT_LAST} are all in use. Run /wire-studio start --port <n>.`
  }
  await $.process.run(['mkdir', '-p', paths.dir], { timeoutMs: 3000 })
  // Arguments reach the shell as positional parameters, never spliced into the script.
  const spawned = await $.process.run([
    'sh', '-c', 'nohup python3 "$1" --repo "$2" --port "$3" --no-browser >"$4" 2>&1 & echo $!',
    'sh', script, cwd, String(port), paths.log,
  ], { timeoutMs: 5000 })
  const pid = Number(String(spawned.stdout ?? '').trim())
  if (!Number.isInteger(pid) || pid <= 0) {
    return `Wire Studio did not start: ${String(spawned.stderr ?? '').trim() || 'no process id returned'}.`
  }
  const rec: StudioRecord = { pid, port, repo: cwd, startedAt: new Date(await $.clock.now()).toISOString() }
  await $.fs.write(paths.state, JSON.stringify(rec))
  for (let i = 0; i < 16 && !(await isServing($, port)); i++) {
    await $.clock.sleep(250)
  }
  const url = `http://127.0.0.1:${port}/`
  if (!(await isServing($, port))) {
    if (!(await exitsZero($, ['kill', '-0', String(pid)]))) {
      let tail = ''
      try {
        tail = String(await $.fs.read(paths.log)).trim().split('\n').slice(-3).join(' ')
      } catch {
        tail = ''
      }
      return `Wire Studio stopped as it started.${tail ? ` ${tail}` : ''} Log: ${paths.log}`
    }
    return `Wire Studio is starting at ${url} (still loading). Log: ${paths.log}`
  }
  const os = await run1($, ['uname', '-s'], cwd)
  await exitsZero($, [os === 'Darwin' ? 'open' : 'xdg-open', url])
  return `Wire Studio is running for this repository at ${url} (stop it with /wire-studio stop).`
}

async function stopStudio($: any, cwd: string): Promise<string> {
  const paths = await studioPaths($, cwd)
  const rec = await readStudio($, paths.state)
  if (!rec || !(await exitsZero($, ['kill', '-0', String(rec.pid)]))) {
    await $.fs.write(paths.state, '')
    return 'Wire Studio is not running for this repository.'
  }
  await exitsZero($, ['kill', String(rec.pid)])
  for (let i = 0; i < 8 && (await exitsZero($, ['kill', '-0', String(rec.pid)])); i++) {
    await $.clock.sleep(250)
  }
  await $.fs.write(paths.state, '')
  return `Wire Studio stopped (it was at http://127.0.0.1:${rec.port}/).`
}

async function studioStatus($: any, cwd: string): Promise<string> {
  const paths = await studioPaths($, cwd)
  const rec = await readStudio($, paths.state)
  if (await studioUp($, rec)) {
    return `Wire Studio is running for this repository at http://127.0.0.1:${rec?.port}/ (started ${rec?.startedAt}).`
  }
  return 'Wire Studio is not running for this repository. Start it with /wire-studio.'
}

// One `on()` per event and matcher: the engine admits one unmatched hook per
// event per module, so every concern's handler is called from here, in the
// order that keeps a refusal ahead of a run record and a note after a result.
export const register: Register = (on, options: Options) => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'wire-usage', description: "Wire: this session's Wire commands with duration, tokens and cost" })
    await $.command.register({ name: 'wire-studio', description: 'Wire: start, restart, stop or check Wire Studio for this repository', argumentHint: '[start|restart|stop|status] [--port <n>]' })
    await registerReviewCommands($)
    await registerBandCommand($)
    await startSession($)
    const result = await next(e)
    const cwd = (e as any).cwd ?? (await $.session.cwd())
    try {
      await autoUpgrade($, cwd, (e as any).isInteractive === true)
    } catch {
      // the upgrade is best effort; the session starts either way
    }
    await startContext($, options, cwd)
    return result
  })

  on('command.run', { command: 'wire-usage' }, async $ => {
    const rows = (await runsOf($)).map(r => ({
      command: r.command, release: r.release, invokedBy: r.invokedBy, tokens: totalTokens(r.usage),
      cost: computeCost(r.model, r.usage), seconds: r.endedAt === null ? null : Math.round((r.endedAt - r.startedAt) / 1000), filled: r.filled,
    }))
    return { text: usageReport(rows) }
  })

  on('command.run', { command: 'wire-studio' }, async ($, e) => {
    const parsed = parseStudioArgs(e.args)
    if ('error' in parsed) {
      return { text: parsed.error }
    }
    const cwd = await $.session.cwd()
    if (parsed.action === 'stop') {
      return { text: await stopStudio($, cwd) }
    }
    if (parsed.action === 'status') {
      return { text: await studioStatus($, cwd) }
    }
    if (parsed.action === 'restart') {
      await stopStudio($, cwd)
    }
    return { text: await startStudio($, cwd, parsed.port) }
  })

  on('command.run', { command: 'wire-ran' }, async $ => ranCommand($))
  on('command.run', { command: 'wire-approve' }, async ($, e) => approveCommand($, String(e.args ?? '')))
  on('command.run', { command: 'wire-park' }, async ($, e) => parkCommand($, String(e.args ?? '')))
  on('command.run', { command: 'wire-handoff' }, async $ => handoffCommand($))

  // A typed Wire command (also the first prompt of a session Studio opened):
  // the hard gate, then the collision warning, then the run record.
  on('command.run', async ($, e, next) => {
    const command = logCommandOf(e.command)
    if (!command) {
      return next(e)
    }
    const deny = await hardGate($, options, command, String(e.args ?? ''))
    if (deny) {
      return { text: deny }
    }
    try {
      await warnCollision($, command, String(e.args ?? ''))
    } catch {
      // the warning is best effort
    }
    if (command === '/wire:autopilot') {
      await $.state.set(AUTOPILOT, true)
    }
    const by = invokedBy('command', null, false, await $.env.get('WIRE_INVOKED_BY'))
    await startRun($, options, await newRun($, `cmd-${crypto.randomUUID()}`, command, e.args, null, by))
    return next(e)
  })

  // A Wire command run through the Skill tool: the orchestrator, Autopilot, or a lane.
  on('tool.call', { tool: 'Skill' }, async ($, e, next) => {
    const command = logCommandOf(String(e.skill ?? ''))
    if (!command) {
      return next(e)
    }
    const agentId = e.agentId ?? null
    const deny = await hardGate($, options, command, String(e.args ?? ''))
    if (deny) {
      return { deny }
    }
    if (!agentId) {
      try {
        await warnCollision($, command, String(e.args ?? ''))
      } catch {
        // best effort
      }
    }
    const { value: autopilot } = await $.state.get(AUTOPILOT)
    const by = invokedBy('skill', agentId, autopilot === true, undefined)
    await startRun($, options, await newRun($, e.tool_use_id ?? `skill-${crypto.randomUUID()}`, command, String(e.args ?? ''), agentId, by))
    return next(e)
  }).catch(($, e, next) => (next.called ? next(e) : { deny: 'Wire mod: the gate check failed; the command was not run.' }))

  // Rule 1: a lane does not fan out.
  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    const deny = await denyAgentCall($, options, e)
    return deny ? { deny } : next(e)
  }).catch(($, e, next) => (next.called ? next(e) : { deny: 'Wire mod: rule 1 check failed; the spawn was not admitted.' }))

  // The write tools: rules 3 and 6 before; then the lane's late log row, the
  // status line and convention lint after.
  for (const tool of ['Write', 'Edit', 'MultiEdit', 'NotebookEdit'] as const) {
    on('tool.call', { tool }, async ($, e, next) => {
      const deny = await denyWrite($, options, e)
      if (deny) {
        return { deny }
      }
      const result = await next(e)
      const path = String((e as any).file_path ?? '')
      if (path.endsWith('execution_log.md')) {
        await backfillPending($, options)
      }
      await afterStatusWrite($, e, result)
      if (tool !== 'NotebookEdit') {
        await afterWrite($, options, e, result)
      }
      return result
    }).catch(($, e, next) => (next.called ? next(e) : { deny: 'Wire mod: the tree-ownership check failed; the write was not made.' }))
  }

  // Bash from a lane: rule 6 best effort, warehouse_spend: none, the build slot.
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => onBash($, options, e, next))
    .catch(($, e, next) => (next.called ? next(e) : { deny: 'Wire mod: the Bash guard failed; the command was not run.' }))

  // Warehouse tools (MCP): warehouse_spend: none, the spend ledger and the cap.
  on('tool.call', async ($, e, next) => onWarehouseCall($, options, e, next))
    .catch(($, e, next) => (next.called ? next(e) : { deny: 'Wire mod: the warehouse guard failed; the query was not run.' }))

  // Lane registry: a spawn carrying a Wire lane brief.
  on('agent.spawn', async ($, e, next) => onAgentSpawn($, options, e, next))
    .catch(($, e, next) => (next.called ? next(e) : { deny: 'Wire mod: the lane registry failed; the spawn was not admitted.' }))

  // Each model request's measured usage goes to the Wire run open in its loop.
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    await addStepUsage($, e.agentId ?? null, e.turnId, result?.usage ?? null)
    return result
  })

  // The loop's turn ended: its runs close and their log rows are filled; a
  // lane leaves the registry; the main loop's reply is checked for rule 7.
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    const agentId = e.agentId ?? null
    const open = (await runsOf($)).filter(r => r.endedAt === null && r.agentId === agentId)
    await closeRuns($, agentId, e.turnId, e.usage ?? result?.usage ?? null)
    await backfillPending($, options)
    await onLaneTurnComplete($, agentId)
    if (agentId === null) {
      await checkRanLines($, options, open, String(e.answer ?? ''))
      await refreshNotRun($)
      await onMainTurnComplete($, options)
    }
    return result
  })

  on('prompt.compose', async ($, e, next) => composePrompt($, options, await next(e)))

  on('session.measure', async ($, e, next) => {
    await measureContext($, e)
    return next(e)
  })

  on('session.compact', async ($, e, next) => onCompact($, e, next))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => renderBand($, e, next))
}
