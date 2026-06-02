import { Check, Loader2, AlertCircle } from 'lucide-react'
import type { DealStatus } from '@/lib/types'

const PHASES: { key: DealStatus; label: string; sub: string }[] = [
  { key: 'created',   label: 'Created',   sub: 'Deal queued'         },
  { key: 'indexing',  label: 'Indexing',  sub: 'BM25 + graph'        },
  { key: 'analyzing', label: 'Analyzing', sub: '16 agents'           },
  { key: 'debating',  label: 'Debating',  sub: '6-persona debate'    },
  { key: 'judging',   label: 'Judging',   sub: 'Judge synthesis'     },
  { key: 'complete',  label: 'Complete',  sub: 'Verdict ready'       },
]

const ORDER = PHASES.map((p) => p.key)

function phaseIdx(status: DealStatus | null) {
  return status ? ORDER.indexOf(status) : -1
}

export function PipelineProgress({ status }: { status: DealStatus | null }) {
  const cur     = phaseIdx(status)
  const isError = status === 'error'
  const pct     = isError
    ? 100
    : cur < 0 ? 0
    : Math.round((cur / (PHASES.length - 1)) * 100)

  return (
    <div className="select-none">
      {/* Progress track sits behind all circles */}
      <div className="relative">
        {/* Background track */}
        <div className="absolute top-5 left-0 right-0 h-0.5 bg-slate-200 mx-8" />
        {/* Filled track */}
        <div
          className={`absolute top-5 left-8 h-0.5 transition-all duration-700 ease-in-out ${
            isError ? 'bg-red-400' : 'bg-indigo-500'
          }`}
          style={{
            width: `calc(${pct}% - ${pct === 100 ? '2rem' : '2rem'})`,
          }}
        />

        {/* Steps row */}
        <ol className="relative z-10 flex justify-between items-start">
          {PHASES.map((phase, i) => {
            const done    = cur > i
            const active  = cur === i && !isError
            const errHere = isError && cur === i

            return (
              <li key={phase.key} className="flex flex-col items-center gap-2.5 w-20">
                {/* Circle */}
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all ${
                    errHere
                      ? 'bg-red-50   border-red-400   text-red-500'
                      : done
                      ? 'bg-indigo-600 border-indigo-600 text-white'
                      : active
                      ? 'bg-white     border-indigo-500 text-indigo-500 shadow-md shadow-indigo-100'
                      : 'bg-white     border-slate-200  text-slate-400'
                  }`}
                >
                  {errHere  ? <AlertCircle size={16} />
                  : done    ? <Check size={16} strokeWidth={2.5} />
                  : active  ? <Loader2 size={16} className="animate-spin" />
                  : <span className="text-xs font-semibold">{i + 1}</span>}
                </div>

                {/* Label */}
                <div className="text-center">
                  <p className={`text-xs font-semibold leading-tight ${
                    errHere ? 'text-red-500'
                    : done || active ? 'text-slate-800'
                    : 'text-slate-400'
                  }`}>
                    {phase.label}
                  </p>
                  <p className="text-[10px] text-slate-400 mt-0.5 leading-tight">
                    {active ? <span className="text-indigo-500 font-medium">Running…</span> : phase.sub}
                  </p>
                </div>
              </li>
            )
          })}
        </ol>
      </div>

      {/* Status bar */}
      <div className="mt-6 pt-5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <span>
          {isError
            ? 'Pipeline failed — check service dependencies'
            : status === 'complete'
            ? 'All phases complete — verdict ready'
            : `Phase ${Math.max(cur + 1, 1)} of ${PHASES.length} running`}
        </span>
        <span className={`font-semibold tabular-nums ${
          isError ? 'text-red-500' : status === 'complete' ? 'text-emerald-600' : 'text-indigo-600'
        }`}>
          {pct}%
        </span>
      </div>
    </div>
  )
}
