// TypeScript types mirroring VerdictOS Pydantic schemas

export type DealStatus =
  | 'created'
  | 'indexing'
  | 'analyzing'
  | 'debating'
  | 'judging'
  | 'complete'
  | 'error'

export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Confidence = 'high' | 'medium' | 'speculative'
export type FindingDimension =
  | 'risk_exposure'
  | 'valuation_fairness'
  | 'strategic_fit'
  | 'synergy_validity'
  | 'integration_complexity'
  | 'market_timing'
  | 'regulatory_approval'
  | 'exit_scenario'

export type EscalationDecision = 'resolve' | 'request_docs' | 'accept_risk'
export type DebatePersona =
  | 'proponent'
  | 'critic'
  | 'devils_advocate'
  | 'valuation_skeptic'
  | 'integration_realist'
  | 'regulators_eye'
export type DebateStance = 'support' | 'oppose' | 'neutral'

export interface Deal {
  deal_id: string
  client_id: string
  status: DealStatus
  metadata: Record<string, unknown>
}

export interface Finding {
  finding_id: string
  claim: string
  citation: string
  confidence: Confidence
  severity: Severity
  dimension: FindingDimension
  clause_type: string
  agent_name: string
  verified: boolean
}

export interface GoNoGoFinding {
  finding_id: string
  claim: string
  severity: string
  confidence: number
  dimension: string
  section_citation: string
  clause_type: string
}

export interface EscalationArgument {
  persona: DebatePersona
  stance: DebateStance
  argument: string
  calibrated_confidence: string
}

export interface EscalationItem {
  finding_id: string
  claim: string
  dimension: string
  arguments: EscalationArgument[]
  has_contradictions: boolean
  has_dropouts: boolean
  judge_override: boolean
  judge_notes: string
}

export interface EvidenceGapItem {
  dimension: string
  missing_claims: string[]
  unconfirmed_entities: string[]
  suggested_remedies: string[]
}

export interface EvidenceGapReport {
  skipped_dimensions: string[]
  gaps: EvidenceGapItem[]
}

// Actual backend verdict response shape
export interface VerdictResponse {
  deal_id: string
  status: string
  findings: Finding[]
}

export interface AuditRecord {
  audit_id: string
  event_type: string
  actor: string
  description: string
  timestamp: string
}

export interface Escalation {
  escalation_id: string
  deal_id: string
  finding_id: string | null
  status: 'pending' | 'resolved'
  decision: EscalationDecision | null
  decision_text: string | null
  resolved_by: string | null
  created_at: string
  resolved_at: string | null
}

export interface PipelineEvent {
  type: string
  payload: Record<string, unknown>
  ts: number
}

export interface DealStatusResponse {
  deal_id: string
  status: DealStatus
  metadata: Record<string, unknown>
}

export interface AuditTrailResponse {
  deal_id: string
  audit_trail: AuditRecord[]
}

// Display-layer aliases (backend still uses "deal" field names)
export type Matter = Deal
export type MatterStatus = DealStatus
