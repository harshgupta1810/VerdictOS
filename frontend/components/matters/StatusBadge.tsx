import type { DealStatus } from '@/lib/types'

const styles: Record<DealStatus, string> = {
  created:   'bg-slate-100  text-slate-600  border-slate-200',
  indexing:  'bg-blue-50    text-blue-700   border-blue-200',
  analyzing: 'bg-cyan-50    text-cyan-700   border-cyan-200',
  debating:  'bg-teal-50    text-teal-700   border-teal-200',
  judging:   'bg-sky-50     text-sky-700    border-sky-200',
  complete:  'bg-emerald-50 text-emerald-700 border-emerald-200',
  error:     'bg-red-50     text-red-700    border-red-200',
}

const dots: Record<DealStatus, string> = {
  created:   'bg-slate-400',
  indexing:  'bg-blue-500 animate-pulse',
  analyzing: 'bg-cyan-500 animate-pulse',
  debating:  'bg-teal-500 animate-pulse',
  judging:   'bg-sky-500 animate-pulse',
  complete:  'bg-emerald-500',
  error:     'bg-red-500',
}

export function StatusBadge({ status }: { status: DealStatus }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dots[status]}`} />
      {status}
    </span>
  )
}
