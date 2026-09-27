export type UserRole = 'STUDENT' | 'ADMIN' | 'RECRUITER' | 'INTERVIEWER'

export interface AuthUser {
  id: number
  email: string
  full_name: string
  role: UserRole
  created_at: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface Credentials {
  email: string
  password: string
}

export interface RegistrationDetails extends Credentials {
  full_name: string
}
