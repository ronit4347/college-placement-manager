import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { createCompany, fetchCompany, updateCompany, type CompanyInput } from '../services/companies'
import { getErrorMessage } from '../utils/errors'

const empty: CompanyInput = { name: '', industry: '', location: '', website: '', hr_name: '', hr_email: '', description: '' }

export default function CompanyFormPage() {
  const { companyId } = useParams()
  const navigate = useNavigate()
  const editing = Boolean(companyId)
  const [values, setValues] = useState<CompanyInput>(empty)
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!companyId) return
    fetchCompany(Number(companyId)).then((company) => setValues({ name: company.name, industry: company.industry || '', location: company.location || '', website: company.website || '', hr_name: company.hr_name || '', hr_email: company.hr_email || '', description: company.description || '' }))
      .catch((reason: unknown) => setError(getErrorMessage(reason, 'Could not load this company.'))).finally(() => setLoading(false))
  }, [companyId])

  function change(field: keyof CompanyInput, value: string) { setValues((current) => ({ ...current, [field]: value || null })) }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      const payload = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, typeof value === 'string' ? value.trim() || null : value])) as CompanyInput
      const company = editing ? await updateCompany(Number(companyId), payload) : await createCompany(payload)
      navigate(`/admin/companies/${company.id}`, { replace: true })
    } catch (reason) { setError(getErrorMessage(reason, 'Could not save the company.')) } finally { setSaving(false) }
  }

  if (loading) return <p className="text-sm text-muted">Loading company…</p>
  const fields: { key: keyof CompanyInput; label: string; type?: string }[] = [
    { key: 'name', label: 'Company name' }, { key: 'industry', label: 'Industry' }, { key: 'location', label: 'Location' },
    { key: 'website', label: 'Website', type: 'url' }, { key: 'hr_name', label: 'HR contact name' }, { key: 'hr_email', label: 'HR contact email', type: 'email' },
  ]
  return <section className="mx-auto max-w-3xl space-y-6"><Link to={editing ? `/admin/companies/${companyId}` : '/admin/companies'} className="text-sm font-medium text-brand hover:underline">← Back to companies</Link><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Company management</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{editing ? 'Edit company' : 'Add a company'}</h1></div><form onSubmit={submit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-panel sm:p-8">{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="grid gap-5 sm:grid-cols-2">{fields.map(({ key, label, type }) => <label key={key} className="form-label">{label}<input className="form-input mt-2" type={type || 'text'} value={values[key] || ''} onChange={(event) => change(key, event.target.value)} required={key === 'name'} maxLength={key === 'name' ? 200 : undefined} /></label>)}</div><label className="form-label">Description<textarea className="form-input mt-2 min-h-32" maxLength={10000} value={values.description || ''} onChange={(event) => change('description', event.target.value)} /></label><div className="flex justify-end gap-3"><Link className="rounded-lg border border-slate-200 px-4 py-3 text-sm font-medium" to={editing ? `/admin/companies/${companyId}` : '/admin/companies'}>Cancel</Link><button className="primary-button inline-flex" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Create company'}</button></div></form></section>
}
