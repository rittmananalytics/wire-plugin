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

export async function readText($: any, path: string): Promise<string | null> {
  try {
    return String(await $.fs.read(path))
  } catch {
    return null
  }
}

export async function exists($: any, path: string): Promise<boolean> {
  try {
    return (await $.fs.exists(path)) === true
  } catch {
    return false
  }
}

export async function mtimeOf($: any, path: string): Promise<number> {
  try {
    const st = await $.fs.stat(path)
    return typeof st?.mtimeMs === 'number' ? st.mtimeMs : 0
  } catch {
    return 0
  }
}

/** The real path of `path`, or of its parent folder plus its name when it does not exist yet, or the path itself. */
export async function realPathOf($: any, path: string): Promise<string> {
  try {
    const own = await $.fs.stat(path, { resolve: true })
    if (own?.realPath) {
      return String(own.realPath)
    }
  } catch {
    // not there yet
  }
  const i = path.lastIndexOf('/')
  if (i > 0) {
    try {
      const dir = await $.fs.stat(path.slice(0, i), { resolve: true })
      if (dir?.realPath) {
        return `${String(dir.realPath).replace(/\/$/, '')}/${path.slice(i + 1)}`
      }
    } catch {
      // parent not there either
    }
  }
  return path
}

export async function run1($: any, argv: string[], cwd: string, timeoutMs = 3000): Promise<string> {
  try {
    const r = await $.process.run(argv, { cwd, timeoutMs })
    return r.exitCode === 0 ? String(r.stdout ?? '').trim() : ''
  } catch {
    return ''
  }
}

export async function gitUserName($: any, cwd: string): Promise<string> {
  return (await run1($, ['git', 'config', '--get', 'user.name'], cwd)) || 'unknown'
}

export async function gitBranch($: any, cwd: string): Promise<string> {
  const b = await run1($, ['git', 'branch', '--show-current'], cwd)
  if (b) {
    return b
  }
  const h = await run1($, ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd)
  return h === 'HEAD' ? '' : h
}

/** A file of the framework in either layout: the built plugin root, or `wire/` above the source tree. */
export async function frameworkFile($: any, rel: string): Promise<string | null> {
  for (const path of [`${$.plugin.root}/${rel}`, `${$.plugin.root}/../../${rel}`]) {
    if (await exists($, path)) {
      return path
    }
  }
  return null
}

export async function sessionIdOf($: any): Promise<string> {
  try {
    return String((await $.session.id()) ?? '')
  } catch {
    return ''
  }
}

export function toast($: any, text: string): void {
  try {
    $.ui.toast(text)
  } catch {
    // a surface with no toasts
  }
}

/** A user-role row the model reads and the person does not see as typed. */
export async function appendNote($: any, text: string, agentId?: string | null): Promise<void> {
  try {
    await $.session.append({ message: { type: 'user', content: [{ type: 'text', text }] }, ...(agentId ? { agentId } : {}) })
  } catch {
    // a loop that is no longer running
  }
}

export function isOn(option: boolean | undefined, envValue: string | undefined): boolean {
  return option !== false && envValue !== 'false'
}

/** The release folders under `.wire/releases/` with their status.md times. */
export async function listReleases($: any, cwd: string): Promise<{ folder: string; mtime: number; statusText: string | null }[]> {
  const out: { folder: string; mtime: number; statusText: string | null }[] = []
  try {
    for (const d of await $.fs.list(`${cwd}/.wire/releases`)) {
      if (d.kind !== 'dir') {
        continue
      }
      const path = `${cwd}/.wire/releases/${d.name}/status.md`
      out.push({ folder: d.name, mtime: await mtimeOf($, path), statusText: await readText($, path) })
    }
  } catch {
    return []
  }
  return out.sort((a, b) => a.folder.localeCompare(b.folder))
}
