// Small `$`-using helpers the mod's concern files share: reading files that
// may be absent, running a host command, locating the framework's scripts in
// both layouts, and the state refs every file addresses by the same literals.
export const MAX_RUNS = 200

export type Options = {
  telemetry?: boolean
  metrics?: boolean
  enforce?: boolean
  context?: boolean
  lintOnWrite?: boolean
  driftWatch?: boolean
  contextLines?: number
}

export function isOn(option: boolean | undefined, envValue: string | undefined): boolean {
  return option !== false && envValue !== 'false'
}
