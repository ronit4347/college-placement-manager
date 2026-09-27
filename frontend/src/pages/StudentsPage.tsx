import { useEffect, useState } from 'react'
import Pagination from '../components/Pagination'
import { fetchAdminStudents, type AdminStudent, type AdminStudentFilters } from '../services/students'
import { getErrorMessage } from '../utils/errors'

const PAGE_SIZE = 20
const placementStatuses: NonNullable<AdminStudentFilters['placement_status']>[] = ['NOT_APPLIED', 'APPLIED', 'SHORTLISTED', 'INTERVIEW', 'SELECTED', 'OFFERED', 'REJECTED', 'PLACED']

export default function StudentsPage() {
  const [students, setStudents] = useState<AdminStudent[]>([])
  const [query, setQuery] = useState('')
  const [rollNumber, setRollNumber] = useState('')
  const [branch, setBranch] = useState('')
  const [minCgpa, setMinCgpa] = useState('')
  const [maxCgpa, setMaxCgpa] = useState('')
  const [placementStatus, setPlacementStatus] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    const filters: AdminStudentFilters = { q: query || undefined, roll_number: rollNumber || undefined, branch: branch || undefined,
      min_cgpa: minCgpa ? Number(minCgpa) : undefined, max_cgpa: maxCgpa ? Number(maxCgpa) : undefined,
      placement_status: (placementStatus || undefined) as AdminStudentFilters['placement_status'], limit: PAGE_SIZE + 1, offset: (page - 1) * PAGE_SIZE }
    fetchAdminStudents(filters).then((items) => { if (active) { setStudents(items); setError('') } })
      .catch((reason: unknown) => { if (active) setError(getErrorMessage(reason, 'Could not load students.')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [query, rollNumber, branch, minCgpa, maxCgpa, placementStatus, page])

  function change(setter: (value: string) => void, value: string) { setter(value); setPage(1) }
  return <section className="space-y-6"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Administration</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Students</h1><p className="mt-2 text-sm text-muted">Find students by name, roll number, branch, academic performance, and placement progress.</p></div>
    <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2 lg:grid-cols-3"><label className="form-label">Student name<input className="form-input mt-2" value={query} onChange={(event) => change(setQuery, event.target.value)} placeholder="Search name or email" /></label><label className="form-label">Roll number<input className="form-input mt-2" value={rollNumber} onChange={(event) => change(setRollNumber, event.target.value)} placeholder="Search roll number" /></label><label className="form-label">Branch<input className="form-input mt-2" value={branch} onChange={(event) => change(setBranch, event.target.value)} placeholder="Filter branch" /></label><label className="form-label">Minimum CGPA<input className="form-input mt-2" type="number" min="0" max="10" step="0.01" value={minCgpa} onChange={(event) => change(setMinCgpa, event.target.value)} /></label><label className="form-label">Maximum CGPA<input className="form-input mt-2" type="number" min="0" max="10" step="0.01" value={maxCgpa} onChange={(event) => change(setMaxCgpa, event.target.value)} /></label><label className="form-label">Placement status<select className="form-input mt-2" value={placementStatus} onChange={(event) => change(setPlacementStatus, event.target.value)}><option value="">All statuses</option>{placementStatuses.map((item) => <option key={item}>{item === 'JOINED' ? 'PLACED' : item.replace('_', ' ')}</option>)}</select></label></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {loading ? <p role="status" className="text-sm text-muted">Loading students…</p> : students.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-muted">No students match these filters.</div> : <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">Student</th><th className="px-5 py-3">Roll number</th><th className="px-5 py-3">Branch</th><th className="px-5 py-3">CGPA</th><th className="px-5 py-3">Placement status</th><th className="px-5 py-3">Graduation</th></tr></thead><tbody className="divide-y divide-slate-100">{students.slice(0, PAGE_SIZE).map((student) => <tr key={student.student_id ?? student.email} className="hover:bg-slate-50"><td className="px-5 py-4"><p className="font-semibold">{student.full_name}</p><p className="text-xs text-muted">{student.email}</p></td><td className="px-5 py-4">{student.roll_number || '—'}</td><td className="px-5 py-4">{student.branch || '—'}</td><td className="px-5 py-4">{student.cgpa ?? '—'}</td><td className="px-5 py-4"><span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-800">{student.placement_status}</span></td><td className="px-5 py-4">{student.graduation_year ?? '—'}</td></tr>)}</tbody></table></div></div>}
    {!loading && students.length > 0 && <Pagination page={page} canGoNext={students.length > PAGE_SIZE} onPageChange={setPage} />}
  </section>
}
