export function LogoMark({ size = 32, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Outer shield shape */}
      <path
        d="M20 3L5 9V20C5 28.5 11.5 36.2 20 38C28.5 36.2 35 28.5 35 20V9L20 3Z"
        fill="url(#shield-grad)"
        opacity="0.12"
      />
      <path
        d="M20 3L5 9V20C5 28.5 11.5 36.2 20 38C28.5 36.2 35 28.5 35 20V9L20 3Z"
        stroke="url(#shield-grad)"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />

      {/* Balance beam — horizontal bar */}
      <line x1="11" y1="18" x2="29" y2="18" stroke="url(#shield-grad)" strokeWidth="1.8" strokeLinecap="round" />

      {/* Center post */}
      <line x1="20" y1="13" x2="20" y2="27" stroke="url(#shield-grad)" strokeWidth="1.8" strokeLinecap="round" />

      {/* Left pan */}
      <path d="M11 18 Q8 23 11 26 Q14 23 11 18Z" fill="url(#shield-grad)" opacity="0.7" />

      {/* Right pan */}
      <path d="M29 18 Q26 23 29 26 Q32 23 29 18Z" fill="url(#shield-grad)" opacity="0.7" />

      {/* Center diamond (verdict mark) */}
      <rect x="18" y="11" width="4" height="4" rx="1" transform="rotate(45 20 13)" fill="url(#shield-grad)" />

      <defs>
        <linearGradient id="shield-grad" x1="5" y1="3" x2="35" y2="38" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0f766e" />
          <stop offset="100%" stopColor="#0369a1" />
        </linearGradient>
      </defs>
    </svg>
  )
}

export function LogoFull({ className = '' }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <LogoMark size={32} />
      <div className="leading-none">
        <span className="text-sm font-bold text-slate-800 tracking-tight">VerdictOS</span>
      </div>
    </div>
  )
}
