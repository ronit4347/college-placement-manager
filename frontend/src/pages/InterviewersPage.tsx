import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { createInterviewer, fetchInterviewers, setInterviewerActive } from '../services/adminUsers'
import type { InterviewerCredentials, InterviewerRecord } from '../services/adminUsers'
import { getErrorMessage } from '../utils/errors'

const emptyForm: InterviewerCredentials = { full_name: '', email: '', initial_password: '' }

export default function InterviewersPage() {
  const [interviewers, setInterviewers] = useState<InterviewerRecord[]>([])
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setInterviewers(await fetchInterviewers()) }
    catch (reason: unknown) { setError(getErrorMessage(reason, 'Could not load interviewer accounts.')) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const created = await createInterviewer(form)
      setInterviewers((current) => [...current, created].sort((left, right) => left.full_name.localeCompare(right.full_name)))
      setForm(emptyForm)
      setNotice(`${created.full_name} can now sign in as an interviewer.`)
    } catch (reason: unknown) {
      setError(getErrorMessage(reason, 'Could not create the interviewer account.'))
    } finally { setSaving(false) }
  }

  async function toggleActive(item: InterviewerRecord) {
    setBusyId(item.id)
    setError('')
    setNotice('')
    try {
      const updated = await setInterviewerActive(item.id, !item.is_active)
      setInterviewers((current) => current.map((candidate) => candidate.id === item.id ? updated : candidate))
      setNotice(`${item.full_name}'s account is ${updated.is_active ? 'active' : 'suspended'}.`)
    } catch (reason: unknown) {
      setError(getErrorMessage(reason, 'Could not update this interviewer account.'))
    } finally { setBusyId(null) }
  }

  return <section className="space-y-6">
    <header><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Administration</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Interviewer accounts</h1><p className="mt-2 max-w-2xl text-sm text-muted">Create and suspend interviewer access. New accounts receive the INTERVIEWER role only.</p></header>

    <form onSubmit={(event) => void submit(event)} className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-panel sm:grid-cols-2 lg:grid-cols-4">
      <label className="form-label">Full name<input className="form-input mt-2" required minLength={2} maxLength={160} value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} /></label>
      <label className="form-label">Email address<input className="form-input mt-2" type="email" autoComplete="off" required maxLength={320} value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
      <label className="form-label">Initial password<input className="form-input mt-2" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={form.initial_password} onChange={(event) => setForm({ ...form, initial_password: event.target.value })} /><span className="mt-1 block text-xs font-normal text-muted">At least 12 characters. It is never returned by the API.</span></label>
      <div className="flex items-end"><button className="primary-button w-full" type="submit" disabled={saving}>{saving ? 'Creating account…' : 'Create interviewer'}</button></div>
    </form>

    {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error} <button type="button" className="ml-2 font-semibold underline" onClick={() => void load()}>Retry</button></p>}
    {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}

    {loading ? <p role="status" className="text-sm text-muted">Loading interviewer accounts…</p> : interviewers.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center"><h2 className="font-semibold">No interviewer accounts yet</h2><p className="mt-2 text-sm text-muted">Create an account above to make an interviewer available for assignments.</p></div> : <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="bg-slate-50"><tr><th className="px-5 py-3">Interviewer</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Created</th><th className="px-5 py-3"><span className="sr-only">Account action</span></th></tr></thead><tbody className="divide-y divide-slate-100">{interviewers.map((item) => <tr key={item.id} className="hover:bg-slate-50"><td className="px-5 py-4"><p className="font-semibold">{item.full_name}</p><p className="text-xs text-muted">{item.email}</p></td><td className="px-5 py-4"><span className="rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-800">{item.role}</span></td><td className="px-5 py-4"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${item.is_active ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}>{item.is_active ? 'Active' : 'Suspended'}</span></td><td className="px-5 py-4 text-muted">{new Date(item.created_at).toLocaleDateString()}</td><td className="px-5 py-4 text-right"><button type="button" className="button button-quiet" disabled={busyId === item.id} onClick={() => void toggleActive(item)}>{busyId === item.id ? 'Saving…' : item.is_active ? 'Suspend' : 'Reactivate'}<span className="sr-only"> {item.full_name}</span></button></td></tr>)}</tbody></table></div></div>}
  </section>
}
