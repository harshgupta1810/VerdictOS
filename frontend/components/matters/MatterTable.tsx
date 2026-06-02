'use client'

import Link from 'next/link'
import { ArrowUpRight, Clock, Inbox, Plus } from 'lucide-react'
import { useMatters } from '@/hooks/useMatters'
import { StatusBadge } from './StatusBadge'
import type { DealStatus } from '@/lib/types'

const PHASE_LABEL: Record<DealStatus, string> = {
  created:   'Queued for analysis',
  indexing:  'Parsing & indexing documents…',
  analyzing: 'Running specialist agents…',
  debating:  'Adversarial debate in progress…',
  judging:   'Judge synthesis…',
  complete:  'Verdict ready to review',
  error:     'Pipeline encountered an error',
}

export function MatterTable() {
  const { data: matters, isLoading, error } = useMatters()

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="card h-36 animate-pulse bg-slate-100" />
        ))}
      </div>
    )
  }

  if (error) {
    return <div className="card p-8 text-center text-red-600 text-sm">Failed to load matters: {(error as Error).message}</div>
  }

  if (!matters || matters.length === 0) {
    return (
      <div className="card p-16 flex flex-col items-center gap-4 text-center">
        <div className="w-14 h-14 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center">
          <Inbox size={24} className="text-slate-400" />
        </div>
        <div>
          <p className="text-slate-700 font-semibold">No matters yet</p>
          <p className="text-sm text-slate-400 mt-1">Open a new matter to start your first analysis</p>
        </div>
        <Link href="/matters/new"
          className="inline-flex items-center gap-2 mt-1 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-sm font-medium transition-colors shadow-sm">
          <Plus size={14} /> Open New Matter
        </Link>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {matters.map((m) => (
        <Link key={m.deal_id} href={`/matters/${m.deal_id}/status`}>
          <div className="card p-5 flex flex-col gap-4 hover:border-teal-200 hover:shadow-md hover:shadow-teal-50 transition-all cursor-pointer group h-full">
            <div className="flex items-start justify-between gap-2">
              <StatusBadge status={m.status} />
              <ArrowUpRight size={15} className="text-slate-300 group-hover:text-teal-700 transition-colors shrink-0 mt-0.5" />
            </div>
            <div className="flex-1">
              <p className="text-base font-semibold text-slate-800 leading-snug">{m.client_id}</p>
              <p className="text-xs text-slate-400 mt-1">{PHASE_LABEL[m.status]}</p>
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <span className="font-mono text-[10px] text-slate-400">{m.deal_id.slice(0, 8).toUpperCase()}</span>
              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                <Clock size={10} /><span>M&A Analysis</span>
              </div>
            </div>
          </div>
        </Link>
      ))}
    </div>
  )
}
