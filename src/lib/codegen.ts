import type { BlockInstance, BlockSpec, WorkspaceGraph } from './types'

const indent = (text: string, level = 1) => text.split('\n').map(line => line ? `${'    '.repeat(level)}${line}` : line).join('\n')

function applyFields(template: string, values: Record<string, string>) {
  return template.replace(/\{([a-zA-Z0-9_-]+)\}/g, (_, key: string) => values[key] ?? `{${key}}`)
}

export function blockToPython(instance: BlockInstance, spec: BlockSpec, bodyText = ''): string {
  const values = { ...(spec.fields ?? {}), ...instance.values }
  let text = applyFields(spec.pythonTemplate, values)
  if (text.includes('{body}')) text = text.replace('{body}', indent(bodyText || values.body || 'pass'))
  if (text.includes('{orelse}')) text = text.replace('{orelse}', indent(values.orelse || 'pass'))
  if (text.includes('{handler}')) text = text.replace('{handler}', indent(values.handler || 'pass'))
  return text
}

export function workspaceToPython(graph: WorkspaceGraph, specs: BlockSpec[]): string {
  const specMap = new Map(specs.map(s => [s.id, s]))
  const blockMap = new Map(graph.blocks.map(b => [b.id, b]))
  const renderChain = (startId: string | undefined, seen = new Set<string>()): string => {
    if (!startId || seen.has(startId)) return ''
    const block = blockMap.get(startId)
    if (!block) return ''
    seen.add(startId)
    const spec = specMap.get(block.specId)
    if (!spec) return renderChain(block.nextId, seen)
    const body = block.bodyIds?.map(id => renderChain(id, new Set(seen))).filter(Boolean).join('\n') || ''
    const current = block.specId === 'event-start' ? '' : blockToPython(block, spec, body)
    const next = renderChain(block.nextId, seen)
    return [current, next].filter(Boolean).join('\n')
  }
  const output = graph.roots.map(root => renderChain(root)).filter(Boolean).join('\n\n')
  return `${output.trim()}\n`
}

export const starterPython = `from pathlib import Path


def find_python_files(root: Path) -> None:
    for path in root.rglob('*'):
        if path.suffix == '.py':
            print(path)


find_python_files(Path('.'))
`
