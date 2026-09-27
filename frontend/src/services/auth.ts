import { api } from './api'
import type { AuthUser, Credentials, LoginResponse, RegistrationDetails } from '../types/auth'

const TOKEN_KEY = 'cpm_access_token'

export async function loginRequest(credentials: Credentials): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/api/auth/login', credentials)
  return data
}

export async function registerRequest(details: RegistrationDetails): Promise<AuthUser> {
  const { data } = await api.post<AuthUser>('/api/auth/register', details)
  return data
}

export async function currentUserRequest(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>('/api/auth/me')
  return data
}

export const getStoredToken = () => sessionStorage.getItem(TOKEN_KEY)
export const storeToken = (token: string) => sessionStorage.setItem(TOKEN_KEY, token)
export const clearStoredToken = () => sessionStorage.removeItem(TOKEN_KEY)
