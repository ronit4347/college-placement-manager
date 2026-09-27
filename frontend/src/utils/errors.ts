import axios from 'axios'

export function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError<{ detail?: string | Array<{ msg: string }> }>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((issue) => issue.msg).join(' ')
  }
  return fallback
}
