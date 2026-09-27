import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { fetchJobDrive, fetchJobDriveEligibility, transitionJobDrive, type EligibilityResult, type JobDrive } from '../services/jobDrives'
import { fetchApplications, submitApplication, type ApplicationRecord } from '../services/applications'
import { getErrorMessage } from '../utils/errors'

function StudentApplicationPanel({ driveId, deadline }: { driveId: string; deadline: string | null }) {
  const [result, setResult] = useState<EligibilityResult | null>(null)
  const [application, setApplication] = useState<ApplicationRecord | null>(null)
  const [error, setError] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [notice, setNotice] = useState('')
  useEffect(() => {
    let mounted = true
    setResult(null)
    setError(false)
    Promise.all([fetchJobDriveEligibility(Number(driveId)), fetchApplications({ job_drive_id: Number(driveId) })])
      .then(([eligibility, applications]) => {
        if (mounted) { setResult(eligibility); setApplication(applications[0] || null) }
      })
      .catch(() => mounted && setError(true))
    return () => { mounted = false }
  }, [driveId])

  async function apply() {
    setSubmitting(true); setNotice('')
    try {
      setApplication(await submitApplication(Number(driveId)))
      setNotice('Your application was submitted successfully.')
    } catch {
      setNotice('Could not submit your application. Refresh the eligibility check and try again.')
    } finally { setSubmitting(false) }
  }

  const deadlinePassed = deadline !== null && Date.parse(deadline) <= Date.now()

  return <section aria-live="polite" className={`rounded-2xl border p-5 ${result?.eligible ? 'border-emerald-200 bg-emerald-50' : result ? 'border-rose-200 bg-rose-50' : 'border-slate-200 bg-white'}`}>
    {error ? <p className="text-sm text-muted">Eligibility is unavailable right now.</p> : !result ? <p className="text-sm text-muted">Checking eligibility…</p> : <>
      <h2 className={`text-lg font-semibold ${result.eligible ? 'text-emerald-800' : 'text-rose-800'}`}>{result.eligible ? '✓ Eligible' : '✗ Not Eligible'}</h2>
      {result.reasons.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">{result.reasons.map((reason, index) => <li key={`${index}-${reason}`}>{reason}</li>)}</ul>}
      {application ? <div className="mt-4 flex flex-wrap items-center gap-3"><span className="text-sm font-medium">Application status: {application.status}</span><Link className="text-sm font-semibold text-brand hover:underline" to={`/applications/${application.id}`}>View application</Link></div> : <div className="mt-4 flex flex-wrap items-center gap-3"><button className="primary-button inline-flex" disabled={!result.eligible || deadlinePassed || submitting} onClick={apply}>{submitting ? 'Submitting…' : 'Apply for this role'}</button>{deadlinePassed && <span className="text-sm text-rose-700">The application deadline has passed.</span>}</div>}
      {notice && <p role="status" className="mt-3 text-sm text-slate-700">{notice}</p>}
    </>}
  </section>
}

export default function JobDriveDetailsPage() {
  const { driveId } = useParams()
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN'
  const root = isAdmin ? '/admin/job-drives' : user?.role === 'RECRUITER' ? '/recruiter/job-drives' : '/student/job-drives'
  const [drive, setDrive] = useState<JobDrive | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() { if (driveId) setDrive(await fetchJobDrive(Number(driveId))) }
  useEffect(() => { refresh().catch((reason: unknown) => setError(getErrorMessage(reason, 'Could not load this job drive.'))) }, [driveId])

  async function changeStatus(action: 'publish' | 'close' | 'cancel') {
    if (!drive) return
    setBusy(true); setError('')
    try { setDrive(await transitionJobDrive(drive.id, action)) }
    catch (reason) { setError(getErrorMessage(reason, 'Could not change job drive status.')) }
    finally { setBusy(false) }
  }

  if (!drive) return <section><Link to={root} className="text-sm font-medium text-brand hover:underline">← Job drives</Link>{error ? <p role="alert" className="mt-5 text-sm text-red-700">{error}</p> : <p className="mt-5 text-sm text-muted">Loading job drive…</p>}</section>
  const terminal = drive.status === 'CLOSED' || drive.status === 'CANCELLED'
  const deadline = drive.application_deadline ? new Date(drive.application_deadline).toLocaleString() : 'Not set'
  return <section className="job-detail-page">
    <Link to={root} className="job-detail-breadcrumb">← All job drives</Link>
    {error && <p role="alert" className="job-detail-error">{error}</p>}
    <div className={`job-detail-columns${user?.role === 'STUDENT' ? ' has-application-panel' : ''}`}>
      <article className="job-detail-main">
        <header className="job-detail-hero"><div className="job-detail-company-mark">{drive.company_name.slice(0, 1).toUpperCase()}</div><div className="job-detail-title"><p>{drive.company_name}</p><h1>{drive.title}</h1><span>{drive.location || 'Location not specified'}{drive.employment_type ? ` · ${drive.employment_type.replace('_', ' ').toLowerCase()}` : ''}</span></div><span className={`status-pill ${drive.status === 'PUBLISHED' ? 'status-live' : drive.status === 'DRAFT' ? 'status-pending' : 'status-neutral'}`}>{drive.status.toLowerCase()}</span></header>
        <dl className="job-detail-facts"><div><dt>Compensation</dt><dd>{drive.package_min ?? '—'}{drive.package_max !== null ? `–${drive.package_max}` : ''} LPA</dd></div><div><dt>Minimum CGPA</dt><dd>{drive.min_cgpa ?? 'No minimum'}</dd></div><div><dt>Maximum backlogs</dt><dd>{drive.max_backlogs ?? 'No limit'}</dd></div><div><dt>Graduation year</dt><dd>{drive.graduation_year ?? 'All years'}</dd></div><div><dt>Application deadline</dt><dd>{deadline}</dd></div><div><dt>Eligible branches</dt><dd>{drive.allowed_branches?.join(', ') || 'All branches'}</dd></div></dl>
        <section className="job-detail-section"><span className="eyebrow">The opportunity</span><h2>About the role</h2><p>{drive.description}</p></section>
        <section className="job-detail-section"><span className="eyebrow">What you’ll bring</span><h2>Required skills</h2>{drive.required_skills.length ? <div className="job-detail-skills">{drive.required_skills.map((skill) => <span key={skill}>{skill}</span>)}</div> : <p>No specific skills listed.</p>}</section>
        {isAdmin && <div className="job-detail-admin-actions">{!terminal && <Link to={`${root}/${drive.id}/edit`} className="button button-quiet">Edit drive</Link>}{drive.status === 'DRAFT' && <button className="primary-button" disabled={busy} onClick={() => changeStatus('publish')}>Publish drive</button>}{drive.status === 'PUBLISHED' && <button className="button button-quiet" disabled={busy} onClick={() => changeStatus('close')}>Close drive</button>}{(drive.status === 'DRAFT' || drive.status === 'PUBLISHED') && <button className="button button-danger" disabled={busy} onClick={() => changeStatus('cancel')}>Cancel drive</button>}<Link to={`${root}/${drive.id}/applicants`} className="button button-quiet">View applicants</Link></div>}
      </article>
      {user?.role === 'STUDENT' && driveId && <aside className="job-detail-sidebar"><div className="job-apply-sticky"><StudentApplicationPanel driveId={driveId} deadline={drive.application_deadline} /><div className="job-detail-side-note"><span>✓</span><p>Eligibility is calculated from your saved profile and this role’s requirements. AI resume analysis does not affect application decisions.</p></div></div></aside>}
    </div>
  </section>
}
