// Identity and the Segment calls the mod makes (wire#270 D3): the anonymous
// install id in ~/.wire/telemetry_id, the identify call made once, and one
// extra event beside wire_command (a rule-7 miss, a drift hit). Telemetry
// never fails or delays a command, and is off under WIRE_TELEMETRY=false or
// the plugin's `telemetry` option.

import type { WireIdentity } from '../types'
import { SEGMENT_IDENTIFY, SEGMENT_TRACK, SEGMENT_WRITE_KEY, WIRE_VERSION } from './constants'
import { type Options, isOn, run1 } from './host'
import { identifyBody } from './logic'

const IDENTITY = { plugin: 'wire', key: 'identity' } as const

export async function identityOf($: any): Promise<{ identity: WireIdentity; isNew: boolean }> {
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

export async function post($: any, url: string, body: string): Promise<void> {
  try {
    await $.http.fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body })
  } catch {
    // Telemetry never fails or blocks a command.
  }
}

/** One extra telemetry event beside wire_command (a rule-7 miss, a drift hit), with the same identity. */
export async function sendEvent($: any, options: Options, event: string, properties: Record<string, unknown>): Promise<void> {
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


/** The identify call for a new install, once. */
export async function identifyIfNew($: any, identity: WireIdentity, isNew: boolean, timestamp: string): Promise<void> {
  if (isNew) {
    await post($, SEGMENT_IDENTIFY, identifyBody(SEGMENT_WRITE_KEY, identity.userId, {
      username: identity.username, hostname: identity.hostname, os: identity.os, version: WIRE_VERSION, timestamp,
    }))
  }
}
