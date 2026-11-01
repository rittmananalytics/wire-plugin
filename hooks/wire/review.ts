// Review commands and hard gates (wire#270 D7, wire#112 R2, R3, R5).
//
// /wire-approve <artifact> [--as internal|client] [--evidence <url>] [--final]
//   appends one typed review event to `review_events:` on the artifact in
//   status.md; --final also sets `review: approved` as <artifact>-review would.
// /wire-park <artifact> "<question>" [--awaiting <who>]
//   appends a `parked_decisions` entry.
// Both run with no model turn and write nothing else.
//
// Hard gate: a Skill call or typed command from the gated set is refused when
// wire_gate.py says a blocking precondition is unmet in status.md. The deny
// names the override path, `--override-gate "<reason>"`, which the mod lets
// through and the precondition gate records against the person's name.
// Advisory gates are never touched; nor is anything in manual mode.

import type { WireActiveRelease } from '../types'
import type { ParkedDecision } from './release'
import { type Options, frameworkFile, gitUserName, isOn, readText, run1 } from './host'
const ACTIVE = { plugin: 'wire', key: 'active' } as const

async function activeOf($: any): Promise<WireActiveRelease | null> {
  const { value } = await $.state.get(ACTIVE)
  return value ?? null
}
import { releaseOf } from './logic'
import { frontMatterOf, nextParkedId, stampOf, topLevelBlock } from './release'

export type ReviewEvent = {
  actor: string
  date: string
  kind: 'internal' | 'client'
  evidence: string | null
  outcome: 'approved'
}

export type ApproveArgs = { artifact: string; release: string | null; as: 'internal' | 'client'; evidence: string | null; final: boolean } | { error: string }
export type ParkArgs = { artifact: string; release: string | null; question: string; awaiting: string | null } | { error: string }

export const APPROVE_USAGE = 'Usage: /wire-approve <artifact> [--release <folder>] [--as internal|client] [--evidence <url>] [--final]'
export const PARK_USAGE = 'Usage: /wire-park <artifact> "<question>" [--release <folder>] [--awaiting <who>]'

function tokens(args: string): string[] {
  const out: string[] = []
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(args ?? '')) !== null) {
    out.push(m[1] ?? m[2] ?? m[3] ?? '')
  }
  return out
}

export function parseApproveArgs(args: string): ApproveArgs {
  const words = tokens(args)
  let artifact = ''
  let release: string | null = null
  let as: 'internal' | 'client' = 'internal'
  let evidence: string | null = null
  let final = false
  for (let i = 0; i < words.length; i++) {
    const w = words[i] ?? ''
    if (w === '--final') {
      final = true
    } else if (w === '--as') {
      const v = words[++i]
      if (v !== 'internal' && v !== 'client') {
        return { error: `--as takes internal or client. ${APPROVE_USAGE}` }
      }
      as = v
    } else if (w === '--evidence') {
      evidence = words[++i] ?? null
    } else if (w === '--release') {
      release = words[++i] ?? null
    } else if (w.startsWith('-')) {
      return { error: `Unknown option "${w}". ${APPROVE_USAGE}` }
    } else if (!artifact) {
      artifact = w
    } else {
      return { error: `Unexpected argument "${w}". ${APPROVE_USAGE}` }
    }
  }
  if (!/^[A-Za-z0-9_]+$/.test(artifact)) {
    return { error: `An artifact id is required (letters, digits, underscores). ${APPROVE_USAGE}` }
  }
  return { artifact, release, as, evidence, final }
}

export function parseParkArgs(args: string): ParkArgs {
  const words = tokens(args)
  let artifact = ''
  let question = ''
  let release: string | null = null
  let awaiting: string | null = null
  for (let i = 0; i < words.length; i++) {
    const w = words[i] ?? ''
    if (w === '--awaiting') {
      awaiting = words[++i] ?? null
    } else if (w === '--release') {
      release = words[++i] ?? null
    } else if (w.startsWith('--')) {
      return { error: `Unknown option "${w}". ${PARK_USAGE}` }
    } else if (!artifact) {
      artifact = w
    } else if (!question) {
      question = w
    } else {
      question += ` ${w}`
    }
  }
  if (!/^[A-Za-z0-9_]+$/.test(artifact) || !question) {
    return { error: `An artifact id and a quoted question are required. ${PARK_USAGE}` }
  }
  return { artifact, release, question, awaiting }
}

const yq = (s: string) => `"${s.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`

/** The line range [start, end) of `  <artifact>:` inside the `artifacts:` block, in the whole file's lines. */
function artifactRange(lines: string[], artifact: string): { start: number; end: number; flow: boolean } | null {
  const top = lines.findIndex(l => /^artifacts:/.test(l))
  if (top < 0) {
    return null
  }
  let start = -1
  for (let i = top + 1; i < lines.length; i++) {
    const l = lines[i] ?? ''
    if (/^\S/.test(l) && l.trim() !== '') {
      break
    }
    if (new RegExp(`^  ${artifact}:`).test(l)) {
      start = i
      break
    }
  }
  if (start < 0) {
    return null
  }
  const flow = /^  [A-Za-z0-9_]+:\s*\{/.test(lines[start] ?? '')
  let end = start + 1
  while (end < lines.length && (/^\s{4,}/.test(lines[end] ?? '') || (lines[end] ?? '').trim() === '')) {
    end++
  }
  while (end > start + 1 && (lines[end - 1] ?? '').trim() === '') {
    end--
  }
  return { start, end, flow }
}

/**
 * Appends one review event to the artifact's `review_events:` list; with
 * `final`, sets `review: approved`, `reviewed_by` and `reviewed_date` as the
 * review spec's Step 4a does. Nothing else in the file changes. Returns the
 * new text, or `{ error }` naming what stopped it.
 */
export function appendReviewEvent(statusText: string, artifact: string, event: ReviewEvent, final: boolean): string | { error: string } {
  const lines = statusText.split('\n')
  const range = artifactRange(lines, artifact)
  if (!range) {
    return { error: `status.md has no artifacts.${artifact} entry.` }
  }
  if (range.flow) {
    return { error: `artifacts.${artifact} is written on one line ({...}); expand it to the block form first (/wire:status-sync does this).` }
  }
  const block = lines.slice(range.start + 1, range.end)
  const item = [
    `      - actor: ${yq(event.actor)}`,
    `        date: ${yq(event.date)}`,
    `        kind: ${event.kind}`,
    ...(event.evidence ? [`        evidence: ${yq(event.evidence)}`] : []),
    `        outcome: ${event.outcome}`,
  ]
  const idx = block.findIndex(l => /^    review_events:/.test(l))
  if (idx >= 0) {
    let insertAt = idx + 1
    while (insertAt < block.length && /^\s{6,}/.test(block[insertAt] ?? '')) {
      insertAt++
    }
    const head = block[idx] ?? ''
    if (/\[\s*\]\s*$/.test(head)) {
      block[idx] = head.replace(/\[\s*\]\s*$/, '')
    }
    block.splice(insertAt, 0, ...item)
  } else {
    block.push('    review_events:', ...item)
  }
  if (final) {
    const set = (key: string, value: string, after: string) => {
      const i = block.findIndex(l => new RegExp(`^    ${key}:`).test(l))
      if (i >= 0) {
        block[i] = `    ${key}: ${value}`
      } else {
        const r = block.findIndex(l => new RegExp(`^    ${after}:`).test(l))
        block.splice(r >= 0 ? r + 1 : block.length, 0, `    ${key}: ${value}`)
      }
    }
    set('review', 'approved', 'validate')
    set('reviewed_by', yq(event.actor), 'review')
    set('reviewed_date', event.date, 'reviewed_by')
  }
  return [...lines.slice(0, range.start + 1), ...block, ...lines.slice(range.end)].join('\n')
}

/** Appends a parked decision; creates the `parked_decisions:` block before the front matter closes when absent. */
export function appendParkedDecision(statusText: string, d: ParkedDecision): string | { error: string } {
  const { front } = frontMatterOf(statusText)
  if (!front) {
    return { error: 'status.md has no YAML front matter.' }
  }
  const lines = statusText.split('\n')
  const item = [
    `  - id: ${d.id}`,
    `    artifact: ${d.artifact}`,
    `    kind: ${d.kind}`,
    `    question: ${yq(d.question)}`,
    `    parked_at: ${yq(d.parkedAt)}`,
    ...(d.awaiting ? [`    awaiting: ${yq(d.awaiting)}`] : []),
  ]
  const key = lines.findIndex((l, i) => i > 0 && /^parked_decisions:/.test(l))
  if (key >= 0) {
    if (topLevelBlock(front, 'parked_decisions')?.length === 0) {
      lines[key] = 'parked_decisions:'
    }
    let end = key + 1
    while (end < lines.length && (/^\s+\S/.test(lines[end] ?? '') || (lines[end] ?? '').trim() === '') && (lines[end] ?? '').trim() !== '---') {
      end++
    }
    while (end > key + 1 && (lines[end - 1] ?? '').trim() === '') {
      end--
    }
    lines.splice(end, 0, ...item)
    return lines.join('\n')
  }
  const close = lines.findIndex((l, i) => i > 0 && l.trim() === '---')
  if (close < 0) {
    return { error: 'status.md front matter does not close.' }
  }
  lines.splice(close, 0, 'parked_decisions:', ...item)
  return lines.join('\n')
}

/** Commands the hard gate covers: destructive, or whose validate does real work (auto_validate: false). */
export const GATED_COMMANDS: readonly string[] = [
  'deployment-generate', 'deployment-validate', 'deployment-review',
  'cutover-generate', 'cutover-validate', 'cutover-review',
  'dbt-migration-defer-build',
  'dbt-generate', 'pipeline-generate', 'dbtcharts-generate', 'data_refactor-generate', 'agents_schema-generate', 'data_app-generate',
  'ads_agent-config-generate', 'ads_canonical-models-generate', 'ads_eval-suite-generate', 'ads_knowledge-skill-generate', 'ads_semantic-layer-generate',
  'ingestion-migration-generate', 'looker-content-generate', 'looker-target-setup-generate', 'lookml-model-generate',
  'omni-content-generate', 'omni-model-generate', 'omni-target-setup-generate',
]

export function isGated(command: string): boolean {
  return GATED_COMMANDS.includes(command.replace(/^\/wire:/, ''))
}

export function hasOverride(args: string): boolean {
  return /(^|\s)--override-gate(=|\s|$)/.test(args ?? '')
}

export function gateDeny(command: string, release: string, reason: string): string {
  return `Wire gate: ${command} ${release} is blocked: ${reason}. Run the blocking command first, or re-run with --override-gate "<reason>" to record an override against your name (specs/utils/precondition_gate.md Step 3).`
}

/** The gate's answer for one command, from wire_gate.py; null when it cannot be asked. */
export async function gateCheck($: any, cwd: string, release: string, command: string): Promise<{ decision: string; reason: string } | null> {
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
export async function hardGate($: any, options: Options, command: string, args: string): Promise<string | null> {
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

export async function registerReviewCommands($: any): Promise<void> {
  await $.command.register({ name: 'wire-approve', description: 'Wire: record a review approval on an artifact in status.md, no model turn', argumentHint: '<artifact> [--as internal|client] [--evidence <url>] [--final]' })
  await $.command.register({ name: 'wire-park', description: 'Wire: park a decision for the release director in status.md, no model turn', argumentHint: '<artifact> "<question>" [--awaiting <who>]' })
}

export async function approveCommand($: any, args: string): Promise<{ text: string }> {
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

export async function parkCommand($: any, args: string): Promise<{ text: string }> {
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
