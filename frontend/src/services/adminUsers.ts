import { api } from './api'

export interface InterviewerRecord {
  id: number
  full_name: string
  email: string
  role: 'INTERVIEWER'
  is_active: boolean
  created_at: string
}

export interface InterviewerCredentials {
  full_name: string
  email: string
  initial_password: string
}

export async function fetchInterviewers() {
  const response = await api.get<InterviewerRecord[]>('/api/admin/interviewers')
  return response.data
}

export async function createInterviewer(payload: InterviewerCredentials) {
  const response = await api.post<InterviewerRecord>('/api/admin/interviewers', payload)
  return response.data
}

export async function setInterviewerActive(userId: number, isActive: boolean) {
  const response = await api.patch<InterviewerRecord>(`/api/admin/interviewers/${userId}/active`, { is_active: isActive })
  return response.data
}
