'use client'

import { use, useState } from 'react'
import { useEscalations, useResolveEscalation } from '@/hooks/useMatters'
import type { Escalation } from '@/lib/types'
import { CheckCircle2, AlertOctagon, Clock, X, Loader2 } from 'lucide-react'

const DECISIONS = [
  { value: 'resolve',      label: 'Resolve',           desc: 'Confirm and accept the finding' },
  { value: 'request_docs', label: 'Request Documents',  desc: 'Trigger delta re-analysis' },
  { value: 'accept_risk',  label: 'Accept Risk',        desc: 'Formally acknowledge risk and proceed' },
] as const

function ResolveModal({ matterId, escalation, onClose }: { matterId: string; escalation: Escalation; onClose: () => void }) {
  const [decision, setDecision] = useState<'resolve' | 'request_docs' | 'accept_risk'>('resolve')
  const [decisionText, setDecisionText] = useState('')
  const [resolvedBy, setResolvedBy] = useState('')
  const { mutate, isPending, error } = useResolveEscalation(matterId)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl border border-slate-200">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-800">Resolve Escalation</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={16} /></button>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); mutate({ escalationId: escalation.escalation_id, body: { decision, decision_text: decisionText, resolved_by: resolvedBy } }, { onSuccess: onClose }) }} className="p-5 space-y-4">
          <p className="text-xs text-slate-400 font-mono bg-slate-50 border border-slate-100 rounded-lg px-3 py-1.5">{escalation.escalation_id.slice(0, 20)}…</p>
          <div className="space-y-2">
            {DECISIONS.map((d) => (
              <label key={d.value} className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${decision === d.value ? 'border-indigo-300 bg-indigo-50' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'}`}>
                <input type="radio" name="decision" value={d.value} checked={decision === d.value} onChange={() => setDecision(d.value)} className="mt-0.5 accent-indigo-600" />
                <div><p className="text-sm font-medium text-slate-700">{d.label}</p><p className="text-xs text-slate-400 mt-0.5">{d.desc}</p></div>
              </label>
            ))}
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-600">Notes (optional)</label>
            <textarea value={decisionText} onChange={(e) => setDecisionText(e.target.value)} rows={2} placeholder="Rationale…" className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 resize-none bg-white" />
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-600">Resolved by <span className="text-red-500">*</span></label>
            <input type="text" value={resolvedBy} onChange={(e) => setResolvedBy(e.target.value)} required placeholder="Your name or ID" className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 bg-white" />
          </div>
          {error && <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{(error as Error).message}</p>}
          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose} className="flex-1 py-2 rounded-xl border border-slate-200 text-sm text-slate-500 hover:text-slate-700 hover:border-slate-300 transition-all">Cancel</button>
            <button type="submit" disabled={isPending || !resolvedBy.trim()} className="flex-1 flex items-center justify-center gap-2 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white text-sm font-medium transition-colors">
              {isPending && <Loader2 size={13} className="animate-spin" />} Confirm
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function EscalationsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data, isLoading, error } = useEscalations(id)
  const [selected, setSelected] = useState<Escalation | null>(null)

  if (isLoading) return <div className="card p-16 flex items-center justify-center"><div className="w-5 h-5 rounded-full border-2 border-indigo-300 border-t-indigo-600 animate-spin" /></div>
  if (error) return <div className="card border-red-200 bg-red-50 p-8 text-center text-red-600 text-sm">Failed: {(error as Error).message}</div>

  const escalations = data?.escalations ?? []
  const pending  = escalations.filter((e) => e.status === 'pending')
  const resolved = escalations.filter((e) => e.status === 'resolved')

  return (
    <>
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Escalations</h2>
          <p className="text-sm text-slate-500 mt-1">{escalations.length} total · {pending.length} pending · {resolved.length} resolved</p>
        </div>
        {escalations.length === 0 ? (
          <div className="card p-16 flex flex-col items-center gap-3 text-center">
            <CheckCircle2 size={28} className="text-emerald-400" />
            <p className="text-slate-500 text-sm">No escalations — all findings are settled.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {escalations.map((e) => (
              <div key={e.escalation_id} className={`card px-4 py-3.5 transition-colors ${e.status === 'resolved' ? 'opacity-60' : 'hover:border-slate-300'}`}>
                <div className="flex items-center gap-3">
                  {e.status === 'resolved' ? <CheckCircle2 size={15} className="text-emerald-500 shrink-0" /> : <AlertOctagon size={15} className="text-orange-500 shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs text-slate-500">{e.escalation_id.slice(0, 8).toUpperCase()}…</span>
                      {e.finding_id && <span className="text-[10px] text-slate-400">finding: {e.finding_id.slice(0, 8)}…</span>}
                    </div>
                    {e.status === 'resolved' && (
                      <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-400">
                        <span>Decision: <span className="text-slate-600 font-medium">{e.decision}</span></span>
                        {e.resolved_by && <span>By: <span className="text-slate-600 font-medium">{e.resolved_by}</span></span>}
                        {e.decision_text && <span className="italic">{e.decision_text}</span>}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${e.status === 'resolved' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-orange-50 text-orange-700 border-orange-200'}`}>{e.status}</span>
                    {e.status === 'pending' && <button onClick={() => setSelected(e)} className="text-xs px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors shadow-sm shadow-indigo-200">Resolve</button>}
                  </div>
                </div>
                {e.status === 'pending' && <div className="flex items-center gap-1 mt-2 text-[10px] text-slate-400"><Clock size={10} /><span>{new Date(e.created_at).toLocaleString()}</span></div>}
              </div>
            ))}
          </div>
        )}
      </div>
      {selected && <ResolveModal matterId={id} escalation={selected} onClose={() => setSelected(null)} />}
    </>
  )
}
