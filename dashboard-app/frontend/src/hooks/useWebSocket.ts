import { useEffect, useRef, useState, useCallback } from 'react'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export function useWebSocket(url: string, onMessage: (data: any) => void) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10
  const baseReconnectDelay = 1000

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return

    setConnectionStatus('connecting')

    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        setConnectionStatus('connected')
        reconnectAttempts.current = 0
        console.log('WebSocket connected')
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage(data)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.current.onclose = (event) => {
        setConnectionStatus('disconnected')
        console.log('WebSocket disconnected:', event.code, event.reason)

        // Attempt to reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = baseReconnectDelay * Math.pow(2, reconnectAttempts.current)
          reconnectAttempts.current++
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`)
          reconnectTimeout.current = setTimeout(connect, delay)
        }
      }

      ws.current.onerror = (error) => {
        setConnectionStatus('error')
        console.error('WebSocket error:', error)
      }
    } catch (err) {
      setConnectionStatus('error')
      console.error('Failed to create WebSocket:', err)
    }
  }, [url, onMessage])

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
      reconnectTimeout.current = null
    }
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
    setConnectionStatus('disconnected')
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not connected, message not sent')
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return { sendMessage, connectionStatus, reconnect: connect }
}
