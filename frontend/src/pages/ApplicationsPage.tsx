import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Pagination from '../components/Pagination'
import { useAuth } from '../context/AuthContext'
import { fetchApplications, type ApplicationRecord, type ApplicationStatus } from '../services/applications'
import { getErrorMessage } from '../utils/errors'

const statuses: ApplicationStatus[] = ['APPLIED', 'SHORTLISTED', 'REJECTED', 'INTERVIEW', 'SELECTED', 'OFFERED', 'JOINED']
const PAGE_SIZE = 20
const studentStages: ApplicationStatus[] = ['APPLIED', 'SHORTLISTED', 'INTERVIEW', 'SELECTED', 'OFFERED', 'JOINED']

function StudentApplicationCard({ application }: { application: ApplicationRecord }) {
  const rejected = application.status === 'REJECTED'
  const activeIndex = studentStages.indexOf(application.status)
  const progress = rejected ? 1 : Math.max(0, activeIndex)
  return <article className="student-application-card">
    <div className="student-application-head"><div className="application-company-mark">{application.company_name.slice(0, 1).toUpperCase()}</div><div className="application-card-title"><span>{application.company_name}</span><h2>{application.drive_title}</h2><small>Applied {new Date(application.applied_at).toLocaleDateString()}</small></div><span className={`pipeline-status pipeline-${application.status.toLowerCase()}`}>{application.status === 'JOINED' ? 'Placed' : application.status.toLowerCase()}</span></div>
    <div className={`application-progress${rejected ? ' progress-rejected' : ''}`} aria-label={`Application status ${application.status}`}>
      {studentStages.map((stage, index) => <div className={`application-progress-step${index <= progress ? ' is-complete' : ''}${stage === application.status ? ' is-current' : ''}`} key={stage}><span>{index < progress ? '✓' : index + 1}</span><small>{stage === 'JOINED' ? 'Joined' : stage.charAt(0) + stage.slice(1).toLowerCase()}</small>{index < studentStages.length - 1 && <i />}</div>)}
    </div>
    {rejected && <p className="application-rejected-note">This application is no longer active. Your other opportunities remain available.</p>}
    <div className="application-card-footer"><span>{application.timeline.length ? `Updated ${new Date(application.timeline[application.timeline.length - 1].created_at).toLocaleDateString()}` : 'Application received'}</span><Link to={`/applications/${application.id}`}>View application <span>↗</span></Link></div>
  </article>
}

export default function ApplicationsPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const [applications, setApplications] = useState<ApplicationRecord[]>([])
  const [status, setStatus] = useState(() => searchParams.get('status') || '')
  const [company, setCompany] = useState('')
  const [job, setJob] = useState('')
  const [branch, setBranch] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const isAdmin = user?.role === 'ADMIN'
  const canFilter = isAdmin || user?.role === 'RECRUITER'
  const root = isAdmin ? '/admin/job-drives' : user?.role === 'RECRUITER' ? '/recruiter/job-drives' : '/student/job-drives'

  useEffect(() => { setStatus(searchParams.get('status') || '') }, [searchParams])

  useEffect(() => {
    let mounted = true
    setLoading(true)
    fetchApplications({ status: (status || undefined) as ApplicationStatus | undefined,
      company: canFilter ? company || undefined : undefined, job: canFilter ? job || undefined : undefined,
      branch: canFilter ? branch || undefined : undefined, limit: PAGE_SIZE + 1, offset: (page - 1) * PAGE_SIZE,
    }).then((items) => { if (mounted) { setApplications(items); setError('') } })
      .catch((reason: unknown) => { if (mounted) setError(getErrorMessage(reason, 'Could not load applications.')) })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [status, company, job, branch, page, canFilter])

  function change(setter: (value: string) => void, value: string) { setter(value); setPage(1) }
  const title = isAdmin ? 'Application management' : user?.role === 'RECRUITER' ? 'Company applications' : 'My applications'
  return <section className="space-y-6"><Link to={root} className="text-sm font-medium text-brand hover:underline">← Back</Link><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Placement workflow</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1><p className="mt-2 text-sm text-muted">{isAdmin ? 'Review applications by employer, role, status, and candidate branch.' : user?.role === 'RECRUITER' ? 'Applications for your company, with filters for role and candidate branch.' : 'Track the status and history of your applications.'}</p></div>
    {canFilter && <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2 lg:grid-cols-4"><label className="form-label">Company<input className="form-input mt-2" value={company} onChange={(event) => change(setCompany, event.target.value)} placeholder="Search company" /></label><label className="form-label">Job<input className="form-input mt-2" value={job} onChange={(event) => change(setJob, event.target.value)} placeholder="Search job title" /></label><label className="form-label">Status<select className="form-input mt-2" value={status} onChange={(event) => change(setStatus, event.target.value)}><option value="">All statuses</option>{statuses.map((item) => <option key={item}>{item}</option>)}</select></label><label className="form-label">Student branch<input className="form-input mt-2" value={branch} onChange={(event) => change(setBranch, event.target.value)} placeholder="Filter branch" /></label></div>}
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {loading ? <div role="status" className="application-loading-list"><div /><div /><div /></div> : applications.length === 0 ? <div className="empty-opportunities"><span aria-hidden="true">↗</span><h2>No applications found</h2><p>{user?.role === 'STUDENT' ? 'Eligible applications you submit will appear here.' : 'No applications match the current filters.'}</p>{user?.role === 'STUDENT' && <Link to="/student/job-drives" className="primary-button mt-5">Explore opportunities</Link>}</div> : user?.role === 'STUDENT' ? <div className="student-application-list">{applications.slice(0, PAGE_SIZE).map((application) => <StudentApplicationCard key={application.id} application={application} />)}</div> : <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Student</th><th className="px-5 py-3">Job drive</th><th className="px-5 py-3">Company</th><th className="px-5 py-3">Branch</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Applied</th><th className="px-5 py-3" /></tr></thead><tbody className="divide-y divide-slate-100">{applications.slice(0, PAGE_SIZE).map((application) => <tr key={application.id} className="hover:bg-slate-50"><td className="px-5 py-4"><p className="font-medium">{application.student_name}</p><p className="text-xs text-muted">{application.student_email}</p></td><td className="px-5 py-4 font-medium">{application.drive_title}</td><td className="px-5 py-4">{application.company_name}</td><td className="px-5 py-4">{application.branch || '—'}</td><td className="px-5 py-4"><span className={`pipeline-status pipeline-${application.status.toLowerCase()}`}>{application.status.toLowerCase()}</span></td><td className="px-5 py-4">{new Date(application.applied_at).toLocaleDateString()}</td><td className="px-5 py-4"><Link to={`/applications/${application.id}`} className="font-semibold text-brand hover:underline">Details</Link></td></tr>)}</tbody></table></div></div>}
    {!loading && applications.length > 0 && <Pagination page={page} canGoNext={applications.length > PAGE_SIZE} onPageChange={setPage} />}
  </section>
}
