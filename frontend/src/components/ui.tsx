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
  if (url) {
    return (
      <img src={url} alt={name} referrerPolicy="no-referrer"
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
