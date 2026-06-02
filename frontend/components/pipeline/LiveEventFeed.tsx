'use client'

import { useEffect, useRef } from 'react'
import { usePipelineStore } from '@/store/pipelineStore'
import { Radio } from 'lucide-react'

const WS_DOT: Record<string, string> = {
  idle:       'bg-slate-300',
  connecting: 'bg-amber-400 animate-pulse',
  open:       'bg-emerald-500',
  closed:     'bg-slate-300',
  error:      'bg-red-500',
}

export function LiveEventFeed() {
  const events    = usePipelineStore((s) => s.events)
  const wsStatus  = usePipelineStore((s) => s.wsStatus)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <div className="flex items-center gap-2 text-slate-500">
          <Radio size={13} />
          <span className="text-xs font-semibold uppercase tracking-widest">Live Events</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <span className={`w-1.5 h-1.5 rounded-full ${WS_DOT[wsStatus]}`} />
          <span className="capitalize">{wsStatus}</span>
        </div>
      </div>

      <div className="h-52 overflow-y-auto p-4 space-y-1.5 font-mono text-[11px] bg-slate-50">
        {events.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-400">
            Waiting for pipeline events…
          </div>
        ) : (
          events.map((ev, i) => (
            <div key={i} className="flex items-start gap-2.5">
              <span className="text-slate-400 shrink-0 tabular-nums">
                {new Date(ev.ts).toLocaleTimeString()}
              </span>
              <span className="text-indigo-500 shrink-0">[{ev.type}]</span>
              <span className="text-slate-500 truncate">{JSON.stringify(ev.payload)}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
