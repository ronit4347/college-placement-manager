import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../utils/errors'

export default function RegisterPage() {
  const { register, user, isLoading } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!isLoading && user) return <Navigate to="/workspace" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await register({ full_name: fullName, email, password })
      navigate('/workspace', { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to create your account. Check your details and try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-panel sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Student access</p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">Create Student Account</h1>
      <p className="mt-2 text-sm leading-6 text-muted">Registration creates a student account. Other roles are provisioned by placement administrators.</p>
      <form className="mt-7 space-y-5" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium">Full name
          <input className="form-input mt-2" type="text" autoComplete="name" required minLength={2} maxLength={160} value={fullName} onChange={(event) => setFullName(event.target.value)} />
        </label>
        <label className="block text-sm font-medium">Email address
          <input className="form-input mt-2" type="email" autoComplete="email" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="block text-sm font-medium">Password
          <input className="form-input mt-2" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} />
          <span className="mt-1 block text-xs font-normal text-muted">Use at least 12 characters.</span>
        </label>
        <label className="block text-sm font-medium">Confirm password
          <input className="form-input mt-2" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
        </label>
        {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{error}</p>}
        <button className="primary-button w-full" type="submit" disabled={submitting}>{submitting ? 'Creating account…' : 'Create student account'}</button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">Already registered? <Link className="font-semibold text-brand hover:underline" to="/login">Sign in</Link></p>
    </section>
  )
}
