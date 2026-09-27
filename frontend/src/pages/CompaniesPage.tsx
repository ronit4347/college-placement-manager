import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Pagination from '../components/Pagination'
import { fetchCompanies, type Company } from '../services/companies'
import { getErrorMessage } from '../utils/errors'

const PAGE_SIZE = 20

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [name, setName] = useState('')
  const [industry, setIndustry] = useState('')
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    fetchCompanies({ name: name || undefined, industry: industry || undefined, is_active: status === 'all' ? undefined : status === 'active', limit: PAGE_SIZE + 1, offset: (page - 1) * PAGE_SIZE })
      .then((items) => { if (active) { setCompanies(items); setError('') } })
      .catch((reason: unknown) => { if (active) setError(getErrorMessage(reason, 'Could not load companies.')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [name, industry, status, page, reload])

  function resetPage(change: () => void) { change(); setPage(1) }

  return <section className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Administration</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Companies</h1><p className="mt-2 text-sm text-muted">Search employers by name and industry, or narrow the list by status.</p></div><Link className="primary-button inline-flex" to="/admin/companies/new">Add company</Link></div>
    <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-3"><label className="form-label">Company name<input className="form-input mt-2" value={name} onChange={(event) => resetPage(() => setName(event.target.value))} placeholder="Search company name" /></label><label className="form-label">Industry<input className="form-input mt-2" value={industry} onChange={(event) => resetPage(() => setIndustry(event.target.value))} placeholder="Filter industry" /></label><label className="form-label">Status<select className="form-input mt-2" value={status} onChange={(event) => resetPage(() => setStatus(event.target.value))}><option value="all">All companies</option><option value="active">Active</option><option value="inactive">Inactive</option></select></label></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error} <button className="ml-2 font-semibold underline" onClick={() => setReload((value) => value + 1)}>Retry</button></p>}
    {loading ? <p role="status" className="text-sm text-muted">Loading companies…</p> : companies.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-muted">No companies match these filters.</div> : <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Company</th><th className="px-5 py-3">Industry</th><th className="px-5 py-3">Location</th><th className="px-5 py-3">Recruiters</th><th className="px-5 py-3">Status</th></tr></thead><tbody className="divide-y divide-slate-100">{companies.slice(0, PAGE_SIZE).map((company) => <tr key={company.id} className="hover:bg-slate-50"><td className="px-5 py-4"><Link className="font-semibold text-brand hover:underline" to={`/admin/companies/${company.id}`}>{company.name}</Link></td><td className="px-5 py-4">{company.industry || '—'}</td><td className="px-5 py-4">{company.location || '—'}</td><td className="px-5 py-4">{company.recruiters.length}</td><td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${company.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{company.is_active ? 'Active' : 'Inactive'}</span></td></tr>)}</tbody></table></div></div>}
    {!loading && companies.length > 0 && <Pagination page={page} canGoNext={companies.length > PAGE_SIZE} onPageChange={setPage} />}
  </section>
}
