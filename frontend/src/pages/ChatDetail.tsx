import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Play, Trash2, BarChart3, Crown, GripVertical,
  UserPlus, Users, X, Sparkles, SlidersHorizontal, ListChecks,
  MoreVertical, LogOut, AlertTriangle, ShieldAlert, RefreshCw, Loader2, UserX, Plus,
  Pencil, Search,
} from 'lucide-react'
import { api, type Chat, type Member, type Team, type TelegramStatus } from '../api/client'
import { useLive, useArrivals } from '../api/live'
import { useAuthConfig, botLink, peerCounts } from '../api/config'
import { Avatar, ChatAvatar, EmptyState, Pill } from '../components/ui'
import Modal from '../components/Modal'
import QuestionnaireDrawer from '../components/QuestionnaireDrawer'
import TeamEditDrawer from '../components/TeamEditDrawer'

export default function ChatDetail() {
  const { chatId } = useParams()
  const navigate = useNavigate()

  // Members and teams stream in on their own — someone writing in the group or
  // finishing their review shows up here without anyone pressing reload.
  const live = useLive<Member[]>(chatId ? `/chats/${chatId}/members` : null, 5000)
  const teamsLive = useLive<Team[]>(chatId ? `/chats/${chatId}/teams` : null, 5000)
  const chatsLive = useLive<Chat[]>('/chats', 15000)
  // Telegram's own view of the group: how many people it has, and whether we
  // are an admin — the two facts that explain a short roster.
  const tgLive = useLive<TelegramStatus>(chatId ? `/chats/${chatId}/telegram` : null, 30000)
  const tg = tgLive.data
  const config = useAuthConfig()
  // Same invite link as the dashboard, admin rights requested up front.
  const inviteBack = botLink(config?.bot_username ?? '', '?startgroup=true&admin=invite_users')
  const minAnswers = config?.min_responses_for_results ?? 3

  /** Will team averages actually be shown, or hidden to protect anonymity? */
  const anonymityCheck = (team: Team) => {
    const { lowest, member, leader } = peerCounts(team.members.length, !!team.leader)
    return { lowest, member, leader, ok: lowest >= minAnswers }
  }
  const members = live.data ?? []
  const teams = teamsLive.data ?? []
  const chat = chatsLive.data?.find(c => String(c.id) === chatId)
  const loading = live.loading
  // Somebody tapping «Участвую» in the group shows up here on the next poll —
  // highlighted, so a list that changes under your eyes is not confusing.
  const arrivals = useArrivals(members.map(m => m.telegram_id), !live.loading)

  // team builder
  const [name, setName] = useState('')
  const [picked, setPicked] = useState<number[]>([])
  const [leader, setLeader] = useState<number | null>(null)
  const [dragging, setDragging] = useState<number | null>(null)
  const [over, setOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // modals & panels
  const [confirmDelete, setConfirmDelete] = useState<Team | null>(null)
  const [confirmStart, setConfirmStart] = useState<Team | null>(null)
  const [confirmDeleteChat, setConfirmDeleteChat] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [syncNote, setSyncNote] = useState<string | null>(null)
  const [chatQuestions, setChatQuestions] = useState(false)
  const [teamQuestions, setTeamQuestions] = useState<Team | null>(null)
  const [editTeam, setEditTeam] = useState<Team | null>(null)

  const loadTeams = teamsLive.refresh

  const add = (id: number) => setPicked(p => (p.includes(id) ? p : [...p, id]))
  const drop = (id: number) => {
    setPicked(p => p.filter(x => x !== id))
    if (leader === id) setLeader(null)
  }

  // Which teams each person is already on — shown as tags next to their name.
  const teamsOf = new Map<number, Team[]>()
  for (const team of teams) {
    for (const m of team.members) {
      teamsOf.set(m.telegram_id, [...(teamsOf.get(m.telegram_id) ?? []), team])
    }
  }
  const assigned = new Set(teamsOf.keys())

  const needle = query.trim().toLowerCase()
  const available = members
    .filter(m => !picked.includes(m.telegram_id))
    .filter(m => !needle
      || m.display_name.toLowerCase().includes(needle)
      || (m.username ?? '').toLowerCase().includes(needle))
    // People with nowhere to go come first — they are the work left to do.
    .sort((a, b) => {
      const byTeam = (teamsOf.get(a.telegram_id)?.length ?? 0) -
                     (teamsOf.get(b.telegram_id)?.length ?? 0)
      return byTeam !== 0 ? byTeam : a.display_name.localeCompare(b.display_name, 'ru')
    })
  const chosen = picked
    .map(id => members.find(m => m.telegram_id === id))
    .filter((m): m is Member => Boolean(m))

  const create = async () => {
    setError(null); setBusy(true)
    try {
      await api.post(`/chats/${chatId}/teams`, {
        name: name.trim(),
        leader_telegram_id: leader,
        member_telegram_ids: picked,
      })
      setName(''); setPicked([]); setLeader(null)
      await loadTeams()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }

  const startRound = async (team: Team) => {
    setConfirmStart(null)
    try {
      const round = await api.post<{ id: number }>(`/teams/${team.id}/rounds`)
      navigate(`/rounds/${round.id}`)
    } catch (e) { setError((e as Error).message) }
  }

  const removeTeam = async (team: Team) => {
    setConfirmDelete(null)
    await api.del(`/teams/${team.id}`)
    loadTeams()
  }

  const syncMembers = async () => {
    setSyncing(true); setSyncNote(null)
    try {
      const r = await api.post<{ added: number; member_count: number | null }>(
        `/chats/${chatId}/sync`,
      )
      await live.refresh()
      tgLive.refresh()
      setSyncNote(
        r.member_count && r.added < r.member_count
          ? `Найдено ${r.added} из ${r.member_count} — остальных Telegram не раскрывает, пока они не напишут`
          : `Найдено ${r.added}`,
      )
    } catch (e) { setSyncNote((e as Error).message) } finally { setSyncing(false) }
  }

  const removeChat = async () => {
    setConfirmDeleteChat(false)
    try {
      await api.del(`/chats/${chatId}`)
      navigate('/')
    } catch (e) { setError((e as Error).message) }
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <Link to="/" className="btn btn-ghost px-3 py-2 no-underline inline-flex shrink-0">
          <ArrowLeft className="w-4 h-4" /> Обзор
        </Link>

        <div className="flex-1" />

        <div className="flex items-center gap-2.5 min-w-0">
          <ChatAvatar name={chat?.title ?? '…'} url={chat?.photo_url} size={32} />
          <span className="text-[15px] truncate">{chat?.title ?? 'Чат'}</span>
        </div>

        <div className="flex-1" />

        <button className="btn btn-ghost px-3 py-2 shrink-0" onClick={() => setChatQuestions(true)}>
          <SlidersHorizontal className="w-4 h-4" /> Опросник чата
        </button>

        <div className="relative shrink-0">
          <button className="btn btn-ghost p-2.5" onClick={() => setMenuOpen(o => !o)} aria-label="Ещё">
            <MoreVertical className="w-4 h-4" />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-11 z-20 w-[230px] p-1.5 rounded-xl
                              border border-[var(--color-border)] shadow-xl"
                   style={{ background: 'var(--color-surface-elevated)' }}>
                <button
                  onClick={() => { setMenuOpen(false); setConfirmDeleteChat(true) }}
                  className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left text-[13.5px]
                             text-[var(--color-danger)] hover:bg-[rgba(255,77,94,.1)] transition">
                  <LogOut className="w-4 h-4" /> Удалить чат и выйти из группы
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Removed from the group — the data is still here, so offer both ways out. */}
      {tg && tg.bot_in_chat === false && (
        <div className="card p-5 mb-5"
             style={{ borderColor: 'rgba(255,77,94,.35)', background: 'rgba(255,77,94,.06)' }}>
          <div className="flex gap-3 items-start">
            <UserX className="w-5 h-5 shrink-0 mt-0.5 text-[var(--color-danger)]" />
            <div className="flex-1">
              <h3 className="text-[15px] m-0 mb-1">Бота нет в группе</h3>
              <p className="text-[13px] text-[var(--color-text-secondary)] m-0">
                Его исключили из «{chat?.title ?? 'чата'}» — новые участники и оценки
                оттуда больше не приходят. Данные ({members.length} участник(ов),
                {' '}{teams.length} команд(ы)) пока сохранены.
              </p>
              <div className="flex gap-2 mt-4 flex-wrap">
                <a href={inviteBack} target="_blank" rel="noreferrer"
                   className="btn btn-primary px-4 py-2.5 no-underline">
                  <Plus className="w-4 h-4" /> Вернуть бота в группу
                </a>
                <button className="btn btn-ghost px-4 py-2.5"
                        style={{ color: 'var(--color-danger)', borderColor: 'rgba(255,77,94,.4)' }}
                        onClick={() => setConfirmDeleteChat(true)}>
                  <Trash2 className="w-4 h-4" /> Удалить чат и все данные
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Telegram will not hand over a member list; say so plainly when it shows. */}
      {tg && tg.bot_in_chat !== false && tg.bot_is_admin === false && (
        <div className="card p-4 mb-5 flex gap-3 items-start"
             style={{ borderColor: 'rgba(255,176,32,.35)', background: 'rgba(255,176,32,.06)' }}>
          <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-[var(--color-warning)]" />
          <div className="text-[13px] leading-relaxed">
            <b>Бот не администратор группы.</b>{' '}
            {typeof tg.member_count === 'number' && (
              <>В группе {tg.member_count} человек(а), а видно {tg.known}. </>
            )}
            Telegram не выдаёт ботам список участников: без прав администратора бот
            не видит и сообщения остальных, поэтому список пополняется медленно.
            <div className="text-[12.5px] text-[var(--color-muted)] mt-1.5">
              Откройте настройки группы → Администраторы → добавьте бота. Остальные
              появятся здесь автоматически.
            </div>
          </div>
        </div>
      )}

      {/* ---------------- team builder ---------------- */}
      <div className="grid gap-4 mb-10 md:grid-cols-[1fr_1.15fr]">
        {/* people who are not in the draft yet */}
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-[15px] m-0 flex items-center gap-2">
              <Users className="w-4 h-4 text-[var(--color-muted)]" /> Участники
            </h3>
            <div className="flex items-center gap-2">
              <Pill>{available.length}</Pill>
              <button className="btn btn-ghost p-2" onClick={syncMembers} disabled={syncing}
                      title="Проверить, кто сейчас в группе">
                {syncing ? <Loader2 className="w-3.5 h-3.5 spin" />
                         : <RefreshCw className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
          <p className="text-[12.5px] text-[var(--color-muted)] mt-1.5 mb-3">
            {syncNote ?? 'Подтягиваются из чата автоматически. Перетащите в команду справа — или просто нажмите на карточку'}
          </p>

          <div className="relative mb-3">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2
                                 text-[var(--color-muted)] pointer-events-none" />
              <input className="input !pl-9 !py-2 text-[13.5px]" placeholder="Поиск по имени или @username"
                     value={query} onChange={e => setQuery(e.target.value)} />
            {query && (
              <button onClick={() => setQuery('')} aria-label="Очистить"
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 rounded-md
                                 text-[var(--color-muted)] hover:text-[var(--color-text)] transition">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="scroll-slim flex flex-col gap-2 overflow-y-auto pr-1"
               style={{ maxHeight: 'min(56vh, 520px)' }}>
            {loading && [0, 1, 2].map(i => <div key={i} className="h-[52px] rounded-xl skeleton" />)}

            {!loading && members.length === 0 && (
              <p className="text-[13px] text-[var(--color-muted)] py-6 text-center m-0">
                Пока пусто. Добавьте бота в группу — участники подтянутся сами
              </p>
            )}

            {!loading && members.length > 0 && available.length === 0 && (
              <p className="text-[13px] text-[var(--color-muted)] py-6 text-center m-0">
                {needle ? 'Никого не нашлось — попробуйте другое имя'
                        : 'Все участники уже в черновике команды'}
              </p>
            )}

            {available.map(m => (
              <div key={m.telegram_id}
                draggable
                onDragStart={() => setDragging(m.telegram_id)}
                onDragEnd={() => setDragging(null)}
                onClick={() => add(m.telegram_id)}
                className={`draggable flex items-center gap-3 px-3 py-2.5 rounded-xl border
                            bg-[var(--color-surface-2)] border-[var(--color-border)]
                            hover:border-[var(--color-accent)]
                            ${dragging === m.telegram_id ? 'dragging' : ''}
                            ${arrivals.has(m.telegram_id) ? 'just-arrived' : ''}`}>
                <GripVertical className="w-4 h-4 text-[var(--color-muted)] shrink-0" />
                <Avatar name={m.display_name} url={m.photo_url} size={30} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-[13.5px] truncate">{m.display_name}</span>
                    {!assigned.has(m.telegram_id) && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-warning)] shrink-0
                                       cursor-help"
                            title="Ещё не в команде" />
                    )}
                    <TeamTags teams={teamsOf.get(m.telegram_id) ?? []} />
                  </div>
                  <div className="text-[11.5px] text-[var(--color-muted)] truncate">
                    {m.username ? '@' + m.username : 'без username'}
                    {m.can_dm ? '' : ' · не открыл бота'}
                  </div>
                </div>
                <UserPlus className="w-4 h-4 text-[var(--color-muted)] shrink-0" />
              </div>
            ))}
          </div>
        </div>

        {/* drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setOver(true) }}
          onDragLeave={() => setOver(false)}
          onDrop={e => {
            e.preventDefault(); setOver(false)
            if (dragging !== null) add(dragging)
            setDragging(null)
          }}
          className={`card dropzone p-5 ${over ? 'over' : ''}`}>
          <h3 className="text-[15px] m-0 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[var(--color-accent)]" /> Новая команда
          </h3>
          <p className="text-[12.5px] text-[var(--color-muted)] mt-1.5 mb-4">
            Минимум два человека. Корона отмечает лидера — его взгляд показываем отдельно.
            Один человек может вести несколько команд.
          </p>

          <input className="input" placeholder="Название команды, например «Продукт»"
                 value={name} onChange={e => setName(e.target.value)} />

          <div className={`mt-4 rounded-xl border border-dashed p-3 min-h-[190px] transition
                           ${over ? 'border-[var(--color-accent)] bg-[rgba(59,130,246,.06)]'
                                  : 'border-[var(--color-border)]'}`}>
            {chosen.length === 0 ? (
              <div className="h-[170px] grid place-items-center text-center">
                <div>
                  <div className="text-[13.5px] text-[var(--color-text-secondary)]">
                    Перетащите участников сюда
                  </div>
                  <div className="text-[12px] text-[var(--color-muted)] mt-1">
                    или кликните по карточке слева
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {chosen.map(m => (
                  <div key={m.telegram_id}
                       className="flex items-center gap-3 px-3 py-2 rounded-lg
                                  bg-[var(--color-surface-2)] border border-[var(--color-border)]">
                    <Avatar name={m.display_name} url={m.photo_url} size={26} />
                    <span className="text-[13.5px] flex-1 truncate">{m.display_name}</span>

                    <button
                      onClick={() => setLeader(leader === m.telegram_id ? null : m.telegram_id)}
                      title={leader === m.telegram_id ? 'Снять роль лидера' : 'Назначить лидером'}
                      className={`p-1.5 rounded-md transition
                        ${leader === m.telegram_id
                          ? 'text-[var(--color-accent)] bg-[rgba(59,130,246,.12)]'
                          : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'}`}>
                      <Crown className="w-3.5 h-3.5" />
                    </button>

                    <button onClick={() => drop(m.telegram_id)} title="Убрать из команды"
                            className="p-1.5 rounded-md text-[var(--color-muted)]
                                       hover:text-[var(--color-danger)] transition">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 mt-4">
            <button className="btn btn-ghost px-4 py-2.5"
                    onClick={() => setPicked(members.map(m => m.telegram_id))}>
              Все
            </button>
            {picked.length > 0 && (
              <button className="btn btn-ghost px-4 py-2.5"
                      onClick={() => { setPicked([]); setLeader(null) }}>
                Очистить
              </button>
            )}
            <div className="flex-1" />
            <span className="text-[12.5px] text-[var(--color-muted)]">{picked.length} чел.</span>
            <button className="btn btn-primary px-5 py-2.5"
                    disabled={busy || !name.trim() || picked.length < 2}
                    onClick={create}>
              Создать команду
            </button>
          </div>

          {error && <p className="text-[var(--color-danger)] text-[13px] mt-3 mb-0">{error}</p>}
        </div>
      </div>

      {/* ---------------- teams ---------------- */}
      <div className="flex items-center gap-2.5 mb-4">
        <h3 className="text-[19px] m-0 tracking-tight">Команды</h3>
        {teams.length > 0 && <Pill tone="accent">{teams.length}</Pill>}
      </div>

      {teams.length === 0 ? (
        <EmptyState title="Команд пока нет"
                    text="Соберите первую команду из участников выше — это займёт секунд десять." />
      ) : (
        <div className="grid gap-4 stagger"
             style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(290px,1fr))' }}>
          {teams.map(team => (
            <div key={team.id} className="card dotted p-5 lift">
              <div className="flex items-start justify-between gap-2 mb-3">
                <h4 className="text-[15px] m-0">{team.name}</h4>
                {team.active_round_id
                  ? <Pill tone="warn">идёт оценка</Pill>
                  : !anonymityCheck(team).ok && (
                      <span title={`Средние по коллегам появляются от ${minAnswers} ответов — в такой команде их не будет`}>
                        <Pill tone="warn">мало людей</Pill>
                      </span>
                    )}
              </div>

              <div className="text-[12.5px] text-[var(--color-muted)] mb-3 flex items-center gap-1.5">
                <Crown className="w-3.5 h-3.5" />
                {team.leader?.display_name ?? 'без лидера'} · {team.members.length} чел.
              </div>

              <div className="flex -space-x-2 mb-4">
                {team.members.slice(0, 7).map(m => (
                  <span key={m.telegram_id} className="ring-2 ring-[var(--color-surface)] rounded-[10px]">
                    <Avatar name={m.display_name} url={m.photo_url} size={26} />
                  </span>
                ))}
                {team.members.length > 7 && (
                  <span className="grid place-items-center w-[26px] h-[26px] rounded-[10px] text-[10px]
                                   ring-2 ring-[var(--color-surface)] bg-[var(--color-surface-2)]
                                   text-[var(--color-muted)]">
                    +{team.members.length - 7}
                  </span>
                )}
              </div>

              <div className="flex gap-2">
                {team.active_round_id ? (
                  <Link to={`/rounds/${team.active_round_id}`}
                        className="btn btn-primary px-3 py-2 flex-1 no-underline">
                    <BarChart3 className="w-4 h-4" /> Результаты
                  </Link>
                ) : (
                  <button className="btn btn-primary px-3 py-2 flex-1"
                          onClick={() => setConfirmStart(team)}>
                    <Play className="w-4 h-4" /> Запустить
                  </button>
                )}
                <button className="btn btn-ghost px-3 py-2" title="Изменить состав команды"
                        onClick={() => setEditTeam(team)}>
                  <Pencil className="w-4 h-4" />
                </button>
                <button className="btn btn-ghost px-3 py-2" title="Опросник этой команды"
                        onClick={() => setTeamQuestions(team)}>
                  <ListChecks className="w-4 h-4" />
                </button>
                <button className="btn btn-ghost px-3 py-2" title="Удалить команду"
                        onClick={() => setConfirmDelete(team)}>
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ---------------- modals ---------------- */}
      <Modal
        open={!!confirmStart}
        onClose={() => setConfirmStart(null)}
        title={`Запустить оценку — «${confirmStart?.name ?? ''}»?`}
        subtitle="Бот напишет в группу, отметит участников и раздаст каждому опрос в личку."
        footer={
          <>
            <button className="btn btn-ghost px-4 py-2.5" onClick={() => setConfirmStart(null)}>
              Отмена
            </button>
            <button className="btn btn-primary px-4 py-2.5"
                    onClick={() => confirmStart && startRound(confirmStart)}>
              <Play className="w-4 h-4" /> Запустить
            </button>
          </>
        }>
        {confirmStart && !anonymityCheck(confirmStart).ok && (
          <div className="flex gap-2.5 items-start text-[13px] leading-relaxed rounded-xl p-3.5 mb-3"
               style={{ borderWidth: 1, borderStyle: 'solid',
                        borderColor: 'rgba(255,176,32,.35)', background: 'rgba(255,176,32,.07)' }}>
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-[var(--color-warning)]" />
            <div>
              <b>Средние по команде не посчитаются.</b> В команде
              {' '}{confirmStart.members.length} человек(а), поэтому каждого оценят
              {' '}{anonymityCheck(confirmStart).member === anonymityCheck(confirmStart).leader
                    ? anonymityCheck(confirmStart).member
                    : `${anonymityCheck(confirmStart).member}–${anonymityCheck(confirmStart).leader}`}
              {' '}коллег(и), а средние показываются от {minAnswers} ответов.
              <div className="text-[12.5px] text-[var(--color-muted)] mt-1.5">
                Это защита анонимности: по одному-двум ответам автора вычислить
                тривиально. Самооценки и оценка лидера будут видны, средние по
                коллегам — нет. Нужно {minAnswers + (confirmStart.leader ? 2 : 1)}
                {' '}человек(а) в команде.
              </div>
              <button className="btn btn-ghost px-3 py-2 mt-3"
                      onClick={() => { const t = confirmStart; setConfirmStart(null); setEditTeam(t) }}>
                <UserPlus className="w-4 h-4" /> Добавить людей в команду
              </button>
            </div>
          </div>
        )}

        <div className="rounded-xl bg-[var(--color-surface-2)] border border-[var(--color-border)] p-4">
          <div className="text-[12.5px] text-[var(--color-muted)] mb-2.5">Кого позовём</div>
          <div className="flex flex-wrap gap-2">
            {confirmStart?.members.map(m => (
              <span key={m.telegram_id}
                    className="flex items-center gap-2 px-2 py-1 rounded-lg text-[13px]
                               bg-[var(--color-surface)] border border-[var(--color-border)]">
                <Avatar name={m.display_name} url={m.photo_url} size={20} />
                {m.display_name}
              </span>
            ))}
          </div>
        </div>
      </Modal>

      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title={`Удалить «${confirmDelete?.name ?? ''}»?`}
        subtitle="Команда и все её раунды вместе с ответами исчезнут без возможности вернуть."
        footer={
          <>
            <button className="btn btn-ghost px-4 py-2.5" onClick={() => setConfirmDelete(null)}>
              Отмена
            </button>
            <button className="btn btn-ghost px-4 py-2.5"
                    style={{ color: 'var(--color-danger)', borderColor: 'var(--color-danger)' }}
                    onClick={() => confirmDelete && removeTeam(confirmDelete)}>
              <Trash2 className="w-4 h-4" /> Удалить
            </button>
          </>
        }
      />

      <Modal
        open={confirmDeleteChat}
        onClose={() => setConfirmDeleteChat(false)}
        title={`Удалить «${chat?.title ?? 'чат'}»?`}
        subtitle="Бот выйдет из группы, а все команды, раунды, ответы и настройки этого чата будут удалены безвозвратно."
        footer={
          <>
            <button className="btn btn-ghost px-4 py-2.5" onClick={() => setConfirmDeleteChat(false)}>
              Отмена
            </button>
            <button className="btn btn-ghost px-4 py-2.5"
                    style={{ color: 'var(--color-danger)', borderColor: 'var(--color-danger)' }}
                    onClick={removeChat}>
              <LogOut className="w-4 h-4" /> Удалить и выйти
            </button>
          </>
        }>
        <div className="flex gap-2.5 items-start text-[13px] text-[var(--color-text-secondary)]
                        rounded-xl border p-3.5"
             style={{ borderColor: 'rgba(255,77,94,.3)', background: 'rgba(255,77,94,.06)' }}>
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-[var(--color-danger)]" />
          <span>
            {teams.length > 0
              ? `В чате ${teams.length} команд(ы) и вся история их оценок — это тоже удалится.`
              : 'Восстановить данные будет нельзя. Бота придётся добавлять в группу заново.'}
          </span>
        </div>
      </Modal>

      <TeamEditDrawer
        open={!!editTeam}
        onClose={() => setEditTeam(null)}
        team={editTeam}
        members={members}
        onSaved={loadTeams}
      />

      <QuestionnaireDrawer
        open={chatQuestions}
        onClose={() => setChatQuestions(false)}
        scope="chat"
        id={chatId!}
        title="Опросник чата"
        onSaved={loadTeams}
      />

      <QuestionnaireDrawer
        open={!!teamQuestions}
        onClose={() => setTeamQuestions(null)}
        scope="team"
        id={teamQuestions?.id ?? 0}
        title={`Опросник — «${teamQuestions?.name ?? ''}»`}
        onSaved={loadTeams}
      />
    </div>
  )
}

/** How many team tags fit on one line before the rest collapse into a counter. */
const TAGS_SHOWN = 2

/**
 * Which teams a person already belongs to.
 *
 * Names are user-written and can be long, so each tag truncates on its own and
 * only the first couple are drawn; the rest become "+N" carrying the full list
 * in its tooltip. That keeps a row exactly one line tall no matter how many
 * teams someone ends up in.
 */
function TeamTags({ teams }: { teams: Team[] }) {
  if (!teams.length) return null
  const shown = teams.slice(0, TAGS_SHOWN)
  const rest = teams.slice(TAGS_SHOWN)

  return (
    <div className="flex items-center gap-1 min-w-0 shrink-0">
      {shown.map(team => (
        <span key={team.id} title={team.name}
              className="shrink min-w-0 truncate max-w-[84px] px-1.5 py-0.5 rounded-md text-[10.5px] leading-[1.35]
                         bg-[rgba(59,130,246,.12)] text-[var(--color-accent)]
                         border border-[rgba(59,130,246,.25)]">
          {team.name}
        </span>
      ))}
      {rest.length > 0 && (
        <span title={rest.map(t => t.name).join(', ')}
              className="shrink-0 px-1.5 py-0.5 rounded-md text-[10.5px] leading-[1.35] cursor-help
                         bg-[var(--color-surface)] text-[var(--color-muted)]
                         border border-[var(--color-border)]">
          +{rest.length}
        </span>
      )}
    </div>
  )
}
