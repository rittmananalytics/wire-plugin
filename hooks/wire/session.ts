// Session management (wire#270 D7, wire#43): the lane stall timer, the
// handoff template as compaction instructions, /wire-handoff through one
// $.model.fork, and the opt-in drift watch.
import type { WireLane } from '../types'

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
