'use client'

import { useEffect, useRef } from 'react'
import { usePipelineStore } from '@/store/pipelineStore'
import type { DealStatus } from '@/lib/types'

const PHASE_ORDER: DealStatus[] = [
  'created', 'indexing', 'analyzing', 'debating', 'judging', 'complete',
]

export function useMatterStream(matterId: string | null) {
  const { setPhase, addEvent, setWsStatus } = usePipelineStore()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!matterId) return

    const wsBase = process.env.NEXT_PUBLIC_BACKEND_WS_URL ?? 'ws://localhost:8000'
    const apiKey = process.env.NEXT_PUBLIC_API_KEY ?? ''
    const url = `${wsBase}/api/v1/deals/${matterId}/stream?api_key=${encodeURIComponent(apiKey)}`

    setWsStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setWsStatus('open')
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data as string) as { type: string; payload: Record<string, unknown> }
        addEvent({ type: data.type, payload: data.payload, ts: Date.now() })
        if (PHASE_ORDER.includes(data.type as DealStatus)) setPhase(data.type as DealStatus)
        if (data.payload?.status && PHASE_ORDER.includes(data.payload.status as DealStatus))
          setPhase(data.payload.status as DealStatus)
      } catch { /* ignore malformed */ }
    }
    ws.onerror  = () => setWsStatus('error')
    ws.onclose  = () => setWsStatus('closed')

    return () => { ws.close(); wsRef.current = null }
  }, [matterId, setPhase, addEvent, setWsStatus])
}
