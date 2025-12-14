import { useEffect, useRef, useState, useCallback, useMemo } from 'react'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

// Build WebSocket URL - handles relative paths and protocol
function buildWsUrl(path: string): string {
  if (path.startsWith('ws://') || path.startsWith('wss://')) {
    return path
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsPath = path.startsWith('/') ? path : `/${path}`
  return `${protocol}//${host}${wsPath}`
}

export function useWebSocket(url: string, onMessage: (data: any) => void) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)
  const onMessageRef = useRef(onMessage)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10
  const baseReconnectDelay = 1000

  // Keep onMessage ref updated without triggering reconnects
  useEffect(() => {
    onMessageRef.current = onMessage
  }, [onMessage])

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    if (ws.current?.readyState === WebSocket.OPEN) return
    if (ws.current?.readyState === WebSocket.CONNECTING) return

    setConnectionStatus('connecting')
    const wsUrl = buildWsUrl(url)

    try {
      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        if (!mountedRef.current) return
        setConnectionStatus('connected')
        reconnectAttempts.current = 0
      }

      ws.current.onmessage = (event) => {
        if (!mountedRef.current) return
        try {
          const data = JSON.parse(event.data)
          onMessageRef.current(data)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.current.onclose = (event) => {
        if (!mountedRef.current) return
        setConnectionStatus('disconnected')

        // Attempt to reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts && mountedRef.current) {
          const delay = Math.min(baseReconnectDelay * Math.pow(2, reconnectAttempts.current), 10000)
          reconnectAttempts.current++
          reconnectTimeout.current = setTimeout(connect, delay)
        }
      }

      ws.current.onerror = () => {
        if (!mountedRef.current) return
        if (reconnectAttempts.current > 0) {
          setConnectionStatus('error')
        }
      }
    } catch (err) {
      if (!mountedRef.current) return
      setConnectionStatus('error')
      console.error('Failed to create WebSocket:', err)
    }
  }, [url]) // Only depend on url, not onMessage

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
      reconnectTimeout.current = null
    }
    if (ws.current) {
      ws.current.close(1000, 'Component unmounted')
      ws.current = null
    }
    setConnectionStatus('disconnected')
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
    }
  }, [])

  // Connect once on mount, disconnect on unmount
  useEffect(() => {
    mountedRef.current = true
    const initTimeout = setTimeout(connect, 100)

    return () => {
      mountedRef.current = false
      clearTimeout(initTimeout)
      disconnect()
    }
  }, []) // Empty deps - only run once

  return useMemo(() => ({ 
    sendMessage, 
    connectionStatus, 
    reconnect: connect 
  }), [sendMessage, connectionStatus, connect])
}
