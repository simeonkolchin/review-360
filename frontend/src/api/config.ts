import { useEffect, useState } from 'react'
import { api } from './client'

export interface AuthConfig {
  bot_username: string
  dev_login_enabled: boolean
  /** peer averages stay hidden below this many answers */
  min_responses_for_results: number
}

const FALLBACK: AuthConfig = {
  bot_username: '', dev_login_enabled: false, min_responses_for_results: 3,
}

let cached: AuthConfig | null = null

export function useAuthConfig() {
  const [config, setConfig] = useState<AuthConfig | null>(cached)
  useEffect(() => {
    if (cached) return
    api.get<AuthConfig>('/auth/config')
      .then(c => { cached = c; setConfig(c) })
      .catch(() => setConfig(FALLBACK))
  }, [])
  return config
}

export const botLink = (username: string, path = '') =>
  username ? `https://t.me/${username}${path}` : '#'

/**
 * How many colleagues will end up rating each person in a team.
 *
 * You never rate yourself as a peer, and the leader's opinion is counted apart
 * so it cannot hide inside the team average — which means the leader is rated
 * by everyone else, and everybody else by everyone except themselves and the
 * leader. The smaller of the two is what decides whether averages appear.
 */
export function peerCounts(size: number, hasLeader: boolean) {
  const leader = Math.max(0, size - 1)
  const member = Math.max(0, hasLeader ? size - 2 : size - 1)
  return { leader, member, lowest: hasLeader ? Math.min(leader, member) : member }
}
