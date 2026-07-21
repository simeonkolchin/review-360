import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

/**
 * Panel that slides in from the right over a scrim.
 *
 * Same rules as the modal — Escape and outside-click close it, body scroll is
 * locked — but it keeps the page visible behind, which is what you want while
 * editing settings that belong to what you are looking at.
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
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="scrim !p-0 !place-items-stretch"
         onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className="drawer ml-auto flex flex-col" style={{ width: `min(${width}px, 100%)` }}
           role="dialog" aria-modal="true" aria-label={title}>
        <div className="flex items-start justify-between gap-4 p-6 pb-4 border-b border-[var(--color-border)]">
          <div>
            <h3 className="text-[17px] m-0 tracking-tight">{title}</h3>
            {subtitle && (
              <p className="text-[13px] text-[var(--color-muted)] mt-1.5 mb-0">{subtitle}</p>
            )}
          </div>
          <button onClick={onClose} className="btn btn-ghost p-2 shrink-0" aria-label="Закрыть">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6">{children}</div>

        {footer && (
          <div className="flex items-center gap-2 p-5 border-t border-[var(--color-border)]">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
