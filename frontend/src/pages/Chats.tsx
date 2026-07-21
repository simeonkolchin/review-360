import { Link } from 'react-router-dom'
import { Users, Layers, MessagesSquare, Plus, ArrowRight, ShieldCheck, Zap } from 'lucide-react'
import { type Chat } from '../api/client'
import { useLive, useArrivals } from '../api/live'
import { useAuthConfig, botLink } from '../api/config'
import { Pill, ChatAvatar } from '../components/ui'
import Scramble from '../components/Scramble'

interface Stats { counts: Record<string, number> }

export default function Chats() {
  const config = useAuthConfig()
  // `admin=` makes Telegram offer the bot as an administrator right in the add
  // dialog — one tap instead of digging through group settings afterwards.
  // Admin status is what lifts privacy mode, so the roster fills from messages.
  const addToGroup = botLink(config?.bot_username ?? '', '?startgroup=true&admin=invite_users')
  // A chat appears here the moment the bot is added to a group — no reload.
  const chatsLive = useLive<Chat[]>('/chats', 5000)
  const statsLive = useLive<Stats>('/stats', 15000)
  const chats = chatsLive.data ?? []
  const stats = statsLive.data
  const loading = chatsLive.loading
  const fresh = useArrivals(chats.map(c => c.id))

  const members = chats.reduce((n, c) => n + c.member_count, 0)
  const teams = chats.reduce((n, c) => n + c.team_count, 0)

  return (
    <div className="fade-up">
      {/* ---------- hero ---------- */}
      <section className="text-center pt-6 pb-12">
        <div className="flex items-center justify-center gap-2 mb-6">
          <span className="text-[11px] font-mono tracking-widest text-[var(--color-muted)]">ОЦЕНКА 360</span>
          {['Анонимно', 'В Telegram', 'За 2 минуты'].map(t => (
            <span key={t} className="px-2.5 py-1 rounded-lg text-[12px] bg-[var(--color-surface-2)]
                                     border border-[var(--color-border)] text-[var(--color-text-secondary)]">{t}</span>
          ))}
        </div>

        <h1 className="text-[44px] sm:text-[52px] font-bold leading-[1.05] tracking-[-0.03em] m-0">
          Как вас видит{' '}
          <span className="text-[var(--color-accent)]"><Scramble text="команда" /></span>?
        </h1>

        <p className="max-w-[560px] mx-auto mt-5 mb-8 text-[15px] leading-relaxed text-[var(--color-muted)]">
          Соберите команду, запустите раунд — и каждый получит короткий опрос в личку.
          Ответы анонимны, результат — честная картина сильных сторон и зон роста.
        </p>

        <div className="flex items-center justify-center gap-3 flex-wrap">
          <a href={addToGroup} target="_blank" rel="noreferrer"
             className="btn btn-primary px-5 py-3 no-underline">
            <Plus className="w-4 h-4" /> Добавить бота в группу
          </a>
          {chats.length > 0 && (
            <Link to={`/chats/${chats[0].id}`} className="btn btn-ghost px-5 py-3 no-underline">
              Перейти к командам <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </section>

      {/* ---------- bento stats ---------- */}
      <section className="grid gap-3 mb-12 stagger"
               style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))' }}>
        {[
          { icon: <MessagesSquare className="w-4 h-4" />, label: 'Чаты', value: chats.length },
          { icon: <Users className="w-4 h-4" />, label: 'Участники', value: members },
          { icon: <Layers className="w-4 h-4" />, label: 'Команды', value: teams },
          { icon: <Zap className="w-4 h-4" />, label: 'Раундов', value: stats?.counts?.rounds ?? 0 },
        ].map((tile, i) => (
          <div key={tile.label}
               className="card dotted p-5 lift"
               style={{ animationDelay: `${i * 60}ms` }}>
            <div className="flex items-center gap-2 text-[var(--color-muted)] text-[12px] mb-3">
              {tile.icon} {tile.label}
            </div>
            <div className="text-[32px] font-semibold leading-none tracking-tight">{tile.value}</div>
          </div>
        ))}
      </section>

      {/* ---------- chats / onboarding ---------- */}
      <div className="flex items-end justify-between mb-4">
        <div>
          <h2 className="text-[19px] m-0 tracking-tight">Ваши чаты</h2>
          <p className="text-[13px] text-[var(--color-muted)] mt-1 mb-0">
            Группы, куда добавлен бот и где он видит вас среди участников
          </p>
        </div>
        {chats.length > 0 && <Pill tone="accent">{chats.length}</Pill>}
      </div>

      {loading ? (
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))' }}>
          {[0, 1, 2].map(i => (
            <div key={i} className="card p-5 h-[120px] animate-pulse opacity-40" />
          ))}
        </div>
      ) : chats.length === 0 ? (
        <div className="card dotted p-10 text-center fade-up">
          <h3 className="text-[17px] m-0 mb-2">Здесь пока пусто — начнём?</h3>
          <p className="text-[14px] text-[var(--color-muted)] max-w-[440px] mx-auto mb-7">
            Три шага, и первый раунд оценки поедет.
          </p>
          <div className="grid gap-3 text-left max-w-[720px] mx-auto"
               style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))' }}>
            {[
              ['Добавьте бота', 'В рабочую группу, где сидит команда — лучше сразу админом'],
              ['Участники подтянутся', 'Сами: админы сразу, остальные как напишут в чат'],
              ['Соберите команду', 'Выберите лидера и состав, запустите оценку'],
            ].map(([title, text], i) => (
              <div key={title} className="p-4 rounded-xl bg-[var(--color-surface-2)]
                                          border border-[var(--color-border)] fade-up"
                   style={{ animationDelay: `${i * 80}ms` }}>
                <span className="inline-grid place-items-center w-6 h-6 rounded-lg mb-3 text-[12px]
                                 text-[var(--color-accent)] bg-[rgba(59,130,246,.12)]
                                 border border-[rgba(59,130,246,.3)]">{i + 1}</span>
                <div className="text-[14px] mb-1">{title}</div>
                <div className="text-[12.5px] text-[var(--color-muted)] leading-snug">{text}</div>
              </div>
            ))}
          </div>
          <a href={addToGroup} target="_blank" rel="noreferrer"
             className="btn btn-primary px-5 py-3 mt-8 no-underline inline-flex">
            <Plus className="w-4 h-4" /> Добавить бота в группу
          </a>
        </div>
      ) : (
        <div className="grid gap-4 stagger" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))' }}>
          {chats.map((chat, i) => (
            <Link key={chat.id} to={`/chats/${chat.id}`}
              className={`card dotted p-5 no-underline text-[var(--color-text)] lift
                          ${fresh.has(chat.id) ? 'just-arrived' : ''}`}
              style={{ animationDelay: `${i * 60}ms` }}>
              <div className="flex items-center gap-3 mb-3">
                <ChatAvatar name={chat.title} url={chat.photo_url} size={40} />
                <h3 className="text-[15px] m-0 truncate">{chat.title}</h3>
              </div>
              <div className="flex gap-2">
                <Pill><Users className="w-3 h-3" /> {chat.member_count}</Pill>
                <Pill tone="accent"><Layers className="w-3 h-3" /> {chat.team_count}</Pill>
              </div>
            </Link>
          ))}
        </div>
      )}

      <p className="flex items-center justify-center gap-2 text-[12.5px] text-[var(--color-muted)] mt-12">
        <ShieldCheck className="w-3.5 h-3.5" />
        Оценки анонимны — средние показываются только когда ответили минимум 3 человека
      </p>
    </div>
  )
}
