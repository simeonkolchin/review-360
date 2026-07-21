import clsx from 'clsx'

export function Pill({ children, tone = 'default' }: {
  children: React.ReactNode
  tone?: 'default' | 'ok' | 'warn' | 'accent'
}) {
  const tones = {
    default: 'text-[var(--color-text-secondary)] border-[var(--color-border)] bg-[var(--color-surface-2)]',
    ok: 'text-[var(--color-success)] border-[rgba(74,222,128,.3)] bg-[rgba(74,222,128,.08)]',
    warn: 'text-[var(--color-warning)] border-[rgba(255,176,32,.3)] bg-[rgba(255,176,32,.08)]',
    accent: 'text-[var(--color-accent)] border-[rgba(59,130,246,.35)] bg-[rgba(59,130,246,.12)]',
  }
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium', tones[tone])}>
      {children}
    </span>
  )
}

export function Avatar({ name, url, size = 34 }: { name: string; url?: string | null; size?: number }) {
  const initials = (name || '?').trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase()
  // The bot stores "tg:<file path>" — the real download URL carries the bot
  // token, so the gateway streams those bytes for us instead.
  const src = url?.startsWith('tg:') ? `/api/avatar/${url.slice(3)}` : url
  if (src) {
    return (
      <img src={src} alt={name} referrerPolicy="no-referrer"
        className="rounded-[10px] object-cover shrink-0"
        style={{ width: size, height: size }} />
    )
  }
  return (
    <span
      className="grid place-items-center rounded-[10px] font-semibold text-white shrink-0"
      style={{ width: size, height: size, fontSize: size * 0.36, background: 'var(--gradient-accent)' }}
    >
      {initials}
    </span>
  )
}

export function EmptyState({ icon, title, text }: { icon?: React.ReactNode; title: string; text?: string }) {
  return (
    <div className="card p-12 text-center fade-up">
      {icon && <div className="flex justify-center mb-3 text-[var(--color-muted)]">{icon}</div>}
      <h3 className="text-base mb-1">{title}</h3>
      {text && <p className="text-sm text-[var(--color-text-secondary)] m-0">{text}</p>}
    </div>
  )
}

export function ScoreBar({ label, self, peer }: { label: string; self: number | null; peer: number | null }) {
  const pct = (v: number | null) => (v ? (v / 5) * 100 : 0)
  return (
    <div className="my-3.5">
      <div className="flex justify-between text-[13px] mb-1.5">
        <span>{label}</span>
        <span className="text-[var(--color-text-secondary)]">
          вы {self ?? '—'} · команда <b className="text-[var(--color-accent)]">{peer ?? '—'}</b>
        </span>
      </div>
      <div className="grid gap-1">
        <div className="h-2 rounded-full bg-[var(--color-surface-2)] border border-[var(--color-border)] overflow-hidden">
          <i className="block h-full rounded-full bg-[#4b5563] transition-all duration-700" style={{ width: `${pct(self)}%` }} />
        </div>
        <div className="h-2 rounded-full bg-[var(--color-surface-2)] border border-[var(--color-border)] overflow-hidden">
          <i className="block h-full rounded-full transition-all duration-700"
             style={{ width: `${pct(peer)}%`, background: 'var(--gradient-accent)' }} />
        </div>
      </div>
    </div>
  )
}

/** Resolve the bot's "tg:<path>" avatar marker to the gateway proxy URL. */
export function avatarSrc(url?: string | null): string | undefined {
  if (!url) return undefined
  return url.startsWith('tg:') ? `/api/avatar/${url.slice(3)}` : url
}

/** Square, rounded chat avatar — the group photo, or its initials on the accent gradient. */
export function ChatAvatar({ name, url, size = 44, ring = false }: {
  name: string; url?: string | null; size?: number; ring?: boolean
}) {
  const src = avatarSrc(url)
  const ringCls = ring ? 'ring-2 ring-[var(--color-surface)]' : ''
  if (src) {
    return (
      <img src={src} alt={name} referrerPolicy="no-referrer"
        className={`rounded-2xl object-cover shrink-0 ${ringCls}`}
        style={{ width: size, height: size }} />
    )
  }
  const initials = (name || '?').trim().replace(/[«»]/g, '').split(/\s+/)
    .map(w => w[0]).slice(0, 2).join('').toUpperCase()
  return (
    <span className={`grid place-items-center rounded-2xl font-semibold text-white shrink-0 ${ringCls}`}
          style={{ width: size, height: size, fontSize: size * 0.36, background: 'var(--gradient-accent)' }}>
      {initials}
    </span>
  )
}

/** Blurred, dimmed band of the chat photo — a banner behind the title, or the top of a card. */
export function ChatCover({ url, height }: { url?: string | null; height?: number }) {
  const src = avatarSrc(url)
  const box = height ? { height } : undefined
  const cls = height ? 'relative w-full' : 'absolute inset-0'
  if (!src) {
    return (
      <div className={cls} style={{
        ...box,
        background: 'linear-gradient(120deg, rgba(59,130,246,.14), rgba(99,102,241,.06) 60%, transparent)',
      }} />
    )
  }
  return (
    <div className={cls} style={box}>
      <img src={src} alt="" referrerPolicy="no-referrer" aria-hidden
           className="absolute inset-0 w-full h-full object-cover"
           style={{ filter: 'blur(40px)', transform: 'scale(1.2)', opacity: 0.4 }} />
      <div className="absolute inset-0" style={{ background: 'rgba(19,19,22,.66)' }} />
    </div>
  )
}
