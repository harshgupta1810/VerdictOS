'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Upload, FileText, X, Loader2, Save, ShieldCheck } from 'lucide-react'
import { api } from '@/lib/api'
import { AgentSelector } from './AgentSelector'

export function MatterCreateForm() {
  const router = useRouter()
  const [clientId, setClientId] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [selectedAgents, setSelectedAgents] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((accepted: File[]) => setFiles((prev) => [...prev, ...accepted]), [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    multiple: true,
  })

  const removeFile = (i: number) => setFiles((prev) => prev.filter((_, idx) => idx !== i))

  const saveDraft = () => {
    localStorage.setItem('verdictos:new-matter-draft', JSON.stringify({
      clientId,
      selectedAgents,
      savedAt: new Date().toISOString(),
    }))
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!clientId.trim()) { setError('Client / matter name is required'); return }
    if (files.length === 0) { setError('At least one document is required'); return }
    setError(null)
    setLoading(true)
    try {
      const { paths } = await api.uploadDocuments(files)
      const { deal_id } = await api.createMatter({
        client_id: clientId.trim(),
        document_paths: paths,
        selected_agents: selectedAgents.length > 0 ? selectedAgents : undefined,
      })
      router.push(`/matters/${deal_id}/status`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 pb-24 lg:pb-0">
      <section className="card p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-5 mb-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-teal-700">Matter basics</p>
            <h2 className="text-lg font-bold text-slate-950 mt-1">Name and identify the matter</h2>
            <p className="text-sm text-slate-500 mt-1">Use the client, target, or transaction name your team will search for later.</p>
          </div>
          <ShieldCheck size={20} className="text-teal-700 shrink-0 mt-1" />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_260px] gap-5">
          <div className="space-y-1.5">
            <label className="block text-sm font-semibold text-slate-800">Matter name <span className="text-red-600">*</span></label>
            <input
              type="text"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="e.g. ACME Corp Acquisition 2026"
              className="w-full border border-slate-300 rounded-lg px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-600/20 focus:border-teal-700 transition-all bg-white"
            />
            <p className="text-xs text-slate-500">This appears in the matter list and audit trail.</p>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs font-semibold text-slate-700">Default workflow</p>
            <p className="text-xs text-slate-500 leading-relaxed mt-1">
              Retrieval, specialist review, debate, judge synthesis, verdict, escalations, and audit logging.
            </p>
          </div>
        </div>
      </section>

      <section className="card p-5 sm:p-6">
        <div className="border-b border-slate-100 pb-5 mb-5">
          <p className="text-xs font-bold uppercase tracking-widest text-teal-700">Documents</p>
          <h2 className="text-lg font-bold text-slate-950 mt-1">Upload source files</h2>
          <p className="text-sm text-slate-500 mt-1">Add the materials the review pipeline should inspect. PDF and DOCX files are supported.</p>
        </div>

        <div
          {...getRootProps()}
          className={`rounded-lg p-8 sm:p-10 text-center cursor-pointer transition-all border-2 border-dashed ${
            isDragActive
              ? 'border-teal-600 bg-teal-50'
              : 'border-slate-300 hover:border-teal-500 bg-slate-50 hover:bg-white'
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-3">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${isDragActive ? 'bg-teal-100' : 'bg-white border border-slate-200'}`}>
              <Upload size={20} className={isDragActive ? 'text-teal-700' : 'text-slate-500'} />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">
                {isDragActive ? 'Drop files to add them' : 'Drag and drop files here'}
              </p>
              <p className="text-xs text-slate-500 mt-1">or click to browse your computer</p>
            </div>
          </div>
        </div>

        {files.length > 0 && (
          <ul className="space-y-2 mt-5">
            {files.map((f, i) => (
              <li key={i} className="flex items-center gap-3 bg-white border border-slate-200 rounded-lg px-3 py-2.5">
                <FileText size={15} className="text-teal-700 shrink-0" />
                <span className="truncate text-sm text-slate-700 flex-1">{f.name}</span>
                <span className="text-xs text-slate-400">{(f.size / 1024).toFixed(0)} KB</span>
                <button type="button" onClick={() => removeFile(i)} className="text-slate-300 hover:text-red-500 transition-colors" aria-label={`Remove ${f.name}`}>
                  <X size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card p-5 sm:p-6">
        <div className="border-b border-slate-100 pb-5 mb-5">
          <p className="text-xs font-bold uppercase tracking-widest text-teal-700">Review scope</p>
          <h2 className="text-lg font-bold text-slate-950 mt-1">Choose specialist agents</h2>
          <p className="text-sm text-slate-500 mt-1">Leave this on automatic unless the matter needs a specific review team.</p>
        </div>
        <AgentSelector selected={selectedAgents} onChange={setSelectedAgents} />
      </section>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">{error}</p>
      )}

      <div className="sticky bottom-0 z-10 -mx-5 sm:-mx-6 lg:mx-0 bg-white/95 backdrop-blur border-t border-slate-200 lg:border lg:rounded-xl px-5 sm:px-6 py-3 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <p className="text-xs text-slate-500">
            Required: matter name and at least one document.
          </p>
          <div className="flex items-center gap-2">
            <Link href="/matters" className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
              Cancel
            </Link>
            <button
              type="button"
              onClick={saveDraft}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <Save size={14} /> Save Draft
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-5 py-2 rounded-lg transition-colors text-sm shadow-sm"
            >
              {loading ? <><Loader2 size={15} className="animate-spin" /> Creating Matter...</> : 'Create Matter'}
            </button>
          </div>
        </div>
      </div>
    </form>
  )
}
