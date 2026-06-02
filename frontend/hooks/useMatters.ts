import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export const matterKeys = {
  all: ['matters'] as const,
  detail: (id: string) => ['matters', id] as const,
  status: (id: string) => ['matters', id, 'status'] as const,
  verdict: (id: string) => ['matters', id, 'verdict'] as const,
  audit: (id: string) => ['matters', id, 'audit'] as const,
  escalations: (id: string) => ['matters', id, 'escalations'] as const,
}

export function useMatters() {
  return useQuery({ queryKey: matterKeys.all, queryFn: api.getMatters })
}

export function useMatterStatus(id: string, enabled = true) {
  return useQuery({
    queryKey: matterKeys.status(id),
    queryFn: () => api.getMatterStatus(id),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'complete' || s === 'error' ? false : 5000
    },
    enabled,
  })
}

export function useVerdict(id: string, enabled = true) {
  return useQuery({
    queryKey: matterKeys.verdict(id),
    queryFn: () => api.getVerdict(id),
    enabled,
    retry: false,
  })
}

export function useAudit(id: string) {
  return useQuery({
    queryKey: matterKeys.audit(id),
    queryFn: () => api.getAudit(id),
  })
}

export function useEscalations(id: string) {
  return useQuery({
    queryKey: matterKeys.escalations(id),
    queryFn: () => api.getEscalations(id),
  })
}

export function useResolveEscalation(matterId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      escalationId,
      body,
    }: {
      escalationId: string
      body: { decision: string; decision_text?: string; resolved_by: string }
    }) => api.resolveEscalation(matterId, escalationId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: matterKeys.escalations(matterId) })
    },
  })
}
