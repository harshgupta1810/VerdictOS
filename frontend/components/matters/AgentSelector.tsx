'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, Info, CheckSquare, Square } from 'lucide-react'
import {
  LegalCatIcon, FinanceCatIcon, PeopleCatIcon,
  TechCatIcon, CommercialCatIcon, RiskCatIcon,
} from '@/components/ui/icons'

interface Agent {
  id: string
  label: string
  desc: string
}

interface Category {
  name: string
  color: string
  bgColor: string
  borderColor: string
  Icon: React.FC<{ size?: number; className?: string }>
  agents: Agent[]
}

const CATEGORIES: Category[] = [
  {
    name: 'Legal', color: 'text-blue-700', bgColor: 'bg-blue-50', borderColor: 'border-blue-200',
    Icon: LegalCatIcon,
    agents: [
      { id: 'ip_agent',           label: 'IP',           desc: 'Patents, trademarks, IP ownership & assignments' },
      { id: 'litigation_agent',   label: 'Litigation',   desc: 'Pending lawsuits, arbitration, contingent liabilities' },
      { id: 'regulatory_agent',   label: 'Regulatory',   desc: 'Licenses, permits, GDPR/HIPAA/SOX compliance' },
      { id: 'governance_agent',   label: 'Governance',   desc: 'Cap table, board structure, shareholder rights' },
      { id: 'related_party_agent',label: 'Related Party','desc': 'Insider deals, founder conflicts, self-dealing' },
    ],
  },
  {
    name: 'Financial', color: 'text-emerald-700', bgColor: 'bg-emerald-50', borderColor: 'border-emerald-200',
    Icon: FinanceCatIcon,
    agents: [
      { id: 'finance_agent',   label: 'Finance',   desc: 'P&L, cash flow, debt covenants, revenue quality' },
      { id: 'tax_agent',       label: 'Tax',       desc: 'Tax liabilities, disputes, transfer pricing' },
      { id: 'insurance_agent', label: 'Insurance', desc: 'Coverage gaps, claims history, policy risks' },
      { id: 'assets_agent',    label: 'Assets',    desc: 'Property ownership, leases, asset valuations' },
    ],
  },
  {
    name: 'People & Org', color: 'text-slate-700', bgColor: 'bg-slate-50', borderColor: 'border-slate-200',
    Icon: PeopleCatIcon,
    agents: [
      { id: 'hr_agent', label: 'HR', desc: 'Employment contracts, benefits, retention risks' },
    ],
  },
  {
    name: 'Technology', color: 'text-teal-700', bgColor: 'bg-teal-50', borderColor: 'border-teal-200',
    Icon: TechCatIcon,
    agents: [
      { id: 'cyber_agent',   label: 'Tech & Cyber',  desc: 'IT infra, security posture, tech debt, breaches' },
      { id: 'privacy_agent', label: 'Data Privacy',  desc: 'Data handling, consent, breach history' },
    ],
  },
  {
    name: 'Commercial', color: 'text-cyan-700', bgColor: 'bg-cyan-50', borderColor: 'border-cyan-200',
    Icon: CommercialCatIcon,
    agents: [
      { id: 'supplier_agent', label: 'Supplier', desc: 'Vendor lock-in, supply chain risks, key contracts' },
      { id: 'customer_agent', label: 'Customer', desc: 'Revenue concentration, contract terms, churn risk' },
    ],
  },
  {
    name: 'Risk', color: 'text-red-700', bgColor: 'bg-red-50', borderColor: 'border-red-200',
    Icon: RiskCatIcon,
    agents: [
      { id: 'reputation_agent', label: 'Reputation', desc: 'Adverse media, ESG controversies, executive debarment' },
      { id: 'esg_agent',        label: 'ESG',        desc: 'Emissions, hazardous waste, human rights risks' },
    ],
  },
]

const ALL_AGENT_IDS = CATEGORIES.flatMap((c) => c.agents.map((a) => a.id))

interface AgentSelectorProps {
  selected: string[]
  onChange: (agents: string[]) => void
}

export function AgentSelector({ selected, onChange }: AgentSelectorProps) {
  const [open, setOpen] = useState(false)

  const toggle = (id: string) =>
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id])

  const selectAll = () => onChange([...ALL_AGENT_IDS])
  const clearAll  = () => onChange([])

  return (
    <div className="space-y-2">
      {/* Expand toggle */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-700">Configure agents</span>
          <span className="text-xs text-slate-400 font-normal">(optional)</span>
          {selected.length > 0 && (
            <span className="text-[10px] font-semibold bg-teal-50 text-teal-700 border border-teal-200 px-2 py-0.5 rounded-full">
              {selected.length} selected
            </span>
          )}
        </div>
        {open ? <ChevronUp size={15} className="text-slate-400" /> : <ChevronDown size={15} className="text-slate-400" />}
      </button>

      {open && (
        <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
          {/* Info banner */}
          <div className={`flex items-start gap-2.5 px-4 py-3 border-b ${
            selected.length === 0
              ? 'bg-slate-50 border-slate-100'
              : 'bg-teal-50 border-teal-100'
          }`}>
            <Info size={14} className={`mt-0.5 shrink-0 ${selected.length === 0 ? 'text-slate-500' : 'text-teal-700'}`} />
            <p className={`text-xs leading-relaxed ${selected.length === 0 ? 'text-slate-600' : 'text-teal-700'}`}>
              {selected.length === 0
                ? 'The planner will automatically activate the relevant agents based on your documents. Select agents below only if you want to override this.'
                : `${selected.length} agent${selected.length > 1 ? 's' : ''} selected — only these will run on your matter.`}
            </p>
          </div>

          {/* Select all / clear */}
          <div className="flex items-center gap-3 px-4 py-2.5 border-b border-slate-100 bg-slate-50">
            <button type="button" onClick={selectAll}
              className="text-xs font-medium text-teal-700 hover:text-teal-900 transition-colors">
              Select all ({ALL_AGENT_IDS.length})
            </button>
            <span className="text-slate-300 text-xs">·</span>
            <button type="button" onClick={clearAll}
              className="text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors">
              Clear all
            </button>
          </div>

          {/* Agent groups */}
          <div className="divide-y divide-slate-100">
            {CATEGORIES.map(({ name, color, bgColor, borderColor, Icon, agents }) => (
              <div key={name} className="px-4 py-3">
                <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-widest mb-2.5 ${bgColor} ${borderColor} ${color}`}>
                  <Icon size={10} className={color} />
                  {name}
                </div>
                <div className="grid grid-cols-1 gap-1">
                  {agents.map((agent) => {
                    const checked = selected.includes(agent.id)
                    return (
                      <button
                        key={agent.id}
                        type="button"
                        onClick={() => toggle(agent.id)}
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg border text-left transition-all ${
                          checked
                            ? 'bg-teal-50 border-teal-200'
                            : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        {checked
                          ? <CheckSquare size={15} className="text-teal-700 shrink-0" />
                          : <Square size={15} className="text-slate-300 shrink-0" />}
                        <div className="min-w-0">
                          <p className={`text-sm font-medium ${checked ? 'text-teal-800' : 'text-slate-700'}`}>
                            {agent.label}
                          </p>
                          <p className="text-[11px] text-slate-400 leading-snug truncate">{agent.desc}</p>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
