import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/',
  // Allow the configured AI provider timeout (25s by default) plus request overhead.
  timeout: 30_000,
  headers: { Accept: 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('cpm_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
