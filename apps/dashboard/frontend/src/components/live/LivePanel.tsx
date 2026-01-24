import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Activity, RefreshCw, Wifi, WifiOff } from 'lucide-react'
import { TaskKanban, Task, TaskSessions } from './TaskKanban'
import { TrailFeed, Trail } from './TrailFeed'
import { SignalInput } from './SignalInput'

interface LivePanelProps {
  apiBaseUrl?: string
}

export function LivePanel({ apiBaseUrl = '' }: LivePanelProps) {
  const [taskSessions, setTaskSessions] = useState<TaskSessions>({})
  const [trails, setTrails] = useState<Trail[]>([])
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [taskConnected, setTaskConnected] = useState(false)
  const [trailConnected, setTrailConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const taskEventSourceRef = useRef<EventSource | null>(null)
  const trailEventSourceRef = useRef<EventSource | null>(null)

  // Connect to task SSE
  useEffect(() => {
    const connectTaskSSE = () => {
      const eventSource = new EventSource(`${apiBaseUrl}/api/live/tasks`)
      taskEventSourceRef.current = eventSource

      eventSource.onopen = () => {
        setTaskConnected(true)
        setError(null)
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'initial' || data.type === 'update') {
            setTaskSessions(data.sessions || {})
          } else if (data.type === 'error') {
            console.error('Task SSE error:', data.message)
          }
        } catch (err) {
          console.error('Failed to parse task SSE data:', err)
        }
      }

      eventSource.onerror = () => {
        setTaskConnected(false)
        eventSource.close()

        // Reconnect after 3 seconds
        setTimeout(connectTaskSSE, 3000)
      }
    }

    connectTaskSSE()

    return () => {
      if (taskEventSourceRef.current) {
        taskEventSourceRef.current.close()
      }
    }
  }, [apiBaseUrl])

  // Connect to trail SSE
  useEffect(() => {
    const connectTrailSSE = () => {
      const eventSource = new EventSource(`${apiBaseUrl}/api/live/trails`)
      trailEventSourceRef.current = eventSource

      eventSource.onopen = () => {
        setTrailConnected(true)
      }

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'initial') {
            setTrails(data.trails || [])
          } else if (data.type === 'new_trails') {
            setTrails(prev => [...data.trails, ...prev])
          }
        } catch (err) {
          console.error('Failed to parse trail SSE data:', err)
        }
      }

      eventSource.onerror = () => {
        setTrailConnected(false)
        eventSource.close()

        // Reconnect after 3 seconds
        setTimeout(connectTrailSSE, 3000)
      }
    }

    connectTrailSSE()

    return () => {
      if (trailEventSourceRef.current) {
        trailEventSourceRef.current.close()
      }
    }
  }, [apiBaseUrl])

  // Send note to task
  const handleSendNote = useCallback(async (sessionId: string, taskId: string, note: string) => {
    const response = await fetch(`${apiBaseUrl}/api/live/signal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        task_id: taskId,
        note_text: note,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to send note')
    }
  }, [apiBaseUrl])

  // Change task status
  const handleChangeStatus = useCallback(async (
    sessionId: string,
    taskId: string,
    status: string,
    reason?: string
  ) => {
    const response = await fetch(`${apiBaseUrl}/api/live/task/${sessionId}/${taskId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, reason }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to change status')
    }
  }, [apiBaseUrl])

  // Calculate active agent count
  const activeSessions = Object.keys(taskSessions).length
  const totalTasks = Object.values(taskSessions).flat().length
  const inProgressTasks = Object.values(taskSessions).flat().filter(t => t.status === 'in_progress').length

  const isConnected = taskConnected && trailConnected

  return (
    <div className="h-full flex flex-col bg-slate-900/30 rounded-lg border border-slate-700/50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-violet-400" />
            <h2 className="text-lg font-semibold text-slate-200">Live Agents</h2>
          </div>

          {/* Connection status */}
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${
            isConnected
              ? 'bg-emerald-500/10 text-emerald-400'
              : 'bg-red-500/10 text-red-400'
          }`}>
            {isConnected ? (
              <>
                <Wifi className="w-3 h-3" />
                <span>Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3" />
                <span>Reconnecting...</span>
              </>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">Sessions:</span>
            <span className="text-violet-400 font-semibold">{activeSessions}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">Tasks:</span>
            <span className="text-cyan-400 font-semibold">{totalTasks}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">Active:</span>
            <span className="text-emerald-400 font-semibold">{inProgressTasks}</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Task Kanban */}
        <div className="flex-1 p-4 overflow-hidden">
          <TaskKanban
            sessions={taskSessions}
            selectedSession={selectedSession}
            onSessionSelect={setSelectedSession}
            onTaskSelect={setSelectedTask}
            selectedTask={selectedTask}
          />
        </div>

        {/* Right: Trail Feed */}
        <div className="w-80 border-l border-slate-700/50 flex flex-col relative">
          <TrailFeed
            trails={trails}
            autoScroll={autoScroll}
            onAutoScrollChange={setAutoScroll}
          />
        </div>
      </div>

      {/* Bottom: Signal Input */}
      <SignalInput
        sessions={taskSessions}
        selectedTask={selectedTask}
        onSendNote={handleSendNote}
        onChangeStatus={handleChangeStatus}
      />

      {/* Error Toast */}
      {error && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 px-4 py-2 bg-red-500/90 text-white text-sm rounded-lg shadow-lg">
          {error}
        </div>
      )}
    </div>
  )
}
