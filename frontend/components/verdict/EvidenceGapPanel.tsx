'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react'
import type { EvidenceGapReport } from '@/lib/types'

export function EvidenceGapPanel({ report }: { report: EvidenceGapReport }) {
  const [open, setOpen] = useState(false)
  const total = report.gaps.length + report.skipped_dimensions.length
  if (total === 0) return null

  return (
    <div className="border border-yellow-900 rounded-xl overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 bg-yellow-950/40 hover:bg-yellow-950/60 transition-colors text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <AlertTriangle size={16} className="text-yellow-400 shrink-0" />
        <span className="text-sm font-medium text-yellow-300 flex-1">
          Evidence Gaps ({total})
        </span>
        {open ? <ChevronUp size={14} className="text-yellow-600" /> : <ChevronDown size={14} className="text-yellow-600" />}
      </button>
      {open && (
        <div className="p-4 space-y-4 bg-gray-900/60">
          {report.skipped_dimensions.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase mb-2">Skipped Dimensions</p>
              <div className="flex flex-wrap gap-2">
                {report.skipped_dimensions.map((d) => (
                  <span key={d} className="px-2 py-0.5 bg-gray-800 text-gray-300 rounded text-xs capitalize">
                    {d.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
          {report.gaps.map((gap) => (
            <div key={gap.dimension} className="border-t border-gray-800 pt-3">
              <p className="text-sm font-medium text-gray-200 capitalize mb-2">
                {gap.dimension.replace(/_/g, ' ')}
              </p>
              {gap.missing_claims.length > 0 && (
                <div className="mb-2">
                  <p className="text-xs text-gray-500 mb-1">Missing claims:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {gap.missing_claims.map((c, i) => (
                      <li key={i} className="text-xs text-gray-400">{c}</li>
                    ))}
                  </ul>
                </div>
              )}
              {gap.suggested_remedies.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Suggested remedies:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {gap.suggested_remedies.map((r, i) => (
                      <li key={i} className="text-xs text-indigo-400">{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
