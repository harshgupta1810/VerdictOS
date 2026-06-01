'use client'

import { useState } from 'react'
import { X, Loader2 } from 'lucide-react'
import type { Escalation } from '@/lib/types'
import { useResolveEscalation } from '@/hooks/useMatters'

const DECISIONS = [
  { value: 'resolve',      label: 'Resolve',           desc: 'Confirm and accept the finding' },
  { value: 'request_docs', label: 'Request Documents',  desc: 'Trigger delta re-analysis with new uploads' },
  { value: 'accept_risk',  label: 'Accept Risk',        desc: 'Formally acknowledge risk and proceed' },
] as const

export function ResolveModal({ dealId, escalation, onClose }: {
  dealId: string
  escalation: Escalation
  onClose: () => void
}) {
  const [decision, setDecision]     = useState<'resolve' | 'request_docs' | 'accept_risk'>('resolve')
  const [decisionText, setDecisionText] = useState('')
  const [resolvedBy, setResolvedBy] = useState('')
  const { mutate, isPending, error } = useResolveEscalation(dealId)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutate(
      { escalationId: escalation.escalation_id, body: { decision, decision_text: decisionText, resolved_by: resolvedBy } },
      { onSuccess: onClose }
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl border border-slate-200">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-800">Resolve Escalation</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <p className="text-xs text-slate-400 font-mono bg-slate-50 border border-slate-100 rounded-lg px-3 py-1.5">
            {escalation.escalation_id.slice(0, 20)}…
          </p>

          <div className="space-y-2">
            {DECISIONS.map((d) => (
              <label
                key={d.value}
                className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                  decision === d.value
                    ? 'border-indigo-300 bg-indigo-50'
                    : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <input type="radio" name="decision" value={d.value} checked={decision === d.value}
                  onChange={() => setDecision(d.value)} className="mt-0.5 accent-indigo-600" />
                <div>
                  <p className="text-sm font-medium text-slate-700">{d.label}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{d.desc}</p>
                </div>
              </label>
            ))}
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-600">Notes (optional)</label>
            <textarea value={decisionText} onChange={(e) => setDecisionText(e.target.value)} rows={2}
              placeholder="Decision rationale…"
              className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-300 resize-none bg-white" />
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-600">
              Resolved by <span className="text-red-500">*</span>
            </label>
            <input type="text" value={resolvedBy} onChange={(e) => setResolvedBy(e.target.value)}
              required placeholder="Your name or ID"
              className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-300 bg-white" />
          </div>

          {error && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {(error as Error).message}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 rounded-xl border border-slate-200 text-sm text-slate-500 hover:text-slate-700 hover:border-slate-300 transition-all">
              Cancel
            </button>
            <button type="submit" disabled={isPending || !resolvedBy.trim()}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white text-sm font-medium transition-colors shadow-sm shadow-indigo-200">
              {isPending && <Loader2 size={13} className="animate-spin" />}
              Confirm
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
