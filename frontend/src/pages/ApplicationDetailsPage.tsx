import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { changeApplicationStatus, fetchApplication, type ApplicationRecord, type ApplicationStatus } from '../services/applications'
import { getErrorMessage } from '../utils/errors'

const nextStatuses: Record<ApplicationStatus, ApplicationStatus[]> = {
  APPLIED: ['SHORTLISTED', 'REJECTED'],
  SHORTLISTED: ['INTERVIEW', 'REJECTED'],
  INTERVIEW: ['SELECTED', 'REJECTED'],
  SELECTED: ['OFFERED'],
  OFFERED: ['JOINED'],
  REJECTED: [],
  JOINED: [],
}

export default function ApplicationDetailsPage() {
  const { applicationId } = useParams()
  const { user } = useAuth()
  const [application, setApplication] = useState<ApplicationRecord | null>(null)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!applicationId) return
    fetchApplication(Number(applicationId))
      .then(setApplication)
      .catch((reason: unknown) => setError(getErrorMessage(reason, 'Could not load this application.')))
      .finally(() => setLoading(false))
  }, [applicationId])

  async function transition(status: ApplicationStatus) {
    if (!application) return
    setSaving(true); setError('')
    try { setApplication(await changeApplicationStatus(application.id, status, note)); setNote('') }
    catch (reason) { setError(getErrorMessage(reason, 'Could not update application status.')) }
    finally { setSaving(false) }
  }

  if (loading) return <p className="text-sm text-muted">Loading application…</p>
  if (!application) return <section className="space-y-4"><p role="alert" className="text-sm text-red-700">{error || 'Application not found.'}</p><Link to="/applications" className="text-sm font-medium text-brand hover:underline">← Applications</Link></section>
  const available = nextStatuses[application.status]
  return <section className="space-y-6"><Link to="/applications" className="text-sm font-medium text-brand hover:underline">← Applications</Link>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel sm:p-8"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">{application.company_name}</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{application.drive_title}</h1><p className="mt-2 text-sm text-muted">Application #{application.id}</p></div><span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-800">{application.status}</span></div><dl className="mt-8 grid gap-5 border-y border-slate-100 py-6 sm:grid-cols-2"><div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Student</dt><dd className="mt-1 text-sm font-medium">{application.student_name}</dd></div><div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Email</dt><dd className="mt-1 text-sm">{application.student_email}</dd></div><div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Roll number</dt><dd className="mt-1 text-sm">{application.roll_number || '—'}</dd></div><div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Branch / CGPA</dt><dd className="mt-1 text-sm">{application.branch || '—'} · {application.cgpa ?? '—'}</dd></div><div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Applied</dt><dd className="mt-1 text-sm">{new Date(application.applied_at).toLocaleString()}</dd></div></dl>{application.cover_letter && <section className="mt-6"><h2 className="text-sm font-semibold">Cover letter</h2><p className="mt-2 whitespace-pre-line text-sm leading-6 text-muted">{application.cover_letter}</p></section>}</div>
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel sm:p-8"><h2 className="text-lg font-semibold">Status timeline</h2><ol className="mt-5 space-y-0">{application.timeline.map((event, index) => <li key={event.id} className="relative flex gap-4 pb-6 last:pb-0"><span className="relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-blue-50 text-xs font-bold text-blue-700">{index + 1}</span>{index < application.timeline.length - 1 && <span className="absolute left-4 top-8 h-full w-px bg-slate-200" />}<div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold">{event.to_status}</p><time className="text-xs text-muted">{new Date(event.created_at).toLocaleString()}</time></div>{event.from_status && <p className="mt-1 text-xs text-muted">Changed from {event.from_status}</p>}{event.note && <p className="mt-2 text-sm text-slate-700">{event.note}</p>}{event.actor_name && <p className="mt-1 text-xs text-muted">By {event.actor_name}</p>}</div></li>)}</ol></section>
    {user?.role === 'ADMIN' && available.length > 0 && <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel"><h2 className="text-lg font-semibold">Manage application</h2><label className="form-label mt-4 block">Internal note (optional)<textarea className="form-input mt-2 min-h-20" maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} /></label><div className="mt-4 flex flex-wrap gap-3">{available.map((status) => <button key={status} disabled={saving} onClick={() => transition(status)} className={status === 'REJECTED' ? 'rounded-lg border border-red-200 px-4 py-2.5 text-sm font-medium text-red-700' : 'primary-button inline-flex'}>{saving ? 'Saving…' : status === 'SHORTLISTED' ? 'Shortlist' : status === 'REJECTED' ? 'Reject' : `Mark ${status.toLowerCase()}`}</button>)}</div></section>}
  </section>
}
