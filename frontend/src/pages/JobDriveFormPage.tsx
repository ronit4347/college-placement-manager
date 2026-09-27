import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchCompanies, type Company } from '../services/companies'
import { createJobDrive, fetchJobDrive, updateJobDrive, type EmploymentType, type JobDriveInput } from '../services/jobDrives'
import { getErrorMessage } from '../utils/errors'

const empty: JobDriveInput = { company_id: 0, title: '', description: '', package_min: null, package_max: null, location: '', employment_type: null, min_cgpa: null, max_backlogs: null, allowed_branches: null, graduation_year: null, required_skills: [], application_deadline: null }
const employmentTypes: EmploymentType[] = ['FULL_TIME', 'PART_TIME', 'INTERNSHIP', 'CONTRACT', 'OTHER']

function localDateTime(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

export default function JobDriveFormPage() {
  const { driveId } = useParams()
  const navigate = useNavigate()
  const editing = Boolean(driveId)
  const [companies, setCompanies] = useState<Company[]>([])
  const [values, setValues] = useState<JobDriveInput>(empty)
  const [branches, setBranches] = useState('')
  const [skills, setSkills] = useState('')
  const [deadline, setDeadline] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const root = '/admin/job-drives'

  useEffect(() => {
    Promise.all([fetchCompanies({ is_active: true }), driveId ? fetchJobDrive(Number(driveId)) : Promise.resolve(null)])
      .then(([available, drive]) => {
        setCompanies(available)
        if (drive) {
          setValues({ company_id: drive.company_id, title: drive.title, description: drive.description, package_min: drive.package_min, package_max: drive.package_max, location: drive.location, employment_type: drive.employment_type, min_cgpa: drive.min_cgpa, max_backlogs: drive.max_backlogs, allowed_branches: drive.allowed_branches, graduation_year: drive.graduation_year, required_skills: drive.required_skills, application_deadline: drive.application_deadline })
          setBranches(drive.allowed_branches?.join(', ') || '')
          setSkills(drive.required_skills.join(', '))
          setDeadline(localDateTime(drive.application_deadline))
        } else if (available[0]) setValues((current) => ({ ...current, company_id: available[0].id }))
      })
      .catch((reason: unknown) => setError(getErrorMessage(reason, 'Could not load job drive data.')))
      .finally(() => setLoading(false))
  }, [driveId])

  function set<K extends keyof JobDriveInput>(key: K, value: JobDriveInput[K]) { setValues((current) => ({ ...current, [key]: value })) }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError('')
    const parseNames = (text: string) => text.split(',').map((item) => item.trim()).filter(Boolean)
    const payload: JobDriveInput = { ...values, allowed_branches: branches.trim() ? parseNames(branches) : null, required_skills: parseNames(skills), application_deadline: deadline ? new Date(deadline).toISOString() : null }
    try {
      const drive = editing ? await updateJobDrive(Number(driveId), payload) : await createJobDrive(payload)
      navigate(`${root}/${drive.id}`, { replace: true })
    } catch (reason) { setError(getErrorMessage(reason, 'Could not save the job drive.')) } finally { setSaving(false) }
  }

  if (loading) return <p className="text-sm text-muted">Loading job drive…</p>
  return <section className="mx-auto max-w-4xl space-y-6"><Link to={editing ? `${root}/${driveId}` : root} className="text-sm font-medium text-brand hover:underline">← Back to job drives</Link><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Administration</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{editing ? 'Edit job drive' : 'Create job drive'}</h1><p className="mt-2 text-sm text-muted">New drives are saved as drafts. Set a future deadline before publishing.</p></div><form onSubmit={submit} className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-panel sm:p-8">{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="grid gap-5 sm:grid-cols-2"><label className="form-label sm:col-span-2">Company<select className="form-input mt-2" required value={values.company_id || ''} onChange={(event) => set('company_id', Number(event.target.value))}><option value="" disabled>Select a company</option>{companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label><label className="form-label sm:col-span-2">Job title<input className="form-input mt-2" required minLength={2} maxLength={200} value={values.title} onChange={(event) => set('title', event.target.value)} /></label><label className="form-label sm:col-span-2">Description<textarea className="form-input mt-2 min-h-32" required minLength={20} maxLength={20000} value={values.description} onChange={(event) => set('description', event.target.value)} /></label><label className="form-label">Minimum package (LPA)<input className="form-input mt-2" type="number" min="0" step="0.01" value={values.package_min ?? ''} onChange={(event) => set('package_min', event.target.value ? Number(event.target.value) : null)} /></label><label className="form-label">Maximum package (LPA)<input className="form-input mt-2" type="number" min="0" step="0.01" value={values.package_max ?? ''} onChange={(event) => set('package_max', event.target.value ? Number(event.target.value) : null)} /></label><label className="form-label">Location<input className="form-input mt-2" maxLength={200} value={values.location || ''} onChange={(event) => set('location', event.target.value || null)} /></label><label className="form-label">Employment type<select className="form-input mt-2" value={values.employment_type || ''} onChange={(event) => set('employment_type', (event.target.value || null) as EmploymentType | null)}><option value="">Select type</option>{employmentTypes.map((type) => <option key={type} value={type}>{type.replace('_', ' ')}</option>)}</select></label><label className="form-label">Minimum CGPA<input className="form-input mt-2" type="number" min="0" max="10" step="0.01" value={values.min_cgpa ?? ''} onChange={(event) => set('min_cgpa', event.target.value ? Number(event.target.value) : null)} /></label><label className="form-label">Maximum backlogs<input className="form-input mt-2" type="number" min="0" step="1" value={values.max_backlogs ?? ''} onChange={(event) => set('max_backlogs', event.target.value ? Number(event.target.value) : null)} /></label><label className="form-label">Graduation year<input className="form-input mt-2" type="number" min="2000" max="2100" value={values.graduation_year ?? ''} onChange={(event) => set('graduation_year', event.target.value ? Number(event.target.value) : null)} /></label><label className="form-label">Application deadline<input className="form-input mt-2" type="datetime-local" value={deadline} onChange={(event) => setDeadline(event.target.value)} /><span className="mt-1 block text-xs text-muted">Required to publish. Local time is converted to UTC.</span></label><label className="form-label">Allowed branches<input className="form-input mt-2" placeholder="Leave blank for all branches" value={branches} onChange={(event) => setBranches(event.target.value)} /><span className="mt-1 block text-xs text-muted">Separate branch names with commas.</span></label><label className="form-label">Required skills<input className="form-input mt-2" placeholder="Python, SQL, Communication" value={skills} onChange={(event) => setSkills(event.target.value)} /><span className="mt-1 block text-xs text-muted">Separate skill names with commas.</span></label></div><div className="flex justify-end gap-3"><Link className="rounded-lg border border-slate-200 px-4 py-3 text-sm font-medium" to={editing ? `${root}/${driveId}` : root}>Cancel</Link><button className="primary-button inline-flex" disabled={saving || companies.length === 0}>{saving ? 'Saving…' : editing ? 'Save changes' : 'Save draft'}</button></div>{companies.length === 0 && <p className="text-right text-sm text-amber-700">Create or activate a company before creating a drive.</p>}</form></section>
}
