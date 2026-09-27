import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import type { StudentProfile } from '../services/students'
import { fetchApplications, type ApplicationRecord, type ApplicationStatus } from '../services/applications'
import { fetchEligibleJobDrives, fetchJobDrives, type EligibleJobDrive, type EmploymentType, type JobDrive } from '../services/jobDrives'
import { analyzeResume, type ResumeAnalysis } from '../services/resumeAnalysis'
import { fetchInterviews, type InterviewRecord } from '../services/interviews'
import { fetchOffers, type OfferRecord } from '../services/offers'
import { getErrorMessage } from '../utils/errors'

const employmentTypes: EmploymentType[] = ['FULL_TIME', 'PART_TIME', 'INTERNSHIP', 'CONTRACT', 'OTHER']

function statusTone(status: string) {
  if (['SELECTED', 'OFFERED', 'JOINED', 'ACCEPTED'].includes(status)) return 'bg-emerald-50 text-emerald-800'
  if (['REJECTED', 'DECLINED', 'EXPIRED'].includes(status)) return 'bg-rose-50 text-rose-800'
  if (['SHORTLISTED', 'INTERVIEW', 'ISSUED'].includes(status)) return 'bg-blue-50 text-blue-800'
  return 'bg-slate-100 text-slate-700'
}

function applicationStatusLabel(status: ApplicationStatus) {
  return status === 'JOINED' ? 'PLACED' : status
}

export default function StudentPlacementOverview({ profile }: { profile: StudentProfile }) {
  const [applications, setApplications] = useState<ApplicationRecord[]>([])
  const [interviews, setInterviews] = useState<InterviewRecord[]>([])
  const [offers, setOffers] = useState<OfferRecord[]>([])
  const [eligibleJobs, setEligibleJobs] = useState<EligibleJobDrive[]>([])
  const [analysisJobs, setAnalysisJobs] = useState<JobDrive[]>([])
  const [selectedAnalysisJob, setSelectedAnalysisJob] = useState('')
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState('')
  const [activityLoading, setActivityLoading] = useState(true)
  const [jobsLoading, setJobsLoading] = useState(true)
  const [activityError, setActivityError] = useState('')
  const [jobsError, setJobsError] = useState('')
  const [draftFilters, setDraftFilters] = useState({ q: '', location: '', employment_type: '', graduation_year: profile.graduation_year ? String(profile.graduation_year) : '' })
  const [jobFilters, setJobFilters] = useState({ q: '', location: '', employment_type: '', graduation_year: profile.graduation_year ? String(profile.graduation_year) : '' })

  useEffect(() => {
    let active = true
    setActivityLoading(true)
    Promise.allSettled([fetchApplications(), fetchInterviews(), fetchOffers()]).then(([applicationResult, interviewResult, offerResult]) => {
      if (!active) return
      const errors: string[] = []
      if (applicationResult.status === 'fulfilled') setApplications(applicationResult.value)
      else errors.push(getErrorMessage(applicationResult.reason, 'Applications could not be loaded.'))
      if (interviewResult.status === 'fulfilled') setInterviews(interviewResult.value)
      else errors.push(getErrorMessage(interviewResult.reason, 'Interviews could not be loaded.'))
      if (offerResult.status === 'fulfilled') setOffers(offerResult.value)
      else errors.push(getErrorMessage(offerResult.reason, 'Offers could not be loaded.'))
      setActivityError(errors.join(' '))
    }).finally(() => { if (active) setActivityLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    setJobsLoading(true)
    fetchEligibleJobDrives({
      q: jobFilters.q || undefined,
      location: jobFilters.location || undefined,
      employment_type: (jobFilters.employment_type || undefined) as EmploymentType | undefined,
      graduation_year: jobFilters.graduation_year ? Number(jobFilters.graduation_year) : undefined,
    }).then((items) => { if (active) { setEligibleJobs(items); setJobsError('') } })
      .catch((reason: unknown) => { if (active) setJobsError(getErrorMessage(reason, 'Eligible jobs could not be loaded.')) })
      .finally(() => { if (active) setJobsLoading(false) })
    return () => { active = false }
  }, [jobFilters, profile.cgpa, profile.branch, profile.graduation_year, profile.backlogs, profile.skills.join('|')])

  useEffect(() => {
    fetchJobDrives().then(setAnalysisJobs).catch(() => setAnalysisError('Published jobs could not be loaded for resume analysis.'))
  }, [])

  async function runResumeAnalysis() {
    if (!selectedAnalysisJob) return
    setAnalysisLoading(true)
    setAnalysisError('')
    setAnalysis(null)
    try { setAnalysis(await analyzeResume(Number(selectedAnalysisJob))) }
    catch (reason) { setAnalysisError(getErrorMessage(reason, 'Resume analysis failed. Please try again.')) }
    finally { setAnalysisLoading(false) }
  }

  const upcomingInterviews = useMemo(() => interviews
    .filter((item) => ['SCHEDULED', 'RESCHEDULED'].includes(item.status) && Date.parse(item.scheduled_at) >= Date.now())
    .sort((left, right) => Date.parse(left.scheduled_at) - Date.parse(right.scheduled_at)), [interviews])

  function searchJobs(event: FormEvent) {
    event.preventDefault()
    setJobFilters({ ...draftFilters })
  }

  return <div className="space-y-6 student-placement-overview">
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel sm:p-6">
      <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Resume insights</p><h2 className="mt-1 text-xl font-semibold">Analyze your resume</h2><p className="mt-1 text-sm text-muted">Compare your uploaded PDF with a published role and get suggestions to improve your application.</p></div>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row"><label className="form-label min-w-0 flex-1">Select a job<select className="form-input mt-2" value={selectedAnalysisJob} onChange={(event) => { setSelectedAnalysisJob(event.target.value); setAnalysis(null) }}><option value="">Choose a published job</option>{analysisJobs.map((job) => <option key={job.id} value={job.id}>{job.title} · {job.company_name}</option>)}</select></label><button type="button" className="primary-button self-end" disabled={!selectedAnalysisJob || analysisLoading || !profile.resume_filename} onClick={runResumeAnalysis}>{analysisLoading ? 'Analyzing…' : 'Analyze resume'}</button></div>
      {!profile.resume_filename && <p className="mt-3 text-sm text-amber-800">Upload a PDF resume in your profile before analyzing.</p>}
      {analysisLoading && <p role="status" className="mt-4 text-sm text-muted">Reading your resume and comparing it with this role…</p>}
      {analysisError && <p role="alert" className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{analysisError}</p>}
      {analysis && <div className="mt-5 space-y-4 border-t border-slate-100 pt-5">
        <div className="flex flex-wrap items-center gap-3"><div className="grid h-16 w-16 place-items-center rounded-full bg-brand/10 text-xl font-bold text-brand">{analysis.overall_match_percentage}%</div><div><h3 className="font-semibold">Resume match estimate</h3><p className="text-xs text-muted">{analysis.analysis_mode === 'MOCK' ? 'Mock analysis mode' : 'AI analysis'} · Decision support only; this does not affect eligibility or application status.</p></div></div>
        <div className="grid gap-4 md:grid-cols-2"><div className="rounded-xl bg-emerald-50 p-4"><h4 className="text-sm font-semibold text-emerald-900">Matching skills</h4><p className="mt-2 text-sm text-emerald-800">{analysis.matching_skills.length ? analysis.matching_skills.join(', ') : 'No required skills were identified in the resume text.'}</p></div><div className="rounded-xl bg-amber-50 p-4"><h4 className="text-sm font-semibold text-amber-900">Skills to highlight or develop</h4><p className="mt-2 text-sm text-amber-800">{analysis.missing_skills.length ? analysis.missing_skills.join(', ') : 'No required skills are missing from the extracted text.'}</p></div></div>
        <div className="grid gap-3 md:grid-cols-2">{[['Education', analysis.education_match], ['Experience', analysis.experience_match]].map(([label, detail]) => { const item = detail as ResumeAnalysis['education_match']; return <div key={label as string} className="rounded-xl border border-slate-200 p-4"><p className="text-sm font-semibold">{label as string} · {item.status.replace('_', ' ')}</p><p className="mt-1 text-sm text-muted">{item.explanation}</p></div> })}</div>
        <div><h4 className="text-sm font-semibold">Improvement suggestions</h4><ul className="mt-2 list-inside list-disc space-y-1 text-sm text-muted">{analysis.improvement_suggestions.map((suggestion, index) => <li key={index}>{suggestion}</li>)}</ul></div>
        <p className="text-xs text-muted">Resume text is processed for this request and the analysis is not stored. Matching estimates can miss context and are not hiring decisions.</p>
      </div>}
    </section>
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel"><p className="text-xs font-semibold uppercase tracking-wide text-muted">CGPA</p><p className="mt-2 text-2xl font-semibold">{profile.cgpa ?? '—'}<span className="ml-1 text-sm font-medium text-muted">/ 10</span></p></article>
      <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel"><p className="text-xs font-semibold uppercase tracking-wide text-muted">Branch</p><p className="mt-2 truncate text-lg font-semibold">{profile.branch || 'Add your branch'}</p><p className="mt-1 text-xs text-muted">Graduation {profile.graduation_year ?? 'year not set'}</p></article>
      <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel"><p className="text-xs font-semibold uppercase tracking-wide text-muted">Skills</p><p className="mt-2 text-2xl font-semibold">{profile.skills.length}</p><p className="mt-1 truncate text-xs text-muted">{profile.skills.length ? profile.skills.join(', ') : 'Add skills to check job eligibility'}</p></article>
      <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel"><p className="text-xs font-semibold uppercase tracking-wide text-muted">Placement activity</p><div className="mt-3 flex justify-between text-sm"><span>Applied jobs</span><strong>{activityLoading ? '…' : applications.length}</strong></div><div className="mt-1 flex justify-between text-sm"><span>Upcoming interviews</span><strong>{activityLoading ? '…' : upcomingInterviews.length}</strong></div></article>
    </section>

    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-panel sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Matched to your profile</p><h2 className="mt-1 text-xl font-semibold">Eligible jobs</h2><p className="mt-1 text-sm text-muted">Eligibility is checked against your saved profile and each job’s requirements.</p></div><Link to="/student/job-drives" className="text-sm font-semibold text-brand hover:underline">Browse all published jobs</Link></div>
      <form onSubmit={searchJobs} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><label className="form-label">Search<input className="form-input mt-2" placeholder="Role, company or keywords" value={draftFilters.q} onChange={(event) => setDraftFilters({ ...draftFilters, q: event.target.value })} /></label><label className="form-label">Location<input className="form-input mt-2" placeholder="Any location" value={draftFilters.location} onChange={(event) => setDraftFilters({ ...draftFilters, location: event.target.value })} /></label><label className="form-label">Employment type<select className="form-input mt-2" value={draftFilters.employment_type} onChange={(event) => setDraftFilters({ ...draftFilters, employment_type: event.target.value })}><option value="">Any type</option>{employmentTypes.map((type) => <option key={type} value={type}>{type.replace('_', ' ')}</option>)}</select></label><label className="form-label">Graduation year<input className="form-input mt-2" type="number" min="2000" max="2100" placeholder="Any year" value={draftFilters.graduation_year} onChange={(event) => setDraftFilters({ ...draftFilters, graduation_year: event.target.value })} /></label><button className="primary-button self-end">Search eligible jobs</button></form>
      {jobsError && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{jobsError} <button className="ml-2 font-semibold underline" onClick={() => setJobFilters({ ...jobFilters })}>Retry</button></p>}
      {jobsLoading ? <div role="status" className="grid gap-3 md:grid-cols-2"><div className="h-32 animate-pulse rounded-xl bg-slate-100" /><div className="h-32 animate-pulse rounded-xl bg-slate-100" /></div> : eligibleJobs.length === 0 ? <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center"><p className="text-sm font-medium">No eligible jobs match these filters.</p><p className="mt-1 text-xs text-muted">Complete your profile or adjust the search to see more opportunities.</p></div> : <div className="grid gap-3 md:grid-cols-2">{eligibleJobs.slice(0, 8).map((job) => {
        const application = applications.find((item) => item.job_drive_id === job.id)
        return <article key={job.id} className="rounded-xl border border-slate-200 p-4 transition hover:border-brand/40"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-wide text-brand">{job.company_name}</p><h3 className="mt-1 truncate font-semibold">{job.title}</h3></div><span className="shrink-0 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">Eligible</span></div><div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted"><span>{job.location || 'Location not specified'}</span>{job.employment_type && <span>{job.employment_type.replace('_', ' ')}</span>}{job.package_max !== null && <span>Up to {job.package_max} LPA</span>}</div><div className="mt-4 flex flex-wrap items-center justify-between gap-2"><span className="text-xs text-muted">{application ? `Application: ${application.status}` : job.application_deadline ? `Deadline ${new Date(job.application_deadline).toLocaleDateString()}` : 'Open for applications'}</span><Link to={`/student/job-drives/${job.id}`} className="text-sm font-semibold text-brand hover:underline">{application ? 'Track application' : 'View and apply'} →</Link></div></article>
      })}</div>}
    </section>

    {activityError && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{activityError}</p>}
    <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel sm:p-6"><div className="flex items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Your progress</p><h2 className="mt-1 text-xl font-semibold">Application tracking</h2></div><Link to="/applications" className="text-sm font-semibold text-brand hover:underline">All applications</Link></div>
        {activityLoading ? <p role="status" className="mt-5 text-sm text-muted">Loading applications…</p> : applications.length === 0 ? <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-muted">Your submitted applications and their timelines will appear here.</div> : <div className="mt-5 space-y-4">{applications.map((application) => {
          const interviewItems = interviews.filter((item) => item.application_id === application.id)
          const offerItems = offers.filter((item) => item.application_id === application.id)
          const timeline = [
            ...application.timeline.map((event) => ({ key: `event-${event.id}`, when: event.created_at, title: event.to_status === 'JOINED' ? 'Placed / joined' : event.to_status === 'OFFERED' ? 'Offer issued' : event.to_status === 'INTERVIEW' ? 'Interview stage' : event.to_status.charAt(0) + event.to_status.slice(1).toLowerCase(), detail: event.note })),
            ...interviewItems.map((item) => ({ key: `interview-${item.id}`, when: item.scheduled_at, title: `${item.round.charAt(0) + item.round.slice(1).toLowerCase()} interview`, detail: `${item.status.toLowerCase()} · ${new Date(item.scheduled_at).toLocaleString()}` })),
            ...offerItems.map((item) => ({ key: `offer-${item.id}`, when: item.status === 'ISSUED' ? item.issued_at || item.created_at : item.updated_at, title: `Offer ${item.status.toLowerCase()}`, detail: `${item.currency} ${item.salary?.toLocaleString() ?? 'package pending'}${item.joining_date ? ` · Joining ${item.joining_date}` : ''}` })),
          ].sort((left, right) => Date.parse(left.when) - Date.parse(right.when))
          const selected = ['SELECTED', 'OFFERED', 'JOINED'].includes(application.status)
          return <article key={application.id} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-brand">{application.company_name}</p><h3 className="mt-1 font-semibold">{application.drive_title}</h3></div><div className="flex flex-wrap gap-2"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusTone(application.status)}`}>{applicationStatusLabel(application.status)}</span><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusTone(selected ? 'SELECTED' : application.status === 'REJECTED' ? 'REJECTED' : 'PENDING')}`}>{selected ? 'Selection confirmed' : application.status === 'REJECTED' ? 'Not selected' : 'Selection pending'}</span></div></div><p className="mt-2 text-xs text-muted">Applied {new Date(application.applied_at).toLocaleDateString()}</p><details className="group mt-4"><summary className="cursor-pointer list-none text-sm font-semibold text-brand">View placement timeline <span className="ml-1 inline-block transition group-open:rotate-180">⌄</span></summary><ol className="mt-4 space-y-0">{timeline.map((entry, index) => <li key={entry.key} className="relative flex gap-3 pb-4 last:pb-0"><span className={`relative z-10 mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold ${index === timeline.length - 1 ? 'bg-brand text-white' : 'bg-slate-100 text-slate-600'}`}>{index + 1}</span>{index < timeline.length - 1 && <span className="absolute left-3 top-6 h-full w-px bg-slate-200" />}<div className="min-w-0 flex-1"><div className="flex flex-wrap justify-between gap-2"><p className="text-sm font-medium">{entry.title}</p><time className="text-xs text-muted">{new Date(entry.when).toLocaleString()}</time></div>{entry.detail && <p className="mt-1 text-xs text-muted">{entry.detail}</p>}</div></li>)}</ol></details></article>
        })}</div>}
      </section>

      <div className="space-y-6">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel sm:p-6"><div className="flex items-end justify-between gap-2"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Next steps</p><h2 className="mt-1 text-xl font-semibold">Upcoming interviews</h2></div><Link to="/student/interviews" className="text-sm font-semibold text-brand hover:underline">Schedule</Link></div>{activityLoading ? <p role="status" className="mt-4 text-sm text-muted">Loading interviews…</p> : upcomingInterviews.length === 0 ? <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-muted">No upcoming interviews scheduled.</p> : <ul className="mt-4 space-y-3">{upcomingInterviews.slice(0, 4).map((item) => <li key={item.id} className="rounded-xl border border-slate-100 p-3"><div className="flex items-start justify-between gap-2"><div><p className="text-xs font-semibold text-brand">{item.company_name}</p><p className="mt-1 text-sm font-semibold">{item.round} · {item.drive_title}</p></div><span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${statusTone(item.status)}`}>{item.status}</span></div><p className="mt-2 text-xs text-muted">{new Date(item.scheduled_at).toLocaleString()}</p></li>)}</ul>}</section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel sm:p-6"><div className="flex items-end justify-between gap-2"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Offer decisions</p><h2 className="mt-1 text-xl font-semibold">My offers</h2></div><Link to="/student/offers" className="text-sm font-semibold text-brand hover:underline">View offers</Link></div>{activityLoading ? <p role="status" className="mt-4 text-sm text-muted">Loading offers…</p> : offers.length === 0 ? <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-muted">Offers you receive will appear here.</p> : <ul className="mt-4 space-y-3">{offers.slice(0, 4).map((offer) => <li key={offer.id} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 p-3"><div className="min-w-0"><p className="truncate text-sm font-semibold">{offer.company_name} · {offer.job_title}</p><p className="mt-1 text-xs text-muted">{offer.currency} {offer.salary?.toLocaleString() ?? 'Package pending'}{offer.joining_date ? ` · Joins ${offer.joining_date}` : ''}</p></div><span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-semibold ${statusTone(offer.status)}`}>{offer.status}</span></li>)}</ul>}</section>
      </div>
    </div>
  </div>
}
