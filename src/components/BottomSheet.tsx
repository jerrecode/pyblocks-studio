import { useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent, ReactNode } from 'react'

interface Props { open: boolean; onOpenChange: (open: boolean) => void; children: ReactNode }

export function BottomSheet({ open, onOpenChange, children }: Props) {
  const [height, setHeight] = useState(40)
  const drag = useRef<{ y: number; height: number } | null>(null)
  const onDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId)
    drag.current = { y: e.clientY, height }
  }
  const onMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!drag.current) return
    const delta = (drag.current.y - e.clientY) / window.innerHeight * 100
    setHeight(Math.max(28, Math.min(82, drag.current.height + delta)))
  }
  const onUp = () => { drag.current = null }
  return (
    <div className={`bottom-sheet ${open ? 'open' : ''}`} style={{ height: `${height}dvh` }} aria-hidden={!open}>
      <div className="sheet-grabber" onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
        <span />
        <button onClick={() => onOpenChange(false)}>Close</button>
      </div>
      <div className="sheet-content">{children}</div>
    </div>
  )
}
