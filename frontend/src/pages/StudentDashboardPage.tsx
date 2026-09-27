import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { CSSProperties, FormEvent } from 'react'
import { getErrorMessage } from '../utils/errors'
import { useAuth } from '../context/AuthContext'
import {
  downloadStudentResume,
  fetchStudentProfile,
  updateStudentProfile,
  updateStudentSkills,
  uploadStudentResume,
} from '../services/students'
import type { StudentProfile, StudentProfileUpdate } from '../services/students'
import StudentPlacementOverview from '../components/StudentPlacementOverview'

interface ProfileDraft {
  full_name: string
  email: string
  phone: string
  roll_number: string
  branch: string
  cgpa: string
  graduation_year: string
  backlogs: string
}

function formatFileSize(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MiB`
    : `${Math.ceil(bytes / 1024)} KiB`
}

const EMPTY_DRAFT: ProfileDraft = {
  full_name: '', email: '', phone: '', roll_number: '', branch: '', cgpa: '', graduation_year: '', backlogs: '',
}

function toDraft(profile: StudentProfile): ProfileDraft {
  return {
    full_name: profile.full_name,
    email: profile.email,
    phone: profile.phone ?? '',
    roll_number: profile.roll_number ?? '',
    branch: profile.branch ?? '',
    cgpa: profile.cgpa === null ? '' : String(profile.cgpa),
    graduation_year: profile.graduation_year === null ? '' : String(profile.graduation_year),
    backlogs: profile.backlogs === null ? '' : String(profile.backlogs),
  }
}

export default function StudentDashboardPage() {
  const { refreshUser, user } = useAuth()
  const [profile, setProfile] = useState<StudentProfile | null>(null)
  const [draft, setDraft] = useState(EMPTY_DRAFT)
  const [skillsText, setSkillsText] = useState('')
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchStudentProfile()
      .then((result) => {
        if (!active) return
        setProfile(result)
        setDraft(toDraft(result))
        setSkillsText(result.skills.join(', '))
      })
      .catch((requestError) => active && setError(getErrorMessage(requestError, 'Could not load your student profile.')))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  function updateDraft(field: keyof ProfileDraft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  function applyProfile(result: StudentProfile) {
    setProfile(result)
    setDraft(toDraft(result))
    setSkillsText(result.skills.join(', '))
  }

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    const payload: StudentProfileUpdate = {
      full_name: draft.full_name,
      email: draft.email,
      phone: draft.phone.trim() || null,
      roll_number: draft.roll_number.trim() || null,
      branch: draft.branch.trim() || null,
      cgpa: draft.cgpa === '' ? null : Number(draft.cgpa),
      graduation_year: draft.graduation_year === '' ? null : Number(draft.graduation_year),
      ...(draft.backlogs === '' ? {} : { backlogs: Number(draft.backlogs) }),
    }
    try {
      applyProfile(await updateStudentProfile(payload))
      await refreshUser()
      setNotice('Profile saved.')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Could not save your profile.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleSkillsSave() {
    setSaving(true)
    setError('')
    setNotice('')
    const skills = skillsText.split(',').map((skill) => skill.trim()).filter(Boolean)
    try {
      applyProfile(await updateStudentSkills(skills))
      setNotice('Skills updated.')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Could not update your skills.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleResumeUpload() {
    if (!resumeFile) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      applyProfile(await uploadStudentResume(resumeFile))
      setResumeFile(null)
      setNotice('Resume uploaded.')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Could not upload your resume.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleResumeDownload() {
    try {
      const objectUrl = await downloadStudentResume()
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = 'resume.pdf'
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Could not download your resume.'))
    }
  }

  if (loading) return <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-muted" role="status">Loading your profile…</div>
  if (!profile) return <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700" role="alert">{error || 'Could not load your profile.'}</p>
  const firstName = user?.full_name.trim().split(/\s+/)[0] || 'there'
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="student-dashboard-page">
      <section className="student-welcome-banner">
        <div className="student-welcome-copy"><span className="eyebrow eyebrow-light">Your career space</span><h1>{greeting}, {firstName}.</h1><p>Small steps add up. See what’s moving, what’s next, and where you can go from here.</p>
          <div className="student-welcome-actions"><Link to="/student/job-drives" className="button button-lime">Explore opportunities <span>↗</span></Link><Link to="/applications" className="welcome-secondary-link">Track applications <span>→</span></Link></div>
        </div>
        <div className="profile-progress-card"><div className="profile-progress-ring" style={{ '--profile-progress': `${profile.profile_completion}%` } as CSSProperties}><div><strong>{profile.profile_completion}%</strong><span>complete</span></div></div><div><strong>Your profile</strong><span>{profile.profile_completion >= 80 ? 'You’re ready to explore roles.' : 'Add a little more to improve your job matches.'}</span></div><a href="#profile-details">Complete profile <span>↗</span></a></div>
      </section>

      {error && <p className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">{error}</p>}
      {notice && <p className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700" role="status">{notice}</p>}

      <StudentPlacementOverview profile={profile} />

      <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <form id="profile-details" className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-panel sm:p-8" onSubmit={handleProfileSubmit}>
          <div><p className="eyebrow">Your profile</p><h2 className="mt-2 text-lg font-semibold">Personal and academic details</h2><p className="mt-1 text-sm text-muted">Keep the details recruiters use to understand your placement profile current.</p></div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="form-label">Full name<input className="form-input mt-2" required minLength={2} maxLength={160} autoComplete="name" value={draft.full_name} onChange={(event) => updateDraft('full_name', event.target.value)} /></label>
            <label className="form-label">Email<input className="form-input mt-2" type="email" required maxLength={320} autoComplete="email" value={draft.email} onChange={(event) => updateDraft('email', event.target.value)} /></label>
            <label className="form-label">Phone<input className="form-input mt-2" type="tel" maxLength={32} autoComplete="tel" value={draft.phone} onChange={(event) => updateDraft('phone', event.target.value)} placeholder="+1 555 123 4567" /></label>
            <label className="form-label">Roll number<input className="form-input mt-2" maxLength={40} value={draft.roll_number} onChange={(event) => updateDraft('roll_number', event.target.value)} placeholder="e.g. CS-2027-014" /></label>
            <label className="form-label">Branch<input className="form-input mt-2" maxLength={120} value={draft.branch} onChange={(event) => updateDraft('branch', event.target.value)} placeholder="e.g. Computer Science" /></label>
            <label className="form-label">CGPA<input className="form-input mt-2" type="number" min="0" max="10" step="0.01" value={draft.cgpa} onChange={(event) => updateDraft('cgpa', event.target.value)} placeholder="0.00–10.00" /></label>
            <label className="form-label">Graduation year<input className="form-input mt-2" type="number" min="2000" max="2100" step="1" value={draft.graduation_year} onChange={(event) => updateDraft('graduation_year', event.target.value)} /></label>
            <label className="form-label">Backlogs<input className="form-input mt-2" type="number" min="0" step="1" value={draft.backlogs} onChange={(event) => updateDraft('backlogs', event.target.value)} /></label>
          </div>
          <button className="primary-button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button>
        </form>

        <div className="space-y-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel">
            <h2 className="text-lg font-semibold">Skills</h2>
            <p className="mt-1 text-sm text-muted">Enter skills separated by commas.</p>
            <label className="sr-only" htmlFor="student-skills">Your skills</label>
            <textarea id="student-skills" className="form-input mt-4 min-h-28 resize-y" maxLength={5100} value={skillsText} onChange={(event) => setSkillsText(event.target.value)} placeholder="Python, SQL, React" />
            <div className="mt-4 flex flex-wrap gap-2">
              {profile.skills.length ? profile.skills.map((skill) => <span key={skill} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{skill}</span>) : <span className="text-sm text-muted">No skills added yet.</span>}
            </div>
            <button className="primary-button mt-5" type="button" disabled={saving} onClick={handleSkillsSave}>Save skills</button>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-panel">
            <h2 className="text-lg font-semibold">Resume</h2>
            <p className="mt-1 text-sm leading-6 text-muted">Upload a PDF resume up to {formatFileSize(profile.resume_max_size_bytes)}. A new upload replaces the previous file.</p>
            {profile.resume_filename && <button className="mt-3 text-sm font-semibold text-brand hover:underline" type="button" onClick={handleResumeDownload}>Download current resume</button>}
            <label className="form-label mt-4 block">Choose PDF
              <input className="mt-2 block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium" type="file" accept="application/pdf,.pdf" onChange={(event) => setResumeFile(event.target.files?.[0] ?? null)} />
            </label>
            {resumeFile && <p className="mt-2 truncate text-xs text-muted">{resumeFile.name} · {(resumeFile.size / (1024 * 1024)).toFixed(2)} MB</p>}
            {resumeFile && resumeFile.size > profile.resume_max_size_bytes && <p className="mt-2 text-xs text-rose-700">This file exceeds your configured upload limit.</p>}
            <button className="primary-button mt-5" type="button" disabled={saving || !resumeFile || resumeFile.size > profile.resume_max_size_bytes} onClick={handleResumeUpload}>Upload resume</button>
          </section>
        </div>
      </div>
    </div>
  )
}
