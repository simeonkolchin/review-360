import { useEffect, useState } from 'react'
import { api } from './client'

export interface AuthConfig { bot_username: string; dev_login_enabled: boolean }

let cached: AuthConfig | null = null

export function useAuthConfig() {
  const [config, setConfig] = useState<AuthConfig | null>(cached)
  useEffect(() => {
    if (cached) return
    api.get<AuthConfig>('/auth/config')
      .then(c => { cached = c; setConfig(c) })
      .catch(() => setConfig({ bot_username: '', dev_login_enabled: false }))
  }, [])
  return config
}

export const botLink = (username: string, path = '') =>
  username ? `https://t.me/${username}${path}` : '#'
