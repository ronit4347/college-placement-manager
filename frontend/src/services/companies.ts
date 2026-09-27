import { api } from './api'

export interface RecruiterSummary {
  user_id: number
  full_name: string
  email: string
  is_active: boolean
}

export interface Company {
  id: number
  name: string
  industry: string | null
  location: string | null
  website: string | null
  hr_name: string | null
  hr_email: string | null
  description: string | null
  is_active: boolean
  recruiters: RecruiterSummary[]
  created_at: string
  updated_at: string
}

export type CompanyInput = Omit<Company, 'id' | 'is_active' | 'recruiters' | 'created_at' | 'updated_at'>

export interface CompanyFilters {
  q?: string
  name?: string
  industry?: string
  is_active?: boolean
  limit?: number
  offset?: number
}

export async function fetchCompanies(filters: CompanyFilters = {}) {
  const { data } = await api.get<Company[]>('/api/companies', { params: filters })
  return data
}

export async function fetchCompany(companyId: number) {
  const { data } = await api.get<Company>(`/api/companies/${companyId}`)
  return data
}

export async function createCompany(company: CompanyInput) {
  const { data } = await api.post<Company>('/api/companies', company)
  return data
}

export async function updateCompany(companyId: number, company: Partial<CompanyInput> & { is_active?: boolean }) {
  const { data } = await api.patch<Company>(`/api/companies/${companyId}`, company)
  return data
}

export async function createCompanyRecruiter(companyId: number, input: { full_name: string; email: string; initial_password: string }) {
  const { data } = await api.post<RecruiterSummary>(`/api/companies/${companyId}/recruiters`, input)
  return data
}
