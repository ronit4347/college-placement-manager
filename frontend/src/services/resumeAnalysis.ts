import { api } from './api'

export interface ResumeMatchDetail {
  status: 'MATCH' | 'PARTIAL' | 'NOT_FOUND'
  explanation: string
}

export interface ResumeAnalysis {
  overall_match_percentage: number
  matching_skills: string[]
  missing_skills: string[]
  education_match: ResumeMatchDetail
  experience_match: ResumeMatchDetail
  improvement_suggestions: string[]
  analysis_mode: 'MOCK' | 'AI'
}

export async function analyzeResume(job_drive_id: number) {
  const { data } = await api.post<ResumeAnalysis>('/api/students/me/resume-analysis', { job_drive_id })
  return data
}
