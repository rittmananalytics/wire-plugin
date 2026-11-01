// The commands band (wire#270 D6): a row above the prompt listing the Wire
// commands this session ran, in full, with result, tokens and cost; the
// steps a gate stopped as `Not run:` rows; and the drift watch's last hit.
// /wire-ran prints the same as text, for surfaces without a band.
//
// Rule 7 (director_operating_model.md): a reply that ran Wire commands ends
// with a `Ran:` line naming each in full. checkRanLine says which of a turn's
// runs the reply left out; register.ts marks them and sends the telemetry.
import type { WireNotRun, WireRun } from '../types'

import { computeCost, totalTokens } from './logic'

export const BAND_MAX_RUNS = 8

export function formatTokens(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(1)}M tok`
  }
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)}k tok`
  }
  return `${n} tok`
}

/** `Ran: /wire:dbt-generate 02-data-foundation · complete · 14.2k tok · $0.31 · lane L1` */
export function runLine(r: WireRun): string {
  const full = `${r.command}${r.release ? ` ${r.release}` : ''}${r.args ? ` ${r.args}` : ''}`
  const parts = [`${r.endedAt === null ? 'Running' : 'Ran'}: ${full}`]
  if (r.result) {
    parts.push(r.result)
  }
  if (r.endedAt !== null) {
    parts.push(formatTokens(totalTokens(r.usage)))
    const cost = computeCost(r.model, r.usage)
    if (cost !== null) {
      parts.push(`$${cost.toFixed(2)}`)
    }
  }
  if (r.invokedBy === 'lane') {
    parts.push(r.laneLabel ? `lane ${r.laneLabel}` : 'lane')
  }
  return parts.join(' · ')
}

export function notRunLine(n: WireNotRun): string {
  return `Not run: ${n.command}, gate: ${n.gate}`
}

/** The text of the band and of /wire-ran. */
export function bandText(runs: readonly WireRun[], notRun: readonly WireNotRun[], drift: string | null): string {
  const lines = [...runs.map(runLine), ...notRun.map(notRunLine)]
  if (drift) {
    lines.push(`Drift: ${drift}`)
  }
  return lines.length ? lines.join('\n') : 'No Wire commands have run in this session yet.'
}

/**
 * Which of `runs` the reply's `Ran:` line does not name in full (command
 * plus release). The check is on the orchestrator's own runs: a typed
 * command's reply is the command's output, and a lane reports to its spawner.
 */
export function checkRanLine(runs: readonly WireRun[], answer: string): WireRun[] {
  const ranLines = (answer ?? '').split('\n').filter(l => /^\s*(Ran|Running):/.test(l)).join(' ')
  return runs.filter(r => {
    if (r.invokedBy !== 'orchestrator' && r.invokedBy !== 'autopilot') {
      return false
    }
    const full = `${r.command}${r.release ? ` ${r.release}` : ''}`
    return !ranLines.includes(full)
  })
}

/** Rows of an execution log with Result `blocked`: `Not run: <command>, gate: <Detail>`. Newest last. */
export function blockedRowsOf(logText: string | null, notBefore: string): WireNotRun[] {
  const out: WireNotRun[] = []
  for (const line of (logText ?? '').split('\n')) {
    const t = line.trim()
    if (!t.startsWith('|')) {
      continue
    }
    const cells = t.slice(1, -1).split('|').map(c => c.trim())
    if (cells.length < 4 || cells[2] !== 'blocked' || (cells[0] ?? '').slice(0, 10) < notBefore.slice(0, 10)) {
      continue
    }
    const command = cells[1] ?? ''
    const gate = (cells[3] ?? '').replace(/^gate:\s*/, '')
    out.push({ command, gate })
  }
  return out
}
