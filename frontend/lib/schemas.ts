import { z } from 'zod'

export const createDealSchema = z.object({
  client_id: z.string().min(1, 'Client ID is required'),
})

export const resolveEscalationSchema = z.object({
  decision: z.enum(['resolve', 'request_docs', 'accept_risk']),
  decision_text: z.string().optional(),
  resolved_by: z.string().min(1, 'Resolver name is required'),
})

export type CreateDealFormValues = z.infer<typeof createDealSchema>
export type ResolveEscalationFormValues = z.infer<typeof resolveEscalationSchema>
