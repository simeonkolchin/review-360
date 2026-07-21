import { useEffect, useRef, useState } from 'react'

const GLYPHS = '!<>-_\\/[]{}—=+*^?#$%&@01'

/**
 * Text scramble (decode effect).
 *
 * A requestAnimationFrame loop with a per-character settle deadline: every
 * glyph churns through the charset, then locks into its real character, roughly
 * left to right. Pass several `phrases` and it cycles through them forever.
 *
 * Following the pattern properly:
 *  - the final string lives in `aria-label`, the churning span is `aria-hidden`,
 *    so screen readers get the text and never the noise;
 *  - `prefers-reduced-motion` renders text instantly, no churn;
 *  - the churn sits in a fixed-width, tabular-numeral box so the line never
 *    jitters as glyph widths change;
 *  - the effect keys off the phrase, not off every parent render, so it always
 *    reaches its settle deadline.
 */
export default function Scramble({
  text,
  phrases,
  className = '',
  holdMs = 2200,
  speed = 1.7,
  tickMs = 40,
}: {
  /** single, static string — resolves once */
  text?: string
  /** several strings — resolves, holds, then decodes into the next one */
  phrases?: string[]
  className?: string
  holdMs?: number
  /** ticks of stagger per character; higher is slower */
  speed?: number
  /** milliseconds between glyph swaps — a raw 60fps churn reads as a flicker */
  tickMs?: number
}) {
  const list = phrases?.length ? phrases : [text ?? '']
  const [index, setIndex] = useState(0)
  const target = list[index % list.length]
  const [output, setOutput] = useState(target)
  const raf = useRef<number | null>(null)
  const timer = useRef<number | null>(null)

  const reduced =
    typeof window !== 'undefined' &&
    !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    const clear = () => {
      if (raf.current) cancelAnimationFrame(raf.current)
      if (timer.current) clearTimeout(timer.current)
    }
    const advance = (delay: number) => {
      if (list.length < 2) return
      timer.current = window.setTimeout(() => setIndex(i => i + 1), delay)
    }

    if (reduced) {
      setOutput(target)
      advance(holdMs + 700)
      return clear
    }

    const queue = Array.from(target).map((char, i) => ({
      char,
      start: Math.floor(Math.random() * 5) + i * speed,
      end: Math.floor(Math.random() * 8) + i * speed + 10,
    }))
    let frame = 0
    let last = 0

    // Driven by rAF, but stepped on a timer: the churn advances every `tickMs`
    // instead of every repaint, which is what makes it readable rather than a blur.
    const tick = (now: number) => {
      if (now - last < tickMs) {
        raf.current = requestAnimationFrame(tick)
        return
      }
      last = now

      let settled = 0
      const next = queue
        .map(({ char, start, end }) => {
          if (frame >= end) { settled++; return char }
          if (char === ' ') return ' '
          if (frame < start) return ' '
          return GLYPHS[Math.floor(Math.random() * GLYPHS.length)]
        })
        .join('')

      setOutput(next)

      if (settled === queue.length) {
        advance(holdMs)
        return
      }
      frame++
      raf.current = requestAnimationFrame(tick)
    }

    raf.current = requestAnimationFrame(tick)
    return clear
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, list.length, holdMs, speed, tickMs, reduced])

  // Reserve the widest phrase so the surrounding layout never reflows mid-churn.
  const widest = list.reduce((a, b) => (a.length >= b.length ? a : b), '')

  return (
    <span className={`scramble ${className}`} aria-label={target}>
      <span aria-hidden="true" className="inline-block" style={{ minWidth: `${widest.length}ch` }}>
        {output}
      </span>
    </span>
  )
}
