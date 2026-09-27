import { api } from './api'

export type InterviewRound = 'APTITUDE' | 'TECHNICAL' | 'MANAGERIAL' | 'HR'
export type InterviewStatus = 'SCHEDULED' | 'COMPLETED' | 'CANCELLED' | 'RESCHEDULED'
export interface InterviewRecord {
  id: number; application_id: number; drive_title: string; company_name: string; round: InterviewRound
  interviewer_user_id?: number | null; interviewer_name?: string | null; scheduled_at: string; duration_minutes: number
  status: InterviewStatus; result?: 'PENDING' | 'PASSED' | 'FAILED' | null; feedback?: string | null
  student_name?: string | null; student_email?: string | null; roll_number?: string | null; branch?: string | null; cgpa?: number | null
}
export interface InterviewerOption { id: number; full_name: string; email: string }
export async function fetchInterviews() { return (await api.get<InterviewRecord[]>('/api/interviews')).data }
export async function fetchInterviewers() { return (await api.get<InterviewerOption[]>('/api/interviews/interviewers')).data }
export async function scheduleInterview(input: { application_id: number; round: InterviewRound; interviewer_user_id: number; scheduled_at: string; duration_minutes: number }) { return (await api.post<InterviewRecord>('/api/interviews', input)).data }
export async function updateInterviewResult(id: number, result: 'PASSED' | 'FAILED', feedback: string) { return (await api.patch<InterviewRecord>(`/api/interviews/${id}/result`, { result, feedback })).data }
export async function cancelInterview(id: number) { return (await api.post<InterviewRecord>(`/api/interviews/${id}/cancel`)).data }
export async function rescheduleInterview(id: number, scheduled_at: string) { return (await api.patch<InterviewRecord>(`/api/interviews/${id}/reschedule`, { scheduled_at })).data }
