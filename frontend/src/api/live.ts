import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './client'

/**
 * Keep a resource fresh without the user ever reaching for reload.
 *
 * Polling rather than websockets: a review round changes a handful of times per
 * hour, the payload is small, and this survives the reverse proxy, the phone
 * going to sleep and the laptop lid closing — none of which a socket does for
 * free. The tab pauses while hidden, so a forgotten dashboard costs nothing.
 */
export function useLive<T>(path: string | null, intervalMs = 4000) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  // Bumped whenever the payload actually differs, so views can flash a change.
  const [version, setVersion] = useState(0)
  const previous = useRef<string>('')

  const load = useCallback(async () => {
    if (!path) return
    try {
      const fresh = await api.get<T>(path)
      const serialised = JSON.stringify(fresh)
      if (serialised !== previous.current) {
        previous.current = serialised
        setData(fresh)
        setVersion(v => v + 1)
      }
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    if (!path) return
    previous.current = ''
    setLoading(true)
    load()

    let timer: number | null = null
    const start = () => {
      if (timer === null) timer = window.setInterval(load, intervalMs)
    }
    const stop = () => {
      if (timer !== null) { clearInterval(timer); timer = null }
    }
    const onVisibility = () => {
      if (document.hidden) stop()
      else { load(); start() }
    }

    if (!document.hidden) start()
    document.addEventListener('visibilitychange', onVisibility)
    return () => { stop(); document.removeEventListener('visibilitychange', onVisibility) }
  }, [path, intervalMs, load])

  return { data, error, loading, version, refresh: load }
}
