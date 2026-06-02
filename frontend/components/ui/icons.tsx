type IconProps = { size?: number; className?: string }

/** Pipeline — three stacked bars tapering right, conveying sequential processing */
export function PipelineIcon({ size = 16, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className}>
      <rect x="2" y="4"  width="13" height="2.5" rx="1.25" fill="currentColor" />
      <rect x="2" y="8.75" width="10" height="2.5" rx="1.25" fill="currentColor" opacity=".75" />
      <rect x="2" y="13.5" width="7"  height="2.5" rx="1.25" fill="currentColor" opacity=".5" />
      <path d="M17.5 10 L14 7v6z" fill="currentColor" />
    </svg>
  )
}

/** Verdict — authoritative stamp seal with bold checkmark */
export function VerdictIcon({ size = 16, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className}>
      <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="10" cy="10" r="5.5" stroke="currentColor" strokeWidth="1" opacity=".4" strokeDasharray="2 1.5" />
      <path d="M6.5 10.2 L8.8 12.5 L13.5 7.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/** Escalation — a flag planted in a document, signalling "flag for review" */
export function EscalationIcon({ size = 16, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className}>
      {/* Staff */}
      <line x1="5" y1="3" x2="5" y2="17" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      {/* Flag */}
      <path d="M5 3.5 L14 6.5 L5 9.5Z" fill="currentColor" />
      {/* Exclamation on flag */}
      <circle cx="9.5" cy="6.5" r="0.8" fill="white" />
    </svg>
  )
}

/** Audit — a document with a padlock, "immutable locked record" */
export function AuditIcon({ size = 16, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className}>
      {/* Document */}
      <rect x="3" y="2" width="11" height="14" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <line x1="6" y1="6"  x2="11" y2="6"  stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="6" y1="9"  x2="11" y2="9"  stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="6" y1="12" x2="9"  y2="12" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      {/* Padlock (bottom-right overlay) */}
      <rect x="11" y="13" width="6" height="5" rx="1.2" fill="currentColor" />
      <path d="M12.5 13v-1.2a1.5 1.5 0 013 0V13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" />
      <circle cx="14" cy="15.5" r="0.9" fill="white" />
    </svg>
  )
}

/* ── Agent category mini-icons (14px) ── */

export function LegalCatIcon({ size = 14, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" className={className}>
      {/* Gavel head */}
      <rect x="6" y="1" width="6" height="3" rx="1" fill="currentColor" transform="rotate(45 9 2.5)" />
      {/* Handle */}
      <line x1="3" y1="11" x2="7" y2="7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function FinanceCatIcon({ size = 14, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" className={className}>
      <rect x="1" y="9"  width="3" height="4" rx="0.8" fill="currentColor" />
      <rect x="5.5" y="6" width="3" height="7" rx="0.8" fill="currentColor" opacity=".8" />
      <rect x="10" y="2" width="3" height="11" rx="0.8" fill="currentColor" opacity=".6" />
    </svg>
  )
}

export function PeopleCatIcon({ size = 14, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" className={className}>
      <circle cx="7" cy="4" r="2.5" fill="currentColor" />
      <path d="M1.5 13c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" fill="none" />
    </svg>
  )
}

export function TechCatIcon({ size = 14, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" className={className}>
      <circle cx="7" cy="7" r="2" fill="currentColor" />
      <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1" opacity=".5" />
      <line x1="7" y1="1"   x2="7" y2="2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="7" y1="11.5" x2="7" y2="13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="1"   y1="7" x2="2.5" y2="7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="11.5" y1="7" x2="13" y2="7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

export function CommercialCatIcon({ size = 14, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" className={className}>
      <path d="M1 9 C1 6 3 4 5 5 C5.5 3 8.5 3 9 5 C11 4 13 6 13 9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" />
      <line x1="4" y1="9" x2="10" y2="9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="4" y1="11.5" x2="10" y2="11.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

export function RiskCatIcon({ size = 14, className = '' }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" className={className}>
      <path d="M7 1.5 L13 12.5 H1 Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" fill="currentColor" opacity=".15" />
      <path d="M7 1.5 L13 12.5 H1 Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <line x1="7" y1="6" x2="7" y2="9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="7" cy="11" r="0.8" fill="currentColor" />
    </svg>
  )
}
