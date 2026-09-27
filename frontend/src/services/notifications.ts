import { api } from './api'

export interface NotificationItem {
  id: number
  type: string
  title: string
  message: string
  link: string | null
  created_at: string
  read_at: string | null
}

export async function fetchNotifications() {
  const { data } = await api.get<NotificationItem[]>('/api/notifications', { params: { limit: 30 } })
  return data
}

export async function fetchUnreadNotificationCount() {
  const { data } = await api.get<{ unread_count: number }>('/api/notifications/unread-count')
  return data.unread_count
}

export async function markNotificationRead(id: number) {
  const { data } = await api.patch<NotificationItem>(`/api/notifications/${id}/read`)
  return data
}
