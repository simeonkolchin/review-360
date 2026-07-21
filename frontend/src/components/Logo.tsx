export default function Logo({ size = 28, withText = true }: { size?: number; withText?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <img
        src="/logo.png"
        alt="Review 360"
        width={size}
        height={size}
        className="rounded-[9px] shrink-0"
        style={{ boxShadow: '0 0 0 1px rgba(255,255,255,.06)' }}
      />
      {withText && (
        <span className="font-semibold tracking-tight">
          review <span className="text-[var(--color-accent)]">360</span>
        </span>
      )}
    </span>
  )
}
