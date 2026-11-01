// Lint on write (wire#270 D6): after a Write, Edit or MultiEdit lands in a
// dbt, LookML, dbt Charts, Cube or Airflow file, run the deterministic
// convention checker (scripts/lint_conventions.py) on that file and hand the
// findings back two ways: a toast with the count, and a user-role note in the
// loop that wrote the file, so the model fixes them in the same turn. No
// findings, nothing shown. The skills keep their own call for files written
// another way.

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
