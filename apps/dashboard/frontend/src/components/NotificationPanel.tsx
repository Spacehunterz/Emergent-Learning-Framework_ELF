import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Info, CheckCircle, AlertTriangle, AlertCircle, Volume2, VolumeX } from 'lucide-react'
import { Notification, NotificationType } from '../context/NotificationContext'

interface NotificationPanelProps {
  notifications: Notification[]
  onDismiss: (id: string) => void
  onClearAll: () => void
  soundEnabled: boolean
  onToggleSound: () => void
}

const notificationConfig: Record<
  NotificationType,
  { icon: any; color: string; bg: string; border: string; glow: string }
> = {
  info: {
    icon: Info,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    glow: 'shadow-[0_0_20px_rgba(59,130,246,0.3)]',
  },
  success: {
    icon: CheckCircle,
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    glow: 'shadow-[0_0_20px_rgba(34,197,94,0.3)]',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    glow: 'shadow-[0_0_20px_rgba(245,158,11,0.3)]',
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    glow: 'shadow-[0_0_20px_rgba(239,68,68,0.3)]',
  },
}

interface NotificationItemProps {
  notification: Notification
  onDismiss: (id: string) => void
}

function NotificationItem({ notification, onDismiss }: NotificationItemProps) {
  const [progress, setProgress] = useState(100)
  const config = notificationConfig[notification.type]
  const Icon = config.icon

  // Auto-dismiss progress bar
  useEffect(() => {
    if (!notification.autoDismiss) return

    const duration = 5000
    const interval = 50
    const decrement = (interval / duration) * 100

    const timer = setInterval(() => {
      setProgress((prev) => {
        const next = prev - decrement
        if (next <= 0) {
          clearInterval(timer)
          return 0
        }
        return next
      })
    }, interval)

    return () => clearInterval(timer)
  }, [notification.autoDismiss])

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.95 }}
      className={`
        relative overflow-hidden rounded-lg border ${config.border} ${config.bg} ${config.glow}
        backdrop-blur-sm w-80 group
      `}
    >
      {/* Progress bar */}
      {notification.autoDismiss && (
        <div className="absolute bottom-0 left-0 h-1 bg-white/10 w-full">
          <motion.div
            className={`h-full ${config.color.replace('text-', 'bg-')} opacity-50`}
            initial={{ width: '100%' }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.05, ease: 'linear' }}
          />
        </div>
      )}

      <div className="p-4">
        <button
          onClick={() => onDismiss(notification.id)}
          className="absolute top-2 right-2 p-1 text-slate-400 hover:text-white transition opacity-0 group-hover:opacity-100"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-start space-x-3 pr-6">
          <div className={`p-1.5 rounded ${config.bg}`}>
            <Icon className={`w-5 h-5 ${config.color}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-white">{notification.title}</span>
              <span className="text-xs text-slate-400">{formatTime(notification.timestamp)}</span>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">{notification.message}</p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export function NotificationPanel({
  notifications,
  onDismiss,
  onClearAll,
  soundEnabled,
  onToggleSound,
}: NotificationPanelProps) {
  if (notifications.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3 pointer-events-none">
      {/* Control bar */}
      <div className="pointer-events-auto flex items-center gap-2">
        <button
          onClick={onToggleSound}
          className="p-2 bg-slate-800/90 backdrop-blur-sm rounded-lg border border-slate-700 hover:bg-slate-700 transition"
          title={soundEnabled ? 'Mute notifications' : 'Unmute notifications'}
        >
          {soundEnabled ? (
            <Volume2 className="w-4 h-4 text-slate-400" />
          ) : (
            <VolumeX className="w-4 h-4 text-slate-400" />
          )}
        </button>
        {notifications.length > 1 && (
          <button
            onClick={onClearAll}
            className="px-3 py-2 bg-slate-800/90 backdrop-blur-sm rounded-lg border border-slate-700 hover:bg-slate-700 transition text-xs text-slate-400"
          >
            Clear all ({notifications.length})
          </button>
        )}
      </div>

      {/* Notifications list */}
      <AnimatePresence>
        {notifications.map((notification) => (
          <div key={notification.id} className="pointer-events-auto">
            <NotificationItem notification={notification} onDismiss={onDismiss} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}
