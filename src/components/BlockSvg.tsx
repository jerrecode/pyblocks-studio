import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from 'react'
import { blockPath, connectorPoint } from '../lib/geometry'
import type { BlockInstance, BlockSpec } from '../lib/types'

interface Props {
  spec: BlockSpec
  instance?: BlockInstance
  selected?: boolean
  compact?: boolean
  onPointerDown?: (event: ReactPointerEvent<SVGGElement>) => void
  onClick?: (event: ReactMouseEvent<SVGGElement>) => void
}

export function BlockSvg({ spec, instance, selected, compact, onPointerDown, onClick }: Props) {
  const width = compact ? Math.min(spec.width, 240) : spec.width
  const scale = width / spec.width
  const height = spec.height * scale
  const path = blockPath({ ...spec, width, height })
  return (
    <svg
      width={width + 16}
      height={height + 18}
      viewBox={`-8 -8 ${width + 16} ${height + 18}`}
      className="block-svg"
      aria-label={`${spec.label} block`}
    >
      <g
        tabIndex={0}
        role="button"
        className={`block-shape ${selected ? 'is-selected' : ''}`}
        onPointerDown={onPointerDown}
        onClick={onClick}
      >
        <path d={path} fill={spec.color} stroke={spec.stroke} strokeWidth={selected ? 3 : 2} />
        {spec.connectors.map(connector => {
          const p = connectorPoint(connector, width, height)
          return (
            <g key={connector.id} className={`connector connector-${connector.family}`}>
              <circle cx={p.x} cy={p.y} r={connector.snapRadius > 24 ? 6 : 5} fill={connector.gender === 'male' ? '#fff' : spec.stroke} stroke="#fff" strokeWidth="1.5" />
              <circle cx={p.x} cy={p.y} r={Math.max(11, connector.snapRadius / 2)} fill="transparent" />
            </g>
          )
        })}
        <text x="16" y={Math.min(28, height / 2 + 5)} fill={spec.textColor} fontSize={compact ? 12 : 13} fontWeight="700" className="block-label">
          <tspan>{spec.icon}</tspan>
          <tspan dx="8">{spec.label}</tspan>
        </text>
        {instance && Object.entries({ ...(spec.fields ?? {}), ...instance.values }).slice(0, 3).map(([key, value], index) => (
          <text key={key} x={20 + index * 72} y={height - 11} fill={spec.textColor} fontSize="10" opacity=".88">
            {String(value).slice(0, 14)}
          </text>
        ))}
      </g>
    </svg>
  )
}
