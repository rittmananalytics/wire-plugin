// The Wire mod's $.state contract: every value it keeps for the session.
// `claude plugin validate` holds hooks/register.ts and hooks/wire/*.ts to it;
// wire/tests/schema/validate_mod_contract.py checks every key the module
// names is declared here.

export type WireRun = {
  /** Run id: tool_use_id for a Skill call, or a generated id for a typed command. */
  id: string
  /** As the execution log writes it: `/wire:dbt-generate`. */
  command: string
  /** The command's arguments after the release, as typed; '' when none. Kept for the band, never sent. */
  args?: string
  release: string | null
  /** The loop the run is in: a subagent's id, null on the main loop. */
  agentId: string | null
  invokedBy: 'typed' | 'orchestrator' | 'lane' | 'autopilot' | 'studio'
  /** The persona the run was made as (specs/utils/personas.md), '' when none. */
  persona?: string
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
  /** The Result cell of the log row the run filled (`complete`, `pass`, ...), when known. */
  result?: string | null
  /** The lane's label when a lane ran it (from the lane registry). */
  laneLabel?: string | null
  /** Rule 7: the orchestrator's reply that closed this run had no `Ran:` line naming it. */
  ranLineMissing?: boolean
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

/** The active release, resolved at session start (specs/start.md Step B1 order). */
export type WireActiveRelease = {
  /** `named`, `branch`, `only_recent`, `only_release`, `ask` or `new_engagement`. */
  resolution: string
  release: string | null
  candidates: string[]
  /** `orchestrated` or `manual` (.wire/engagement/context.md). */
  mode: 'orchestrated' | 'manual'
  clientName: string
}

/** The system-prompt section the mod composes, with the file times it was built from. */
export type WireContextCache = {
  text: string
  /** mtimeMs of status.md, decisions.md and the business-rules register, in that order; 0 when absent. */
  mtimes: number[]
  release: string | null
}

/** One live lane, registered from the brief its agent.spawn carried. */
export type WireLane = {
  agentId: string
  label: string
  release: string | null
  /** The brief's Task(s) line, for the collision guard. */
  tasks: string
  /** Owned directories, resolved to real paths, each without a trailing slash. */
  owns: string[]
  stateFile: string | null
  budget: string | null
  startedAt: number
  /** Set once the stall timer has reported the lane, so it reports once. */
  stalledAt: number | null
}

/** A dbt build slot held by a lane for one warehouse project (rule 2). */
export type WireBuildSlot = {
  project: string
  agentId: string
  laneLabel: string
  heldAt: number
}

/** Running warehouse spend for one release (the cost-governance ledger). */
export type WireSpend = {
  release: string
  bytes: number
  usd: number
  /** True once the cap has been passed and the parked decision raised. */
  capBreached: boolean
}

/** A gate the precondition gate stopped, read from the log's `blocked` rows for the band. */
export type WireNotRun = {
  command: string
  gate: string
}

declare module 'claude-code' {
  interface PluginState {
    wire: {
      runs: WireRun[]
      /** One member per run id. Kept apart from `runs` so a request's late write can never overwrite a closed run. */
      stepUsage: StateFamily<WireStepUsage>
      autopilot: boolean
      identity: WireIdentity | null
      /** The active release and orchestration mode, from session.start. */
      active: WireActiveRelease | null
      /** The release-context section, recomputed only when its files change. */
      context: WireContextCache | null
      /** Live lanes, by the agent id their spawn resolved to. */
      lanes: WireLane[]
      buildSlots: WireBuildSlot[]
      spend: WireSpend | null
      /** Gates the band shows as `Not run:` rows. */
      notRun: WireNotRun[]
      /** The last context-window percentage session.measure reported. */
      contextPercent: number
      /** True once the 85 percent toast has been shown this session. */
      contextWarned: boolean
      /** Main-loop turns completed, for the drift watch's cadence. */
      turns: number
      /** The last drift-watch hit, drawn in the band until dismissed. */
      drift: string | null
      /** True while the person has collapsed the band's run list. */
      bandHidden: boolean
    }
  }
}
