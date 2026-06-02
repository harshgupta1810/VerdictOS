import Link from 'next/link'
import { ChevronLeft, FileText, FolderOpen, ShieldCheck } from 'lucide-react'
import { MatterCreateForm } from '@/components/matters/MatterCreateForm'
import { LogoMark } from '@/components/ui/Logo'

const SECTIONS = [
  { icon: FolderOpen, label: 'Matter basics' },
  { icon: FileText, label: 'Documents' },
  { icon: ShieldCheck, label: 'Review scope' },
]

export default function NewMatterPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-5 sm:px-6 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <LogoMark size={26} />
            <span className="text-sm font-bold text-slate-800 tracking-tight">VerdictOS</span>
            <span className="text-slate-300 mx-1 hidden sm:inline">/</span>
            <span className="text-sm text-slate-500 truncate hidden sm:inline">New Matter</span>
          </div>
          <Link
            href="/matters"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ChevronLeft size={14} /> Matters
          </Link>
        </div>
      </header>

      <main className="flex-1 w-full max-w-7xl mx-auto px-5 sm:px-6 py-8 lg:py-10">
        <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-8 items-start">
          <aside className="lg:sticky lg:top-20 space-y-6">
            <div>
              <Link
                href="/matters"
                className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 mb-5 transition-colors"
              >
                <ChevronLeft size={13} /> Back to Matters
              </Link>
              <p className="text-xs font-bold uppercase tracking-widest text-teal-700">Matter intake</p>
              <h1 className="text-3xl font-bold text-slate-950 tracking-tight mt-2">New Matter</h1>
              <p className="text-sm text-slate-600 leading-relaxed mt-3">
                Create the matter, upload source documents, and choose the review scope in one clear workspace.
              </p>
            </div>

            <ol className="card overflow-hidden">
              {SECTIONS.map(({ icon: Icon, label }, index) => (
                <li key={label} className="flex items-center gap-3 px-4 py-3 border-b border-slate-100 last:border-b-0">
                  <span className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-700">
                    <Icon size={15} />
                  </span>
                  <div>
                    <p className="text-[10px] font-bold tracking-widest text-slate-400">STEP {index + 1}</p>
                    <p className="text-sm font-semibold text-slate-800">{label}</p>
                  </div>
                </li>
              ))}
            </ol>

            <div className="card-subtle p-4">
              <p className="text-xs font-semibold text-slate-700">Before you create</p>
              <p className="text-xs text-slate-500 leading-relaxed mt-1">
                PDF and DOCX files are accepted. The pipeline starts after the matter is created.
              </p>
            </div>
          </aside>

          <div className="min-w-0">
            <MatterCreateForm />
          </div>
        </div>
      </main>
    </div>
  )
}
