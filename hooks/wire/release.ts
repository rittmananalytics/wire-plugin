// Pure readers of a Wire engagement's record: status.md front matter, the
// engagement context, decisions.md, the business-rules register, and the
// active-release resolution. No `$` here; tests/context.test.ts and
// tests/review.test.ts exercise these with plain strings.
//
// Parsing is line-based and deliberately narrow: it reads the shapes the
// templates write (wire/TEMPLATES/status-template.md, specs/utils/
// director_operating_model.md) and ignores anything else. A full YAML parser
// is not available in a hooks module, and the mod never writes a value it
// parsed back, so a key it misreads costs a status-line field, not the record.

export type Claim = {
  user: string
  sessionId: string
  branch: string
  claimedAt: string
  lastWrite: string
}

export type Budget = {
  lanesMax: number
  /** `none`, `estimate_required`, `cap:<amount>`, or null when unset. */
  warehouseSpend: string | null
  stopAt: string | null
}

export type ParkedDecision = {
  id: string
  artifact: string
  kind: string
  question: string
  parkedAt: string
  awaiting: string | null
}

export type ArtifactState = { generate?: string; validate?: string; review?: string }

export type Ruling = { id: string; date: string; who: string; title: string }

export type ReleaseInfo = {
  folder: string
  claimedBranch: string | null
  daysSinceWrite: number | null
}

export type Resolution = {
  resolution: 'named' | 'branch' | 'only_recent' | 'only_release' | 'ask' | 'new_engagement'
  release: string | null
  candidates: string[]
  reason?: string
}

const RECENT_DAYS = 7

export function unquote(v: string): string {
  const t = v.trim()
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1)
  }
  return t
}

/** The YAML front matter (without the fences) and the body of a status.md. */
export function frontMatterOf(text: string): { front: string; body: string } {
  if (!text.startsWith('---')) {
    return { front: '', body: text }
  }
  const lines = text.split('\n')
  for (let i = 1; i < lines.length; i++) {
    if (lines[i]?.trim() === '---') {
      return { front: lines.slice(1, i).join('\n'), body: lines.slice(i + 1).join('\n') }
    }
  }
  return { front: '', body: text }
}

function stripComment(line: string): string {
  // A `#` that starts a comment is preceded by whitespace or starts the line;
  // one inside quotes is kept.
  let inQuote: string | null = null
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (inQuote) {
      if (c === inQuote) inQuote = null
    } else if (c === '"' || c === "'") {
      inQuote = c
    } else if (c === '#' && (i === 0 || /\s/.test(line[i - 1] ?? ''))) {
      return line.slice(0, i).trimEnd()
    }
  }
  return line
}

/** The lines of a top-level key's block (the key line excluded), or null when absent. */
export function topLevelBlock(front: string, key: string): string[] | null {
  const lines = front.split('\n')
  const start = lines.findIndex(l => new RegExp(`^${key}:`).test(l))
  if (start < 0) {
    return null
  }
  const out: string[] = []
  for (let i = start + 1; i < lines.length; i++) {
    const l = lines[i] ?? ''
    if (/^\S/.test(l) && l.trim() !== '') {
      break
    }
    out.push(l)
  }
  // A one-line value (`parked_decisions: []`) has no block lines.
  const inline = stripComment(lines[start] ?? '').slice(key.length + 1).trim()
  if (inline && out.every(l => l.trim() === '')) {
    return []
  }
  return out
}

/** A top-level scalar: `project_type: "full_platform"` to `full_platform`. */
export function scalarOf(front: string, key: string): string | null {
  const m = new RegExp(`^${key}:\\s*(.*)$`, 'm').exec(front)
  if (!m) {
    return null
  }
  const v = unquote(stripComment(m[1] ?? ''))
  return v === '' || v === 'null' || v === '~' ? null : v
}

/** A nested scalar inside block lines, by indentation-insensitive key match on the first hit. */
function nestedScalar(lines: string[], key: string): string | null {
  for (const l of lines) {
    const m = new RegExp(`^\\s+${key}:\\s*(.*)$`).exec(l)
    if (m) {
      const v = unquote(stripComment(m[1] ?? ''))
      return v === '' || v === 'null' || v === '~' ? null : v
    }
  }
  return null
}

export function orchestrationModeOf(contextMd: string | null): 'orchestrated' | 'manual' {
  if (!contextMd) {
    return 'orchestrated'
  }
  const { front } = frontMatterOf(contextMd)
  const block = topLevelBlock(front || contextMd, 'orchestration')
  if (!block) {
    return 'orchestrated'
  }
  return nestedScalar(block, 'mode') === 'manual' ? 'manual' : 'orchestrated'
}

export function claimOf(front: string): Claim | null {
  const agents = topLevelBlock(front, 'agents')
  if (!agents) {
    return null
  }
  const i = agents.findIndex(l => /^\s+coordinator_session:/.test(l))
  if (i < 0) {
    return null
  }
  const head = stripComment(agents[i] ?? '').split(':').slice(1).join(':').trim()
  if (head === 'null' || head === '~') {
    return null
  }
  const indent = (agents[i] ?? '').search(/\S/)
  const lines: string[] = []
  for (let k = i + 1; k < agents.length; k++) {
    const l = agents[k] ?? ''
    if (l.trim() !== '' && l.search(/\S/) <= indent) {
      break
    }
    lines.push(l)
  }
  const user = nestedScalar(lines, 'user')
  if (!user) {
    return null
  }
  return {
    user,
    sessionId: nestedScalar(lines, 'session_id') ?? '',
    branch: nestedScalar(lines, 'branch') ?? '',
    claimedAt: nestedScalar(lines, 'claimed_at') ?? '',
    lastWrite: nestedScalar(lines, 'last_write') ?? nestedScalar(lines, 'claimed_at') ?? '',
  }
}

export function budgetOf(front: string): Budget {
  const block = topLevelBlock(front, 'budget')
  const lanes = block ? Number(nestedScalar(block, 'lanes_max')) : NaN
  return {
    lanesMax: Number.isInteger(lanes) && lanes > 0 ? lanes : 4,
    warehouseSpend: block ? nestedScalar(block, 'warehouse_spend') : null,
    stopAt: block ? nestedScalar(block, 'stop_at') : null,
  }
}

/** The amount after `cap:`, as a number, or null for any other setting. */
export function capOf(warehouseSpend: string | null): number | null {
  const m = /^cap:\s*\$?\s*([0-9][0-9_,]*(?:\.[0-9]+)?)/.exec(warehouseSpend ?? '')
  if (!m) {
    return null
  }
  const n = Number((m[1] ?? '').replace(/[_,]/g, ''))
  return Number.isFinite(n) ? n : null
}

/** Items of a top-level list block: each item's lines, the leading `- ` removed from the first. */
function listItems(block: string[]): string[][] {
  const items: string[][] = []
  let current: string[] | null = null
  for (const l of block) {
    if (/^\s*-\s/.test(l)) {
      current = [l.replace(/^(\s*)-\s/, '$1  ')]
      items.push(current)
    } else if (current && l.trim() !== '') {
      current.push(l)
    }
  }
  return items
}

export function parkedDecisionsOf(front: string): ParkedDecision[] {
  const block = topLevelBlock(front, 'parked_decisions')
  if (!block) {
    return []
  }
  return listItems(block).map(lines => ({
    id: nestedScalar(lines, 'id') ?? '',
    artifact: nestedScalar(lines, 'artifact') ?? '',
    kind: nestedScalar(lines, 'kind') ?? 'ruling',
    question: nestedScalar(lines, 'question') ?? '',
    parkedAt: nestedScalar(lines, 'parked_at') ?? '',
    awaiting: nestedScalar(lines, 'awaiting'),
  })).filter(d => d.id)
}

/** The next `PD-<n>` id after those present. */
export function nextParkedId(front: string): string {
  const max = parkedDecisionsOf(front).reduce((m, d) => {
    const n = Number(/^PD-(\d+)$/.exec(d.id)?.[1])
    return Number.isInteger(n) && n > m ? n : m
  }, 0)
  return `PD-${max + 1}`
}

/**
 * Artifact lifecycle states from the `artifacts:` block: the block form the
 * template writes and the flow form (`dbt: {generate: complete, ...}`).
 */
export function artifactStatesOf(front: string): Record<string, ArtifactState> {
  const block = topLevelBlock(front, 'artifacts')
  const out: Record<string, ArtifactState> = {}
  if (!block) {
    return out
  }
  let current: string | null = null
  for (const raw of block) {
    const l = stripComment(raw)
    const head = /^  ([A-Za-z0-9_]+):\s*(.*)$/.exec(l)
    if (head) {
      current = head[1] ?? null
      if (current) {
        out[current] = out[current] ?? {}
        const flow = /^\{(.*)\}$/.exec((head[2] ?? '').trim())
        if (flow) {
          for (const pair of (flow[1] ?? '').split(',')) {
            const kv = /^\s*([a-z_]+):\s*(.*)$/.exec(pair)
            if (kv && (kv[1] === 'generate' || kv[1] === 'validate' || kv[1] === 'review')) {
              out[current][kv[1]] = unquote(kv[2] ?? '')
            }
          }
        }
      }
      continue
    }
    const step = /^    (generate|validate|review):\s*(.*)$/.exec(l)
    if (step && current) {
      out[current][step[1] as 'generate' | 'validate' | 'review'] = unquote(step[2] ?? '')
    }
  }
  return out
}

export function approvedCount(states: Record<string, ArtifactState>): number {
  return Object.values(states).filter(s => s.review === 'approved').length
}

/** Rows of the `## Iterations` table whose State is not closed or merged. */
export function openIterationsOf(body: string): { id: string; title: string; state: string }[] {
  const start = body.indexOf('## Iterations')
  if (start < 0) {
    return []
  }
  const rows: { id: string; title: string; state: string }[] = []
  for (const line of body.slice(start).split('\n').slice(1)) {
    if (/^## /.test(line)) {
      break
    }
    const t = line.trim()
    if (!t.startsWith('|')) {
      continue
    }
    const cells = t.slice(1, -1).split('|').map(c => c.trim())
    if (cells[0] === 'Id' || /^[-:\s]+$/.test(cells[0] ?? '')) {
      continue
    }
    const state = (cells[2] ?? '').toLowerCase()
    if (cells[0] && !['closed', 'merged', 'done', 'complete'].includes(state)) {
      rows.push({ id: cells[0], title: cells[1] ?? '', state: cells[2] ?? '' })
    }
  }
  return rows
}

/** Ruling headers (`## R-n | date | who | title`), in file order. */
export function rulingsOf(decisionsMd: string | null): Ruling[] {
  const out: Ruling[] = []
  for (const line of (decisionsMd ?? '').split('\n')) {
    const m = /^##\s*(R-\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*(.*)$/.exec(line)
    if (m) {
      out.push({ id: m[1] ?? '', date: (m[2] ?? '').trim(), who: (m[3] ?? '').trim(), title: (m[4] ?? '').trim() })
    }
  }
  return out
}

export type RulesSummary = {
  byDomain: Record<string, Record<string, number>>
  assumedOverdue: { id: string; confirmBy: string }[]
}

/** The business-rules register (`artifacts/business_rules.yaml`): rule counts by domain and status. */
export function businessRulesSummary(yamlText: string | null, today: string): RulesSummary {
  const out: RulesSummary = { byDomain: {}, assumedOverdue: [] }
  if (!yamlText) {
    return out
  }
  for (const item of listItems(yamlText.split('\n'))) {
    const id = nestedScalar(item, 'id') ?? ''
    const domain = nestedScalar(item, 'domain') ?? 'unassigned'
    const status = nestedScalar(item, 'status') ?? 'unknown'
    out.byDomain[domain] = out.byDomain[domain] ?? {}
    out.byDomain[domain][status] = (out.byDomain[domain][status] ?? 0) + 1
    const confirmBy = nestedScalar(item, 'confirm_by')
    if (status === 'assumed' && confirmBy && confirmBy.slice(0, 10) < today.slice(0, 10)) {
      out.assumedOverdue.push({ id, confirmBy: confirmBy.slice(0, 10) })
    }
  }
  return out
}

/** Minutes since a `YYYY-MM-DD HH:MM` stamp (read as UTC); Infinity when unreadable. */
export function minutesSince(stamp: string | null | undefined, nowMs: number): number {
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec((stamp ?? '').trim())
  if (!m) {
    return Infinity
  }
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]), Number(m[5]))
  return (nowMs - t) / 60_000
}

/** `YYYY-MM-DD HH:MM` in UTC, the form status.md stamps carry. */
export function stampOf(nowMs: number): string {
  const d = new Date(nowMs)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`
}

/**
 * Active-release resolution (specs/start.md Step B1), ported line for line
 * from wire/tests/core/validate_active_release.py so TypeScript and Python
 * agree; tests/context.test.ts runs the same fixture cases through it.
 */
export function resolveActiveRelease(releases: ReleaseInfo[], named: string | null, branch: string | null): Resolution {
  const folders = releases.map(r => r.folder)
  if (releases.length === 0) {
    return { resolution: 'new_engagement', release: null, candidates: [] }
  }
  if (named) {
    if (folders.includes(named)) {
      return { resolution: 'named', release: named, candidates: [] }
    }
    return { resolution: 'ask', release: null, candidates: folders, reason: `no release named ${named}` }
  }
  if (branch) {
    const claimed = releases.find(r => r.claimedBranch && r.claimedBranch === branch)
    if (claimed) {
      return { resolution: 'branch', release: claimed.folder, candidates: [] }
    }
    const matches = releases.filter(r => branch.includes(r.folder)).map(r => r.folder)
    if (matches.length === 1) {
      return { resolution: 'branch', release: matches[0] ?? null, candidates: [] }
    }
    if (matches.length > 1) {
      return { resolution: 'ask', release: null, candidates: matches, reason: 'more than one release folder matches the branch' }
    }
  }
  const recent = releases.filter(r => r.daysSinceWrite !== null && r.daysSinceWrite < RECENT_DAYS).map(r => r.folder)
  if (recent.length === 1) {
    return { resolution: 'only_recent', release: recent[0] ?? null, candidates: [] }
  }
  if (recent.length > 1) {
    return { resolution: 'ask', release: null, candidates: recent, reason: 'more than one release written to in the last 7 days' }
  }
  if (releases.length === 1) {
    return { resolution: 'only_release', release: folders[0] ?? null, candidates: [] }
  }
  return { resolution: 'ask', release: null, candidates: folders, reason: 'no release written to in the last 7 days' }
}

export type StatusFields = {
  version: string
  release: string | null
  candidates: string[]
  projectType: string | null
  approved: number
  parked: number
  claimUser: string | null
  contextPercent: number | null
}

/** `[Wire v4.5.0] 02-data-foundation (full_platform) · 5 approved · 1 parked · claim: Consultant A · ctx:42%` */
export function statusLine(f: StatusFields): string {
  const head = `[Wire v${f.version}]`
  const ctx = f.contextPercent === null ? '' : ` · ctx:${f.contextPercent}%`
  if (!f.release) {
    if (f.candidates.length > 1) {
      return `${head} ${f.candidates.length} releases active: ${f.candidates.join(', ')} (say which)${ctx}`
    }
    return `${head} no active release${ctx}`
  }
  return `${head} ${f.release} (${f.projectType ?? 'unknown type'}) · ${f.approved} approved · ${f.parked} parked · claim: ${f.claimUser ?? 'none'}${ctx}`
}

export type SessionLineFields = {
  clientName: string
  release: string | null
  candidates: string[]
  projectType: string | null
  approved: number
  parked: ParkedDecision[]
  mode: 'orchestrated' | 'manual'
  releaseCount: number
}

/** The one-line session opener wire-session-check.sh printed, now from the mod. */
export function sessionLine(f: SessionLineFields): string {
  if (f.releaseCount === 0) {
    return '[Wire] Engagement set up — no releases started yet. Run /wire:new to create your first release.'
  }
  if (!f.release) {
    return f.candidates.length > 1
      ? `[Wire] More than one release active: ${f.candidates.join(' ')}. Say which one, or run /wire:start to pick.`
      : '[Wire] No active release could be resolved. Run /wire:start to pick one.'
  }
  let line = `[Wire] ${f.clientName || 'this engagement'} / ${f.release} (${f.projectType ?? 'unknown type'}) — ${f.approved} artifacts approved`
  if (f.parked.length > 0) {
    line += `, ${f.parked.length} decision(s) waiting`
  }
  line += f.mode === 'manual' ? '. Manual mode. Run /wire:start for status and next steps.' : '. Say what you want done, or run /wire:start.'
  return line
}

export type ContextInputs = {
  release: string
  projectType: string | null
  profile: string | null
  phase: string | null
  nextAction: string | null
  parked: ParkedDecision[]
  rulings: Ruling[]
  rules: RulesSummary
  iterations: { id: string; title: string; state: string }[]
  claim: Claim | null
  mode: 'orchestrated' | 'manual'
  maxLines: number
}

/**
 * The release-context section (wire#270 D6), bounded to `maxLines`. Each
 * part is cut before the next starts so the parked decisions are never lost
 * to a long rulings list.
 */
export function releaseContext(c: ContextInputs): string {
  const lines: string[] = []
  lines.push(`Wire release context: ${c.release}${c.projectType ? ` (${c.projectType}${c.profile ? `, profile ${c.profile}` : ''})` : ''}, ${c.mode} mode.`)
  if (c.phase) {
    lines.push(`Current phase: ${c.phase}.`)
  }
  if (c.nextAction) {
    lines.push(`Next action: ${c.nextAction}`)
  }
  if (c.claim) {
    lines.push(`Release claim: ${c.claim.user} (session ${c.claim.sessionId || 'unknown'}, last write ${c.claim.lastWrite || 'unknown'}).`)
  }
  if (c.parked.length > 0) {
    lines.push(`Parked decisions (${c.parked.length}), each cleared by a ruling in decisions.md:`)
    for (const d of c.parked) {
      lines.push(`- ${d.id} (${d.artifact}, ${d.kind}${d.awaiting ? `, awaiting ${d.awaiting}` : ''}): ${d.question}`)
    }
  } else {
    lines.push('Parked decisions: none.')
  }
  const rulings = c.rulings.slice(-10)
  if (rulings.length > 0) {
    lines.push(`Last rulings (decisions.md):`)
    for (const r of rulings) {
      lines.push(`- ${r.id} | ${r.date} | ${r.who} | ${r.title}`)
    }
  }
  const domains = Object.keys(c.rules.byDomain).sort()
  if (domains.length > 0) {
    lines.push('Business rules register, by domain:')
    for (const d of domains) {
      const s = c.rules.byDomain[d] ?? {}
      const parts = ['agreed', 'disputed', 'assumed', 'unknown'].map(k => `${k} ${s[k] ?? 0}`)
      lines.push(`- ${d}: ${parts.join(', ')}`)
    }
    for (const o of c.rules.assumedOverdue) {
      lines.push(`- ${o.id} is assumed and past its confirm_by (${o.confirmBy}).`)
    }
  }
  if (c.iterations.length > 0) {
    lines.push('Iterations in flight:')
    for (const it of c.iterations) {
      lines.push(`- ${it.id} ${it.title} (${it.state})`)
    }
  }
  const max = Math.max(5, c.maxLines)
  if (lines.length > max) {
    return [...lines.slice(0, max - 1), `(${lines.length - (max - 1)} more lines not shown; run /wire:status ${c.release})`].join('\n')
  }
  return lines.join('\n')
}
