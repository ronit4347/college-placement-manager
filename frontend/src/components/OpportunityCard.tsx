import { Link } from 'react-router-dom'
import type { JobDrive } from '../services/jobDrives'

function formatPackage(drive: JobDrive) {
  if (drive.package_min == null && drive.package_max == null) return 'Compensation not listed'
  if (drive.package_min == null) return `Up to ${drive.package_max} LPA`
  if (drive.package_max == null || drive.package_min === drive.package_max) return `${drive.package_min} LPA`
  return `${drive.package_min}–${drive.package_max} LPA`
}

function initials(company: string) {
  return company.split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]?.toUpperCase()).join('') || 'CO'
}

export default function OpportunityCard({ drive, to, audience = 'STUDENT' }: { drive: JobDrive; to: string; audience?: 'STUDENT' | 'ADMIN' | 'RECRUITER' }) {
  const deadline = drive.application_deadline ? new Date(drive.application_deadline) : null
  const deadlinePassed = deadline !== null && deadline.getTime() <= Date.now()
  return <article className="opportunity-card">
    <div className="opportunity-card-top">
      <span className="company-avatar" aria-hidden="true">{initials(drive.company_name)}</span>
      <div className="opportunity-company"><span>{drive.company_name}</span><span className="company-verified" aria-label="Company opportunity">✓</span></div>
      <span className={`status-pill ${drive.status === 'PUBLISHED' ? 'status-live' : drive.status === 'DRAFT' ? 'status-pending' : 'status-neutral'}`}>{drive.status.toLowerCase()}</span>
    </div>
    <Link to={to} className="opportunity-title"><h2>{drive.title}</h2></Link>
    <p className="opportunity-description">{drive.description}</p>
    <div className="opportunity-facts">
      <span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/></svg>{drive.location || 'Location flexible'}</span>
      <span><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18"/></svg>{drive.employment_type?.replace('_', ' ').toLowerCase() || 'Opportunity'}</span>
      <span className="opportunity-compensation">{formatPackage(drive)}</span>
    </div>
    {drive.required_skills.length > 0 && <div className="opportunity-skills">{drive.required_skills.slice(0, 3).map((skill) => <span key={skill}>{skill}</span>)}{drive.required_skills.length > 3 && <span>+{drive.required_skills.length - 3}</span>}</div>}
    <div className="opportunity-card-footer">
      <div className="opportunity-fit">
        {audience === 'STUDENT' && drive.is_eligible !== undefined && drive.is_eligible !== null && <span className={`fit-indicator ${drive.is_eligible ? 'fit-yes' : 'fit-no'}`}><i />{drive.is_eligible ? 'Eligible' : 'Check fit'}</span>}
        {audience === 'STUDENT' && drive.application_status && <span className="status-pill status-neutral">{drive.application_status.toLowerCase()}</span>}
        {deadline && <span className={deadlinePassed ? 'deadline-passed' : ''}>{deadlinePassed ? 'Deadline passed' : `Apply by ${deadline.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`}</span>}
      </div>
      <Link className="opportunity-link" to={to} aria-label={`View ${drive.title} at ${drive.company_name}`}>View details <span aria-hidden="true">↗</span></Link>
    </div>
  </article>
}
