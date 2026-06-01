'use client'

import { useState } from 'react'
import { AlertOctagon, ChevronDown, ChevronUp, CheckCircle } from 'lucide-react'
import type { EscalationItem } from '@/lib/types'

const STANCE_COLOR: Record<string, string> = {
  support: 'text-emerald-400',
  oppose:  'text-red-400',
  neutral: 'text-white/40',
}

const PERSONA_LABEL: Record<string, string> = {
  proponent:           'Proponent',
  critic:              'Critic',
  devils_advocate:     "Devil's Advocate",
  valuation_skeptic:   'Valuation Skeptic',
  integration_realist: 'Integration Realist',
  regulators_eye:      "Regulator's Eye",
}

export function EscalationCard({
  item,
  resolved,
}: {
  item: EscalationItem
  resolved?: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={`glass rounded-xl overflow-hidden ${resolved ? 'opacity-55' : ''}`}>
      <div className="flex items-start gap-3 px-4 py-3">
        <AlertOctagon
          size={16}
          className={`shrink-0 mt-0.5 ${resolved ? 'text-white/30' : 'text-orange-400'}`}
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-white/80 line-clamp-2">{item.claim}</p>
          <div className="flex flex-wrap gap-2 mt-1.5">
            <span className="text-[10px] text-white/25 capitalize">
              {item.dimension.replace(/_/g, ' ')}
            </span>
            {item.has_contradictions && (
              <span className="text-[10px] bg-red-500/15 text-red-300 border border-red-500/20 px-1.5 py-0.5 rounded">
                Contradictions
              </span>
            )}
            {item.judge_override && (
              <span className="text-[10px] bg-violet-500/15 text-violet-300 border border-violet-500/20 px-1.5 py-0.5 rounded">
                Judge Override
              </span>
            )}
            {resolved && (
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400">
                <CheckCircle size={10} /> Resolved
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-white/25 hover:text-white/60 transition-colors shrink-0"
        >
          {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>
      </div>

      {expanded && item.arguments.length > 0 && (
        <div className="divide-y divide-white/5 border-t border-white/6">
          {item.arguments.map((arg, i) => (
            <div key={i} className="px-4 py-3 bg-white/2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-semibold text-white/35">
                  {PERSONA_LABEL[arg.persona] ?? arg.persona}
                </span>
                <span className={`text-[10px] font-medium ${STANCE_COLOR[arg.stance] ?? 'text-white/40'}`}>
                  {arg.stance}
                </span>
              </div>
              <p className="text-sm text-white/65 leading-relaxed">{arg.argument}</p>
              <p className="text-[10px] text-white/25 mt-1">
                Confidence: {arg.calibrated_confidence}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
