// Lint on write (wire#270 D6): after a Write, Edit or MultiEdit lands in a
// dbt, LookML, dbt Charts, Cube or Airflow file, run the deterministic
// convention checker (scripts/lint_conventions.py) on that file and hand the
// findings back two ways: a toast with the count, and a user-role note in the
// loop that wrote the file, so the model fixes them in the same turn. No
// findings, nothing shown. The skills keep their own call for files written
// another way.

import { type Options, appendNote, exists, frameworkFile, isOn, toast } from './host'
import { absolutePath } from './lanes'

export type LintDomain = 'dbt' | 'lookml' | 'dbtcharts' | 'cube' | 'airflow'

/** The convention domain a written file belongs to, or null. `text` decides the Cube case. */
export function domainOf(path: string, text: string | null): LintDomain | null {
  const p = path.replace(/\\/g, '/')
  if (/\.lkml$/.test(p)) {
    return 'lookml'
  }
  if (/(^|\/)charts\/.*\.ya?ml$/.test(p)) {
    return 'dbtcharts'
  }
  if (/(^|\/)(model|schema)\/.*\.(js|ya?ml)$/.test(p) && /\bcube\s*\(|^\s*cubes:\s*$/m.test(text ?? '')) {
    return 'cube'
  }
  if (/(^|\/)models\/.*\.(sql|ya?ml)$/.test(p)) {
    return 'dbt'
  }
  if (/(^|\/)dags\/.*\.py$/.test(p)) {
    return 'airflow'
  }
  return null
}

export type Finding = { rule: string; severity: string; file: string; message: string; line?: number }

/** The findings for one file from the checker's `--format json` output. */
export function findingsOf(json: string, file: string): Finding[] {
  try {
    const report = JSON.parse(json)
    const all: Finding[] = Array.isArray(report?.findings) ? report.findings : []
    const base = file.split('/').pop() ?? file
    return all.filter(f => typeof f?.file === 'string' && (f.file === file || f.file.endsWith(`/${base}`) || f.file === base))
  } catch {
    return []
  }
}

export function findingsNote(domain: LintDomain, file: string, findings: readonly Finding[]): string {
  const shown = findings.slice(0, 20)
  const lines = [
    `Wire conventions (${domain}): ${findings.length} finding${findings.length === 1 ? '' : 's'} in ${file}. Fix them in this turn; the checker's result is ground truth for the rules it covers.`,
    ...shown.map(f => `- [${f.rule}] ${f.severity}${f.line ? ` line ${f.line}` : ''}: ${f.message}`),
  ]
  if (findings.length > shown.length) {
    lines.push(`- (${findings.length - shown.length} more)`)
  }
  return lines.join('\n')
}

async function conventionFor($: any, cwd: string, domain: LintDomain): Promise<string | null> {
  const own = `${cwd}/.wire/conventions/${domain}.yml`
  if (await exists($, own)) {
    return own
  }
  return frameworkFile($, `conventions/${domain}.yml`)
}

export async function lintFile($: any, cwd: string, path: string, agentId: string | null): Promise<Finding[]> {
  let text: string | null = null
  try {
    text = String(await $.fs.read(path))
  } catch {
    return []
  }
  const domain = domainOf(path, text)
  if (!domain) {
    return []
  }
  const script = await frameworkFile($, 'scripts/lint_conventions.py')
  const convention = await conventionFor($, cwd, domain)
  if (!script || !convention) {
    return []
  }
  let out = ''
  try {
    const r = await $.process.run(['python3', script, '--domain', domain, '--convention', convention, '--path', path, '--format', 'json'], { cwd, timeoutMs: 30_000 })
    out = String(r.stdout ?? '')
  } catch {
    return []
  }
  const findings = findingsOf(out, path)
  if (findings.length > 0) {
    toast($, `Wire conventions: ${findings.length} finding${findings.length === 1 ? '' : 's'} in ${path.split('/').pop()}`)
    await appendNote($, findingsNote(domain, path, findings), agentId)
  }
  return findings
}

/** After a write tool ran and did not fail: lint the file it wrote. Never changes the result. */
export async function afterWrite($: any, options: Options, e: any, result: any): Promise<void> {
  if (result?.deny || result?.isError || !isOn(options.lintOnWrite, await $.env.get('WIRE_LINT'))) {
    return
  }
  try {
    const cwd = await $.session.cwd()
    const path = absolutePath(String(e.file_path ?? ''), cwd)
    if (path.startsWith(`${cwd}/`)) {
      await lintFile($, cwd, path, e.agentId ?? null)
    }
  } catch {
    // lint never changes the write's result
  }
}
