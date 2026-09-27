import { FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { createCompanyRecruiter, fetchCompany, updateCompany, type Company } from '../services/companies'
import { getErrorMessage } from '../utils/errors'

export default function CompanyDetailsPage() {
  const { companyId } = useParams()
  const [company, setCompany] = useState<Company | null>(null)
  const [error, setError] = useState('')
  const [recruiter, setRecruiter] = useState({ full_name: '', email: '', initial_password: '' })
  const [saving, setSaving] = useState(false)

  async function refresh() { if (companyId) setCompany(await fetchCompany(Number(companyId))) }
  useEffect(() => { refresh().catch((reason: unknown) => setError(getErrorMessage(reason, 'Could not load this company.'))) }, [companyId])

  async function toggleStatus() {
    if (!company) return
    setError('')
    try { setCompany(await updateCompany(company.id, { is_active: !company.is_active })) }
    catch (reason) { setError(getErrorMessage(reason, 'Could not update company status.')) }
  }

  async function addRecruiter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!company) return
    setSaving(true); setError('')
    try { await createCompanyRecruiter(company.id, recruiter); setRecruiter({ full_name: '', email: '', initial_password: '' }); await refresh() }
    catch (reason) { setError(getErrorMessage(reason, 'Could not create the recruiter account.')) } finally { setSaving(false) }
  }

  if (!company) return <section><Link to="/admin/companies" className="text-sm font-medium text-brand hover:underline">← Companies</Link>{error ? <p role="alert" className="mt-5 text-sm text-red-700">{error}</p> : <p className="mt-5 text-sm text-muted">Loading company…</p>}</section>
  return <section className="space-y-6"><Link to="/admin/companies" className="text-sm font-medium text-brand hover:underline">← All companies</Link>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel sm:p-8"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Company details</p><div className="mt-2 flex flex-wrap items-center gap-3"><h1 className="text-3xl font-semibold tracking-tight">{company.name}</h1><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${company.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{company.is_active ? 'Active' : 'Inactive'}</span></div></div><div className="flex gap-2"><Link className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium" to={`/admin/companies/${company.id}/edit`}>Edit</Link><button className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium hover:bg-slate-50" onClick={toggleStatus}>{company.is_active ? 'Deactivate' : 'Activate'}</button></div></div><dl className="mt-8 grid gap-x-8 gap-y-6 sm:grid-cols-2">{[['Industry', company.industry], ['Location', company.location], ['Website', company.website], ['HR contact', company.hr_name], ['HR email', company.hr_email]].map(([label, value]) => <div key={label}><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm">{label === 'Website' && value ? <a className="text-brand hover:underline" href={String(value)} target="_blank" rel="noreferrer">{String(value)}</a> : value || '—'}</dd></div>)}</dl>{company.description && <div className="mt-6 border-t border-slate-100 pt-5"><h2 className="text-sm font-semibold">About</h2><p className="mt-2 whitespace-pre-line text-sm leading-6 text-muted">{company.description}</p></div>}</div>
    <div className="grid gap-6 lg:grid-cols-2"><section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel"><h2 className="text-lg font-semibold">Recruiters</h2><p className="mt-1 text-sm text-muted">Recruiter accounts are linked to this company.</p>{company.recruiters.length ? <ul className="mt-4 divide-y divide-slate-100">{company.recruiters.map((item) => <li key={item.user_id} className="flex items-center justify-between py-3"><div><p className="text-sm font-medium">{item.full_name}</p><p className="text-sm text-muted">{item.email}</p></div><span className="text-xs text-muted">{item.is_active ? 'Active' : 'Inactive'}</span></li>)}</ul> : <p className="mt-5 rounded-lg bg-slate-50 p-4 text-sm text-muted">No recruiter accounts are associated yet.</p>}</section>
    <form onSubmit={addRecruiter} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-panel"><div><h2 className="text-lg font-semibold">Add recruiter</h2><p className="mt-1 text-sm text-muted">Creates a recruiter login already associated with this company.</p></div>{!company.is_active && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">Activate the company before adding recruiters.</p>}<label className="form-label">Full name<input className="form-input mt-2" required minLength={2} maxLength={160} value={recruiter.full_name} onChange={(event) => setRecruiter({ ...recruiter, full_name: event.target.value })} /></label><label className="form-label">Email<input className="form-input mt-2" type="email" required value={recruiter.email} onChange={(event) => setRecruiter({ ...recruiter, email: event.target.value })} /></label><label className="form-label">Temporary password<input className="form-input mt-2" type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={recruiter.initial_password} onChange={(event) => setRecruiter({ ...recruiter, initial_password: event.target.value })} /><span className="mt-1 block text-xs text-muted">At least 12 characters. Share securely with the recruiter.</span></label><button className="primary-button inline-flex" disabled={saving || !company.is_active}>{saving ? 'Creating…' : 'Create recruiter account'}</button></form></div>
  </section>
}
