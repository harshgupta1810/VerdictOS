'use client'

import { use } from 'react'
import { useVerdict, useMatterStatus } from '@/hooks/useMatters'
import { GoNoGoBrief } from '@/components/verdict/GoNoGoBrief'
import { FindingsTable } from '@/components/verdict/FindingsTable'

export default function VerdictPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data: statusData } = useMatterStatus(id)
  const isComplete = statusData?.status === 'complete'
  const { data: verdict, isLoading, error } = useVerdict(id, isComplete)

  if (!isComplete)
    return <div className="card p-16 flex items-center justify-center text-slate-400 text-sm">Verdict is available once the pipeline completes.</div>
  if (isLoading)
    return <div className="card p-16 flex items-center justify-center text-slate-400 text-sm">Loading verdict…</div>
  if (error || !verdict)
    return <div className="card border-red-200 bg-red-50 p-8 text-center text-red-600 text-sm">Failed to load verdict: {(error as Error)?.message}</div>

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-900">Verdict</h2>
      <GoNoGoBrief findings={verdict.findings} />
      <div>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
          Findings ({verdict.findings.length})
        </h3>
        <FindingsTable findings={verdict.findings} />
      </div>
    </div>
  )
}
