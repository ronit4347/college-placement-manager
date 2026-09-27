import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  clearStoredToken,
  currentUserRequest,
  getStoredToken,
  loginRequest,
  registerRequest,
  storeToken,
} from '../services/auth'
import type { AuthUser, Credentials, RegistrationDetails } from '../types/auth'

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: (credentials: Credentials) => Promise<void>
  register: (details: RegistrationDetails) => Promise<void>
  refreshUser: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let active = true
    if (!getStoredToken()) {
      setIsLoading(false)
      return () => { active = false }
    }
    currentUserRequest()
      .then((currentUser) => active && setUser(currentUser))
      .catch(() => {
        clearStoredToken()
        if (active) setUser(null)
      })
      .finally(() => active && setIsLoading(false))
    return () => { active = false }
  }, [])

  const login = useCallback(async (credentials: Credentials) => {
    const tokenResponse = await loginRequest(credentials)
    storeToken(tokenResponse.access_token)
    try {
      setUser(await currentUserRequest())
    } catch (error) {
      clearStoredToken()
      throw error
    }
  }, [])

  const register = useCallback(async (details: RegistrationDetails) => {
    await registerRequest(details)
    await login({ email: details.email, password: details.password })
  }, [login])

  const refreshUser = useCallback(async () => {
    setUser(await currentUserRequest())
  }, [])

  const logout = useCallback(() => {
    clearStoredToken()
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, isLoading, login, register, refreshUser, logout }), [user, isLoading, login, register, refreshUser, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider.')
  return context
}
