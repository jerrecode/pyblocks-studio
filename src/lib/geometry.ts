import type { BlockKind, BlockSpec, ConnectorSpec } from './types'

const r = 12
const notchX = 28
const notchW = 34
const notchD = 7

function topStack(w: number) {
  return `M ${r} 0 H ${notchX} l 7 ${notchD} h ${notchW - 14} l 7 ${-notchD} H ${w - r} Q ${w} 0 ${w} ${r}`
}

function bottomStack(w: number, h: number) {
  return `V ${h - r} Q ${w} ${h} ${w - r} ${h} H ${notchX + notchW} l -7 ${notchD} h ${-(notchW - 14)} l -7 ${-notchD} H ${r} Q 0 ${h} 0 ${h - r}`
}

export function blockPath(spec: Pick<BlockSpec, 'kind' | 'width' | 'height' | 'bodySlots'>): string {
  const { kind, width: w, height: h } = spec
  switch (kind as BlockKind) {
    case 'hat':
      return `M 0 ${r + 12} Q 10 0 44 0 H ${w - r} Q ${w} 0 ${w} ${r} ${bottomStack(w, h)} V ${r + 12} Q 0 ${r + 12} 0 ${r + 12} Z`
    case 'stack':
    case 'import':
      return `${topStack(w)} ${bottomStack(w, h)} V ${r} Q 0 0 ${r} 0 Z`
    case 'terminal':
      return `${topStack(w)} V ${h - r} Q ${w} ${h} ${w - r} ${h} H ${r} Q 0 ${h} 0 ${h - r} V ${r} Q 0 0 ${r} 0 Z`
    case 'reporter':
      return `M ${h / 2} 0 H ${w - h / 2} Q ${w} 0 ${w} ${h / 2} Q ${w} ${h} ${w - h / 2} ${h} H ${h / 2} Q 0 ${h} 0 ${h / 2} Q 0 0 ${h / 2} 0 Z`
    case 'boolean':
      return `M ${h / 2} 0 H ${w - h / 2} L ${w} ${h / 2} L ${w - h / 2} ${h} H ${h / 2} L 0 ${h / 2} Z`
    case 'decorator':
      return `M 10 0 H ${w - r} Q ${w} 0 ${w} ${r} V ${h - r} Q ${w} ${h} ${w - r} ${h} H 0 V 10 Z`
    case 'comment':
      return `M ${r} 0 H ${w - 24} L ${w} 24 V ${h - r} Q ${w} ${h} ${w - r} ${h} H ${r} Q 0 ${h} 0 ${h - r} V ${r} Q 0 0 ${r} 0 Z M ${w - 24} 0 V 24 H ${w}`
    case 'container':
    case 'declaration': {
      const mouthTop = 50
      const mouthBottom = h - 30
      return `${topStack(w)} V ${mouthTop} H 32 V ${mouthBottom} H ${w} ${bottomStack(w, h)} V ${r} Q 0 0 ${r} 0 Z`
    }
    default:
      return `M ${r} 0 H ${w - r} Q ${w} 0 ${w} ${r} V ${h - r} Q ${w} ${h} ${w - r} ${h} H ${r} Q 0 ${h} 0 ${h - r} V ${r} Q 0 0 ${r} 0 Z`
  }
}

export function connectorPoint(connector: ConnectorSpec, width: number, height: number) {
  return { x: connector.x * width, y: connector.y * height }
}

export function compatible(a: ConnectorSpec, b: ConnectorSpec) {
  if (a.role === b.role || a.gender === b.gender) return false
  if (a.family === 'any' || b.family === 'any') return true
  if (a.family === b.family) return true
  if (a.coercion || b.coercion) {
    const valueFamilies = new Set(['expression', 'boolean', 'iterable', 'callable', 'name', 'type'])
    return valueFamilies.has(a.family) && valueFamilies.has(b.family)
  }
  return false
}
