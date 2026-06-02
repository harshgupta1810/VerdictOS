import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { LogoMark } from '@/components/ui/Logo'
import { PipelineIcon, VerdictIcon, EscalationIcon, AuditIcon } from '@/components/ui/icons'

const NAV = [
  { href: 'status',      label: 'Pipeline',    Icon: PipelineIcon    },
  { href: 'verdict',     label: 'Verdict',     Icon: VerdictIcon     },
  { href: 'escalations', label: 'Escalations', Icon: EscalationIcon  },
  { href: 'audit',       label: 'Audit Trail', Icon: AuditIcon       },
]

export default async function MatterLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 shrink-0 sticky top-0 h-screen flex flex-col bg-white border-r border-slate-200 z-20">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-slate-100">
          <Link href="/matters" className="flex items-center gap-2.5 group">
            <LogoMark size={30} />
            <span className="text-sm font-bold text-slate-800 tracking-tight group-hover:text-slate-900 transition-colors">
              VerdictOS
            </span>
          </Link>
        </div>

        {/* Back + Matter ID */}
        <div className="px-4 py-4 border-b border-slate-100">
          <Link href="/matters"
            className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors mb-3">
            <ChevronLeft size={12} /> All Matters
          </Link>
          <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-widest mb-0.5">Matter ID</p>
            <p className="font-mono text-xs text-slate-600 truncate">{id.slice(0, 16)}…</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ href, label, Icon }) => (
            <Link key={href} href={`/matters/${id}/${href}`}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-all group">
              <Icon size={18} className="shrink-0 group-hover:text-indigo-600 transition-colors" />
              {label}
            </Link>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-slate-100">
          <p className="text-[10px] text-slate-400 text-center">M&A Due Diligence Engine</p>
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <main className="max-w-4xl mx-auto px-8 py-8">{children}</main>
      </div>
    </div>
  )
}
