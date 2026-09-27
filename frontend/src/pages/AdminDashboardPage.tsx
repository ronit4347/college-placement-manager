import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { fetchAnalyticsFilters, fetchDashboard, type AnalyticsFilterOptions, type DashboardData, type DashboardFilters } from '../services/analytics'
import { getErrorMessage } from '../utils/errors'

const palette = ['#176b68', '#c78b3d', '#668a79', '#71839a', '#b56d54', '#7d8fbc']
const number = new Intl.NumberFormat('en-IN')

function ChartPanel({ title, subtitle, hasData, children }: { title: string; subtitle: string; hasData: boolean; children: ReactNode }) {
  return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel sm:p-6"><div><h2 className="text-base font-semibold">{title}</h2><p className="mt-1 text-xs text-muted">{subtitle}</p></div>{hasData ? <div className="mt-5 h-72 w-full">{children}</div> : <div className="mt-5 grid h-72 place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-5 text-center"><p className="max-w-xs text-sm text-muted">No records match the selected filters yet.</p></div>}</section>
}

export default function AdminDashboardPage() {
  const [options, setOptions] = useState<AnalyticsFilterOptions | null>(null)
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [draft, setDraft] = useState({ graduation_year: '', branch: '', company_id: '', date_from: '', date_to: '' })
  const [applied, setApplied] = useState<DashboardFilters>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetchAnalyticsFilters().then((result) => { if (active) setOptions(result) }).catch((reason: unknown) => { if (active) setError(getErrorMessage(reason, 'Could not load dashboard filters.')) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    setLoading(true)
    fetchDashboard(applied).then((result) => {
      if (active) { setDashboard(result); setError('') }
    }).catch((reason: unknown) => { if (active) setError(getErrorMessage(reason, 'Could not load dashboard analytics.')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [applied])

  function applyFilters(event: FormEvent) {
    event.preventDefault()
    setApplied({
      graduation_year: draft.graduation_year ? Number(draft.graduation_year) : undefined,
      branch: draft.branch || undefined,
      company_id: draft.company_id ? Number(draft.company_id) : undefined,
      date_from: draft.date_from || undefined,
      date_to: draft.date_to || undefined,
    })
  }

  function resetFilters() {
    setDraft({ graduation_year: '', branch: '', company_id: '', date_from: '', date_to: '' })
    setApplied({})
  }

  const metrics = dashboard?.metrics
  const cards = metrics ? [
    { label: 'Total students', value: number.format(metrics.total_students), accent: 'bg-brand' },
    { label: 'Total companies', value: number.format(metrics.total_companies), accent: 'bg-violet-500' },
    { label: 'Active job drives', value: number.format(metrics.active_job_drives), accent: 'bg-cyan-600' },
    { label: 'Applications', value: number.format(metrics.total_applications), accent: 'bg-sky-600' },
    { label: 'Shortlisted', value: number.format(metrics.shortlisted_candidates), accent: 'bg-amber-500' },
    { label: 'Interviews', value: number.format(metrics.interviews), accent: 'bg-indigo-500' },
    { label: 'Selected', value: number.format(metrics.selected_candidates), accent: 'bg-orange-500' },
    { label: 'Offers issued', value: number.format(metrics.offers), accent: 'bg-rose-500' },
    { label: 'Placements', value: number.format(metrics.placements), accent: 'bg-emerald-600' },
    { label: 'Placement rate', value: `${metrics.placement_rate.toFixed(1)}%`, accent: 'bg-teal-500' },
  ] : []
  const hasBranch = Boolean(dashboard?.placement_by_branch.length)
  const hasFunnel = Boolean(dashboard?.application_funnel.some((item) => item.count > 0))
  const hasCompany = Boolean(dashboard?.company_selections.length)
  const hasPackages = Boolean(dashboard?.package_distribution.some((item) => item.value > 0))
  const hasMonths = Boolean(dashboard?.monthly_placement_activity.some((item) => item.placements > 0))

  return <section className="space-y-7">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">Placement overview</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Admin dashboard</h1><p className="mt-2 max-w-2xl text-sm text-muted">A live view of student outcomes and hiring activity across your campus.</p></div><div className="flex flex-wrap gap-2"><Link to="/admin/students" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Students</Link><Link to="/admin/job-drives" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Job drives</Link><Link to="/applications" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Applications</Link><Link to="/admin/offers" className="primary-button">Manage offers</Link></div></header>

    <form onSubmit={applyFilters} className="grid items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-panel sm:grid-cols-2 lg:grid-cols-6">
      <label className="form-label">Graduation year<select className="form-input mt-2" value={draft.graduation_year} onChange={(event) => setDraft({ ...draft, graduation_year: event.target.value })}><option value="">All years</option>{options?.graduation_years.map((year) => <option key={year} value={year}>{year}</option>)}</select></label>
      <label className="form-label">Branch<select className="form-input mt-2" value={draft.branch} onChange={(event) => setDraft({ ...draft, branch: event.target.value })}><option value="">All branches</option>{options?.branches.map((branch) => <option key={branch}>{branch}</option>)}</select></label>
      <label className="form-label">Company<select className="form-input mt-2" value={draft.company_id} onChange={(event) => setDraft({ ...draft, company_id: event.target.value })}><option value="">All companies</option>{options?.companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label>
      <label className="form-label">Applications from<input className="form-input mt-2" type="date" value={draft.date_from} onChange={(event) => setDraft({ ...draft, date_from: event.target.value })} /></label>
      <label className="form-label">Applications to<input className="form-input mt-2" type="date" value={draft.date_to} onChange={(event) => setDraft({ ...draft, date_to: event.target.value })} /></label>
      <div className="flex gap-2"><button className="primary-button flex-1">Apply filters</button><button type="button" onClick={resetFilters} className="rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50">Reset</button></div>
    </form>

    {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"><span>{error}</span><button className="font-semibold underline" onClick={() => setApplied({ ...applied })}>Retry</button></div>}
    {loading && !dashboard ? <div role="status" className="space-y-6"><p className="text-sm text-muted">Loading placement analytics…</p><div className="grid grid-cols-2 gap-3 lg:grid-cols-5">{Array.from({ length: 10 }, (_, index) => <div key={index} className="h-24 animate-pulse rounded-2xl bg-slate-100" />)}</div><div className="grid gap-5 lg:grid-cols-2">{Array.from({ length: 4 }, (_, index) => <div key={index} className="h-80 animate-pulse rounded-2xl bg-slate-100" />)}</div></div> : dashboard && <>
      <div className="flex items-center justify-between text-xs text-muted"><p>Placement rate is placements divided by registered students in the selected cohort.</p><p>{loading ? 'Refreshing…' : `Updated ${new Date(dashboard.generated_at).toLocaleString()}`}</p></div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">{cards.map((card) => <article key={card.label} className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-panel sm:p-5"><span className={`absolute inset-y-0 left-0 w-1 ${card.accent}`} /><p className="text-xs font-medium text-muted sm:text-sm">{card.label}</p><p className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{card.value}</p></article>)}</div>

      <div className="grid gap-5 xl:grid-cols-2">
        <ChartPanel title="Placement by branch" subtitle="Students who reached JOINED, grouped by branch" hasData={hasBranch}><ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.placement_by_branch} layout="vertical" margin={{ left: 8, right: 18 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} /><YAxis dataKey="name" type="category" width={120} axisLine={false} tickLine={false} tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey="value" name="Placements" fill="#176b68" radius={[0, 6, 6, 0]} /></BarChart></ResponsiveContainer></ChartPanel>
        <ChartPanel title="Application funnel" subtitle="Candidates progressing through each milestone" hasData={hasFunnel}><ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.application_funnel} margin={{ top: 12, right: 12, bottom: 8, left: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="stage" tick={{ fontSize: 11 }} interval={0} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} /><Tooltip /><Bar dataKey="count" name="Candidates" radius={[6, 6, 0, 0]}>{dashboard.application_funnel.map((entry, index) => <Cell key={entry.stage} fill={palette[index % palette.length]} />)}</Bar></BarChart></ResponsiveContainer></ChartPanel>
        <ChartPanel title="Company-wise selections" subtitle="Candidates selected by employer" hasData={hasCompany}><ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.company_selections} layout="vertical" margin={{ left: 8, right: 18 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} /><YAxis dataKey="name" type="category" width={130} axisLine={false} tickLine={false} tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey="value" name="Selected candidates" fill="#668a79" radius={[0, 6, 6, 0]} /></BarChart></ResponsiveContainer></ChartPanel>
        <ChartPanel title="Package distribution" subtitle="Issued offers grouped by annual INR package" hasData={hasPackages}><ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.package_distribution} margin={{ top: 12, right: 12, bottom: 8, left: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} /><Tooltip /><Bar dataKey="value" name="Offers" fill="#d27b4b" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></ChartPanel>
        <div className="xl:col-span-2"><ChartPanel title="Monthly placement activity" subtitle="Candidates reaching JOINED over the latest twelve months" hasData={hasMonths}><ResponsiveContainer width="100%" height="100%"><AreaChart data={dashboard.monthly_placement_activity} margin={{ top: 12, right: 18, bottom: 4, left: 0 }}><defs><linearGradient id="placementFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#176b68" stopOpacity={0.24} /><stop offset="95%" stopColor="#176b68" stopOpacity={0} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} axisLine={false} tickLine={false} /><Tooltip /><Area type="monotone" dataKey="placements" name="Placements" stroke="#176b68" strokeWidth={2.5} fill="url(#placementFill)" /></AreaChart></ResponsiveContainer></ChartPanel></div>
      </div>
    </>}
  </section>
}
