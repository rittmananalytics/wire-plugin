// Automatic upgrade of the safe, deterministic parts (wire#270 follow-up):
// at every session start in a Wire repository the mod applies the two
// `/wire:upgrade` steps that need no judgment and change no artifact state,
// then says which releases still need the full command.
//
// 1. The 4.0 session-check hook (`UserPromptSubmit` running
//    `wire-session-check.sh` in .claude/settings.json) is removed, with its
//    script: the mod's prompt.compose section carries the same line, and a
//    repository with both shows it twice. Every other hook stays.
// 2. An execution log whose header has fewer than the nine columns of
//    specs/utils/execution_log.md gets the full header and separator
//    (upgrade.md Step 6e). Data rows are never touched.
//
// Both edits are idempotent, so they run every start without a marker. A
// release whose `wire_plugin_version` is older than the plugin, or absent, is
// named in one note, and (wire#400) the real command is queued for it:
// `/wire:upgrade --from-mod <release> ...` through $.command.run, which shows
// the status.md diff and asks before writing, as a typed run does. Queued once per repository per
// plugin version (a $.store marker), only in an interactive session, and never
// for a release another person holds with a live claim. The log header is left
// alone for such a release too.

import { WIRE_VERSION } from './constants'
import { appendNote, exists, gitUserName, listReleases, readText, sessionIdOf, toast } from './host'
import { claimOf, frontMatterOf, minutesSince, scalarOf } from './release'

export const SESSION_CHECK_SCRIPT = 'wire-session-check.sh'
export const LOG_HEADER_9 = '| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |'
export const LOG_SEPARATOR_9 = '|-----------|---------|--------|--------|----|---------|----------|--------|------------|'
const CLAIM_LIVE_MINUTES = 30

/** Removes the session-check entry from a settings.json text; `removed` says whether anything changed. */
export function removeSessionCheckHook(settingsText: string): { text: string; removed: boolean } {
  let settings: any
  try {
    settings = JSON.parse(settingsText)
  } catch {
    return { text: settingsText, removed: false }
  }
  const hooks = settings?.hooks
  const entries = hooks?.UserPromptSubmit
  if (!Array.isArray(entries)) {
    return { text: settingsText, removed: false }
  }
  const names = (entry: any) => (Array.isArray(entry?.hooks) ? entry.hooks : [entry]).some((h: any) => typeof h?.command === 'string' && h.command.includes(SESSION_CHECK_SCRIPT))
  const kept = entries.filter(e => !names(e))
  if (kept.length === entries.length) {
    return { text: settingsText, removed: false }
  }
  if (kept.length > 0) {
    hooks.UserPromptSubmit = kept
  } else {
    delete hooks.UserPromptSubmit
    if (Object.keys(hooks).length === 0) {
      delete settings.hooks
    }
  }
  return { text: `${JSON.stringify(settings, null, 2)}\n`, removed: true }
}

/**
 * The log with its header and separator extended to nine columns, or null
 * when there is nothing to do: already nine, no header, or a header that is
 * not one of the shapes Wire ever wrote (four or six columns).
 */
export function extendLogHeader(logText: string): string | null {
  const lines = logText.split('\n')
  const i = lines.findIndex(l => /^\|\s*Timestamp\s*\|/.test(l))
  if (i < 0 || !/^\|[-:\s|]+\|\s*$/.test(lines[i + 1] ?? '')) {
    return null
  }
  const cells = (lines[i] ?? '').trim().slice(1, -1).split('|').map(c => c.trim())
  if (cells.length >= 9) {
    return null
  }
  const four = ['Timestamp', 'Command', 'Result', 'Detail']
  const six = [...four, 'By', 'Session']
  const matches = (shape: string[]) => cells.length === shape.length && shape.every((c, k) => cells[k] === c)
  if (!matches(four) && !matches(six)) {
    return null
  }
  lines[i] = LOG_HEADER_9
  lines[i + 1] = LOG_SEPARATOR_9
  return lines.join('\n')
}

/**
 * -1, 0 or 1 comparing dotted versions. A missing version is older than any
 * readable one. An unreadable version on either side (the source tree's
 * unsubstituted version placeholder, a hand-typed value) compares equal: the mod
 * cannot say, so it does not call a release behind.
 */
export function compareVersions(a: string | null, b: string | null): number {
  const parse = (v: string | null) => (v ?? '').trim().split('.').map(n => Number(n))
  const readable = (v: string | null) => v !== null && v.trim() !== '' && parse(v).every(n => Number.isInteger(n))
  if (a === null && b === null) {
    return 0
  }
  if (a === null) {
    return readable(b) ? -1 : 0
  }
  if (b === null) {
    return readable(a) ? 1 : 0
  }
  if (!readable(a) || !readable(b)) {
    return 0
  }
  const pa = parse(a)
  const pb = parse(b)
  for (let k = 0; k < Math.max(pa.length, pb.length); k++) {
    const d = (pa[k] ?? 0) - (pb[k] ?? 0)
    if (d !== 0) {
      return d < 0 ? -1 : 1
    }
  }
  return 0
}

export type UpgradeReport = {
  hookRemoved: boolean
  scriptRemoved: boolean
  logsExtended: string[]
  /** Releases whose wire_plugin_version is older than the plugin, with the version recorded or 'none'. */
  behind: { release: string; version: string }[]
  /** Releases behind that another person holds with a live claim: named, not queued. */
  heldElsewhere: string[]
  /** The /wire:upgrade prompt queued this start, or null. */
  queued: string | null
}

export const QUEUED_STORE_KEY = 'upgradeQueued'

/** The prompt that upgrades `releases` in order through the real command. */
export function upgradePrompt(releases: readonly string[]): string {
  return `/wire:upgrade --from-mod ${releases.join(' ')}`
}

export function upgradeNote(r: UpgradeReport, pluginVersion: string): string | null {
  const lines: string[] = []
  if (r.hookRemoved) {
    lines.push(`- Removed the 4.0 session-check hook from .claude/settings.json${r.scriptRemoved ? ' and deleted .claude/hooks/wire-session-check.sh' : ''}: the Wire mod now carries the session line, and both together showed it twice.`)
  }
  for (const log of r.logsExtended) {
    lines.push(`- Extended the header of ${log} to the nine-column shape (existing rows unchanged; metrics are recorded from the next command).`)
  }
  if (r.behind.length > 0) {
    const tail = r.queued
      ? `The next turn runs \`${r.queued}\`, which shows the status.md changes and asks before writing them.`
      : 'Run /wire:upgrade <release> for each; it shows the status.md changes and asks before writing them.'
    lines.push(`- Releases last upgraded before Wire ${pluginVersion}: ${r.behind.map(b => `${b.release} (${b.version})`).join(', ')}. ${tail}`)
  }
  if (r.heldElsewhere.length > 0) {
    lines.push(`- Not queued: ${r.heldElsewhere.join(', ')} (held by another person's live session; upgrade it from that session, or after their claim lapses).`)
  }
  if (lines.length === 0) {
    return null
  }
  const head = r.hookRemoved || r.logsExtended.length > 0
    ? 'Wire upgrade: the mod applied the safe steps for this plugin version. Commit these changes with your next pull request.'
    : 'Wire upgrade: nothing was changed automatically.'
  return [head, ...lines].join('\n')
}

/** Runs the automatic upgrade for the repository at `cwd` and reports what it did. */
export async function autoUpgrade($: any, cwd: string, isInteractive: boolean): Promise<UpgradeReport> {
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
