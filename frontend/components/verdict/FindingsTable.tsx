'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { Finding } from '@/lib/types'
import { SeverityBadge } from './SeverityBadge'

const SEV_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }

export function FindingsTable({ findings }: { findings: Finding[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [dimFilter, setDimFilter] = useState('all')

  const dimensions = [...new Set(findings.map((f) => f.dimension))]
  const filtered   = dimFilter === 'all' ? findings : findings.filter((f) => f.dimension === dimFilter)
  const sorted     = [...filtered].sort((a, b) => (SEV_ORDER[a.severity] ?? 99) - (SEV_ORDER[b.severity] ?? 99))

  return (
    <div className="space-y-3">
      {/* Filter pills */}
      <div className="flex flex-wrap gap-1.5">
        {['all', ...dimensions].map((d) => (
          <button
            key={d}
            onClick={() => setDimFilter(d)}
            className={`px-3 py-1 rounded-full text-xs font-medium capitalize transition-all border ${
              dimFilter === d
                ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm shadow-indigo-200'
                : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-700'
            }`}
          >
            {d.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {sorted.length === 0 ? (
          <p className="text-center text-slate-400 py-12 text-sm">No findings match this filter.</p>
        ) : (
          sorted.map((f, i) => (
            <div key={f.finding_id} className={i < sorted.length - 1 ? 'border-b border-slate-100' : ''}>
              <button
                className="w-full text-left px-4 py-3.5 flex items-center gap-3 hover:bg-slate-50 transition-colors"
                onClick={() => setExpanded((p) => (p === f.finding_id ? null : f.finding_id))}
              >
                <SeverityBadge severity={f.severity} />
                <p className="flex-1 text-sm text-slate-700 truncate">{f.claim}</p>
                <span className="text-[10px] text-slate-400 hidden sm:block capitalize shrink-0">
                  {f.dimension.replace(/_/g, ' ')}
                </span>
                {expanded === f.finding_id
                  ? <ChevronDown size={13} className="text-slate-400 shrink-0" />
                  : <ChevronRight size={13} className="text-slate-400 shrink-0" />}
              </button>

              {expanded === f.finding_id && (
                <div className="px-5 pb-4 pt-1 bg-slate-50 border-t border-slate-100 space-y-3">
                  <div>
                    <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">
                      Source Citation
                    </p>
                    <blockquote className="border-l-2 border-indigo-300 pl-3 text-sm text-slate-600 italic leading-relaxed">
                      {f.citation}
                    </blockquote>
                  </div>
                  <div className="flex flex-wrap gap-4 text-xs text-slate-400">
                    <span>Clause: <span className="text-slate-600 font-medium">{f.clause_type}</span></span>
                    <span>Confidence: <span className="text-slate-600 font-medium">{f.confidence}</span></span>
                    <span>Agent: <span className="text-slate-600 font-medium">{f.agent_name}</span></span>
                    <span>Verified: <span className={f.verified ? 'text-emerald-600 font-medium' : 'text-slate-500'}>{f.verified ? 'Yes' : 'No'}</span></span>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
