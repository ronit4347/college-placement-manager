import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchNotifications, fetchUnreadNotificationCount, markNotificationRead, type NotificationItem } from '../services/notifications'
import { getErrorMessage } from '../utils/errors'

function relativeTime(value: string) {
  const minutes = Math.max(0, Math.floor((Date.now() - Date.parse(value)) / 60000))
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`
  return `${Math.floor(minutes / 1440)}d ago`
}

export default function NotificationMenu() {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const container = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  async function refreshCount() {
    try { setUnreadCount(await fetchUnreadNotificationCount()) } catch { /* Keep the last known badge count while offline. */ }
  }

  async function loadItems() {
    setLoading(true)
    setError('')
    try { setItems(await fetchNotifications()) }
    catch (reason) { setError(getErrorMessage(reason, 'Notifications could not be loaded.')) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    void refreshCount()
    const timer = window.setInterval(() => { void refreshCount() }, 30000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  async function openNotification(item: NotificationItem) {
    if (!item.read_at) {
      try {
        const updated = await markNotificationRead(item.id)
        setItems((current) => current.map((entry) => entry.id === item.id ? updated : entry))
        setUnreadCount((count) => Math.max(0, count - 1))
      } catch (reason) { setError(getErrorMessage(reason, 'This notification could not be marked as read.')); return }
    }
    setOpen(false)
    if (item.link) navigate(item.link)
  }

  return <div ref={container} className="relative">
    <button type="button" aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`} aria-expanded={open} aria-controls="notification-panel" onClick={() => { const next = !open; setOpen(next); if (next) void loadItems() }} className="relative grid h-10 w-10 place-items-center rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.7"><path strokeLinecap="round" strokeLinejoin="round" d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg>
      {unreadCount > 0 && <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-rose-600 px-1 text-center text-[10px] font-bold leading-5 text-white">{unreadCount > 99 ? '99+' : unreadCount}</span>}
    </button>
    {open && <section id="notification-panel" aria-label="Notifications" className="absolute right-0 z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3"><h2 className="text-sm font-semibold">Notifications</h2><span className="text-xs text-muted">{unreadCount} unread</span></div>
      {error && <p role="alert" className="px-4 py-3 text-xs text-rose-700">{error}</p>}
      {loading ? <p role="status" className="px-4 py-6 text-center text-sm text-muted">Loading notifications…</p> : items.length === 0 ? <p className="px-4 py-8 text-center text-sm text-muted">You’re all caught up.</p> : <ul className="max-h-[min(65vh,28rem)] overflow-y-auto">{items.map((item) => <li key={item.id}><button type="button" onClick={() => void openNotification(item)} className={`w-full border-b border-slate-100 px-4 py-3 text-left hover:bg-slate-50 ${item.read_at ? '' : 'bg-blue-50/60'}`}><span className="flex items-start gap-2"><span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${item.read_at ? 'bg-slate-300' : 'bg-brand'}`} /><span className="min-w-0 flex-1"><span className="block text-sm font-semibold">{item.title}</span><span className="mt-1 block text-xs leading-5 text-slate-600">{item.message}</span><time className="mt-1 block text-[10px] text-muted">{relativeTime(item.created_at)}</time></span></span></button></li>)}</ul>}
    </section>}
  </div>
}
