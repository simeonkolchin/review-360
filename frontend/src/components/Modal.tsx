import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { useBodyScrollLock } from './useBodyScrollLock'

/**
 * Dialog over a scrim — the dimmed, blurred layer behind a popup.
 * Closes on Escape and on a click outside, and locks body scroll while open.
 */
export default function Modal({
  open, onClose, title, subtitle, children, footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children?: React.ReactNode
  footer?: React.ReactNode
}) {
  useBodyScrollLock(open)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className="scrim" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
        <div className="flex items-start justify-between gap-4 p-6 pb-4">
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

        <div className="px-6 pb-2">{children}</div>

        {footer && (
          <div className="flex justify-end gap-2 p-6 pt-4 border-t border-[var(--color-border)] mt-4">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
