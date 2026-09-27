export interface HealthResponse {
  status: string
}

export type HealthStatus =
  | { state: 'checking' }
  | { state: 'online'; message: string }
  | { state: 'offline' }
