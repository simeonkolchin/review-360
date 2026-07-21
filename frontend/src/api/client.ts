const BASE = '/api'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    let detail = response.statusText
    try { detail = (await response.json()).detail || detail } catch { /* keep status text */ }
    throw new Error(detail)
  }
  if (response.status === 204) return null as T
  const text = await response.text()
  return (text ? JSON.parse(text) : null) as T
}

export const api = {
  get:  <T,>(p: string) => request<T>(p),
  post: <T,>(p: string, body?: unknown) =>
    request<T>(p, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  del:  <T,>(p: string) => request<T>(p, { method: 'DELETE' }),
}

export interface User { telegram_id: number; username: string | null; display_name: string; photo_url: string | null }
export interface Member extends User { can_dm: boolean; is_admin: boolean }
export interface Chat { id: number; telegram_chat_id: number; title: string; member_count: number; team_count: number }
export interface Team { id: number; name: string; leader: User | null; members: User[]; active_round_id: number | null }
export interface Round {
  id: number; team_id: number; team_name: string; status: string; token: string
  bot_deep_link: string | null
  total_assignments: number; completed_assignments: number
  participants_done: number; participants_total: number
}
export interface Score {
  competency_id: number; competency: string
  self_score: number | null; peer_average: number | null; leader_score: number | null
  responses_count: number; hidden_for_anonymity: boolean
}
export interface MemberResult {
  user: User; round_id: number; scores: Score[]
  overall_self: number | null; overall_peer: number | null; message: string | null
  /** anonymous free-text notes, shuffled; empty until enough people answered */
  comments: string[]
}
export interface TeamResults { round_id: number; team_name: string; status: string; members: MemberResult[] }
