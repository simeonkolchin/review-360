import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { useBodyScrollLock } from './useBodyScrollLock'

/** Keep the panel mounted long enough to play the closing animation. */
const CLOSE_MS = 260

/**
 * Panel that slides in from the right over a scrim.
 *
 * Same rules as the modal — Escape and outside-click close it, body scroll is
 * locked — but it keeps the page visible behind, which is what you want while
 * editing settings that belong to what you are looking at.
 *
 * Closing is animated too: the component stays mounted for one animation and
 * only then tells the parent, so the panel slides out instead of vanishing.
 */
export default function Drawer({
  open, onClose, title, subtitle, children, footer, width = 520,
}: {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: React.ReactNode
  footer?: React.ReactNode
  width?: number
}) {
  const [mounted, setMounted] = useState(open)
  const [closing, setClosing] = useState(false)

  // Play the exit animation first, then unmount and notify the parent.
  const requestClose = useCallback(() => {
    setClosing(true)
    window.setTimeout(() => {
      setClosing(false)
      setMounted(false)
      onClose()
    }, CLOSE_MS)
  }, [onClose])

  useEffect(() => {
    if (open) { setMounted(true); setClosing(false) }
  }, [open])

  useBodyScrollLock(mounted)

  useEffect(() => {
    if (!mounted) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && requestClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [mounted, requestClose])

  if (!mounted) return null

  return createPortal(
    <div className={`drawer-scrim ${closing ? 'closing' : ''}`}
         onMouseDown={e => e.target === e.currentTarget && requestClose()}>
      <div className={`drawer ${closing ? 'closing' : ''}`} style={{ width: `min(${width}px, 100%)` }}
           role="dialog" aria-modal="true" aria-label={title}>
        <div className="flex items-start justify-between gap-4 p-6 pb-4 border-b
                        border-[var(--color-border)] shrink-0">
          <div>
            <h3 className="text-[17px] m-0 tracking-tight">{title}</h3>
            {subtitle && (
              <p className="text-[13px] text-[var(--color-muted)] mt-1.5 mb-0">{subtitle}</p>
            )}
          </div>
          <button onClick={requestClose} className="btn btn-ghost p-2 shrink-0" aria-label="Закрыть">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="drawer-body scroll-slim p-6">{children}</div>

        {footer && (
          <div className="flex items-center gap-2 p-5 border-t border-[var(--color-border)] shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
