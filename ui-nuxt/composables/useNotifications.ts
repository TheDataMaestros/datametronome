import { ref, computed, readonly } from 'vue'
import { checksService, type Check } from '~/services/checks'
import { insightsService, type InsightNotification } from '~/services/insights'

export interface Notification {
  id: string
  type: 'error' | 'warning' | 'info' | 'assignment'
  title: string
  body: string
  source: string
  timestamp: string
  read: boolean
  checkId: string
  referenceId?: string
  origin: 'check' | 'insight'
}

const STORAGE_KEY = 'dm:read-notification-ids'

function loadReadIds(): Set<string> {
  if (import.meta.server) return new Set()
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? new Set(JSON.parse(raw)) : new Set()
  } catch {
    return new Set()
  }
}

function saveReadIds(ids: Set<string>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]))
  } catch {}
}

function checkToNotification(check: Check, readIds: Set<string>): Notification | null {
  const status = check.status?.toLowerCase()
  if (status !== 'fail' && status !== 'failed' && status !== 'warn' && status !== 'warning') {
    return null
  }

  const isError = status === 'fail' || status === 'failed'
  const source = check.clef_name
    ? `${check.clef_name}${check.stave_name ? ` · ${check.stave_name}` : ''}`
    : `Clef ${check.clef_id}`

  return {
    id: check.id,
    type: isError ? 'error' : 'warning',
    title: isError ? 'Check Failed' : 'Check Warning',
    body: check.message || `${check.check_type?.replace(/_/g, ' ')} check ${isError ? 'failed' : 'flagged a warning'}`,
    source,
    timestamp: check.timestamp,
    read: readIds.has(check.id),
    checkId: check.id,
    origin: 'check' as const,
  }
}

function insightNotifToNotification(n: InsightNotification, readIds: Set<string>): Notification {
  return {
    id: n.id,
    type: 'assignment',
    title: n.title,
    body: n.body,
    source: 'AI Insights',
    timestamp: n.created_at,
    read: !!n.read_at || readIds.has(n.id),
    checkId: '',
    referenceId: n.reference_id ?? undefined,
    origin: 'insight',
  }
}

const _notifications = ref<Notification[]>([])
const _isLoading = ref(false)
const _readIds = ref<Set<string>>(new Set())

export const useNotifications = () => {
  const notifications = computed(() => _notifications.value)

  const unreadCount = computed(() => _notifications.value.filter((n) => !n.read).length)

  const unread = computed(() => _notifications.value.filter((n) => !n.read))

  async function fetchNotifications(limit = 50, userId?: string) {
    _isLoading.value = true
    try {
      _readIds.value = loadReadIds()

      // Check-based notifications
      const checks = await checksService.list({ limit })
      const checkNotifs = checks
        .map((c) => checkToNotification(c, _readIds.value))
        .filter((n): n is Notification => n !== null)

      // Insight assignment notifications (if userId provided)
      let insightNotifs: Notification[] = []
      if (userId) {
        try {
          const apiNotifs = await insightsService.getNotifications()
          insightNotifs = apiNotifs.map((n) => insightNotifToNotification(n, _readIds.value))
        } catch { /* insight notifications optional */ }
      }

      // Merge and sort by timestamp descending
      _notifications.value = [...checkNotifs, ...insightNotifs].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      )
    } catch (err) {
      console.error('Failed to fetch notifications:', err)
    } finally {
      _isLoading.value = false
    }
  }

  function markRead(id: string) {
    _readIds.value.add(id)
    saveReadIds(_readIds.value)
    const n = _notifications.value.find((n) => n.id === id)
    if (n) n.read = true
    // If it's an insight notification, also persist to backend
    if (n?.origin === 'insight') {
      insightsService.markNotificationRead(id).catch(() => {})
    }
  }

  function markAllRead() {
    _notifications.value.forEach((n) => {
      n.read = true
      _readIds.value.add(n.id)
    })
    saveReadIds(_readIds.value)
  }

  return {
    notifications: readonly(notifications),
    unread: readonly(unread),
    unreadCount: readonly(unreadCount),
    isLoading: readonly(_isLoading),
    fetchNotifications,
    markRead,
    markAllRead,
  }
}
