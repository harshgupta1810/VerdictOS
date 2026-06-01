// Typed API client — calls Next.js proxy routes which inject the backend API key

import type {
  Deal,
  DealStatusResponse,
  VerdictResponse,
  AuditTrailResponse,
  Escalation,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.message ?? res.statusText)
  }
  return res.json() as Promise<T>
}

export const api = {
  // Upload documents → returns server-side file paths
  uploadDocuments: async (files: File[]): Promise<{ paths: string[] }> => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    const res = await fetch('/api/upload', { method: 'POST', body: form })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: res.statusText }))
      throw new Error(err.message ?? res.statusText)
    }
    return res.json()
  },

  // Create a new matter (proxied to backend /api/v1/deals)
  createMatter: (body: {
    client_id: string
    document_paths: string[]
    metadata_json?: Record<string, unknown>
    selected_agents?: string[]
  }) => request<{ deal_id: string; status: string }>('/api/matters', {
    method: 'POST',
    body: JSON.stringify(body),
  }),

  // Get all matters
  getMatters: () => request<Deal[]>('/api/matters'),

  // Get matter status
  getMatterStatus: (id: string) =>
    request<DealStatusResponse>(`/api/matters/${id}/status`),

  // Get final verdict
  getVerdict: (id: string) => request<VerdictResponse>(`/api/matters/${id}/verdict`),

  // Get audit trail
  getAudit: (id: string) =>
    request<AuditTrailResponse>(`/api/matters/${id}/audit`),

  // Get escalations
  getEscalations: (id: string) =>
    request<{ escalations: Escalation[] }>(`/api/matters/${id}/escalations`),

  // Resolve an escalation
  resolveEscalation: (
    matterId: string,
    escalationId: string,
    body: { decision: string; decision_text?: string; resolved_by: string }
  ) =>
    request<{ escalation_id: string; status: string }>(
      `/api/matters/${matterId}/escalations/${escalationId}/resolve`,
      { method: 'POST', body: JSON.stringify(body) }
    ),
}
