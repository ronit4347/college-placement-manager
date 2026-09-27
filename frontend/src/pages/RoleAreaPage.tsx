import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { UserRole } from '../types/auth'
import { useAuth } from '../context/AuthContext'
import { fetchJobDrives, type JobDrive } from '../services/jobDrives'
import { fetchApplications, type ApplicationRecord } from '../services/applications'
import { fetchInterviews, type InterviewRecord } from '../services/interviews'
import { fetchOffers, type OfferRecord } from '../services/offers'
import { getErrorMessage } from '../utils/errors'

function shortDate(value: string) {
  return new Date(value).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

export default function RoleAreaPage({ role }: { role: UserRole }) {
  const { user } = useAuth()
  const [drives, setDrives] = useState<JobDrive[]>([])
  const [applications, setApplications] = useState<ApplicationRecord[]>([])
  const [interviews, setInterviews] = useState<InterviewRecord[]>([])
  const [offers, setOffers] = useState<OfferRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const recruiter = role === 'RECRUITER'
  const firstName = user?.full_name.trim().split(/\s+/)[0] || 'there'

  useEffect(() => {
    let active = true
    setLoading(true)
    const requests = recruiter
      ? Promise.all([fetchJobDrives({ limit: 100 }), fetchApplications({ limit: 100 }), fetchOffers()]).then(([jobs, apps, issuedOffers]) => {
        if (active) { setDrives(jobs); setApplications(apps); setOffers(issuedOffers) }
      })
      : fetchInterviews().then((scheduled) => { if (active) setInterviews(scheduled) })
    requests.catch((reason: unknown) => active && setError(getErrorMessage(reason, 'Could not load your workspace data.')))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [recruiter])

  const upcoming = useMemo(() => interviews.filter((item) => ['SCHEDULED', 'RESCHEDULED'].includes(item.status) && Date.parse(item.scheduled_at) >= Date.now()).sort((a, b) => Date.parse(a.scheduled_at) - Date.parse(b.scheduled_at)), [interviews])
  const activeDrives = drives.filter((drive) => drive.status === 'PUBLISHED')
  const shortlisted = applications.filter((item) => ['SHORTLISTED', 'INTERVIEW', 'SELECTED', 'OFFERED', 'JOINED'].includes(item.status)).length
  const statCards = recruiter ? [
    ['Active job drives', activeDrives.length, '/recruiter/job-drives', 'Published opportunities under your company'],
    ['Applicants', applications.length, '/applications', 'Candidates across your hiring pipeline'],
    ['Shortlisted', shortlisted, '/applications?status=SHORTLISTED', 'Candidates progressing in the process'],
    ['Offers', offers.length, '/recruiter/offers', 'Offers associated with your company'],
  ] as const : [
    ['Upcoming interviews', upcoming.length, '/interviewer/interviews', 'Assigned conversations on your schedule'],
    ['All assigned rounds', interviews.length, '/interviewer/interviews', 'Interview history and upcoming rounds'],
    ['Awaiting evaluation', interviews.filter((item) => ['SCHEDULED', 'RESCHEDULED'].includes(item.status) && item.result === 'PENDING').length, '/interviewer/interviews', 'Rounds awaiting your feedback'],
  ] as const

  return <section className="role-dashboard">
    <header className="workspace-welcome"><div><span className="eyebrow">{recruiter ? 'Recruiter workspace' : 'Interview workspace'}</span><h1>Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}, {firstName}.</h1><p>{recruiter ? 'A live view of your opportunities and campus hiring pipeline.' : 'Your assigned candidate conversations, ready for the next step.'}</p></div><span className="welcome-mark" aria-hidden="true">{recruiter ? '↗' : '◷'}</span></header>
    {error && <div className="page-error" role="alert"><span>{error}</span><button type="button" onClick={() => window.location.reload()}>Retry</button></div>}
    {loading ? <div className="role-stat-grid">{statCards.map(([label]) => <div className="role-stat-skeleton" key={label} />)}</div> : <div className={`role-stat-grid${recruiter ? '' : ' role-stat-three'}`}>
      {statCards.map(([label, value, to, detail]) => <Link to={to} className="role-stat-card" key={label}><span>{label}</span><strong>{value}</strong><small>{detail}</small><i aria-hidden="true">↗</i></Link>)}
    </div>}
    {recruiter ? <div className="role-dashboard-columns">
      <section className="workspace-panel"><div className="panel-heading"><div><span className="eyebrow">Your openings</span><h2>Active job drives</h2></div><Link to="/recruiter/job-drives">All job drives <span>↗</span></Link></div>
        {loading ? <div className="workspace-skeleton" /> : activeDrives.length === 0 ? <div className="workspace-empty"><span>◷</span><h3>No published drives yet</h3><p>Published opportunities for your company will appear here.</p></div> : <div className="workspace-list">{activeDrives.slice(0, 5).map((drive) => <Link to={`/recruiter/job-drives/${drive.id}`} className="workspace-list-item" key={drive.id}><span className="workspace-company-mark">{drive.company_name.slice(0, 1).toUpperCase()}</span><span className="workspace-list-copy"><strong>{drive.title}</strong><small>{drive.location || 'Location flexible'} · {drive.employment_type?.replace('_', ' ').toLowerCase() || 'Role'}</small></span><span className="workspace-list-meta">{drive.package_max ? `Up to ${drive.package_max} LPA` : 'View role'}<i>↗</i></span></Link>)}</div>}
      </section>
      <section className="workspace-panel"><div className="panel-heading"><div><span className="eyebrow">Candidate pipeline</span><h2>Recent applications</h2></div><Link to="/applications">View all <span>↗</span></Link></div>
        {loading ? <div className="workspace-skeleton" /> : applications.length === 0 ? <div className="workspace-empty"><span>▧</span><h3>Applications will show here</h3><p>Review candidates as they apply to your company's published roles.</p></div> : <div className="workspace-list">{applications.slice(0, 5).map((application) => <Link to={`/applications/${application.id}`} className="workspace-list-item" key={application.id}><span className="candidate-avatar">{application.student_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()}</span><span className="workspace-list-copy"><strong>{application.student_name}</strong><small>{application.drive_title} · {application.branch || 'Branch not set'}</small></span><span className={`pipeline-status pipeline-${application.status.toLowerCase()}`}>{application.status.toLowerCase()}</span></Link>)}</div>}
      </section>
    </div> : <div className="workspace-panel interviewer-panel"><div className="panel-heading"><div><span className="eyebrow">Your calendar</span><h2>Upcoming interviews</h2></div><Link to="/interviewer/interviews">All assigned interviews <span>↗</span></Link></div>
      {loading ? <div className="workspace-skeleton" /> : upcoming.length === 0 ? <div className="workspace-empty"><span>◷</span><h3>Your schedule is clear</h3><p>New interviews assigned to you will appear here with candidate and role details.</p></div> : <div className="workspace-list">{upcoming.map((item) => <article className="interview-agenda-item" key={item.id}><div className="agenda-date"><strong>{new Date(item.scheduled_at).toLocaleDateString(undefined, { day: '2-digit' })}</strong><span>{new Date(item.scheduled_at).toLocaleDateString(undefined, { month: 'short' })}</span></div><div className="workspace-list-copy"><strong>{item.student_name} <span className="agenda-round">{item.round.toLowerCase()}</span></strong><small>{item.drive_title} · {item.branch || 'Branch not set'}</small><small>{shortDate(item.scheduled_at)} · {item.duration_minutes} minutes</small></div><Link className="button button-quiet agenda-action" to="/interviewer/interviews">Review <span>↗</span></Link></article>)}</div>}
    </div>}
  </section>
}
