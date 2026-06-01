import type { AuditRecord } from '@/lib/types'

const EVENT_DOT: Record<string, string> = {
  deal_created:        'bg-blue-500',
  indexing_started:    'bg-indigo-500',
  indexing_complete:   'bg-indigo-400',
  analysis_started:    'bg-violet-500',
  debate_started:      'bg-purple-500',
  judging_started:     'bg-amber-500',
  verdict_generated:   'bg-emerald-500',
  escalation_created:  'bg-orange-500',
  escalation_resolved: 'bg-teal-500',
  DISPUTE_FILED:       'bg-red-500',
  ESCALATION_RESOLVED: 'bg-teal-500',
}

export function AuditTimeline({ records }: { records: AuditRecord[] }) {
  if (records.length === 0) {
    return (
      <div className="card p-12 flex items-center justify-center text-slate-400 text-sm">
        No audit records yet.
      </div>
    )
  }

  return (
    <ol className="relative space-y-3 pl-6 before:absolute before:left-1.75 before:top-2 before:bottom-2 before:w-px before:bg-slate-200">
      {records.map((r) => (
        <li key={r.audit_id} className="relative">
          <span className={`absolute -left-5.25 top-2 w-3.5 h-3.5 rounded-full border-2 border-[#f4f6f9] ${EVENT_DOT[r.event_type] ?? 'bg-slate-400'}`} />
          <div className="card px-4 py-3 hover:border-slate-300 transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-mono font-semibold text-indigo-600 uppercase tracking-wide">
                {r.event_type}
              </span>
              <time className="text-[10px] text-slate-400 tabular-nums font-mono">
                {new Date(r.timestamp).toLocaleString()}
              </time>
            </div>
            <p className="text-sm text-slate-700">{r.description}</p>
            {r.actor && <p className="text-[11px] text-slate-400 mt-1">Actor: {r.actor}</p>}
          </div>
        </li>
      ))}
    </ol>
  )
}
