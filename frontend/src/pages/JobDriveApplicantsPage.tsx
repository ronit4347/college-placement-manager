import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchApplicants, fetchJobDrive, type Applicant, type JobDrive } from '../services/jobDrives'
import { getErrorMessage } from '../utils/errors'

export default function JobDriveApplicantsPage() {
  const { driveId } = useParams()
  const [drive, setDrive] = useState<JobDrive | null>(null)
  const [applicants, setApplicants] = useState<Applicant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!driveId) return
    Promise.all([fetchJobDrive(Number(driveId)), fetchApplicants(Number(driveId))])
      .then(([detail, records]) => { setDrive(detail); setApplicants(records) })
      .catch((reason: unknown) => setError(getErrorMessage(reason, 'Could not load applicants.')))
      .finally(() => setLoading(false))
  }, [driveId])

  return <section className="space-y-6"><Link to={`/admin/job-drives/${driveId}`} className="text-sm font-medium text-brand hover:underline">← Back to job drive</Link><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Applicant review</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{drive ? `${drive.title} applicants` : 'Applicants'}</h1>{drive && <p className="mt-2 text-sm text-muted">{drive.company_name}</p>}</div>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}{loading ? <p className="text-sm text-muted">Loading applicants…</p> : applicants.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center"><h2 className="font-semibold">No applicants yet</h2><p className="mt-2 text-sm text-muted">Application submission will be available in a later milestone.</p></div> : <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Student</th><th className="px-5 py-3">Roll number</th><th className="px-5 py-3">Branch</th><th className="px-5 py-3">CGPA</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Applied</th></tr></thead><tbody className="divide-y divide-slate-100">{applicants.map((applicant) => <tr key={applicant.application_id}><td className="px-5 py-4"><p className="font-medium">{applicant.student_name}</p><p className="text-xs text-muted">{applicant.email}</p></td><td className="px-5 py-4">{applicant.roll_number || '—'}</td><td className="px-5 py-4">{applicant.branch || '—'}</td><td className="px-5 py-4">{applicant.cgpa ?? '—'}</td><td className="px-5 py-4">{applicant.status}</td><td className="px-5 py-4">{new Date(applicant.applied_at).toLocaleDateString()}</td></tr>)}</tbody></table></div></div>}</section>
}
