import { useEffect, useState } from 'react'
import { Crown, Save, Loader2, UserPlus, UserMinus, AlertTriangle, Check } from 'lucide-react'
import { api, type Member, type Team } from '../api/client'
import { useAuthConfig, peerCounts } from '../api/config'
import { Avatar } from './ui'
import Drawer from './Drawer'

/**
 * Edit a team: rename it, move the crown, add or drop people.
 *
 * The panel also does the arithmetic nobody wants to discover after a round:
 * how many colleagues will rate each person, and whether that clears the
 * threshold below which averages stay hidden.
 */
export default function TeamEditDrawer({
  open, onClose, team, members, onSaved,
}: {
  open: boolean
  onClose: () => void
  team: Team | null
  members: Member[]
  onSaved?: () => void
}) {
  const config = useAuthConfig()
  const minAnswers = config?.min_responses_for_results ?? 3

  const [name, setName] = useState('')
  const [picked, setPicked] = useState<number[]>([])
  const [leader, setLeader] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !team) return
    setName(team.name)
    setPicked(team.members.map(m => m.telegram_id))
    setLeader(team.leader?.telegram_id ?? null)
    setError(null)
  }, [open, team])

  const toggle = (id: number) =>
    setPicked(p => {
      if (p.includes(id)) {
        if (leader === id) setLeader(null)
        return p.filter(x => x !== id)
      }
      return [...p, id]
    })

  const save = async () => {
    if (!team) return
    setError(null); setBusy(true)
    try {
      await api.put(`/teams/${team.id}`, {
        name: name.trim(),
        leader_telegram_id: leader,
        member_telegram_ids: picked,
      })
      onSaved?.()
      onClose()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }

  const counts = peerCounts(picked.length, leader !== null)
  const enough = counts.lowest >= minAnswers
  const needed = minAnswers + (leader !== null ? 2 : 1)
  const valid = name.trim().length > 0 && picked.length >= 2

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={`Команда «${team?.name ?? ''}»`}
      subtitle={`${picked.length} человек(а) в составе`}
      footer={
        <>
          <span className="text-[12.5px] text-[var(--color-muted)]">
            {enough
              ? `Средние будут посчитаны — по ${counts.lowest} и больше ответов`
              : `Средние не посчитаются: нужно ${needed} человек(а)`}
          </span>
          <div className="flex-1" />
          <button className="btn btn-primary px-5 py-2.5" onClick={save} disabled={!valid || busy}>
            {busy ? <Loader2 className="w-4 h-4 spin" /> : <Save className="w-4 h-4" />}
            Сохранить
          </button>
        </>
      }>

      {team?.active_round_id && (
        <div className="flex gap-2.5 items-start text-[13px] rounded-xl p-3.5 mb-4"
             style={{ borderWidth: 1, borderStyle: 'solid',
                      borderColor: 'rgba(255,176,32,.35)', background: 'rgba(255,176,32,.07)' }}>
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-[var(--color-warning)]" />
          <span>
            Идёт оценка — состав менять нельзя, пока раунд не закрыт: задания уже
            розданы по текущему списку. Название и лидера поменять можно.
          </span>
        </div>
      )}

      <label className="block text-[12px] uppercase tracking-wide text-[var(--color-muted)] mb-2">
        Название
      </label>
      <input className="input" value={name} onChange={e => setName(e.target.value)} />

      <div className="flex items-center justify-between mt-6 mb-2">
        <label className="block text-[12px] uppercase tracking-wide text-[var(--color-muted)]">
          Состав
        </label>
        <span className="text-[12px] text-[var(--color-muted)]">
          {picked.length} из {members.length}
        </span>
      </div>

      {!enough && (
        <p className="text-[12.5px] text-[var(--color-warning)] mt-0 mb-3 leading-relaxed">
          Добавьте ещё {Math.max(1, needed - picked.length)} человек(а): каждого сейчас
          оценят {counts.member === counts.leader ? counts.member
                  : `${counts.member}–${counts.leader}`} коллег(и),
          а средние показываются от {minAnswers} ответов.
        </p>
      )}

      <div className="flex flex-col gap-2">
        {members.map(m => {
          const inTeam = picked.includes(m.telegram_id)
          return (
            <div key={m.telegram_id}
                 className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border transition
                   ${inTeam ? 'border-[var(--color-accent)] bg-[rgba(59,130,246,.08)]'
                            : 'border-[var(--color-border)] bg-[var(--color-surface-2)]'}`}>
              <Avatar name={m.display_name} url={m.photo_url} size={30} />
              <div className="min-w-0 flex-1">
                <div className="text-[13.5px] truncate">{m.display_name}</div>
                <div className="text-[11.5px] text-[var(--color-muted)] truncate">
                  {m.username ? '@' + m.username : 'без username'}
                  {m.can_dm ? '' : ' · не открыл бота'}
                </div>
              </div>

              {inTeam && (
                <button
                  onClick={() => setLeader(leader === m.telegram_id ? null : m.telegram_id)}
                  title={leader === m.telegram_id ? 'Снять роль лидера' : 'Назначить лидером'}
                  className={`p-1.5 rounded-md transition
                    ${leader === m.telegram_id
                      ? 'text-[var(--color-accent)] bg-[rgba(59,130,246,.14)]'
                      : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'}`}>
                  <Crown className="w-3.5 h-3.5" />
                </button>
              )}

              <button onClick={() => toggle(m.telegram_id)}
                      disabled={!!team?.active_round_id}
                      title={inTeam ? 'Убрать из команды' : 'Добавить в команду'}
                      className={`p-1.5 rounded-md transition disabled:opacity-40
                        ${inTeam ? 'text-[var(--color-muted)] hover:text-[var(--color-danger)]'
                                 : 'text-[var(--color-muted)] hover:text-[var(--color-accent)]'}`}>
                {inTeam ? <UserMinus className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
              </button>
            </div>
          )
        })}
      </div>

      {enough && (
        <p className="flex items-center gap-2 text-[12.5px] text-[var(--color-success)] mt-4 mb-0">
          <Check className="w-3.5 h-3.5" /> Состава хватает: средние по коллегам будут видны
        </p>
      )}

      {error && <p className="text-[var(--color-danger)] text-[13px] mt-4 mb-0">{error}</p>}
    </Drawer>
  )
}
