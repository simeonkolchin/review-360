import { useEffect, useRef, useState } from 'react'
import { Send, Loader2, Check, Users, EyeOff, GitCompareArrows } from 'lucide-react'
import { api, type User } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Logo from '../components/Logo'
import Scramble from '../components/Scramble'

// The headline decodes into a new ending every couple of seconds.
const HEADLINES = [
  'тебя видит команда',
  'ты выглядишь извне',
  'тебя слышат коллеги',
  'ты растёшь в роли',
]

// Short and near-equal in length, so the line under the text never jumps.
const NOTES = ['анонимно', 'пять минут', 'без форм', 'в telegram']

const STEPS = [
  'Нажмите кнопку — откроется бот',
  'Отправьте боту «Старт»',
  'Вернитесь сюда — вы уже внутри',
]

const FACTS = [
  { icon: Users, title: 'Каждый оценивает каждого', text: 'Себя, коллег и лидера — по пяти компетенциям' },
  { icon: EyeOff, title: 'Анонимно по умолчанию', text: 'Средние открываются только с трёх ответов' },
  { icon: GitCompareArrows, title: 'Главное — разрыв', text: 'Самооценка против взгляда команды на одном графике' },
]

export default function Login() {
  const { setUser } = useAuth()
  const [link, setLink] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | null>(null)

  // Ask the gateway for a one-time login token + deep link into the bot.
  const start = async () => {
    setError(null)
    try {
      const data = await api.post<{ token: string; link: string | null }>('/auth/login-link')
      setToken(data.token)
      setLink(data.link)
      if (data.link) window.open(data.link, '_blank')
    } catch (e) { setError((e as Error).message) }
  }

  // Poll until the bot confirms the user pressed Start.
  useEffect(() => {
    if (!token) return
    timer.current = window.setInterval(async () => {
      try {
        const user = await api.get<User | null>(`/auth/login-status?token=${token}`)
        if (user) {
          if (timer.current) clearInterval(timer.current)
          setUser(user)
        }
      } catch { /* token not confirmed yet */ }
    }, 1500)
    return () => { if (timer.current) clearInterval(timer.current) }
  }, [token, setUser])

  return (
    <div className="min-h-screen px-6">
      <div className="max-w-[1080px] mx-auto min-h-screen flex flex-col">

        <div className="py-7">
          <Logo />
        </div>

        {/* ---------- decoding headline ---------- */}
        <div className="flex-1 flex flex-col justify-center py-10 fade-up">
          <div className="flex items-center gap-2.5 mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent)]" />
            <span className="text-[11.5px] uppercase tracking-[.18em] text-[var(--color-muted)] font-mono">
              оценка 360
            </span>
          </div>

          <h1 className="hero-line m-0">
            <span className="block text-[var(--color-text)]">Узнай, как</span>
            <span className="block scramble-accent caret">
              <Scramble phrases={HEADLINES} />
            </span>
          </h1>

          <p className="mt-7 mb-0 text-[15.5px] text-[var(--color-text-secondary)]
                        max-w-[560px] leading-relaxed">
            Собираем честную обратную связь по методу 360°: каждый оценивает коллег
            и себя, а разницу между этими взглядами вы видите на одном экране.
          </p>

          <div className="mt-3.5 flex items-center gap-2 text-[12.5px] font-mono text-[var(--color-muted)]">
            <span className="w-3 h-px bg-[var(--color-border)]" />
            <Scramble phrases={NOTES} holdMs={2200} speed={2.6} />
          </div>
        </div>

        {/* ---------- login card at the bottom ---------- */}
        <div className="grid gap-4 pb-10 md:grid-cols-[1.05fr_1fr] fade-up"
             style={{ animationDelay: '.12s' }}>
          <div className="card p-6">
            {!token ? (
              <>
                <div className="flex flex-col gap-3 mb-6">
                  {STEPS.map((step, i) => (
                    <div key={i}
                         className="flex gap-3 items-center text-[14px] text-[var(--color-text-secondary)]">
                      <b className="grid place-items-center shrink-0 w-6 h-6 rounded-lg text-[11px] font-mono
                                    text-[var(--color-accent)] bg-[var(--color-surface-2)]
                                    border border-[var(--color-border)]">{i + 1}</b>
                      {step}
                    </div>
                  ))}
                </div>
                <button onClick={start} className="btn btn-primary w-full py-3.5 text-[15px]">
                  <Send className="w-4 h-4" /> Войти через Telegram
                </button>
              </>
            ) : (
              <>
                <div className="flex flex-col gap-3 mb-6">
                  <div className="flex gap-3 items-center text-[14px] text-[var(--color-muted)]">
                    <span className="grid place-items-center shrink-0 w-6 h-6 rounded-lg
                                     bg-[rgba(74,222,128,.12)] text-[var(--color-success)]">
                      <Check className="w-3.5 h-3.5" />
                    </span>
                    Ссылка создана — она живёт 10 минут
                  </div>
                  <div className="flex gap-3 items-center text-[14px] text-[var(--color-text-secondary)]">
                    <span className="grid place-items-center shrink-0 w-6 h-6 rounded-lg
                                     bg-[var(--color-surface-2)] border border-[var(--color-border)]
                                     text-[var(--color-accent)]">
                      <Loader2 className="w-3.5 h-3.5 spin" />
                    </span>
                    Ждём, пока вы нажмёте «Старт» в боте…
                  </div>
                </div>

                {link && (
                  <a href={link} target="_blank" rel="noreferrer"
                     className="btn btn-primary w-full py-3.5 no-underline">
                    <Send className="w-4 h-4" /> Открыть бота ещё раз
                  </a>
                )}
              </>
            )}

            {error && <p className="text-[var(--color-danger)] text-sm mt-4 mb-0">{error}</p>}
          </div>

          <div className="card dotted p-6 flex flex-col justify-center gap-4">
            {FACTS.map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex gap-3 items-start">
                <span className="grid place-items-center shrink-0 w-8 h-8 rounded-[10px]
                                 bg-[var(--color-surface-2)] border border-[var(--color-border)]
                                 text-[var(--color-accent)]">
                  <Icon className="w-4 h-4" />
                </span>
                <div>
                  <div className="text-[13.5px]">{title}</div>
                  <div className="text-[12.5px] text-[var(--color-muted)] mt-0.5 leading-snug">{text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
