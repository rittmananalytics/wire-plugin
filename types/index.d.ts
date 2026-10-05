// The Wire mod's $.state contract: every value it keeps for the session.
// `claude plugin validate` holds hooks/register.ts to it.

export type WireRun = {
  /** Run id: tool_use_id for a Skill call, or a generated id for a typed command. */
  id: string
  /** As the execution log writes it: `/wire:dbt-generate`. */
  command: string
  release: string | null
  /** The loop the run is in: a subagent's id, null on the main loop. */
  agentId: string | null
  invokedBy: 'typed' | 'orchestrator' | 'lane' | 'autopilot' | 'studio'
  startedAt: number
  endedAt: number | null
  /** Final usage, set when the run closes (zero while it is open; see stepUsage). */
  usage: {
    input_tokens: number
    output_tokens: number
    cache_creation_input_tokens: number
    cache_read_input_tokens: number
  }
  model: string | null
  /** True once its execution_log.md row carries the measured cells. */
  filled: boolean
}

/** Usage recorded per model request for one run, while it is open. */
export type WireStepUsage = {
  usage: WireRun['usage']
  model: string | null
}

export type WireIdentity = {
  userId: string
  username: string
  hostname: string
  os: string
  gitRepo: string
  gitBranch: string
}

declare module 'claude-code' {
  interface PluginState {
    wire: {
      runs: WireRun[]
      /** One member per run id. Kept apart from `runs` so a request's late write can never overwrite a closed run. */
      stepUsage: StateFamily<WireStepUsage>
      autopilot: boolean
      identity: WireIdentity | null
    }
  }
}
