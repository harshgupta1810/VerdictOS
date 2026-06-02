'use client'

import { use } from 'react'
import { useAudit } from '@/hooks/useMatters'
import { AuditTimeline } from '@/components/audit/AuditTimeline'

export default function AuditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data, isLoading, error } = useAudit(id)

  if (isLoading)
    return <div className="card p-16 flex items-center justify-center text-slate-400 text-sm">Loading audit trail…</div>
  if (error)
    return <div className="card border-red-200 bg-red-50 p-8 text-center text-red-600 text-sm">Failed to load audit: {(error as Error).message}</div>

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Audit Trail</h2>
        <p className="text-sm text-slate-500 mt-1">
          Immutable record of all pipeline events · {data?.audit_trail.length ?? 0} entries
        </p>
      </div>
      <AuditTimeline records={data?.audit_trail ?? []} />
    </div>
  )
}
