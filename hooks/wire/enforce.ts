// Enforcement (wire#270 D5): the operating model's rules 1, 3 and 6, the
// budget's lanes_max and warehouse_spend, the build slot, the spend ledger
// and cap, and the collision guard, as refusals in `agent.spawn` and
// `tool.call` hooks. Every refusal names the rule and what to do instead.
//
// Nothing here refuses unless all three hold: the `enforce` option is on, the
// engagement is in orchestrated mode, and the lane's release carries a claim
// held by this session (or this user, who may resume in a new session). In
// manual mode, or on a release nobody has claimed, the mod observes and
// refuses nothing.

import type { WireActiveRelease, WireBuildSlot, WireLane, WireSpend } from '../types'
import { type Options, appendNote, gitUserName, isOn, readText, realPathOf, sessionIdOf, toast } from './host'
const BUILD_SLOTS = { plugin: 'wire', key: 'buildSlots' } as const
const SPEND = { plugin: 'wire', key: 'spend' } as const
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
import {
  BUILD_SLOT_MINUTES, absolutePath, bashWritesRecord, bytesBilledOf, bytesToUsd, dbtProjectOf, isDbtBuild,
  isDbtWarehouseRun, isRecordFile, isUnderAny, isWarehouseWriteTool, normalisePath, parseLaneBrief, refusal,
} from './lanes'
import { releaseOf } from './logic'
import { budgetOf, capOf, claimOf, frontMatterOf, minutesSince, nextParkedId, stampOf } from './release'
import { appendParkedDecision } from './review'

const CLAIM_LIVE_MINUTES = 30

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

/** The release's claim is held by this session, or by this user (who may resume). */
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

/** agent.spawn: the lane registry, the brief check and lanes_max. A full hook body. */
export async function onAgentSpawn($: any, options: Options, e: any, next: any): Promise<any> {
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

/** turn.complete of a lane: it leaves the registry and releases any build slot. */
export async function onLaneTurnComplete($: any, agentId: string | null): Promise<void> {
  if (!agentId) {
    return
  }
  const lanes = await lanesOf($)
  if (lanes.some(l => l.agentId === agentId)) {
    await saveLanes($, lanes.filter(l => l.agentId !== agentId))
    await $.state.set(BUILD_SLOTS, (await slotsOf($)).filter(s => s.agentId !== agentId))
  }
}

/** Rule 1: the reason to refuse a lane's Agent call, or null. */
export async function denyAgentCall($: any, options: Options, e: any): Promise<string | null> {
  const lane = await laneOf($, e.agentId)
  return lane && (await enforcing($, options)) ? refusal.flatLane(lane.label) : null
}

/** Rules 3 and 6: the reason to refuse a lane's write, or null. */
export async function denyWrite($: any, options: Options, e: any): Promise<string | null> {
  const lane = await laneOf($, e.agentId)
  if (!lane || !(await enforcing($, options))) {
    return null
  }
  const path = e.file_path ?? e.notebook_path ?? ''
  return writeRecordDeny($, lane, await $.session.cwd(), String(path))
}

/** Bash from a lane: rule 6 best effort, warehouse_spend: none, the build slot. A full hook body. */
export async function onBash($: any, options: Options, e: any, next: any): Promise<any> {
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

/** A warehouse tool from a lane: warehouse_spend: none, the ledger and the cap. Any other tool: next(e). */
export async function onWarehouseCall($: any, options: Options, e: any, next: any): Promise<any> {
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

/** Collision guard: a warning, never a refusal. */
export async function warnCollision($: any, command: string, args: string): Promise<void> {
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

export async function liveLaneLabels($: any): Promise<string[]> {
  return (await lanesOf($)).map(l => l.label)
}
