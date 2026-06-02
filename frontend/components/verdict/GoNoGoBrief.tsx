import { ShieldAlert, ShieldCheck } from 'lucide-react'
import type { Finding } from '@/lib/types'

export function GoNoGoBrief({ findings }: { findings: Finding[] }) {
  const critical = findings.filter((f) => f.severity === 'critical').length
  const high     = findings.filter((f) => f.severity === 'high').length
  const medium   = findings.filter((f) => f.severity === 'medium').length
  const low      = findings.filter((f) => f.severity === 'low').length
  const isNoGo   = critical > 0 || high > 2

  return (
    <div className={`rounded-2xl overflow-hidden border ${isNoGo ? 'border-red-200' : 'border-emerald-200'}`}>
      {/* Hero */}
      <div className={`px-8 py-8 flex items-center gap-5 ${isNoGo ? 'bg-red-50' : 'bg-emerald-50'}`}>
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 shadow-sm ${
          isNoGo ? 'bg-red-100 border border-red-200' : 'bg-emerald-100 border border-emerald-200'
        }`}>
          {isNoGo
            ? <ShieldAlert size={24} className="text-red-500" />
            : <ShieldCheck size={24} className="text-emerald-600" />}
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">
            AI Determination
          </p>
          <h2 className={`text-4xl font-bold tracking-tight ${isNoGo ? 'text-red-600' : 'text-emerald-600'}`}>
            {isNoGo ? 'NO-GO' : 'GO'}
          </h2>
          <p className="text-sm text-slate-500 mt-1.5 max-w-md">
            {isNoGo
              ? `${critical} critical and ${high} high-severity findings require resolution before proceeding.`
              : `No blocking issues found across ${findings.length} finding${findings.length !== 1 ? 's' : ''}. Deal can proceed.`}
          </p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-4 divide-x divide-slate-100 border-t border-slate-100 bg-white">
        {[
          { label: 'Critical', count: critical, color: 'text-red-600',    bg: critical > 0 ? 'bg-red-50' : '' },
          { label: 'High',     count: high,     color: 'text-orange-600', bg: high > 0 ? 'bg-orange-50' : '' },
          { label: 'Medium',   count: medium,   color: 'text-amber-600',  bg: '' },
          { label: 'Low',      count: low,      color: 'text-slate-500',  bg: '' },
        ].map(({ label, count, color, bg }) => (
          <div key={label} className={`px-6 py-4 text-center ${bg}`}>
            <p className={`text-2xl font-bold ${color}`}>{count}</p>
            <p className="text-xs text-slate-400 mt-0.5">{label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
