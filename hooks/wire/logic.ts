// Pure logic for the Wire mod's telemetry and execution-log metrics.
// No `$` here: everything takes plain values and returns plain values, so
// tests/logic.test.ts exercises it directly. The contract it implements is
// specs/utils/execution_log.md ("Metrics Backfill") and specs/utils/telemetry.md.

export type Usage = {
  input_tokens: number
  output_tokens: number
  cache_creation_input_tokens: number
  cache_read_input_tokens: number
}

export const NA = 'n/a'

// Anthropic API prices, USD per million tokens, as of 2026-09:
// (input, output, cache_read). Cache writes are charged at 1.25x input.
// Matched by substring against the model id, first match wins, so more
// specific ids come before their prefixes. Carried over unchanged from the
// retired hooks/wire_metrics.py.
export const PRICING: ReadonlyArray<readonly [string, readonly [number, number, number]]> = [
  ['claude-haiku-4-5', [1.0, 5.0, 0.1]],
  ['claude-sonnet-4-6', [3.0, 15.0, 0.3]],
  ['claude-sonnet-5', [2.0, 10.0, 0.2]],
  ['claude-opus-4', [5.0, 25.0, 0.5]],
  ['claude-opus-5', [5.0, 25.0, 0.5]],
  ['claude-fable-5-1', [10.0, 50.0, 0.25]],
  ['claude-fable-5', [10.0, 50.0, 1.0]],
  ['claude-mythos-5', [10.0, 50.0, 1.0]],
]
export const CACHE_WRITE_MULTIPLIER = 1.25

export const INVOKED_BY = ['typed', 'orchestrator', 'lane', 'autopilot', 'studio'] as const
export type InvokedBy = (typeof INVOKED_BY)[number]

export function emptyUsage(): Usage {
  return { input_tokens: 0, output_tokens: 0, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 }
}

/** Adds a usage record (any object with the four counts) to a running total. */
export function addUsage(total: Usage, more: Partial<Record<keyof Usage, unknown>> | null | undefined): Usage {
  if (!more) {
    return total
  }
  const n = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? Math.trunc(v) : 0)
  return {
    input_tokens: total.input_tokens + n(more.input_tokens),
    output_tokens: total.output_tokens + n(more.output_tokens),
    cache_creation_input_tokens: total.cache_creation_input_tokens + n(more.cache_creation_input_tokens),
    cache_read_input_tokens: total.cache_read_input_tokens + n(more.cache_read_input_tokens),
  }
}

export function totalTokens(u: Usage): number {
  return u.input_tokens + u.output_tokens + u.cache_creation_input_tokens + u.cache_read_input_tokens
}

/** Estimated USD cost, or null for an unknown model: never a guessed price. */
export function computeCost(model: string | null | undefined, u: Usage): number | null {
  if (!model) {
    return null
  }
  const hit = PRICING.find(([key]) => model.includes(key))
  if (!hit) {
    return null
  }
  const [inRate, outRate, readRate] = hit[1]
  const cost =
    (u.input_tokens * inRate +
      u.output_tokens * outRate +
      u.cache_read_input_tokens * readRate +
      u.cache_creation_input_tokens * inRate * CACHE_WRITE_MULTIPLIER) /
    1_000_000
  return Math.round(cost * 100) / 100
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
    return NA
  }
  const s = Math.max(0, Math.trunc(seconds))
  const pad = (n: number) => String(n).padStart(2, '0')
  if (s < 60) {
    return `${s}s`
  }
  if (s < 3600) {
    return `${Math.floor(s / 60)}m ${pad(s % 60)}s`
  }
  return `${Math.floor(s / 3600)}h ${pad(Math.floor((s % 3600) / 60))}m`
}

export type Measured = {
  command: string
  usage: Usage
  model: string | null
  durationSeconds: number | null
  /**
   * Rows dated before this day (`YYYY-MM-DD`, local) are never filled: they
   * belong to an earlier run. A day, not a time, because commands write the
   * row's time themselves and it is often rough (a model writing `00:00`).
   */
  notBefore?: string
}

function cellsOf(line: string): string[] | null {
  const t = line.trim()
  if (!(t.startsWith('|') && t.endsWith('|'))) {
    return null
  }
  return t.slice(1, -1).split('|').map(c => c.trim())
}

/**
 * Backfills the Duration, Tokens and Cost cells of the newest row that logs
 * this command, whose Tokens cell is still `n/a` and whose date is not
 * before `notBefore`. Returns the new text, or null when nothing may change:
 * no such row, or only legacy rows without the nine metric-bearing columns.
 * Only those three cells of that one row change; Duration only when still
 * `n/a`. Searching upward, not only the last row, lets concurrent lanes'
 * rows each be filled by their own run.
 */
export function backfillLog(text: string, run: Measured): string | null {
  const lines = text.split('\n')
  for (let i = lines.length - 1; i >= 0; i--) {
    const cells = cellsOf(lines[i] ?? '')
    if (!cells) {
      continue
    }
    if (cells[0] === 'Timestamp' || /^[-:\s]+$/.test(cells[0] ?? '')) {
      return null
    }
    if (cells.length < 9) {
      continue
    }
    const command = (cells[1] ?? '').split(/\s+/)[0]
    if (command !== run.command || cells[cells.length - 2] !== NA) {
      continue
    }
    if (run.notBefore && (cells[0] ?? '').slice(0, 10) < run.notBefore.slice(0, 10)) {
      return null
    }
    const n = cells.length
    if (cells[n - 3] === NA) {
      cells[n - 3] = formatDuration(run.durationSeconds)
    }
    cells[n - 2] = String(totalTokens(run.usage))
    const cost = computeCost(run.model, run.usage)
    cells[n - 1] = cost === null ? NA : `$${cost.toFixed(2)}`
    lines[i] = `| ${cells.join(' | ')} |`
    return lines.join('\n')
  }
  return null
}

/** `YYYY-MM-DD HH:MM` in local time, the execution log's timestamp form, `minutes` before `ms`. */
export function logStamp(ms: number, minutes = 0): string {
  const d = new Date(ms - minutes * 60_000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** The release folder a command names as its first argument, if it looks like one. */
export function releaseOf(args: string): string | null {
  const first = (args ?? '').trim().split(/\s+/)[0] ?? ''
  return /^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$/.test(first) && !first.startsWith('-') ? first : null
}

/** `wire:dbt-generate` (command.run) or `wire:dbt-generate` (Skill) to the log's `/wire:dbt-generate`. */
export function logCommandOf(name: string): string | null {
  const m = /^wire:([A-Za-z0-9_-]+)$/.exec((name ?? '').trim())
  return m ? `/wire:${m[1]}` : null
}

/**
 * Who started a run (specs/utils/telemetry.md, invoked_by):
 * - a typed command is `typed`, or `studio` when the session was opened by
 *   Wire Studio's "Run in Claude Code" (WIRE_INVOKED_BY=studio in its env);
 * - a Skill call on the main loop is `orchestrator`, or `autopilot` while
 *   /wire:autopilot runs in this session;
 * - a Skill call inside a subagent's loop is `lane`.
 */
export function invokedBy(path: 'command' | 'skill', agentId: string | null, autopilot: boolean, envValue: string | undefined): InvokedBy {
  if (path === 'command') {
    return envValue === 'studio' ? 'studio' : 'typed'
  }
  if (agentId) {
    return 'lane'
  }
  return autopilot ? 'autopilot' : 'orchestrator'
}

export type TrackFields = {
  command: string
  invokedBy: InvokedBy
  timestamp: string
  release: string | null
  sessionId: string | null
  agentId: string | null
  gitRepo: string
  gitBranch: string
  username: string
  hostname: string
  os: string
  version: string
}

/**
 * The Segment track body. Keeps the properties the 4.0 hook sent and adds
 * release, session_id and agent_id. Deliberately leaves out the command's
 * arguments: they can hold free text a consultant typed, and telemetry has
 * never carried prompt text.
 */
export function trackBody(writeKey: string, userId: string, f: TrackFields): string {
  return JSON.stringify({
    writeKey,
    userId,
    event: 'wire_command',
    properties: {
      command: f.command,
      timestamp: f.timestamp,
      git_repo: f.gitRepo,
      git_branch: f.gitBranch,
      username: f.username,
      hostname: f.hostname,
      plugin_version: f.version,
      os: f.os,
      runtime: 'claude',
      invoked_by: f.invokedBy,
      release: f.release,
      session_id: f.sessionId,
      agent_id: f.agentId,
    },
  })
}

export function identifyBody(writeKey: string, userId: string, f: Pick<TrackFields, 'username' | 'hostname' | 'os' | 'version' | 'timestamp'>): string {
  return JSON.stringify({
    writeKey,
    userId,
    traits: { username: f.username, hostname: f.hostname, os: f.os, plugin_version: f.version, first_seen: f.timestamp },
  })
}

/** Off when the option is false or the matching environment variable is "false". */
export function isOn(option: boolean | undefined, envValue: string | undefined): boolean {
  return option !== false && envValue !== 'false'
}

export type RunRow = { command: string; release: string | null; invokedBy: InvokedBy; tokens: number; cost: number | null; seconds: number | null; filled: boolean }

/** The text /wire-usage prints: this session's Wire runs with tokens and cost. */
export function usageReport(rows: readonly RunRow[]): string {
  if (rows.length === 0) {
    return 'No Wire commands have run in this session yet.'
  }
  const lines = ['| Command | Release | Started by | Duration | Tokens | Cost (USD) | In log |', '|---|---|---|---|---|---|---|']
  let tokens = 0
  let cost = 0
  let costKnown = true
  for (const r of rows) {
    tokens += r.tokens
    if (r.cost === null) {
      costKnown = false
    } else {
      cost += r.cost
    }
    lines.push(`| ${r.command} | ${r.release ?? '-'} | ${r.invokedBy} | ${formatDuration(r.seconds)} | ${r.tokens} | ${r.cost === null ? NA : `$${r.cost.toFixed(2)}`} | ${r.filled ? 'yes' : 'not yet'} |`)
  }
  lines.push('', `Total: ${tokens} tokens, ${costKnown ? `$${cost.toFixed(2)}` : `at least $${cost.toFixed(2)} (some models unpriced)`}.`)
  return lines.join('\n')
}

// ---------------------------------------------------------------------------
// /wire-studio: start, restart, stop and report Wire Studio for this repository
// ---------------------------------------------------------------------------

export type StudioAction = 'start' | 'restart' | 'stop' | 'status'
export type StudioArgs = { action: StudioAction; port: number | null } | { error: string }

export const STUDIO_USAGE = 'Usage: /wire-studio [start|restart|stop|status] [--port <n>]'
export const STUDIO_PORT_FIRST = 4800
export const STUDIO_PORT_LAST = 4820

/** `start` when nothing is given; `--port` between 1024 and 65535. */
export function parseStudioArgs(args: string): StudioArgs {
  const words = (args ?? '').trim().split(/\s+/).filter(Boolean)
  let action: StudioAction = 'start'
  let port: number | null = null
  for (let i = 0; i < words.length; i++) {
    const w = words[i] ?? ''
    if (w === 'start' || w === 'restart' || w === 'stop' || w === 'status') {
      action = w
    } else if (w === '--port' || w.startsWith('--port=')) {
      const raw = w.includes('=') ? w.split('=')[1] : words[++i]
      const n = Number(raw)
      if (!Number.isInteger(n) || n < 1024 || n > 65535) {
        return { error: `--port needs a number between 1024 and 65535. ${STUDIO_USAGE}` }
      }
      port = n
    } else {
      return { error: `Unknown argument "${w}". ${STUDIO_USAGE}` }
    }
  }
  return { action, port }
}

/** One state file per repository, named from its path. */
export function studioStateName(repo: string): string {
  const slug = repo.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(-80)
  return `${slug || 'repo'}.json`
}

export type StudioRecord = { pid: number; port: number; repo: string; startedAt: string }

export function parseStudioRecord(text: string | null): StudioRecord | null {
  if (!text) {
    return null
  }
  try {
    const r = JSON.parse(text)
    return Number.isInteger(r?.pid) && Number.isInteger(r?.port) && typeof r?.repo === 'string' ? r : null
  } catch {
    return null
  }
}
