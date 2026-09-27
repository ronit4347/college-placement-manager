import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { createOffer, fetchOffers, issueOffer, respondToOffer, updateOfferStatus, type OfferRecord } from '../services/offers'
import { getErrorMessage } from '../utils/errors'

function offerReference(value: string | null) {
  if (!value) return '—'
  try {
    const parsed = new URL(value)
    if (parsed.protocol === 'https:' || parsed.protocol === 'http:') return <a className="text-brand hover:underline" href={parsed.href} target="_blank" rel="noreferrer">View reference</a>
  } catch { /* Non-URL references are shown as text. */ }
  return value
}

export default function OffersPage() {
  const { user } = useAuth()
  const [offers, setOffers] = useState<OfferRecord[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ application_id: '', salary: '', joining_date: '', expires_at: '', offer_letter_reference: '' })
  async function reload() { try { setOffers(await fetchOffers()); setError('') } catch (reason) { setError(getErrorMessage(reason, 'Could not load offers.')) } }
  useEffect(() => { void reload() }, [])
  async function action(work: () => Promise<unknown>) { setBusy(true); setError(''); try { await work(); await reload() } catch (reason) { setError(getErrorMessage(reason, 'Could not update offer.')) } finally { setBusy(false) } }
  async function submit(event: FormEvent) { event.preventDefault(); await action(() => createOffer({ application_id: Number(form.application_id), salary: Number(form.salary), joining_date: form.joining_date, expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : undefined, offer_letter_reference: form.offer_letter_reference || undefined })); setForm({ application_id: '', salary: '', joining_date: '', expires_at: '', offer_letter_reference: '' }) }
  const admin = user?.role === 'ADMIN'
  const student = user?.role === 'STUDENT'
  const title = admin ? 'Offer management' : student ? 'My offers' : 'Company offers'
  return <section className="space-y-6"><header><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Placement workflow</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1><p className="mt-2 text-sm text-muted">{admin ? 'Create offers for selected candidates and issue or expire them.' : student ? 'Review and respond to offers made to you.' : 'Offers associated with job drives for your company.'}</p></header>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {admin && <form onSubmit={(event) => void submit(event)} className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-panel sm:grid-cols-2 lg:grid-cols-5"><label className="form-label">Application ID<input required min="1" type="number" className="form-input mt-2" value={form.application_id} onChange={(event) => setForm({ ...form, application_id: event.target.value })} /></label><label className="form-label">Salary (INR)<input required min="0.01" step="0.01" type="number" className="form-input mt-2" value={form.salary} onChange={(event) => setForm({ ...form, salary: event.target.value })} /></label><label className="form-label">Joining date<input required type="date" className="form-input mt-2" value={form.joining_date} onChange={(event) => setForm({ ...form, joining_date: event.target.value })} /></label><label className="form-label">Expiry (optional)<input type="datetime-local" className="form-input mt-2" value={form.expires_at} onChange={(event) => setForm({ ...form, expires_at: event.target.value })} /></label><label className="form-label">Offer letter reference<input className="form-input mt-2" maxLength={2048} placeholder="Document URL or reference" value={form.offer_letter_reference} onChange={(event) => setForm({ ...form, offer_letter_reference: event.target.value })} /></label><button disabled={busy} className="primary-button sm:col-span-2 lg:col-span-5">Create draft offer</button></form>}
    {offers.length === 0 ? <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-muted">No offers found.</div> : <div className="space-y-4">{offers.map((offer) => <article key={offer.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-brand">{offer.company_name}</p><h2 className="mt-1 text-lg font-semibold">{offer.job_title}</h2><p className="mt-2 text-sm">{student ? 'Offer details' : `${offer.candidate_name} · ${offer.candidate_email}`}</p></div><span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">{offer.status}</span></div><dl className="mt-4 grid gap-3 border-t border-slate-100 pt-4 text-sm sm:grid-cols-3"><div><dt className="text-xs text-muted">Package</dt><dd className="mt-1 font-medium">{offer.currency} {offer.salary?.toLocaleString()}</dd></div><div><dt className="text-xs text-muted">Joining date</dt><dd className="mt-1 font-medium">{offer.joining_date || '—'}</dd></div><div><dt className="text-xs text-muted">Offer letter</dt><dd className="mt-1 font-medium">{offerReference(offer.offer_letter_reference)}</dd></div></dl>{student && offer.status === 'ISSUED' && <div className="mt-4 flex gap-3"><button disabled={busy} className="primary-button" onClick={() => void action(() => respondToOffer(offer.id, 'ACCEPTED'))}>Accept offer</button><button disabled={busy} className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-700" onClick={() => void action(() => respondToOffer(offer.id, 'DECLINED'))}>Decline</button></div>}{admin && offer.status === 'DRAFT' && <button disabled={busy} className="primary-button mt-4" onClick={() => void action(() => issueOffer(offer.id))}>Issue offer</button>}{admin && ['DRAFT', 'ISSUED'].includes(offer.status) && <button disabled={busy} className="ml-3 mt-4 rounded-lg border px-4 py-2 text-sm" onClick={() => void action(() => updateOfferStatus(offer.id, 'EXPIRED'))}>Expire offer</button>}{!student && <Link className="ml-3 mt-4 inline-block text-sm font-semibold text-brand hover:underline" to={`/applications/${offer.application_id}`}>Application details</Link>}</article>)}</div>}
  </section>
}
