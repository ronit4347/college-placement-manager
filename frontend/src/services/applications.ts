import { api } from './api'
export type ApplicationStatus = 'APPLIED' | 'SHORTLISTED' | 'REJECTED' | 'INTERVIEW' | 'SELECTED' | 'OFFERED' | 'JOINED'

export interface ApplicationStatusEvent {
  id: number
  from_status: ApplicationStatus | null
  to_status: ApplicationStatus
  actor_name: string | null
  note: string | null
  created_at: string
}

export interface ApplicationRecord {
  id: number
  job_drive_id: number
  drive_title: string
  company_name: string
  student_id: number
  student_name: string
  student_email: string
  roll_number: string | null
  branch: string | null
  cgpa: number | null
  status: ApplicationStatus
  cover_letter: string | null
  applied_at: string
  updated_at: string
  timeline: ApplicationStatusEvent[]
}

export async function submitApplication(jobDriveId: number, coverLetter?: string) {
  const { data } = await api.post<ApplicationRecord>(`/api/job-drives/${jobDriveId}/applications`, { cover_letter: coverLetter || null })
  return data
}

export async function fetchApplications(filters: { status?: ApplicationStatus; job_drive_id?: number; company?: string; job?: string; branch?: string; limit?: number; offset?: number } = {}) {
  const { data } = await api.get<ApplicationRecord[]>('/api/applications', { params: filters })
  return data
}

export async function fetchApplication(applicationId: number) {
  const { data } = await api.get<ApplicationRecord>(`/api/applications/${applicationId}`)
  return data
}

export async function changeApplicationStatus(applicationId: number, status: ApplicationStatus, note?: string) {
  const { data } = await api.patch<ApplicationRecord>(`/api/applications/${applicationId}/status`, { status, note: note || null })
  return data
}
