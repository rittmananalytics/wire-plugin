// Pure rules for the lane registry and the operating-model refusals
// (specs/utils/director_operating_model.md rules 1, 2, 3, 5 and 6; wire#270
// D5). No `$` here: hooks/wire/enforce.ts applies these to events, and
// tests/enforce-lanes.test.ts and tests/enforce-budget.test.ts exercise them.

export type LaneBrief = {
  label: string
  release: string | null
  tasks: string
  owns: string[]
  stateFile: string | null
  budget: string | null
  /** Lines the template requires that the brief lacks (`Owns:`, `State file:`, `Resume:`). */
  missing: string[]
}

const BRIEF_FIELDS = ['Lane', 'Release', 'Task', 'Tasks', 'Owns', 'State file', 'Resume', 'Budget', 'Flat', 'Status', 'Report'] as const

/**
 * A Wire lane brief in a spawn prompt (the template in
 * director_operating_model.md), or null when the prompt is not one. A brief
 * has a `Lane:` line and at least one of `Owns:`, `State file:` or `Resume:`;
 * an ordinary subagent prompt that happens to say "Lane:" once is not one.
 */
export function parseLaneBrief(prompt: string): LaneBrief | null {
  const fields = new Map<string, string[]>()
  let current: string | null = null
  for (const raw of (prompt ?? '').split('\n')) {
    const m = /^\s*(Lane|Release|Tasks?|Owns|State file|Resume|Budget|Flat|Status|Report|Inputs|Context file)\s*:\s*(.*)$/.exec(raw)
    if (m) {
      current = m[1] === 'Task' ? 'Tasks' : (m[1] ?? null)
      if (current) {
        fields.set(current, [...(fields.get(current) ?? []), (m[2] ?? '').trim()])
      }
      continue
    }
    // A continuation line of the current field (indented, under Owns: or Resume:).
    if (current && /^\s{2,}\S/.test(raw) && !/^\s*-\s*\S+:/.test(raw)) {
      fields.set(current, [...(fields.get(current) ?? []), raw.trim()])
    } else if (raw.trim() === '') {
      current = null
    }
  }
  const label = fields.get('Lane')?.[0]
  if (!label) {
    return null
  }
  const hasAny = ['Owns', 'State file', 'Resume'].some(k => fields.has(k))
  if (!hasAny) {
    return null
  }
  const owns = (fields.get('Owns') ?? [])
    .flatMap(v => v.split(/[,\s]+/))
    .map(v => v.trim().replace(/[.;]+$/, '').replace(/\/+$/, ''))
    .filter(v => v && !/^(nothing|else|—|-)$/i.test(v) && /[\/.]/.test(v))
  const missing = (['Owns', 'State file', 'Resume'] as const).filter(k => !(fields.get(k)?.some(v => v !== '')))
  if (owns.length === 0 && !missing.includes('Owns')) {
    missing.push('Owns')
  }
  return {
    label,
    release: fields.get('Release')?.[0]?.split(/\s+/)[0] || null,
    tasks: (fields.get('Tasks') ?? []).join(' '),
    owns,
    stateFile: fields.get('State file')?.[0]?.split(/\s+/)[0] || null,
    budget: fields.get('Budget')?.join(' ') || null,
    missing,
  }
}

export function isBriefField(name: string): boolean {
  return (BRIEF_FIELDS as readonly string[]).includes(name)
}

/** Without a trailing slash, `./` segments removed. Not a realpath: the host resolves symlinks. */
export function normalisePath(p: string): string {
  let out = p.replace(/\/\.\//g, '/').replace(/\/+/g, '/')
  if (out.length > 1 && out.endsWith('/')) {
    out = out.slice(0, -1)
  }
  return out
}

/** Absolute form of `p` against `cwd`. */
export function absolutePath(p: string, cwd: string): string {
  return normalisePath(p.startsWith('/') ? p : `${cwd}/${p}`)
}

/** True when `path` is `dir` or inside it. */
export function isUnder(path: string, dir: string): boolean {
  const a = normalisePath(path)
  const d = normalisePath(dir)
  return a === d || a.startsWith(`${d}/`)
}

export function isUnderAny(path: string, dirs: readonly string[]): boolean {
  return dirs.some(d => isUnder(path, d))
}

/** `.wire/releases/<release>/status.md` or `execution_log.md`: the record the orchestrator alone writes (rule 6). */
export function isRecordFile(path: string): boolean {
  return /\/\.wire\/releases\/[^/]+\/(status\.md|execution_log\.md)$/.test(normalisePath(path))
}

/** The release folder a record-file path names. */
export function releaseOfRecordPath(path: string): string | null {
  return /\/\.wire\/releases\/([^/]+)\/(?:status\.md|execution_log\.md)$/.exec(normalisePath(path))?.[1] ?? null
}

/**
 * Best effort for Bash (rule 6): the command names status.md or
 * execution_log.md under .wire/releases/ together with a way of writing it:
 * a redirect, `sed -i`, `tee`, or `python3 -c`.
 */
export function bashWritesRecord(command: string): boolean {
  const c = command ?? ''
  if (!/\.wire\/releases\/[^\s'"]*\/(status\.md|execution_log\.md)/.test(c)) {
    return false
  }
  return /(^|[^<>])>{1,2}\s*[^\s&|]/.test(c) || /\bsed\s+(-[a-zA-Z]*i|--in-place)/.test(c) || /\btee\b/.test(c) || /\bpython3?\s+-c\b/.test(c)
}

/** `dbt build|run|snapshot|seed`: a warehouse build (rule 2's slot). */
export function isDbtBuild(command: string): boolean {
  return /(^|[\s;&|])dbt\s+(?:--[^\s]+\s+)*(build|run|snapshot|seed)\b/.test(command ?? '')
}

/** `dbt build|run|snapshot|seed|test`: anything that queries the warehouse. */
export function isDbtWarehouseRun(command: string): boolean {
  return /(^|[\s;&|])dbt\s+(?:--[^\s]+\s+)*(build|run|snapshot|seed|test)\b/.test(command ?? '')
}

/** The warehouse project a dbt command names (`--project <x>`, `--project-dir <x>`), else the fallback. */
export function dbtProjectOf(command: string, fallback: string): string {
  const m = /--project(?:-dir)?[=\s]+["']?([^\s"']+)/.exec(command ?? '')
  return m?.[1] ?? fallback
}

/** A warehouse tool that runs SQL and may bill: BigQuery execute_sql (not the read-only one), Snowflake sql_exec. */
export function isWarehouseWriteTool(tool: string): boolean {
  const t = tool ?? ''
  if (!t.startsWith('mcp__')) {
    return false
  }
  if (/bigquery/i.test(t) && /__execute_sql$/.test(t)) {
    return true
  }
  return /snowflake/i.test(t) && /__sql_exec$/.test(t)
}

/** `totalBytesProcessed` (BigQuery) or `bytes_scanned` (Snowflake) in a tool result's text. */
export function bytesBilledOf(resultText: string | null | undefined): number {
  const m = /"?(?:totalBytesProcessed|totalBytesBilled|total_bytes_processed|bytes_scanned)"?\s*[:=]\s*"?(\d+)/.exec(resultText ?? '')
  const n = Number(m?.[1])
  return Number.isFinite(n) ? n : 0
}

/** BigQuery on-demand analysis price, USD per TiB (the default; the cost rules in the specs estimate ahead of time). */
export const USD_PER_TIB = 6.25

export function bytesToUsd(bytes: number): number {
  return Math.round((bytes / 2 ** 40) * USD_PER_TIB * 10_000) / 10_000
}

export const BUILD_SLOT_MINUTES = 60

export const refusal = {
  flatLane: (label: string) =>
    `Wire rule 1 (flat lanes): lane "${label}" may not spawn a sub-agent. Report that the work is bigger than one lane; the orchestrator splits it.`,
  outsideTree: (label: string, path: string, owns: readonly string[]) =>
    `Wire rule 3 (tree ownership): lane "${label}" may write only under ${owns.join(', ') || 'its owned directories'}; ${path} is outside them. Record the need in your state file and report it.`,
  singleWriter: (label: string, path: string, stateFile: string | null) =>
    `Wire rule 6 (single writer): lane "${label}" may not write ${path}. The orchestrating session writes status.md and execution_log.md from your state file${stateFile ? ` (${stateFile})` : ''}.`,
  missingBrief: (label: string, missing: readonly string[]) =>
    `Wire lane brief for "${label}" lacks ${missing.map(m => `${m}:`).join(', ')}; every dispatch carries the lane brief template in specs/utils/director_operating_model.md.`,
  lanesMax: (max: number, live: readonly string[]) =>
    `Wire budget: lanes_max ${max} reached; queued behind ${live.join(', ')}. Change the budget in status.md or wait for a lane to finish.`,
  warehouseNone: (label: string, what: string) =>
    `budget-blocked: warehouse_spend: none. Lane "${label}" may not run ${what}. Change the budget in status.md, or report it as budget-blocked.`,
  buildSlot: (project: string, holder: string, minutes: number) =>
    `Wire rule 2 (one build per project): the build slot for "${project}" is held by lane "${holder}" (${minutes} min). Wait for it, or report the contention.`,
  capPassed: (usd: number, cap: number, release: string) =>
    `budget-blocked: warehouse spend for ${release} is $${usd.toFixed(2)}, past cap:${cap}. A parked decision (kind budget) has been raised in status.md; no further warehouse call runs until the director rules.`,
}
