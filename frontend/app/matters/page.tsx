import Link from 'next/link'
import { Plus, Upload, Brain, ShieldCheck, ArrowRight, Search, GitBranch, Lock, Zap } from 'lucide-react'
import { MatterTable } from '@/components/matters/MatterTable'
import { LogoMark } from '@/components/ui/Logo'

const STEPS = [
  {
    n: '01', icon: Upload,
    title: 'Upload your documents',
    desc: 'Drag in your M&A contracts, disclosure schedules, and due diligence files — PDF or DOCX. The pipeline starts immediately.',
  },
  {
    n: '02', icon: Brain,
    title: '16 agents run in parallel',
    desc: 'Specialist agents for IP, finance, regulatory, tax, cyber, HR, and more analyse your documents simultaneously — each focused on the risks in their domain.',
  },
  {
    n: '03', icon: ShieldCheck,
    title: 'Six personas debate every finding',
    desc: 'A Proponent, Critic, Devil\'s Advocate, Valuation Skeptic, and two more challenge each conclusion over up to three adversarial rounds. Only source-verified findings reach the verdict.',
  },
]

const FEATURES = [
  {
    icon: Zap,
    title: '16 agents running in parallel',
    desc: 'IP, finance, regulatory, tax, privacy, cyber, HR, governance, and more — all run simultaneously. A matter that would take days of manual review is covered in one pipeline run.',
    color: 'text-teal-700', bg: 'bg-teal-50 border-teal-100',
  },
  {
    icon: GitBranch,
    title: 'Adversarial debate, not one opinion',
    desc: 'Every finding is challenged by six adversarial personas across three rounds. Contradictions are flagged, weak claims are dropped, and only the evidence-backed conclusions survive to the verdict.',
    color: 'text-blue-600', bg: 'bg-blue-50 border-blue-100',
  },
  {
    icon: Search,
    title: 'Every answer traced to source',
    desc: 'Findings link to exact document passages — not paraphrases or summaries. You can read the sentence behind every conclusion before you decide.',
    color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-100',
  },
  {
    icon: Lock,
    title: 'Human oversight at every stage',
    desc: 'Contested findings escalate for expert review. Every decision is logged in an immutable audit trail so your team always knows what was checked, who decided, and why.',
    color: 'text-sky-700', bg: 'bg-sky-50 border-sky-100',
  },
]

export default function MattersPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <LogoMark size={28} />
            <span className="text-sm font-bold text-slate-800 tracking-tight">VerdictOS</span>
          </div>
          <Link href="/matters/new"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 transition-colors shadow-sm">
            <Plus size={13} /> Open New Matter
          </Link>
        </div>
      </header>

      <div className="flex-1 max-w-6xl mx-auto w-full px-6">
        {/* Hero */}
        <div className="py-14 border-b border-slate-100">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-teal-50 border border-teal-100 rounded-full text-xs font-semibold text-teal-700 mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-600" />
              Autonomous M&A Due Diligence
            </div>
            <h1 className="text-4xl font-bold text-slate-900 leading-tight tracking-tight">
              A calmer way to verify<br />
              <span className="text-teal-700">high-stakes documents.</span>
            </h1>
            <p className="mt-4 text-lg text-slate-500 leading-relaxed max-w-xl">
              VerdictOS uses a multi-agent pipeline where 16 specialists — covering IP, finance,
              regulatory, tax, cyber, and more — run in parallel across your matter. Each finding
              is source-verified and challenged through structured debate before it reaches the
              verdict, so your team reviews evidence, not assumptions.
            </p>
            <div className="flex items-center gap-3 mt-8">
              <Link href="/matters/new"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-sm font-semibold transition-colors shadow-sm">
                Open a new matter <ArrowRight size={15} />
              </Link>
              <span className="text-xs text-slate-400">Takes 60 seconds to set up</span>
            </div>
          </div>
        </div>

        {/* How it works */}
        <div className="py-12 border-b border-slate-100">
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-8">How it works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {STEPS.map(({ n, icon: Icon, title, desc }) => (
              <div key={n} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className="w-9 h-9 rounded-lg bg-teal-700 text-white flex items-center justify-center shrink-0 shadow-sm">
                    <Icon size={16} />
                  </div>
                  <div className="flex-1 w-px bg-slate-100 mt-3 hidden md:block" />
                </div>
                <div className="pb-6">
                  <span className="text-[10px] font-bold text-teal-700 tracking-widest">{n}</span>
                  <h3 className="text-sm font-semibold text-slate-800 mt-0.5 mb-1.5">{title}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Features */}
        <div className="py-12 border-b border-slate-100">
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-8">Why VerdictOS</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {FEATURES.map(({ icon: Icon, title, desc, color, bg }) => (
              <div key={title} className={`card p-5 border ${bg} flex gap-4`}>
                <div className={`w-9 h-9 rounded-lg ${bg} border flex items-center justify-center shrink-0`}>
                  <Icon size={17} className={color} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 mb-1">{title}</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Matters list */}
        <div className="py-10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Your Matters</h2>
              <p className="text-sm text-slate-500 mt-0.5">Active and completed due diligence matters</p>
            </div>
            <Link href="/matters/new"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-100 transition-colors">
              <Plus size={13} /> Open Matter
            </Link>
          </div>
          <MatterTable />
        </div>
      </div>
    </div>
  )
}
