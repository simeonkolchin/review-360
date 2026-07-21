import { useEffect } from 'react'

/**
 * Freeze the page behind an overlay without shifting it sideways.
 *
 * Hiding body overflow removes the scrollbar, and the page jumps by its width.
 * `scrollbar-gutter: stable` (set on html) handles that in current browsers;
 * this measures the bar and pads the body by the same amount for the ones that
 * do not support it yet, so the layout never moves either way.
 */
export function useBodyScrollLock(active: boolean) {
  useEffect(() => {
    if (!active) return

    const { body } = document
    const previousOverflow = body.style.overflow
    const previousPadding = body.style.paddingRight

    const supportsGutter =
      typeof CSS !== 'undefined' && CSS.supports?.('scrollbar-gutter', 'stable')
    const barWidth = window.innerWidth - document.documentElement.clientWidth

    body.style.overflow = 'hidden'
    if (!supportsGutter && barWidth > 0) {
      const current = parseFloat(getComputedStyle(body).paddingRight) || 0
      body.style.paddingRight = `${current + barWidth}px`
    }

    return () => {
      body.style.overflow = previousOverflow
      body.style.paddingRight = previousPadding
    }
  }, [active])
}
