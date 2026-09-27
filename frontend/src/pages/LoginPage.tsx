import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../utils/errors'

export default function LoginPage() {
  const { login, user, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!isLoading && user) return <Navigate to="/workspace" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login({ email, password })
      const requested = (location.state as { from?: { pathname?: string; search?: string; hash?: string } } | null)?.from
      const requestedPath = requested?.pathname
      const from = requestedPath?.startsWith('/') && !requestedPath.startsWith('//')
        ? `${requestedPath}${requested?.search?.startsWith('?') ? requested.search : ''}${requested?.hash?.startsWith('#') ? requested.hash : ''}`
        : undefined
      navigate(from || '/workspace', { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to sign in. Check your details and try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-panel sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Welcome back</p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">Sign in to your workspace</h1>
      <p className="mt-2 text-sm leading-6 text-muted">Use your college placement account to continue.</p>
      <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium">Email address
          <input className="form-input mt-2" type="email" autoComplete="email" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="block text-sm font-medium">Password
          <input className="form-input mt-2" type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{error}</p>}
        <button className="primary-button w-full" type="submit" disabled={submitting}>{submitting ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">New to the workspace? <Link className="font-semibold text-brand hover:underline" to="/register">Create a student account</Link></p>
    </section>
  )
}
