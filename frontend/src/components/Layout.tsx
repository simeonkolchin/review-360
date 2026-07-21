import { useEffect, useState } from 'react'
import { LogOut, ChevronDown, Check } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api, type Chat } from '../api/client'
import { useAuth } from '../context/AuthContext'
import BackgroundFX from './BackgroundFX'
import Logo from './Logo'
import { Avatar, ChatAvatar } from './ui'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const { chatId } = useParams()
  const navigate = useNavigate()

  const [chats, setChats] = useState<Chat[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => { api.get<Chat[]>('/chats').then(setChats).catch(() => setChats([])) }, [pathname])

  const active = chats.find(c => String(c.id) === chatId)
  const isOverview = pathname === '/'

  return (
    <>
      <BackgroundFX />

      <div className="w-full text-center text-[12px] py-2 border-b border-[var(--color-border)]
                      text-[var(--color-muted)]" style={{ background: '#08080a' }}>
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-accent)] mr-2 align-middle" />
        Анонимная оценка 360 для команд — прямо в Telegram
      </div>

      <header className="sticky top-0 z-30 border-b border-[var(--color-border)] backdrop-blur-xl"
              style={{ background: 'rgba(10,10,11,.82)' }}>
        <div className="max-w-[1180px] mx-auto flex items-center gap-5 px-6 h-14">
          <Link to="/" className="no-underline text-[var(--color-text)]"><Logo /></Link>

          <nav className="flex items-center gap-1">
            <Link to="/"
              className={`px-3 py-1.5 rounded-lg text-[13.5px] no-underline transition
                ${isOverview ? 'text-[var(--color-text)] bg-[var(--color-surface-2)]'
                             : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'}`}>
              Обзор
            </Link>

            {/* Teams always needs a chat, so this is a picker rather than a plain link */}
            <div className="relative">
              <button onClick={() => setOpen(o => !o)}
                className={`px-3 py-1.5 rounded-lg text-[13.5px] transition flex items-center gap-1.5
                  ${!isOverview ? 'text-[var(--color-text)] bg-[var(--color-surface-2)]'
                                : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'}`}>
                {active && <ChatAvatar name={active.title} url={active.photo_url} size={18} />}
                <span className="truncate max-w-[180px]">{active ? active.title : 'Команды'}</span>
                <ChevronDown className={`w-3.5 h-3.5 transition ${open ? 'rotate-180' : ''}`} />
              </button>

              {open && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
                  <div className="absolute left-0 top-11 z-20 w-[260px] p-1.5 rounded-xl
                                  border border-[var(--color-border)] shadow-xl"
                       style={{ background: 'var(--color-surface-elevated)' }}>
                    {chats.length === 0 ? (
                      <p className="text-[13px] text-[var(--color-muted)] px-3 py-3 m-0">
                        Нет подключённых чатов
                      </p>
                    ) : chats.map(chat => (
                      <button key={chat.id}
                        onClick={() => { setOpen(false); navigate(`/chats/${chat.id}`) }}
                        className="w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg
                                   text-left text-[13.5px] hover:bg-[var(--color-surface-2)] transition">
                        <span className="flex items-center gap-2.5 min-w-0">
                          <ChatAvatar name={chat.title} url={chat.photo_url} size={24} />
                          <span className="truncate">{chat.title}</span>
                        </span>
                        {String(chat.id) === chatId
                          ? <Check className="w-3.5 h-3.5 text-[var(--color-accent)] shrink-0" />
                          : <span className="text-[11px] text-[var(--color-muted)] shrink-0">
                              {chat.team_count} ком.
                            </span>}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </nav>

          <div className="flex-1" />

          {user && (
            <div className="flex items-center gap-2.5">
              <Avatar name={user.display_name} url={user.photo_url} size={28} />
              <span className="text-[13.5px] hidden sm:block">{user.display_name}</span>
              <button onClick={logout} className="btn btn-ghost px-2.5 py-1.5" title="Выйти">
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-[1180px] mx-auto px-6 pt-10 pb-24" key={pathname}>
        <div className="page-enter">{children}</div>
      </main>
    </>
  )
}
