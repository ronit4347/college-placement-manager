import { api } from './api'

export interface AnalyticsFilterOptions {
  graduation_years: number[]
  branches: string[]
  companies: { id: number; name: string }[]
}
export interface DashboardFilters {
  graduation_year?: number
  branch?: string
  company_id?: number
  date_from?: string
  date_to?: string
}
export interface DashboardData {
  generated_at: string
  metrics: {
    total_students: number; total_companies: number; active_job_drives: number; total_applications: number
    shortlisted_candidates: number; interviews: number; selected_candidates: number; offers: number
    placements: number; placement_rate: number
  }
  placement_by_branch: { name: string; value: number }[]
  application_funnel: { stage: string; count: number }[]
  company_selections: { name: string; value: number }[]
  package_distribution: { name: string; value: number }[]
  monthly_placement_activity: { month: string; placements: number }[]
}
export async function fetchAnalyticsFilters() { return (await api.get<AnalyticsFilterOptions>('/api/admin/analytics/filters')).data }
export async function fetchDashboard(filters: DashboardFilters = {}) { return (await api.get<DashboardData>('/api/admin/analytics/dashboard', { params: filters })).data }
