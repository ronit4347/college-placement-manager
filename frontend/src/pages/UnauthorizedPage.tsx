import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function UnauthorizedPage() {
  const { user } = useAuth()
  return (
    <section className="mx-auto max-w-lg rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-panel">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-rose-600">Access restricted</p>
      <h1 className="mt-3 text-2xl font-semibold">You don’t have access to this page</h1>
      <p className="mt-3 text-sm leading-6 text-muted">{user ? `Your ${user.role.toLowerCase()} account is not allowed to open this section.` : 'Sign in with an account that has permission to continue.'}</p>
      <Link className="primary-button mt-6 inline-flex" to={user ? '/workspace' : '/login'}>Return to workspace</Link>
    </section>
  )
}
