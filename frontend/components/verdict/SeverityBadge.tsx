const styles: Record<string, string> = {
  critical: 'bg-red-50    text-red-700    border-red-200',
  high:     'bg-orange-50 text-orange-700 border-orange-200',
  medium:   'bg-amber-50  text-amber-700  border-amber-200',
  low:      'bg-slate-100 text-slate-600  border-slate-200',
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide border ${styles[severity] ?? styles.low}`}>
      {severity}
    </span>
  )
}
