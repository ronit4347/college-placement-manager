import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import OpportunityCard from '../components/OpportunityCard'
import { fetchJobDrives, type JobDrive } from '../services/jobDrives'
import { fetchApplications, type ApplicationRecord } from '../services/applications'
import { fetchHealth } from '../services/health'
import type { HealthStatus } from '../types/health'

const journey = [
  ['01', 'Discover', 'Find opportunities that fit your goals.'],
  ['02', 'Check eligibility', 'See how your profile lines up with each role.'],
  ['03', 'Apply', 'Keep your applications together in one place.'],
  ['04', 'Get shortlisted', 'Track updates as your application progresses.'],
  ['05', 'Interview', 'Follow your rounds and upcoming schedule.'],
  ['06', 'Get selected', 'See each milestone as it is confirmed.'],
  ['07', 'Receive an offer', 'Review and respond when an offer arrives.'],
]

export default function HomePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [health, setHealth] = useState<HealthStatus>({ state: 'checking' })
  const [drives, setDrives] = useState<JobDrive[]>([])
  const [applications, setApplications] = useState<ApplicationRecord[]>([])
  const [loadingData, setLoadingData] = useState(false)
  const [search, setSearch] = useState('')
  const role = user?.role
  const drivePath = role === 'ADMIN' ? '/admin/job-drives' : role === 'RECRUITER' ? '/recruiter/job-drives' : '/student/job-drives'
  const explorePath = role === 'INTERVIEWER' ? '/interviewer/interviews' : drivePath

  useEffect(() => {
    let active = true
    fetchHealth().then((result) => active && setHealth({ state: 'online', message: result.status })).catch(() => active && setHealth({ state: 'offline' }))
    if (role && role !== 'INTERVIEWER') {
      setLoadingData(true)
      Promise.all([fetchJobDrives({ limit: 100 }), fetchApplications({ limit: 100 })])
        .then(([jobs, apps]) => { if (active) { setDrives(jobs); setApplications(apps) } })
        .catch(() => { if (active) { setDrives([]); setApplications([]) } })
        .finally(() => active && setLoadingData(false))
    }
    return () => { active = false }
  }, [role])

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const suffix = search.trim() ? `?q=${encodeURIComponent(search.trim())}` : ''
    if (user && role !== 'INTERVIEWER') navigate(`${drivePath}${suffix}`)
    else if (user) navigate(explorePath)
    else navigate('/login', { state: { from: { pathname: '/student/job-drives', search: suffix } } })
  }

  const visibleDrives = drives.filter((drive) => drive.status === 'PUBLISHED').slice(0, 3)
  const featuredCompanies = Array.from(new Set(drives.filter((drive) => drive.status === 'PUBLISHED').map((drive) => drive.company_name))).slice(0, 6)
  const placementRoute = role === 'STUDENT' ? '/student' : role === 'ADMIN' ? '/admin' : role === 'RECRUITER' ? '/recruiter' : '/interviewer'

  return <div className="landing-page">
    <section className="hero-section" aria-labelledby="hero-title">
      <div className="hero-glow hero-glow-one" aria-hidden="true" /><div className="hero-glow hero-glow-two" aria-hidden="true" />
      <div className="hero-inner">
        <div className="hero-copy">
          <div className="eyebrow eyebrow-light"><span className="eyebrow-spark">✳</span> A clearer path from campus to career</div>
          <h1 id="hero-title">Your next opportunity <em>starts here.</em></h1>
          <p>Discover campus roles, understand your eligibility, and follow every step from application to offer — all in one place.</p>
          <form className="hero-search" onSubmit={submitSearch} role="search">
            <span className="search-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></svg></span>
            <label className="sr-only" htmlFor="opportunity-search">Search jobs, internships, companies</label>
            <input id="opportunity-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search jobs, internships, companies" />
            <button type="submit">Explore <span aria-hidden="true">→</span></button>
          </form>
          <div className="hero-actions"><Link to={user ? explorePath : '/register'} className="button button-lime">{user ? role === 'INTERVIEWER' ? 'Open interview workspace' : 'Explore opportunities' : 'Get started'} <span aria-hidden="true">↗</span></Link><a href="#how-it-works" className="hero-secondary">See how it works <span aria-hidden="true">↓</span></a></div>
          <div className="hero-proof"><span className="proof-avatars" aria-hidden="true"><i>CP</i><i>↗</i><i>✓</i></span><span>One connected journey for students and campus teams</span></div>
        </div>
        <div className="hero-visual" aria-label="Preview of the opportunity workspace">
          <div className="visual-orbit orbit-a" aria-hidden="true" /><div className="visual-orbit orbit-b" aria-hidden="true" />
          <div className="preview-window">
            <div className="preview-topbar"><div className="preview-brand"><span className="preview-mark">C</span><span>Career hub</span></div><span className="preview-menu-dots">•••</span></div>
            <div className="preview-content"><div className="preview-greeting"><div><span className="preview-caption">YOUR NEXT CHAPTER</span><strong>Find your kind of work.</strong></div><span className="preview-sun">✳</span></div>
              <div className="preview-mini-search"><span>⌕</span> Roles that match your skills <kbd>⌘ K</kbd></div>
              <div className="preview-section-line"><span>Picked for you</span><span className="preview-live"><i /> Connected to your profile</span></div>
              <div className="preview-job"><span className="preview-company-icon icon-violet">N</span><div className="preview-job-copy"><strong>Opportunity discovery</strong><span>Role details · eligibility · next step</span><div className="preview-chip-line"><i>Skills match</i><i>Deadline visible</i></div></div><span className="preview-arrow">↗</span></div>
              <div className="preview-job preview-job-secondary"><span className="preview-company-icon icon-lime">+</span><div className="preview-job-copy"><strong>Application journey</strong><span>Applied <b>→</b> Interview <b>→</b> Offer</span></div><span className="preview-progress"><i /></span></div>
              <div className="preview-bottom"><div><span className="preview-caption">YOUR MOMENTUM</span><strong>Everything in one view</strong></div><div className="preview-bars" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></div></div>
            </div>
          </div>
          <div className="floating-note note-match"><span className="note-check">✓</span><div><strong>Eligibility, made clear</strong><span>Based on your profile</span></div></div>
          <div className="floating-note note-interview"><span className="note-calendar">▦</span><div><strong>Stay in the loop</strong><span>Application updates</span></div><i className="note-dot" /></div>
          <span className="hero-stamp" aria-hidden="true">CAMPUS<br />TO CAREER</span>
        </div>
      </div>
      <div className="hero-bottom"><span><i className={health.state === 'online' ? 'connection-dot is-online' : health.state === 'offline' ? 'connection-dot is-offline' : 'connection-dot'} />{health.state === 'online' ? 'Platform services connected' : health.state === 'offline' ? 'Platform API currently unavailable' : 'Connecting to platform'}</span><span>Built for the complete campus hiring journey</span></div>
    </section>

    <section className="signal-strip" aria-label="Live platform information">
      <div className="signal-intro"><span className="eyebrow">A shared career workspace</span><h2>One place to move forward.</h2></div>
      <div className="signal-items">
        {user && role === 'INTERVIEWER' ? <>
          <div className="signal-item"><strong>Assigned</strong><span>Candidate interviews</span></div>
          <div className="signal-item"><strong>Evaluate</strong><span>Feedback and results</span></div>
          <div className="signal-item signal-link"><Link to={placementRoute}>Open interview workspace <span>↗</span></Link><span>Assigned interviews are private</span></div>
        </> : user ? <>
          <div className="signal-item"><strong>{loadingData ? '—' : drives.length}</strong><span>opportunities loaded</span></div>
          <div className="signal-item"><strong>{loadingData ? '—' : applications.length}</strong><span>{role === 'STUDENT' ? 'applications loaded' : 'applications in this view'}</span></div>
          <div className="signal-item signal-link"><Link to={placementRoute}>Open your workspace <span>↗</span></Link><span>Live data · latest 100 records</span></div>
        </> : <>
          <div className="signal-item"><strong>Discover</strong><span>Roles from your campus</span></div>
          <div className="signal-item"><strong>Navigate</strong><span>Every stage in one view</span></div>
          <div className="signal-item signal-link"><Link to="/register">Create your student account <span>↗</span></Link><span>Start with your profile</span></div>
        </>}
      </div>
    </section>

    <section id="opportunities" className="landing-section opportunity-section">
      <div className="section-heading"><div><span className="eyebrow">Find your next move</span><h2>Explore opportunities</h2><p>Thoughtful discovery, transparent eligibility, and the details you need to decide.</p></div><Link className="text-link" to={user ? explorePath : '/login'}>{role === 'INTERVIEWER' ? 'Open interview workspace' : 'Browse opportunities'} <span>↗</span></Link></div>
      {visibleDrives.length ? <div className="opportunity-grid">{visibleDrives.map((drive) => <OpportunityCard key={drive.id} drive={drive} audience={role === 'ADMIN' ? 'ADMIN' : role === 'RECRUITER' ? 'RECRUITER' : 'STUDENT'} to={`${drivePath}/${drive.id}`} />)}</div> : <div className="opportunity-preview-panel"><div className="preview-icon-stack"><span>⌕</span><span>↗</span><span>✓</span></div><div><h3>{user ? role === 'INTERVIEWER' ? 'Your interview workspace is ready' : loadingData ? 'Finding opportunities in your workspace…' : 'Your opportunity feed is ready' : 'A focused feed for your next step'}</h3><p>{user ? role === 'INTERVIEWER' ? 'Open your assigned interviews, candidate details, and evaluation workspace.' : loadingData ? 'Loading published opportunities from your account.' : 'Open published opportunities, real eligibility, and application status from your campus.' : 'Sign in to explore published campus opportunities and check your eligibility against each role.'}</p></div><Link className="button button-dark" to={user ? explorePath : '/login'}>{user ? role === 'INTERVIEWER' ? 'View assigned interviews' : 'Open opportunities' : 'Sign in to explore'} <span>→</span></Link></div>}
    </section>

    <section id="companies" className="company-discovery-section"><div className="section-heading"><div><span className="eyebrow">Meet the teams hiring</span><h2>Companies on your campus</h2><p>Discover employers through their published opportunities. Company information reflects the hiring data available to your account.</p></div><Link className="text-link" to={user ? explorePath : '/login'}>See opportunities <span>↗</span></Link></div>
      {featuredCompanies.length ? <div className="company-discovery-grid">{featuredCompanies.map((company) => <Link key={company} to={user && role !== 'INTERVIEWER' ? `${drivePath}?q=${encodeURIComponent(company)}` : user ? explorePath : '/login'} className="company-discovery-card"><span className="company-discovery-mark">{company.split(/\s+/).filter(Boolean).slice(0,2).map((part) => part[0]?.toUpperCase()).join('')}</span><span><strong>{company}</strong><small>Hiring through campus opportunities</small></span><i>↗</i></Link>)}</div> : <div className="company-discovery-empty"><span aria-hidden="true">▤</span><p>{user ? 'Company profiles will appear here when published opportunities are available.' : 'Sign in to discover the employers hiring through your campus.'}</p><Link to={user ? explorePath : '/login'}>{user ? 'Open your workspace' : 'Sign in to discover companies'} <span>↗</span></Link></div>}
    </section>

    <section id="interests" className="category-section"><div className="category-copy"><span className="eyebrow eyebrow-light">Explore by interest</span><h2>Bring your skills<br />to the right place.</h2><p>From building products to keeping systems running, discover paths that fit what you want to do next.</p><Link className="button button-lime" to={user ? explorePath : '/login'}>Find your path <span>↗</span></Link></div><div className="category-grid">
      {[
        ['01', 'Software engineering', '</>'], ['02', 'Data & AI', '⌁'], ['03', 'Cloud & platform', '◌'], ['04', 'Product & design', '✳'], ['05', 'Quality engineering', '✓'], ['06', 'Network & security', '⌘'],
      ].map(([number, label, icon]) => <Link className="category-tile" key={number} to={user ? role === 'INTERVIEWER' ? explorePath : `${drivePath}?q=${encodeURIComponent(label)}` : '/login'}><span className="category-number">{number}</span><span className="category-icon" aria-hidden="true">{icon}</span><strong>{label}</strong><span className="category-arrow" aria-hidden="true">↗</span></Link>)}
    </div></section>

    <section id="students" className="ai-feature-section"><div className="ai-feature-copy"><span className="eyebrow">Career tools, built in</span><h2>Make your resume<br /><em>work smarter.</em></h2><p>Get a clearer view of how your resume maps to a role. See relevant skills, potential gaps, and practical ways to strengthen your application.</p><ul className="ai-points"><li><span>✓</span> Skills detected from your resume</li><li><span>✓</span> Role-specific match insights</li><li><span>✓</span> Actionable improvement suggestions</li></ul><p className="ai-boundary">AI analysis is decision support for students. It never selects or rejects candidates.</p><Link className="button button-dark" to={user ? role === 'STUDENT' ? '/student' : placementRoute : '/register'}>{user ? role === 'STUDENT' ? 'Open your career dashboard' : 'Open your workspace' : 'Create your account'} <span>↗</span></Link></div>
      <div className="analysis-preview"><div className="analysis-preview-header"><div><span className="analysis-kicker">RESUME INSIGHTS</span><strong>Role compatibility</strong></div><span className="analysis-status"><i /> Analysis ready</span></div><div className="analysis-meter"><div className="meter-ring"><div><strong>—</strong><span>match</span></div></div><div className="meter-copy"><strong>See where you align</strong><span>Your analysis uses your resume and the selected job description.</span></div></div><div className="analysis-divider" /><div className="analysis-list-title"><strong>Skills and signals</strong><span>Personalized</span></div><div className="analysis-skill-row"><span className="skill-symbol skill-good">✓</span><div><strong>Matching skills</strong><span>Skills already represented in your resume</span></div><b>View</b></div><div className="analysis-skill-row"><span className="skill-symbol skill-growth">＋</span><div><strong>Growth opportunities</strong><span>Areas you could make more visible</span></div><b>View</b></div><div className="analysis-tip"><span>✳</span><p>Suggestions help you improve your resume. Hiring decisions remain with authorized people.</p></div></div>
    </section>

    <section id="how-it-works" className="journey-section"><div className="section-heading"><div><span className="eyebrow">From first look to first day</span><h2>A connected placement journey</h2><p>Each step stays visible, so you know where things stand and what comes next.</p></div></div><div className="journey-grid">{journey.map(([number, title, detail], index) => <article className="journey-step" key={number}><div className="journey-step-top"><span>{number}</span>{index < journey.length - 1 && <i aria-hidden="true" />}</div><h3>{title}</h3><p>{detail}</p></article>)}</div></section>

    <section className="audience-section"><div className="audience-card audience-students"><span className="audience-mark">01 / STUDENTS</span><h2>Your career journey,<br />in your hands.</h2><p>Discover roles, track applications, prepare for interviews, and respond to offers with a clearer view of every next step.</p><div className="audience-tags"><span>Opportunities</span><span>Application tracking</span><span>Resume insights</span></div><Link to={user ? '/student' : '/register'} className="audience-link">For students <span>↗</span></Link><span className="audience-graphic student-graphic" aria-hidden="true"><i>✳</i><b>→</b><i>✓</i></span></div>
      <div className="audience-card audience-recruiters"><span className="audience-mark">02 / RECRUITERS</span><h2>Hire campus talent<br />with more clarity.</h2><p>Keep company job drives and candidate applications in one focused hiring workspace, with role and application status close at hand.</p><div className="audience-tags"><span>Company job drives</span><span>Applicants</span><span>Offers</span></div><Link to={user?.role === 'RECRUITER' ? '/recruiter' : '/login'} className="audience-link">For recruiters <span>↗</span></Link><span className="audience-graphic team-graphic" aria-hidden="true"><i>▥</i><b>◌</b><i>↗</i></span></div></section>

    <section id="recruiters" className="college-feature"><div className="college-feature-copy"><span className="eyebrow eyebrow-light">For colleges and placement officers</span><h2>Manage the complete placement lifecycle in one platform.</h2><p>A reliable view across students, employers, opportunities, interviews, offers, and outcomes — with role-based access for the people who need it.</p><Link to={user?.role === 'ADMIN' ? '/admin' : '/login'} className="button button-lime">See the placement workspace <span>↗</span></Link></div><div className="lifecycle-visual" aria-label="Students to placement outcome"><div className="lifecycle-node"><span>01</span><strong>Students</strong><i>↗</i></div><div className="lifecycle-node"><span>02</span><strong>Opportunities</strong><i>↗</i></div><div className="lifecycle-node"><span>03</span><strong>Interviews</strong><i>↗</i></div><div className="lifecycle-node lifecycle-node-active"><span>04</span><strong>Outcomes</strong><i>✓</i></div><div className="lifecycle-line" /></div></section>

    <section className="final-cta"><div><span className="eyebrow">Your next step is closer</span><h2>Ready to move forward?</h2><p>Start with a student profile and explore the opportunities available through your campus.</p></div><Link className="button button-dark" to={user ? placementRoute : '/register'}>{user ? 'Go to your workspace' : 'Create a student account'} <span>↗</span></Link><span className="cta-star" aria-hidden="true">✳</span></section>

    <footer className="landing-footer"><div className="footer-brand"><span className="brand-mark">CP</span><div><strong>Campus</strong><span>Placement Manager</span></div><p>From campus potential to career possibility.</p></div><div className="footer-links"><div><strong>Discover</strong><a href="#opportunities">Opportunities</a><a href="#companies">Career paths</a></div><div><strong>Your journey</strong><a href="#students">For students</a><a href="#how-it-works">How it works</a></div><div><strong>Platform</strong><a href="#recruiters">For placement teams</a><Link to="/login">Sign in</Link></div></div><div className="footer-bottom"><span>© {new Date().getFullYear()} College Placement Manager</span><span>Designed for the campus-to-career journey.</span></div></footer>
  </div>
}
