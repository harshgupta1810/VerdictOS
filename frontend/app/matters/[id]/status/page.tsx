'use client'

import { use } from 'react'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { useMatterStatus } from '@/hooks/useMatters'
import { useMatterStream } from '@/hooks/useMatterStream'
import { usePipelineStore } from '@/store/pipelineStore'
import { PipelineProgress } from '@/components/pipeline/PipelineProgress'
import { LiveEventFeed } from '@/components/pipeline/LiveEventFeed'
import { StatusBadge } from '@/components/matters/StatusBadge'

export default function StatusPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data } = useMatterStatus(id)
  const phase = usePipelineStore((s) => s.phase)
  useMatterStream(id)

  const status = data?.status ?? null
  const displayPhase = phase ?? status

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Pipeline</h2>
          <p className="text-xs text-slate-400 mt-1 font-mono">{id}</p>
        </div>
        {status && <StatusBadge status={status} />}
      </div>

      <div className="card px-7 py-7">
        <PipelineProgress status={displayPhase} />
      </div>

      <LiveEventFeed />

      {status === 'complete' && (
        <div className="flex justify-end">
          <Link href={`/matters/${id}/verdict`}
            className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-colors shadow-sm shadow-emerald-200">
            View Verdict <ArrowRight size={15} />
          </Link>
        </div>
      )}

      {status === 'error' && (
        <div className="card border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          Pipeline failed — verify Elasticsearch, Ollama, and Redis are running and document paths exist.
        </div>
      )}
    </div>
  )
}
