import { useState, useCallback, useEffect, useMemo } from 'react'

export type NotificationType = 'info' | 'success' | 'warning' | 'error'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  timestamp: number
  autoDismiss?: boolean
}

interface NotificationOptions {
  type?: NotificationType
  autoDismiss?: boolean
  duration?: number
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [soundEnabled, setSoundEnabled] = useState(() => {
    const stored = localStorage.getItem('notifications-sound-enabled')
    return stored !== 'false' // Default to true
  })

  useEffect(() => {
    localStorage.setItem('notifications-sound-enabled', String(soundEnabled))
  }, [soundEnabled])

  const playSound = useCallback((type: NotificationType) => {
    if (!soundEnabled) return

    // Create simple notification sounds using Web Audio API
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)

    // Different tones for different notification types
    const frequencies: Record<NotificationType, number[]> = {
      info: [440, 550],
      success: [523, 659, 784],
      warning: [392, 523],
      error: [330, 262],
    }

    const freqs = frequencies[type] || frequencies.info
    oscillator.frequency.value = freqs[0]

    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2)

    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + 0.2)

    // Play second note for multi-note notifications
    if (freqs.length > 1) {
      setTimeout(() => {
        const osc2 = audioContext.createOscillator()
        const gain2 = audioContext.createGain()
        osc2.connect(gain2)
        gain2.connect(audioContext.destination)
        osc2.frequency.value = freqs[1]
        gain2.gain.setValueAtTime(0.1, audioContext.currentTime)
        gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2)
        osc2.start(audioContext.currentTime)
        osc2.stop(audioContext.currentTime + 0.2)
      }, 150)
    }
  }, [soundEnabled])

  const addNotification = useCallback(
    (title: string, message: string, options: NotificationOptions = {}) => {
      const {
        type = 'info',
        autoDismiss = true,
        duration = 5000,
      } = options

      const id = `notification-${Date.now()}-${Math.random()}`
      const notification: Notification = {
        id,
        type,
        title,
        message,
        timestamp: Date.now(),
        autoDismiss,
      }

      setNotifications((prev) => [...prev, notification])
      playSound(type)

      // Auto-dismiss after duration
      if (autoDismiss) {
        setTimeout(() => {
          removeNotification(id)
        }, duration)
      }

      return id
    },
    [playSound]
  )

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id))
  }, [])

  const clearAll = useCallback(() => {
    setNotifications([])
  }, [])

  // Convenience methods
  const info = useCallback(
    (title: string, message: string, autoDismiss = true) =>
      addNotification(title, message, { type: 'info', autoDismiss }),
    [addNotification]
  )

  const success = useCallback(
    (title: string, message: string, autoDismiss = true) =>
      addNotification(title, message, { type: 'success', autoDismiss }),
    [addNotification]
  )

  const warning = useCallback(
    (title: string, message: string, autoDismiss = true) =>
      addNotification(title, message, { type: 'warning', autoDismiss }),
    [addNotification]
  )

  const error = useCallback(
    (title: string, message: string, autoDismiss = false) =>
      addNotification(title, message, { type: 'error', autoDismiss }),
    [addNotification]
  )

  const toggleSound = useCallback(() => {
    setSoundEnabled((prev) => !prev)
  }, [])

  return useMemo(() => ({
    notifications,
    addNotification,
    removeNotification,
    clearAll,
    info,
    success,
    warning,
    error,
    soundEnabled,
    toggleSound,
  }), [notifications, addNotification, removeNotification, clearAll, info, success, warning, error, soundEnabled, toggleSound])

}
