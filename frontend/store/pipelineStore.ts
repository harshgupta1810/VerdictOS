import { create } from 'zustand'
import type { DealStatus, PipelineEvent } from '@/lib/types'

interface PipelineStore {
  phase: DealStatus | null
  events: PipelineEvent[]
  wsStatus: 'idle' | 'connecting' | 'open' | 'closed' | 'error'
  setPhase: (phase: DealStatus) => void
  addEvent: (event: PipelineEvent) => void
  setWsStatus: (status: PipelineStore['wsStatus']) => void
  reset: () => void
}

export const usePipelineStore = create<PipelineStore>((set) => ({
  phase: null,
  events: [],
  wsStatus: 'idle',
  setPhase: (phase) => set({ phase }),
  addEvent: (event) =>
    set((s) => ({ events: [...s.events.slice(-199), event] })),
  setWsStatus: (wsStatus) => set({ wsStatus }),
  reset: () => set({ phase: null, events: [], wsStatus: 'idle' }),
}))
