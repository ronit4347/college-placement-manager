import { api } from './api'

export type DriveStatus = 'DRAFT' | 'PUBLISHED' | 'CLOSED' | 'CANCELLED'
export type EmploymentType = 'FULL_TIME' | 'PART_TIME' | 'INTERNSHIP' | 'CONTRACT' | 'OTHER'

export interface JobDrive {
  id: number
  company_id: number
  company_name: string
  title: string
  description: string
  package_min: number | null
  package_max: number | null
  location: string | null
  employment_type: EmploymentType | null
  min_cgpa: number | null
  max_backlogs: number | null
  allowed_branches: string[] | null
  graduation_year: number | null
  required_skills: string[]
  application_deadline: string | null
  status: DriveStatus
  created_at: string
  updated_at: string
  is_eligible?: boolean | null
  application_status?: ApplicationDriveStatus | null
}

export type ApplicationDriveStatus = 'APPLIED' | 'SHORTLISTED' | 'REJECTED' | 'INTERVIEW' | 'SELECTED' | 'OFFERED' | 'JOINED'

export interface EligibleJobDrive extends JobDrive {
  eligibility_reasons: string[]
}

export type JobDriveInput = Omit<JobDrive, 'id' | 'company_name' | 'status' | 'created_at' | 'updated_at'>

export interface JobDriveFilters {
  q?: string
  location?: string
  employment_type?: EmploymentType
  graduation_year?: number
  status?: DriveStatus
  company?: string
  package_min?: number
  package_max?: number
  eligibility?: boolean
  application_status?: ApplicationDriveStatus | 'NOT_APPLIED'
  limit?: number
  offset?: number
}

export interface Applicant {
  application_id: number
  student_id: number
  student_name: string
  email: string
  roll_number: string | null
  branch: string | null
  cgpa: number | null
  status: string
  applied_at: string
}

export interface EligibilityResult {
  eligible: boolean
  reasons: string[]
}

export async function fetchJobDrives(filters: JobDriveFilters = {}) {
  const { data } = await api.get<JobDrive[]>('/api/job-drives', { params: filters })
  return data
}

export async function fetchEligibleJobDrives(filters: Omit<JobDriveFilters, 'status'> = {}) {
  const { data } = await api.get<EligibleJobDrive[]>('/api/job-drives/eligible', { params: filters })
  return data
}

export async function fetchJobDrive(driveId: number) {
  const { data } = await api.get<JobDrive>(`/api/job-drives/${driveId}`)
  return data
}

export async function fetchJobDriveEligibility(driveId: number) {
  const { data } = await api.get<EligibilityResult>(`/api/job-drives/${driveId}/eligibility`)
  return data
}

export async function createJobDrive(input: JobDriveInput) {
  const { data } = await api.post<JobDrive>('/api/job-drives', input)
  return data
}

export async function updateJobDrive(driveId: number, input: Partial<JobDriveInput>) {
  const { data } = await api.patch<JobDrive>(`/api/job-drives/${driveId}`, input)
  return data
}

export async function transitionJobDrive(driveId: number, action: 'publish' | 'close' | 'cancel') {
  const { data } = await api.post<JobDrive>(`/api/job-drives/${driveId}/${action}`)
  return data
}

export async function fetchApplicants(driveId: number) {
  const { data } = await api.get<Applicant[]>(`/api/job-drives/${driveId}/applicants`)
  return data
}
