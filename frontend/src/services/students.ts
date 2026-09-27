import { api } from './api'

export interface StudentProfile {
  student_id: number | null
  full_name: string
  email: string
  phone: string | null
  roll_number: string | null
  branch: string | null
  cgpa: number | null
  graduation_year: number | null
  backlogs: number | null
  skills: string[]
  resume_filename: string | null
  resume_max_size_bytes: number
  profile_completion: number
  created_at: string | null
  updated_at: string | null
}

export interface AdminStudent extends StudentProfile {
  placement_status: 'NOT_APPLIED' | 'APPLIED' | 'SHORTLISTED' | 'INTERVIEW' | 'SELECTED' | 'OFFERED' | 'REJECTED' | 'PLACED'
}

export interface AdminStudentFilters {
  q?: string
  roll_number?: string
  branch?: string
  min_cgpa?: number
  max_cgpa?: number
  placement_status?: AdminStudent['placement_status'] | 'JOINED'
  limit?: number
  offset?: number
}

export async function fetchAdminStudents(filters: AdminStudentFilters = {}) {
  const { data } = await api.get<AdminStudent[]>('/api/students', { params: filters })
  return data
}

export type StudentProfileUpdate = Pick<StudentProfile, 'full_name' | 'email'> & {
  phone: string | null
  roll_number: string | null
  branch: string | null
  cgpa: number | null
  graduation_year: number | null
  backlogs?: number
}

export async function fetchStudentProfile() {
  const { data } = await api.get<StudentProfile>('/api/students/me')
  return data
}

export async function updateStudentProfile(profile: StudentProfileUpdate) {
  const { data } = await api.patch<StudentProfile>('/api/students/me', profile)
  return data
}

export async function updateStudentSkills(skills: string[]) {
  const { data } = await api.put<StudentProfile>('/api/students/me/skills', { skills })
  return data
}

export async function uploadStudentResume(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<StudentProfile>('/api/students/me/resume', form)
  return data
}

export async function downloadStudentResume() {
  const { data } = await api.get<Blob>('/api/students/me/resume', { responseType: 'blob' })
  return URL.createObjectURL(data)
}
