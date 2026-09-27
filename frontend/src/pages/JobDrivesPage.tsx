import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Pagination from '../components/Pagination'
import OpportunityCard from '../components/OpportunityCard'
import { getErrorMessage } from '../utils/errors'
import { fetchJobDrives, type ApplicationDriveStatus, type DriveStatus, type EmploymentType, type JobDrive } from '../services/jobDrives'

type Audience = 'ADMIN' | 'STUDENT' | 'RECRUITER'
const types: EmploymentType[] = ['FULL_TIME', 'PART_TIME', 'INTERNSHIP', 'CONTRACT', 'OTHER']
const applicationStatuses: (ApplicationDriveStatus | 'NOT_APPLIED')[] = ['NOT_APPLIED', 'APPLIED', 'SHORTLISTED', 'INTERVIEW', 'SELECTED', 'OFFERED', 'JOINED', 'REJECTED']
const PAGE_SIZE = 20

export default function JobDrivesPage({ audience }: { audience: Audience }) {
  const [searchParams] = useSearchParams()
  const [drives, setDrives] = useState<JobDrive[]>([])
  const [query, setQuery] = useState(() => searchParams.get('q') || '')
  const [company, setCompany] = useState('')
  const [location, setLocation] = useState('')
  const [employmentType, setEmploymentType] = useState('')
  const [year, setYear] = useState('')
  const [status, setStatus] = useState('')
  const [packageMin, setPackageMin] = useState('')
  const [packageMax, setPackageMax] = useState('')
  const [eligibility, setEligibility] = useState('')
  const [applicationStatus, setApplicationStatus] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const root = audience === 'ADMIN' ? '/admin/job-drives' : audience === 'STUDENT' ? '/student/job-drives' : '/recruiter/job-drives'

  useEffect(() => { setQuery(searchParams.get('q') || '') }, [searchParams])

  useEffect(() => {
    let current = true
    setLoading(true)
    fetchJobDrives({ q: query || undefined, company: company || undefined, location: location || undefined,
      employment_type: (employmentType || undefined) as EmploymentType | undefined,
      graduation_year: year ? Number(year) : undefined,
      status: (audience === 'ADMIN' ? status || undefined : undefined) as DriveStatus | undefined,
      package_min: packageMin ? Number(packageMin) : undefined, package_max: packageMax ? Number(packageMax) : undefined,
      eligibility: audience === 'STUDENT' && eligibility ? eligibility === 'eligible' : undefined,
      application_status: audience === 'STUDENT' ? (applicationStatus || undefined) as ApplicationDriveStatus | 'NOT_APPLIED' | undefined : undefined,
      limit: PAGE_SIZE + 1, offset: (page - 1) * PAGE_SIZE,
    }).then((items) => { if (current) { setDrives(items); setError('') } })
      .catch((reason: unknown) => { if (current) setError(getErrorMessage(reason, 'Could not load job drives.')) })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [query, company, location, employmentType, year, status, packageMin, packageMax, eligibility, applicationStatus, page, audience])

  const heading = audience === 'ADMIN' ? 'Job drive management' : audience === 'STUDENT' ? 'Published job drives' : 'Company job drives'
  function resetPage(change: () => void) { change(); setPage(1) }
  return <section className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">{audience === 'STUDENT' ? 'Explore opportunities' : audience === 'RECRUITER' ? 'Recruiter workspace' : 'Administration'}</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{heading}</h1><p className="mt-2 text-sm text-muted">{audience === 'STUDENT' ? 'Search published openings and check your eligibility and application status.' : audience === 'RECRUITER' ? 'Drives associated with your company.' : 'Create, publish, and filter placement opportunities.'}</p></div>{audience === 'ADMIN' && <Link className="primary-button inline-flex" to={`${root}/new`}>Create job drive</Link>}</div>
    <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2 lg:grid-cols-4">
      <label className="form-label">Search jobs<input className="form-input mt-2" placeholder="Job title or description" value={query} onChange={(event) => resetPage(() => setQuery(event.target.value))} /></label>
      {audience !== 'RECRUITER' && <label className="form-label">Company<input className="form-input mt-2" placeholder="Company name" value={company} onChange={(event) => resetPage(() => setCompany(event.target.value))} /></label>}
      <label className="form-label">Location<input className="form-input mt-2" placeholder="Any location" value={location} onChange={(event) => resetPage(() => setLocation(event.target.value))} /></label>
      <label className="form-label">Employment type<select className="form-input mt-2" value={employmentType} onChange={(event) => resetPage(() => setEmploymentType(event.target.value))}><option value="">Any type</option>{types.map((item) => <option key={item} value={item}>{item.replace('_', ' ')}</option>)}</select></label>
      <label className="form-label">Graduation year<input className="form-input mt-2" type="number" min="2000" max="2100" placeholder="Any year" value={year} onChange={(event) => resetPage(() => setYear(event.target.value))} /></label>
      <label className="form-label">Minimum package (LPA)<input className="form-input mt-2" type="number" min="0" step="0.1" value={packageMin} onChange={(event) => resetPage(() => setPackageMin(event.target.value))} /></label>
      <label className="form-label">Maximum package (LPA)<input className="form-input mt-2" type="number" min="0" step="0.1" value={packageMax} onChange={(event) => resetPage(() => setPackageMax(event.target.value))} /></label>
      {audience === 'ADMIN' && <label className="form-label">Drive status<select className="form-input mt-2" value={status} onChange={(event) => resetPage(() => setStatus(event.target.value))}><option value="">All statuses</option>{(['DRAFT', 'PUBLISHED', 'CLOSED', 'CANCELLED'] as DriveStatus[]).map((item) => <option key={item}>{item}</option>)}</select></label>}
      {audience === 'STUDENT' && <><label className="form-label">Eligibility<select className="form-input mt-2" value={eligibility} onChange={(event) => resetPage(() => setEligibility(event.target.value))}><option value="">Any eligibility</option><option value="eligible">Eligible</option><option value="ineligible">Not eligible</option></select></label><label className="form-label">Application status<select className="form-input mt-2" value={applicationStatus} onChange={(event) => resetPage(() => setApplicationStatus(event.target.value))}><option value="">All application states</option>{applicationStatuses.map((item) => <option key={item} value={item}>{item === 'NOT_APPLIED' ? 'Not applied' : item}</option>)}</select></label></>}
    </div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {loading ? <div role="status" className="opportunity-grid">{Array.from({ length: 4 }, (_, index) => <div className="opportunity-skeleton" key={index} />)}</div> : drives.length === 0 ? <div className="empty-opportunities"><span aria-hidden="true">⌕</span><h2>No opportunities found</h2><p>Try another search or clear a filter to see more published roles.</p></div> : <div className="opportunity-grid">{drives.slice(0, PAGE_SIZE).map((drive) => <OpportunityCard key={drive.id} drive={drive} audience={audience} to={`${root}/${drive.id}`} />)}</div>}
    {!loading && drives.length > 0 && <Pagination page={page} canGoNext={drives.length > PAGE_SIZE} onPageChange={setPage} />}
  </section>
}
