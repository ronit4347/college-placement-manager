import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import type { UserRole } from '../types/auth'
import NotificationMenu from '../components/NotificationMenu'

type NavItem = { label: string; to: string; end?: boolean; icon: string }
const iconPaths: Record<string, string[]> = {
  overview: ['M3.5 13h7V3.5h-7z', 'M13.5 20.5h7V11h-7z', 'M13.5 3.5h7v4h-7z', 'M3.5 20.5h7v-4h-7z'],
  students: ['M16 20v-1.5a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4V20', 'M9.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z', 'M17 3.2a4 4 0 0 1 0 7.6', 'M21 20v-1.5a4 4 0 0 0-3-3.87'],
  companies: ['M3 20.5h18', 'M5 20V5.5l7-2 7 2V20', 'M9 8h.01M15 8h.01M9 12h.01M15 12h.01', 'M10 20v-4h4v4'],
  drives: ['M4 7.5h16v12H4z', 'M8 7.5V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2.5', 'M4 12h16', 'M10 12v2h4v-2'],
  applications: ['M6 3.5h8l4 4V20H6z', 'M14 3.5V8h4', 'M9 12h6M9 15.5h6'],
  interviews: ['M4 5.5h16v11H9l-5 3z', 'M8 10h.01M12 10h.01M16 10h.01'],
  offers: ['M5 4h14v16H5z', 'M8 8h8M8 11.5h8M8 15h5'],
  explore: ['M10.8 17.2a6.4 6.4 0 1 0 0-12.8 6.4 6.4 0 0 0 0 12.8Z', 'm16 16 4.5 4.5'],
}
const iconNames: Record<string, string> = { '◫': 'overview', '♙': 'students', '▤': 'companies', '◷': 'drives', '▧': 'applications', '◉': 'interviews', '▱': 'offers', '⌕': 'explore' }

const navigation: Record<UserRole, NavItem[]> = {
  ADMIN: [
    { label: 'Overview & analytics', to: '/admin', end: true, icon: '◫' },
    { label: 'Students', to: '/admin/students', icon: '♙' },
    { label: 'Interviewers', to: '/admin/interviewers', icon: '◉' },
    { label: 'Companies', to: '/admin/companies', icon: '▤' },
    { label: 'Job drives', to: '/admin/job-drives', icon: '◷' },
    { label: 'Applications', to: '/applications', icon: '▧' },
    { label: 'Interviews', to: '/admin/interviews', icon: '◉' },
    { label: 'Offers', to: '/admin/offers', icon: '▱' },
  ],
  STUDENT: [
    { label: 'My dashboard', to: '/student', end: true, icon: '◫' },
    { label: 'Explore jobs', to: '/student/job-drives', icon: '⌕' },
    { label: 'Applications', to: '/applications', icon: '▧' },
    { label: 'Interviews', to: '/student/interviews', icon: '◉' },
    { label: 'Offers', to: '/student/offers', icon: '▱' },
  ],
  RECRUITER: [
    { label: 'Workspace', to: '/recruiter', end: true, icon: '◫' },
    { label: 'Job drives', to: '/recruiter/job-drives', icon: '◷' },
    { label: 'Applications', to: '/applications', icon: '▧' },
    { label: 'Offers', to: '/recruiter/offers', icon: '▱' },
  ],
  INTERVIEWER: [
    { label: 'Workspace', to: '/interviewer', end: true, icon: '◫' },
    { label: 'Interviews', to: '/interviewer/interviews', icon: '◉' },
  ],
}

function initials(name: string) {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'U'
}

export default function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className={`topbar${user ? ' topbar-workspace' : ' topbar-public'}`}>
        <NavLink to={user ? '/workspace' : '/'} className="brand-lockup" aria-label="College Placement Manager home">
          <span className="brand-mark" aria-hidden="true"><span>c</span><i /></span>
          <span className="brand-copy"><strong>Campus</strong><span>Placement Manager</span></span>
        </NavLink>
        {user ? (
          <div className="topbar-actions">
            <span className="topbar-context">Placement workspace</span>
            <NotificationMenu />
            <span className="topbar-divider" aria-hidden="true" />
            <details className="profile-menu">
              <summary className="profile-menu-trigger" aria-label={`Account menu for ${user.full_name}`}>
                <span className="user-avatar" aria-hidden="true">{initials(user.full_name)}</span>
                <span className="user-summary"><strong>{user.full_name}</strong><span>{user.role.toLowerCase()}</span></span>
                <span className="profile-menu-chevron" aria-hidden="true">⌄</span>
              </summary>
              <div className="profile-menu-panel">
                <div className="profile-menu-identity"><strong>{user.full_name}</strong><span>{user.role.toLowerCase()}</span></div>
                <NavLink to={user.role === 'STUDENT' ? '/student#profile-details' : '/workspace'} onClick={(event) => event.currentTarget.closest('details')?.removeAttribute('open')}>{user.role === 'STUDENT' ? 'View profile' : 'Open workspace'}<span aria-hidden="true">↗</span></NavLink>
                <button type="button" onClick={handleLogout}>Log out</button>
              </div>
            </details>
          </div>
        ) : (
          <>
            <nav id="mobile-public-navigation" className={`public-navigation${mobileMenuOpen ? ' is-open' : ''}`} aria-label="Main navigation" onClick={() => setMobileMenuOpen(false)}>
              <a href="/#opportunities">Opportunities</a><a href="/#companies">Companies</a><a href="/#how-it-works">How it works</a><a href="/#students">For students</a><a href="/#recruiters">For placement teams</a>
              <span className="public-nav-mobile-actions"><NavLink to="/login" className="button button-quiet">Sign in</NavLink><NavLink to="/register" className="button button-primary">Get started</NavLink></span>
            </nav>
            <nav className="topbar-actions public-account-actions" aria-label="Account navigation"><NavLink to="/login" className="button button-quiet">Sign in</NavLink><NavLink to="/register" className="button button-primary">Get started <span>↗</span></NavLink></nav>
            <button type="button" className="mobile-menu-toggle" aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'} aria-expanded={mobileMenuOpen} aria-controls="mobile-public-navigation" onClick={() => setMobileMenuOpen((open) => !open)}><span /><span /></button>
          </>
        )}
      </header>

      <div className={user ? 'workspace-frame' : 'public-frame'}>
        {user && <aside className="sidebar" aria-label="Workspace navigation">
          <div className="sidebar-label">WORKSPACE</div>
          <nav className="sidebar-nav">
            {navigation[user.role].map((item) => <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `sidebar-link${isActive ? ' is-active' : ''}`}>
              <span className="sidebar-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{iconPaths[iconNames[item.icon]].map((path) => <path key={path} d={path} />)}</svg></span><span>{item.label}</span>
            </NavLink>)}
          </nav>
          <div className="sidebar-footer"><span className="sidebar-footer-mark" aria-hidden="true">✓</span><span><strong>Campus hiring</strong><small>One coordinated workspace</small></span></div>
        </aside>}
        <div className="content-column">
          <main id="main-content" tabIndex={-1} className="page-content"><Outlet /></main>
          <footer className="app-footer"><span>College Placement Manager</span><span>Placement coordination, from one shared workspace.</span></footer>
        </div>
      </div>
    </div>
  )
}
