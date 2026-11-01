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
import { SEGMENT_IDENTIFY, SEGMENT_TRACK, SEGMENT_WRITE_KEY, WIRE_VERSION } from './wire/constants'
import { BUILD_SLOT_MINUTES, absolutePath, bashWritesRecord, bytesBilledOf, bytesToUsd, dbtProjectOf, isDbtBuild, isDbtWarehouseRun, isRecordFile, isUnderAny, isWarehouseWriteTool, normalisePath, parseLaneBrief, refusal } from './wire/lanes'
import { approvedCount, artifactStatesOf, budgetOf, businessRulesSummary, capOf, claimOf, frontMatterOf, minutesSince, nextParkedId, openIterationsOf, orchestrationModeOf, parkedDecisionsOf, releaseContext, resolveActiveRelease, rulingsOf, scalarOf, sessionLine, stampOf, statusLine } from './wire/release'
import { type Options, isOn } from './wire/host'
import { type Finding, type LintDomain, domainOf, findingsNote, findingsOf } from './wire/lint'
import { BAND_MAX_RUNS, bandText, blockedRowsOf, checkRanLine, notRunLine, runLine } from './wire/band'
import { type ReviewEvent, appendParkedDecision, appendReviewEvent, gateDeny, hasOverride, isGated, parseApproveArgs, parseParkArgs } from './wire/review'
import { DRIFT_EVERY_TURNS, DRIFT_FROM_PERCENT, HANDOFF_FALLBACK, STALL_CHECK_MS, STALL_MINUTES, driftPrompt, stallNote, stalledLanes } from './wire/session'
import { QUEUED_STORE_KEY, SESSION_CHECK_SCRIPT, type UpgradeReport, compareVersions, extendLogHeader, removeSessionCheckHook, upgradeNote, upgradePrompt } from './wire/upgrade'
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
import { addUsage, backfillLog, computeCost, emptyUsage, identifyBody, invokedBy, personaOf, logCommandOf, logRowResult, logStamp, parseStudioArgs, parseStudioRecord, releaseOf, restArgsOf, STUDIO_PORT_FIRST, STUDIO_PORT_LAST, studioStateName, type StudioRecord, totalTokens, trackBody, usageReport } from './wire/logic'

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

// ---------------------------------------------------------------------------
// Everything below takes `$`. It lives in this file because Claude Code's
// validator (2.1.287 and later) follows `$` only into functions declared in the
// same file as the hook; the concern files under wire/ keep the pure logic.
// ---------------------------------------------------------------------------

async function exists($: any, path: string): Promise<boolean> {
  try {
    return (await $.fs.exists(path)) === true
  } catch {
    return false
  }
}

async function mtimeOf($: any, path: string): Promise<number> {
  try {
    const st = await $.fs.stat(path)
    return typeof st?.mtimeMs === 'number' ? st.mtimeMs : 0
  } catch {
    return 0
  }
}

async function realPathOf($: any, path: string): Promise<string> {
  try {
    const own = await $.fs.stat(path, { resolve: true })
    if (own?.realPath) {
      return String(own.realPath)
    }
  } catch {
    // not there yet
  }
  const i = path.lastIndexOf('/')
  if (i > 0) {
    try {
      const dir = await $.fs.stat(path.slice(0, i), { resolve: true })
      if (dir?.realPath) {
        return `${String(dir.realPath).replace(/\/$/, '')}/${path.slice(i + 1)}`
      }
    } catch {
      // parent not there either
    }
  }
  return path
}

async function gitUserName($: any, cwd: string): Promise<string> {
  return (await run1($, ['git', 'config', '--get', 'user.name'], cwd)) || 'unknown'
}

async function gitBranch($: any, cwd: string): Promise<string> {
  const b = await run1($, ['git', 'branch', '--show-current'], cwd)
  if (b) {
    return b
  }
  const h = await run1($, ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd)
  return h === 'HEAD' ? '' : h
}

async function frameworkFile($: any, rel: string): Promise<string | null> {
  for (const path of [`${$.plugin.root}/${rel}`, `${$.plugin.root}/../../${rel}`]) {
    if (await exists($, path)) {
      return path
    }
  }
  return null
}

async function sessionIdOf($: any): Promise<string> {
  try {
    return String((await $.session.id()) ?? '')
  } catch {
    return ''
  }
}

function toast($: any, text: string): void {
  try {
    $.ui.toast(text)
  } catch {
    // a surface with no toasts
  }
}

async function appendNote($: any, text: string, agentId?: string | null): Promise<void> {
  try {
    await $.session.append({ message: { type: 'user', content: [{ type: 'text', text }] }, ...(agentId ? { agentId } : {}) })
  } catch {
    // a loop that is no longer running
  }
}

async function listReleases($: any, cwd: string): Promise<{ folder: string; mtime: number; statusText: string | null }[]> {
  const out: { folder: string; mtime: number; statusText: string | null }[] = []
  try {
    for (const d of await $.fs.list(`${cwd}/.wire/releases`)) {
      if (d.kind !== 'dir') {
        continue
      }
      const path = `${cwd}/.wire/releases/${d.name}/status.md`
      out.push({ folder: d.name, mtime: await mtimeOf($, path), statusText: await readText($, path) })
    }
  } catch {
    return []
  }
  return out.sort((a, b) => a.folder.localeCompare(b.folder))
}

const IDENTITY = { plugin: 'wire', key: 'identity' } as const

async function identityOf($: any): Promise<{ identity: WireIdentity; isNew: boolean }> {
  const { value } = await $.state.get(IDENTITY)
  if (value) {
    return { identity: value, isNew: false }
  }
  const cwd = await $.session.cwd()
  const home = (await $.env.get('HOME')) ?? ''
  const idFile = `${home}/.wire/telemetry_id`
  let userId = ''
  let isNew = false
  try {
    userId = String(await $.fs.read(idFile)).trim()
  } catch {
    userId = ''
  }
  if (!userId) {
    userId = crypto.randomUUID()
    isNew = true
    try {
      await $.fs.write(idFile, userId)
    } catch {
      // No home folder to write to: the id lasts this session only.
    }
  }
  const identity: WireIdentity = {
    userId,
    username: (await $.env.get('USER')) ?? (await $.env.get('USERNAME')) ?? '',
    hostname: await run1($, ['hostname'], cwd),
    os: await run1($, ['uname', '-s'], cwd),
    gitRepo: (await run1($, ['git', 'config', '--get', 'remote.origin.url'], cwd)) || 'unknown',
    gitBranch: (await run1($, ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd)) || 'unknown',
  }
  await $.state.set(IDENTITY, identity)
  return { identity, isNew }
}

async function post($: any, url: string, body: string): Promise<void> {
  try {
    await $.http.fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body })
  } catch {
    // Telemetry never fails or blocks a command.
  }
}

async function sendEvent($: any, options: Options, event: string, properties: Record<string, unknown>): Promise<void> {
  if (!isOn(options.telemetry, await $.env.get('WIRE_TELEMETRY'))) {
    return
  }
  const { identity } = await identityOf($)
  let sessionId: string | null = null
  try {
    sessionId = await $.session.id()
  } catch {
    sessionId = null
  }
  const timestamp = new Date(await $.clock.now()).toISOString().replace(/\.\d{3}Z$/, 'Z')
  await post($, SEGMENT_TRACK, JSON.stringify({
    writeKey: SEGMENT_WRITE_KEY, userId: identity.userId, event,
    properties: { ...properties, timestamp, plugin_version: WIRE_VERSION, runtime: 'claude', session_id: sessionId, git_repo: identity.gitRepo, git_branch: identity.gitBranch },
  }))
}

async function identifyIfNew($: any, identity: WireIdentity, isNew: boolean, timestamp: string): Promise<void> {
  if (isNew) {
    await post($, SEGMENT_IDENTIFY, identifyBody(SEGMENT_WRITE_KEY, identity.userId, {
      username: identity.username, hostname: identity.hostname, os: identity.os, version: WIRE_VERSION, timestamp,
    }))
  }
}

const CONTEXT = { plugin: 'wire', key: 'context' } as const

const CONTEXT_PERCENT = { plugin: 'wire', key: 'contextPercent' } as const

const CONTEXT_WARNED = { plugin: 'wire', key: 'contextWarned' } as const

async function resolveActive($: any, cwd: string): Promise<WireActiveRelease> {
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

async function refreshStatus($: any): Promise<void> {
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

async function nextActionOf($: any, cwd: string, release: string): Promise<string | null> {
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

async function startContext($: any, options: Options, cwd: string): Promise<void> {
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

async function composePrompt($: any, options: Options, result: any): Promise<any> {
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

async function measureContext($: any, e: any): Promise<void> {
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

async function afterStatusWrite($: any, e: any, result: any): Promise<void> {
  if (/\/status\.md$/.test(String(e.file_path ?? '')) && !result?.deny) {
    await refreshStatus($)
  }
}

const BUILD_SLOTS = { plugin: 'wire', key: 'buildSlots' } as const

const SPEND = { plugin: 'wire', key: 'spend' } as const

async function saveLanes($: any, lanes: WireLane[]): Promise<void> {
  await $.state.set(LANES, lanes)
}

async function enforcing($: any, options: Options): Promise<boolean> {
  if (!isOn(options.enforce, await $.env.get('WIRE_ENFORCE'))) {
    return false
  }
  const active = await activeOf($)
  return !!active && active.mode !== 'manual'
}

async function statusFrontOf($: any, cwd: string, release: string | null): Promise<string> {
  if (!release) {
    return ''
  }
  return frontMatterOf((await readText($, `${cwd}/.wire/releases/${release}/status.md`)) ?? '').front
}

async function claimHeldHere($: any, cwd: string, release: string | null): Promise<boolean> {
  const claim = claimOf(await statusFrontOf($, cwd, release))
  if (!claim) {
    return false
  }
  if (claim.sessionId && claim.sessionId === (await sessionIdOf($))) {
    return true
  }
  return claim.user === (await gitUserName($, cwd))
}

async function laneOf($: any, agentId: string | null | undefined): Promise<WireLane | null> {
  if (!agentId) {
    return null
  }
  return (await lanesOf($)).find(l => l.agentId === agentId) ?? null
}

async function slotsOf($: any): Promise<WireBuildSlot[]> {
  const { value } = await $.state.get(BUILD_SLOTS)
  return Array.isArray(value) ? value : []
}

async function writeRecordDeny($: any, lane: WireLane, cwd: string, filePath: string): Promise<string | null> {
  const abs = absolutePath(String(filePath), cwd)
  const real = normalisePath(await realPathOf($, abs))
  if (isRecordFile(real) || isRecordFile(abs)) {
    return refusal.singleWriter(lane.label, filePath, lane.stateFile)
  }
  if (lane.stateFile && (real === normalisePath(await realPathOf($, lane.stateFile)) || abs === normalisePath(lane.stateFile))) {
    return null
  }
  // decisions.md is the lane's to append to (the lane contract, rule 4).
  if (lane.release && real === `${cwd}/.wire/releases/${lane.release}/decisions.md`) {
    return null
  }
  // Judged on the real path alone: a symlink into the tree is allowed, one out of it is not.
  if (lane.owns.length > 0 && !isUnderAny(real, lane.owns)) {
    return refusal.outsideTree(lane.label, filePath, lane.owns)
  }
  return null
}

async function spendOf($: any, release: string): Promise<WireSpend> {
  const { value } = await $.state.get(SPEND)
  const s = value as WireSpend | null
  return s && s.release === release ? s : { release, bytes: 0, usd: 0, capBreached: false }
}

async function recordSpend($: any, cwd: string, lane: WireLane, tool: string, bytes: number): Promise<WireSpend | null> {
  if (!lane.release) {
    return null
  }
  const spend = await spendOf($, lane.release)
  spend.bytes += bytes
  spend.usd = Math.round((spend.usd + bytesToUsd(bytes)) * 10_000) / 10_000
  await $.state.set(SPEND, spend)
  const now = await $.clock.now()
  const row = JSON.stringify({ lane: lane.label, tool, bytes, usd: bytesToUsd(bytes), timestamp: new Date(now).toISOString() })
  const path = `${cwd}/.wire/releases/${lane.release}/lanes/_spend.jsonl`
  try {
    const current = (await readText($, path)) ?? ''
    await $.fs.write(path, `${current}${current && !current.endsWith('\n') ? '\n' : ''}${row}\n`)
  } catch {
    // the lanes folder may not exist yet; the state total still holds
  }
  return spend
}

async function raiseBudgetDecision($: any, cwd: string, release: string, spend: WireSpend, cap: number): Promise<void> {
  const path = `${cwd}/.wire/releases/${release}/status.md`
  const text = await readText($, path)
  if (!text) {
    return
  }
  const now = await $.clock.now()
  const updated = appendParkedDecision(text, {
    id: nextParkedId(frontMatterOf(text).front),
    artifact: 'budget',
    kind: 'budget',
    question: `Warehouse spend is $${spend.usd.toFixed(2)} against cap:${cap}. Raise the cap, or stop the warehouse work?`,
    parkedAt: stampOf(now),
    awaiting: null,
  })
  if (typeof updated === 'string') {
    await $.fs.write(path, updated)
  }
}

async function onAgentSpawn($: any, options: Options, e: any, next: any): Promise<any> {
  const brief = parseLaneBrief(String(e.prompt ?? ''))
  if (!brief || e.resume || e.workflow) {
    return next(e)
  }
  const cwd = e.cwd ?? (await $.session.cwd())
  const release = brief.release ?? (await activeOf($))?.release ?? null
  if (!(await enforcing($, options)) || !(await claimHeldHere($, cwd, release))) {
    return next(e)
  }
  if (brief.missing.length > 0) {
    return { deny: refusal.missingBrief(brief.label, brief.missing) }
  }
  const lanes = await lanesOf($)
  const { lanesMax } = budgetOf(await statusFrontOf($, cwd, release))
  if (lanes.length >= lanesMax) {
    return { deny: refusal.lanesMax(lanesMax, lanes.map(l => l.label)) }
  }
  const result = await next(e)
  if (result?.agentId) {
    const owns: string[] = []
    for (const d of brief.owns) {
      owns.push(normalisePath(await realPathOf($, absolutePath(d, cwd))))
    }
    const lane: WireLane = {
      agentId: result.agentId, label: brief.label, release, tasks: brief.tasks,
      owns, stateFile: brief.stateFile ? absolutePath(brief.stateFile, cwd) : null,
      budget: brief.budget, startedAt: await $.clock.now(), stalledAt: null,
    }
    await saveLanes($, [...(await lanesOf($)).filter(l => l.agentId !== lane.agentId), lane])
  }
  return result
}

async function onLaneTurnComplete($: any, agentId: string | null): Promise<void> {
  if (!agentId) {
    return
  }
  const lanes = await lanesOf($)
  if (lanes.some(l => l.agentId === agentId)) {
    await saveLanes($, lanes.filter(l => l.agentId !== agentId))
    await $.state.set(BUILD_SLOTS, (await slotsOf($)).filter(s => s.agentId !== agentId))
  }
}

async function denyAgentCall($: any, options: Options, e: any): Promise<string | null> {
  const lane = await laneOf($, e.agentId)
  return lane && (await enforcing($, options)) ? refusal.flatLane(lane.label) : null
}

async function denyWrite($: any, options: Options, e: any): Promise<string | null> {
  const lane = await laneOf($, e.agentId)
  if (!lane || !(await enforcing($, options))) {
    return null
  }
  const path = e.file_path ?? e.notebook_path ?? ''
  return writeRecordDeny($, lane, await $.session.cwd(), String(path))
}

async function onBash($: any, options: Options, e: any, next: any): Promise<any> {
  const lane = await laneOf($, e.agentId)
  if (!lane || !(await enforcing($, options))) {
    return next(e)
  }
  const command = String(e.command ?? '')
  if (bashWritesRecord(command)) {
    return { deny: refusal.singleWriter(lane.label, 'status.md or execution_log.md', lane.stateFile) }
  }
  const cwd = await $.session.cwd()
  const { warehouseSpend } = budgetOf(await statusFrontOf($, cwd, lane.release))
  if (warehouseSpend === 'none' && isDbtWarehouseRun(command)) {
    return { deny: refusal.warehouseNone(lane.label, 'a dbt build, run, snapshot, seed or test') }
  }
  if (!isDbtBuild(command)) {
    return next(e)
  }
  const project = dbtProjectOf(command, lane.release ?? 'default')
  const now = await $.clock.now()
  const slots = (await slotsOf($)).filter(s => now - s.heldAt < BUILD_SLOT_MINUTES * 60_000)
  const held = slots.find(s => s.project === project && s.agentId !== lane.agentId)
  if (held) {
    return { deny: refusal.buildSlot(project, held.laneLabel, Math.round((now - held.heldAt) / 60_000)) }
  }
  await $.state.set(BUILD_SLOTS, [...slots.filter(s => s.project !== project), { project, agentId: lane.agentId, laneLabel: lane.label, heldAt: now }])
  try {
    return await next(e)
  } finally {
    await $.state.set(BUILD_SLOTS, (await slotsOf($)).filter(s => !(s.project === project && s.agentId === lane.agentId)))
  }
}

async function onWarehouseCall($: any, options: Options, e: any, next: any): Promise<any> {
  const tool = String(e.tool ?? '')
  if (!isWarehouseWriteTool(tool)) {
    return next(e)
  }
  const lane = await laneOf($, e.agentId)
  if (!lane || !(await enforcing($, options))) {
    return next(e)
  }
  const cwd = await $.session.cwd()
  const { warehouseSpend } = budgetOf(await statusFrontOf($, cwd, lane.release))
  if (warehouseSpend === 'none') {
    return { deny: refusal.warehouseNone(lane.label, tool) }
  }
  const cap = capOf(warehouseSpend)
  if (cap !== null && lane.release) {
    const spend = await spendOf($, lane.release)
    if (spend.capBreached) {
      return { deny: refusal.capPassed(spend.usd, cap, lane.release) }
    }
  }
  const result = await next(e)
  const bytes = bytesBilledOf(result?.text ?? (result?.result ? JSON.stringify(result.result) : ''))
  const spend = await recordSpend($, cwd, lane, tool, bytes)
  if (spend && cap !== null && spend.usd > cap && !spend.capBreached && lane.release) {
    await $.state.set(SPEND, { ...spend, capBreached: true })
    await raiseBudgetDecision($, cwd, lane.release, spend, cap)
    toast($, `Warehouse spend for ${lane.release} is $${spend.usd.toFixed(2)}, past cap:${cap}. Parked for the director.`)
    await appendNote($, `Wire budget: warehouse spend for ${lane.release} has passed cap:${cap} ($${spend.usd.toFixed(2)}). A parked decision has been raised in status.md; the next warehouse call from a lane will be refused until the director rules.`)
  }
  return result
}

async function warnCollision($: any, command: string, args: string): Promise<void> {
  const active = await activeOf($)
  if (!active || active.mode === 'manual') {
    return
  }
  const cwd = await $.session.cwd()
  const release = releaseOf(args) ?? active.release
  const claim = claimOf(await statusFrontOf($, cwd, release))
  if (claim && release) {
    const now = await $.clock.now()
    const age = minutesSince(claim.lastWrite, now)
    if (claim.sessionId !== (await sessionIdOf($)) && claim.user !== (await gitUserName($, cwd)) && age <= CLAIM_LIVE_MINUTES) {
      toast($, `${release} is claimed by ${claim.user} (last write ${Math.max(0, Math.round(age))} min ago). ${command} runs anyway; they may be mid-flight.`)
    }
  }
  const base = command.replace(/^\/wire:/, '').replace(/-(generate|validate|review|lint|publish)$/, '')
  const owner = (await lanesOf($)).find(l => l.tasks && new RegExp(`(^|[\\s,])${base.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(-|\\b)`).test(l.tasks))
  if (owner) {
    toast($, `${command} touches work lane "${owner.label}" is doing now. Running anyway.`)
  }
}

async function liveLaneLabels($: any): Promise<string[]> {
  return (await lanesOf($)).map(l => l.label)
}

const BAND_HIDDEN = { plugin: 'wire', key: 'bandHidden' } as const

const DRIFT = { plugin: 'wire', key: 'drift' } as const

async function registerBandCommand($: any): Promise<void> {
  await $.command.register({ name: 'wire-ran', description: "Wire: the Wire commands this session ran, in full, with result, tokens and cost" })
}

async function ranCommand($: any): Promise<{ text: string }> {
  const { value: notRun } = await $.state.get(NOT_RUN)
  const { value: drift } = await $.state.get(DRIFT)
  return { text: bandText(await runsOf($), Array.isArray(notRun) ? notRun : [], typeof drift === 'string' ? drift : null) }
}

async function renderBand($: any, e: any, next: any): Promise<any> {
  const runs = await runsOf($)
  const { value: notRun } = await $.state.get(NOT_RUN)
  const { value: drift } = await $.state.get(DRIFT)
  const { value: hidden } = await $.state.get(BAND_HIDDEN)
  const rows = runs.slice(-BAND_MAX_RUNS)
  const gates: WireNotRun[] = Array.isArray(notRun) ? notRun.slice(-3) : []
  const hit = typeof drift === 'string' ? drift : null
  if (e.props.hasSurvey || hidden === true || (rows.length === 0 && gates.length === 0 && !hit)) {
    return next(e)
  }
  const { Box, Button, Text } = $.ui.resolve(e)
  // Built with the global `h` factory rather than JSX, so this file stays .ts.
  const children: any[] = [
    ...rows.map(r => h(Text, { key: r.id, dimColor: r.endedAt !== null, wrap: 'truncate-end' }, runLine(r))),
    ...gates.map((g, i) => h(Text, { key: `gate-${i}`, wrap: 'truncate-end' }, notRunLine(g))),
  ]
  if (hit) {
    children.push(h(Box, {},
      h(Text, { wrap: 'truncate-end' }, `Drift: ${hit} `),
      h(Button, { key: 'dismiss-drift', label: 'Dismiss', onPress: async () => { await $.state.set(DRIFT, null) } })))
  }
  children.push(h(Box, {},
    h(Text, { dimColor: true }, '/wire-ran for the full list '),
    h(Button, { key: 'hide-band', label: 'Hide', onPress: async () => { await $.state.set(BAND_HIDDEN, true) } })))
  return h(Box, { flexDirection: 'column' }, ...children)
}

const TURNS = { plugin: 'wire', key: 'turns' } as const

async function handoffTemplate($: any): Promise<string> {
  const path = await frameworkFile($, 'TEMPLATES/handoff-template.md')
  const text = path ? await readText($, path) : null
  return text?.trim() || HANDOFF_FALLBACK
}

async function startSession($: any): Promise<void> {
  await $.command.register({ name: 'wire-handoff', description: "Wire: write a session handoff (built, rulings, state, next command) to the release's lanes folder" })
  $.clock.every(STALL_CHECK_MS, async () => {
    try {
      await checkStalls($)
    } catch {
      // the timer is best effort
    }
  })
}

async function checkStalls($: any): Promise<WireLane[]> {
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

async function onCompact($: any, e: any, next: any): Promise<any> {
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

async function handoffCommand($: any): Promise<{ text: string }> {
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

async function onMainTurnComplete($: any, options: Options): Promise<void> {
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

async function autoUpgrade($: any, cwd: string, isInteractive: boolean): Promise<UpgradeReport> {
  const report: UpgradeReport = { hookRemoved: false, scriptRemoved: false, logsExtended: [], behind: [], heldElsewhere: [], queued: null }
  if (!(await exists($, `${cwd}/.wire`))) {
    return report
  }
  const settingsPath = `${cwd}/.claude/settings.json`
  const settingsText = await readText($, settingsPath)
  if (settingsText !== null) {
    const { text, removed } = removeSessionCheckHook(settingsText)
    if (removed) {
      await $.fs.write(settingsPath, text)
      report.hookRemoved = true
      const script = `${cwd}/.claude/hooks/${SESSION_CHECK_SCRIPT}`
      if (await exists($, script)) {
        try {
          const r = await $.process.run(['rm', '-f', script], { cwd, timeoutMs: 3000 })
          report.scriptRemoved = r.exitCode === 0
        } catch {
          report.scriptRemoved = false
        }
      }
    }
  }
  const now = await $.clock.now()
  const me = await gitUserName($, cwd)
  const sid = await sessionIdOf($)
  for (const rel of await listReleases($, cwd)) {
    const front = frontMatterOf(rel.statusText ?? '').front
    const recorded = scalarOf(front, 'wire_plugin_version')
    // Absent means never upgraded, whatever the plugin version reads (the
    // source tree's placeholder included); present is compared.
    if (recorded === null || compareVersions(recorded, WIRE_VERSION) < 0) {
      report.behind.push({ release: rel.folder, version: recorded ?? 'none' })
    }
    const claim = claimOf(front)
    const heldElsewhere = !!claim && claim.sessionId !== sid && claim.user !== me && minutesSince(claim.lastWrite, now) <= CLAIM_LIVE_MINUTES
    if (heldElsewhere) {
      if (report.behind.some(b => b.release === rel.folder)) {
        report.heldElsewhere.push(rel.folder)
      }
      continue
    }
    const logPath = `${cwd}/.wire/releases/${rel.folder}/execution_log.md`
    const log = await readText($, logPath)
    if (log !== null) {
      const extended = extendLogHeader(log)
      if (extended !== null) {
        await $.fs.write(logPath, extended)
        report.logsExtended.push(`.wire/releases/${rel.folder}/execution_log.md`)
      }
    }
  }
  // Queue the real command for the releases behind, once per repository per
  // plugin version. Not in a headless session: a queued turn there would run
  // with nobody to answer the confirmation.
  const toQueue = report.behind.map(b => b.release).filter(r => !report.heldElsewhere.includes(r))
  if (toQueue.length > 0 && isInteractive) {
    let marks: Record<string, string> = {}
    try {
      const v = await $.store.get(QUEUED_STORE_KEY)
      marks = v && typeof v === 'object' ? (v as Record<string, string>) : {}
    } catch {
      marks = {}
    }
    if (marks[cwd] !== WIRE_VERSION) {
      const prompt = upgradePrompt(toQueue)
      try {
        // A command is run as one, not submitted as prompt text (the engine
        // refuses a submitted text that starts with `/`).
        await $.command.run({ command: 'wire:upgrade', args: `--from-mod ${toQueue.join(' ')}` })
        report.queued = prompt
        await $.store.set(QUEUED_STORE_KEY, { ...marks, [cwd]: WIRE_VERSION })
      } catch {
        report.queued = null
      }
    }
  }
  const note = upgradeNote(report, WIRE_VERSION)
  if (note) {
    await appendNote($, note)
    // A release behind the plugin is said in the note alone: a toast at every
    // session start would nag until someone runs the command.
    if (report.hookRemoved || report.logsExtended.length > 0) {
      toast($, `Wire upgrade: ${[report.hookRemoved ? 'session-check hook removed' : '', report.logsExtended.length ? `${report.logsExtended.length} log header(s) extended` : ''].filter(Boolean).join(', ')}. Commit the change.`)
    }
  }
  return report
}

async function conventionFor($: any, cwd: string, domain: LintDomain): Promise<string | null> {
  const own = `${cwd}/.wire/conventions/${domain}.yml`
  if (await exists($, own)) {
    return own
  }
  return frameworkFile($, `conventions/${domain}.yml`)
}

async function lintFile($: any, cwd: string, path: string, agentId: string | null): Promise<Finding[]> {
  let text: string | null = null
  try {
    text = String(await $.fs.read(path))
  } catch {
    return []
  }
  const domain = domainOf(path, text)
  if (!domain) {
    return []
  }
  const script = await frameworkFile($, 'scripts/lint_conventions.py')
  const convention = await conventionFor($, cwd, domain)
  if (!script || !convention) {
    return []
  }
  let out = ''
  try {
    const r = await $.process.run(['python3', script, '--domain', domain, '--convention', convention, '--path', path, '--format', 'json'], { cwd, timeoutMs: 30_000 })
    out = String(r.stdout ?? '')
  } catch {
    return []
  }
  const findings = findingsOf(out, path)
  if (findings.length > 0) {
    toast($, `Wire conventions: ${findings.length} finding${findings.length === 1 ? '' : 's'} in ${path.split('/').pop()}`)
    await appendNote($, findingsNote(domain, path, findings), agentId)
  }
  return findings
}

/** After a write tool ran and did not fail: lint the file it wrote. Never changes the result. */
async function afterWrite($: any, options: Options, e: any, result: any): Promise<void> {
  if (result?.deny || result?.isError || !isOn(options.lintOnWrite, await $.env.get('WIRE_LINT'))) {
    return
  }
  try {
    const cwd = await $.session.cwd()
    const path = absolutePath(String(e.file_path ?? ''), cwd)
    if (path.startsWith(`${cwd}/`)) {
      await lintFile($, cwd, path, e.agentId ?? null)
    }
  } catch {
    // lint never changes the write's result
  }
}

/** The gate's answer for one command, from wire_gate.py; null when it cannot be asked. */
async function gateCheck($: any, cwd: string, release: string, command: string): Promise<{ decision: string; reason: string } | null> {
  const script = await frameworkFile($, 'scripts/wire_gate.py')
  if (!script) {
    return null
  }
  const out = await run1($, ['python3', script, 'gate', '--repo', cwd, '--release', release, '--command', command.replace(/^\/wire:/, '')], cwd, 20_000)
  try {
    const j = JSON.parse(out)
    return typeof j.decision === 'string' ? { decision: j.decision, reason: String(j.reason ?? '') } : null
  } catch {
    return null
  }
}

/** The deny for a gated command whose blocking precondition is unmet, or null. */
async function hardGate($: any, options: Options, command: string, args: string): Promise<string | null> {
  if (!isGated(command) || hasOverride(args) || !isOn(options.enforce, await $.env.get('WIRE_ENFORCE'))) {
    return null
  }
  const active = await activeOf($)
  if (!active || active.mode === 'manual') {
    return null
  }
  const release = releaseOf(args) ?? active.release
  if (!release) {
    return null
  }
  const verdict = await gateCheck($, await $.session.cwd(), release, command)
  return verdict?.decision === 'refuse' ? gateDeny(command, release, verdict.reason) : null
}

async function releaseFor($: any, named: string | null): Promise<string | { error: string }> {
  if (named) {
    return named
  }
  const active = await activeOf($)
  if (active?.release) {
    return active.release
  }
  return { error: active && active.candidates.length > 1
    ? `More than one release is active (${active.candidates.join(', ')}); pass --release <folder>.`
    : 'No active release; pass --release <folder>.' }
}

async function checkStatusFile($: any, cwd: string, release: string): Promise<string> {
  const script = await frameworkFile($, 'scripts/status_file.py')
  if (!script) {
    return ''
  }
  try {
    const r = await $.process.run(['python3', script, 'check', `${cwd}/.wire/releases/${release}`], { cwd, timeoutMs: 20_000 })
    return r.exitCode === 0 ? '' : ` status_file.py check reports: ${String(r.stdout ?? '').trim()}`
  } catch {
    return ''
  }
}

async function registerReviewCommands($: any): Promise<void> {
  await $.command.register({ name: 'wire-approve', description: 'Wire: record a review approval on an artifact in status.md, no model turn', argumentHint: '<artifact> [--as internal|client] [--evidence <url>] [--final]' })
  await $.command.register({ name: 'wire-park', description: 'Wire: park a decision for the release director in status.md, no model turn', argumentHint: '<artifact> "<question>" [--awaiting <who>]' })
}

async function approveCommand($: any, args: string): Promise<{ text: string }> {
  const parsed = parseApproveArgs(args)
  if ('error' in parsed) {
    return { text: parsed.error }
  }
  const release = await releaseFor($, parsed.release)
  if (typeof release !== 'string') {
    return { text: release.error }
  }
  const cwd = await $.session.cwd()
  const path = `${cwd}/.wire/releases/${release}/status.md`
  const text = await readText($, path)
  if (text === null) {
    return { text: `No status.md at ${path}.` }
  }
  const now = await $.clock.now()
  const event: ReviewEvent = { actor: await gitUserName($, cwd), date: stampOf(now).slice(0, 10), kind: parsed.as, evidence: parsed.evidence, outcome: 'approved' }
  const updated = appendReviewEvent(text, parsed.artifact, event, parsed.final)
  if (typeof updated !== 'string') {
    return { text: updated.error }
  }
  await $.fs.write(path, updated)
  const check = await checkStatusFile($, cwd, release)
  return { text: `Recorded ${parsed.as} approval of ${parsed.artifact} in ${release} by ${event.actor} (${event.date})${parsed.final ? '; review: approved' : ''}.${check}` }
}

async function parkCommand($: any, args: string): Promise<{ text: string }> {
  const parsed = parseParkArgs(args)
  if ('error' in parsed) {
    return { text: parsed.error }
  }
  const release = await releaseFor($, parsed.release)
  if (typeof release !== 'string') {
    return { text: release.error }
  }
  const cwd = await $.session.cwd()
  const path = `${cwd}/.wire/releases/${release}/status.md`
  const text = await readText($, path)
  if (text === null) {
    return { text: `No status.md at ${path}.` }
  }
  const now = await $.clock.now()
  const id = nextParkedId(frontMatterOf(text).front)
  const updated = appendParkedDecision(text, { id, artifact: parsed.artifact, kind: 'ruling', question: parsed.question, parkedAt: stampOf(now), awaiting: parsed.awaiting })
  if (typeof updated !== 'string') {
    return { text: updated.error }
  }
  await $.fs.write(path, updated)
  const check = await checkStatusFile($, cwd, release)
  return { text: `Parked ${id} on ${parsed.artifact} in ${release}${parsed.awaiting ? `, awaiting ${parsed.awaiting}` : ''}: ${parsed.question}${check}` }
}

const DAY_MS = 24 * 60 * 60_000

const CONTEXT_WARN_AT = 85

type Snapshot = {
  active: WireActiveRelease
  front: string
  body: string
  projectType: string | null
  approved: number
  parked: ReturnType<typeof parkedDecisionsOf>
  claimUser: string | null
}

const CLAIM_LIVE_MINUTES = 30
