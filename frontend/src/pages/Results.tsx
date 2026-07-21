import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Lock, CheckCircle2, MessageSquareQuote } from 'lucide-react'
import {
  PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Legend, Tooltip,
} from 'recharts'
import { api, type Round, type TeamResults } from '../api/client'
import { Avatar, Pill, ScoreBar } from '../components/ui'

export default function Results() {
  const { roundId } = useParams()
  const navigate = useNavigate()
  const [round, setRound] = useState<Round | null>(null)
  const [results, setResults] = useState<TeamResults | null>(null)

  const load = useCallback(async () => {
    setRound(await api.get<Round>(`/rounds/${roundId}`))
    setResults(await api.get<TeamResults>(`/rounds/${roundId}/results`))
  }, [roundId])

  useEffect(() => { load() }, [load])

  const close = async () => {
    await api.post(`/rounds/${roundId}/close`)
    load()
  }

  if (!round || !results) return <p className="text-[var(--color-text-secondary)]">Загрузка…</p>

  const pct = round.total_assignments
    ? Math.round((round.completed_assignments / round.total_assignments) * 100) : 0

  return (
    <div className="fade-up">
      <button onClick={() => navigate(-1)} className="btn btn-ghost px-3 py-2 mb-4">
        <ArrowLeft className="w-4 h-4" /> Назад
      </button>

      <h2 className="text-[22px] m-0 mb-4 tracking-tight">Оценка · {round.team_name}</h2>

      <div className="card p-5 mb-5">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex gap-2 flex-wrap">
            <Pill tone={round.status === 'active' ? 'warn' : 'ok'}>
              {round.status === 'active' ? 'идёт' : 'закрыт'}
            </Pill>
            <Pill>{round.participants_done}/{round.participants_total} прошли</Pill>
            <Pill tone="accent">{pct}% заданий</Pill>
          </div>
          <div className="flex gap-2">
            {round.status === 'active' && (
              <button className="btn btn-ghost px-3 py-2" onClick={close}>
                <CheckCircle2 className="w-4 h-4" /> Закрыть раунд
              </button>
            )}
            <button className="btn btn-ghost px-3 py-2" onClick={load}>
              <RefreshCw className="w-4 h-4" /> Обновить
            </button>
          </div>
        </div>

        <div className="h-2 rounded-full bg-[var(--color-surface-2)] border border-[var(--color-border)] overflow-hidden mt-4">
          <i className="block h-full rounded-full transition-all duration-700"
             style={{ width: `${pct}%`, background: 'var(--gradient-accent)' }} />
        </div>

        {round.bot_deep_link && (
          <p className="text-[11px] font-mono text-[var(--color-muted)] mt-3 mb-0 break-all">
            {round.bot_deep_link}
          </p>
        )}
      </div>

      <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(420px,1fr))' }}>
        {results.members.map(member => {
          const data = member.scores.map(s => ({
            competency: s.competency,
            Самооценка: s.self_score ?? 0,
            Команда: s.peer_average ?? 0,
          }))
          return (
            <div key={member.user.telegram_id} className="card p-5">
              <div className="flex items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-3">
                  <Avatar name={member.user.display_name} url={member.user.photo_url} />
                  <div>
                    <div className="text-[15px]">{member.user.display_name}</div>
                    <div className="text-xs text-[var(--color-muted)]">
                      {member.user.username ? '@' + member.user.username : ''}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Pill>вы {member.overall_self ?? '—'}</Pill>
                  <Pill tone="accent">команда {member.overall_peer ?? '—'}</Pill>
                </div>
              </div>

              <div style={{ height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={data} outerRadius="72%">
                    <PolarGrid stroke="var(--color-border)" />
                    <PolarAngleAxis dataKey="competency" tick={{ fill: '#aab3c5', fontSize: 11 }} />
                    <PolarRadiusAxis domain={[0, 5]} tick={{ fill: '#7b8494', fontSize: 10 }} />
                    <Radar name="Самооценка" dataKey="Самооценка" stroke="#94a3b8"
                           fill="#94a3b8" fillOpacity={0.18} />
                    <Radar name="Команда" dataKey="Команда" stroke="#3b82f6"
                           fill="#3b82f6" fillOpacity={0.32} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Tooltip contentStyle={{
                      background: 'var(--color-surface-elevated)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 12, fontSize: 12,
                    }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-2">
                {member.scores.map(s => (
                  <ScoreBar key={s.competency_id} label={s.competency}
                            self={s.self_score} peer={s.peer_average} />
                ))}
              </div>

              {member.comments?.length > 0 && (
                <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                  <div className="flex items-center gap-2 text-[12.5px] text-[var(--color-muted)] mb-2.5">
                    <MessageSquareQuote className="w-3.5 h-3.5" />
                    Что написали коллеги · анонимно
                  </div>
                  <div className="flex flex-col gap-2">
                    {member.comments.map((comment, i) => (
                      <blockquote key={i}
                        className="m-0 pl-3 py-1.5 text-[13.5px] leading-relaxed
                                   text-[var(--color-text-secondary)]
                                   border-l-2 border-[var(--color-border)]">
                        {comment}
                      </blockquote>
                    ))}
                  </div>
                </div>
              )}

              {member.message && (
                <p className="flex items-start gap-2 text-xs text-[var(--color-muted)] mt-3 mb-0">
                  <Lock className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {member.message}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
