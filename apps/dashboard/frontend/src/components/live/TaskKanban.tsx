import React, { useState } from 'react'
import { ChevronDown, ChevronRight, Link2, AlertCircle, Clock, CheckCircle2, Circle, X } from 'lucide-react'

export interface Task {
  id: string
  subject: string
  description?: string
  status: 'pending' | 'in_progress' | 'completed' | 'blocked' | 'cancelled'
  activeForm?: string
  blocks?: string[]
  blockedBy?: string[]
  notes?: Array<{ text: string; timestamp: string; source: string }>
  session_id: string
  session_name?: string
}

export interface TaskSessions {
  [sessionId: string]: Task[]
}

interface TaskKanbanProps {
  sessions: TaskSessions
  selectedSession: string | null
  onSessionSelect: (sessionId: string | null) => void
  onTaskSelect: (task: Task | null) => void
  selectedTask: Task | null
}

const STATUS_CONFIG = {
  pending: {
    label: 'Pending',
    icon: Circle,
    color: 'text-slate-400',
    bgColor: 'bg-slate-500/10',
    borderColor: 'border-slate-500/30',
  },
  in_progress: {
    label: 'In Progress',
    icon: Clock,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10',
    borderColor: 'border-cyan-500/30',
  },
  completed: {
    label: 'Completed',
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/30',
  },
  blocked: {
    label: 'Blocked',
    icon: AlertCircle,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/30',
  },
  cancelled: {
    label: 'Cancelled',
    icon: X,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
  },
}

function TaskCard({
  task,
  isSelected,
  onClick,
  allTasks,
}: {
  task: Task
  isSelected: boolean
  onClick: () => void
  allTasks: Task[]
}) {
  const [expanded, setExpanded] = useState(false)
  const config = STATUS_CONFIG[task.status] || STATUS_CONFIG.pending
  const StatusIcon = config.icon

  const blockedByTasks = task.blockedBy?.map(id => allTasks.find(t => t.id === id)).filter(Boolean) || []
  const blocksTasks = task.blocks?.map(id => allTasks.find(t => t.id === id)).filter(Boolean) || []

  return (
    <div
      className={`
        p-3 rounded-lg border cursor-pointer transition-all duration-200
        ${config.bgColor} ${config.borderColor}
        ${isSelected ? 'ring-2 ring-violet-500 shadow-lg shadow-violet-500/20' : 'hover:border-slate-500'}
      `}
      onClick={onClick}
    >
      <div className="flex items-start gap-2">
        <StatusIcon className={`w-4 h-4 mt-0.5 ${config.color} flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-slate-200 truncate">
            {task.subject}
          </div>

          {task.status === 'in_progress' && task.activeForm && (
            <div className="mt-1 text-xs text-cyan-400 flex items-center gap-1">
              <span className="animate-pulse">●</span>
              {task.activeForm}
            </div>
          )}

          {(blockedByTasks.length > 0 || blocksTasks.length > 0) && (
            <div className="mt-2 flex flex-wrap gap-1">
              {blockedByTasks.length > 0 && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  <Link2 className="w-3 h-3" />
                  Blocked by {blockedByTasks.length}
                </span>
              )}
              {blocksTasks.length > 0 && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-violet-500/20 text-violet-400 border border-violet-500/30">
                  <Link2 className="w-3 h-3" />
                  Blocks {blocksTasks.length}
                </span>
              )}
            </div>
          )}

          {isSelected && task.description && (
            <div className="mt-2 pt-2 border-t border-slate-700">
              <button
                className="text-xs text-slate-400 flex items-center gap-1 hover:text-slate-300"
                onClick={(e) => {
                  e.stopPropagation()
                  setExpanded(!expanded)
                }}
              >
                {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                Details
              </button>
              {expanded && (
                <div className="mt-2 text-xs text-slate-400 whitespace-pre-wrap">
                  {task.description}
                </div>
              )}
            </div>
          )}

          {isSelected && task.notes && task.notes.length > 0 && (
            <div className="mt-2 pt-2 border-t border-slate-700">
              <div className="text-xs text-slate-500 mb-1">Notes ({task.notes.length})</div>
              <div className="space-y-1 max-h-24 overflow-y-auto">
                {task.notes.slice(-3).map((note, i) => (
                  <div key={i} className="text-xs text-slate-400 bg-slate-800/50 rounded px-2 py-1">
                    {note.text}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function KanbanColumn({
  title,
  tasks,
  status,
  selectedTask,
  onTaskSelect,
  allTasks,
}: {
  title: string
  tasks: Task[]
  status: string
  selectedTask: Task | null
  onTaskSelect: (task: Task | null) => void
  allTasks: Task[]
}) {
  const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.pending

  return (
    <div className="flex-1 min-w-[250px] flex flex-col">
      <div className={`flex items-center gap-2 px-3 py-2 rounded-t-lg ${config.bgColor} border-b ${config.borderColor}`}>
        <span className={`text-xs font-bold tracking-wider ${config.color}`}>
          {title}
        </span>
        <span className={`text-xs px-1.5 py-0.5 rounded-full ${config.bgColor} ${config.color}`}>
          {tasks.length}
        </span>
      </div>
      <div className="flex-1 p-2 space-y-2 bg-slate-900/50 rounded-b-lg border border-t-0 border-slate-700/50 overflow-y-auto max-h-[60vh]">
        {tasks.length === 0 ? (
          <div className="text-xs text-slate-600 text-center py-4">No tasks</div>
        ) : (
          tasks.map(task => (
            <TaskCard
              key={`${task.session_id}-${task.id}`}
              task={task}
              isSelected={selectedTask?.id === task.id && selectedTask?.session_id === task.session_id}
              onClick={() => onTaskSelect(
                selectedTask?.id === task.id && selectedTask?.session_id === task.session_id
                  ? null
                  : task
              )}
              allTasks={allTasks}
            />
          ))
        )}
      </div>
    </div>
  )
}

export function TaskKanban({
  sessions,
  selectedSession,
  onSessionSelect,
  onTaskSelect,
  selectedTask,
}: TaskKanbanProps) {
  // Get all tasks from selected session or all sessions
  const allTasks = selectedSession
    ? sessions[selectedSession] || []
    : Object.values(sessions).flat()

  // Group tasks by status
  const pendingTasks = allTasks.filter(t => t.status === 'pending' || t.status === 'blocked')
  const inProgressTasks = allTasks.filter(t => t.status === 'in_progress')
  const completedTasks = allTasks.filter(t => t.status === 'completed' || t.status === 'cancelled')

  const sessionIds = Object.keys(sessions)

  return (
    <div className="flex flex-col h-full">
      {/* Session Filter */}
      {sessionIds.length > 1 && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-xs text-slate-500">Session:</span>
          <select
            value={selectedSession || ''}
            onChange={(e) => onSessionSelect(e.target.value || null)}
            className="text-xs bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-300 focus:outline-none focus:border-violet-500"
          >
            <option value="">All Sessions ({sessionIds.length})</option>
            {sessionIds.map(id => {
              const sessionTasks = sessions[id]
              const sessionName = sessionTasks[0]?.session_name || id.slice(0, 8) + '...'
              return (
                <option key={id} value={id}>
                  {sessionName} ({sessionTasks.length} tasks)
                </option>
              )
            })}
          </select>
        </div>
      )}

      {/* Kanban Columns */}
      <div className="flex gap-4 flex-1 overflow-x-auto">
        <KanbanColumn
          title="PENDING"
          tasks={pendingTasks}
          status="pending"
          selectedTask={selectedTask}
          onTaskSelect={onTaskSelect}
          allTasks={allTasks}
        />
        <KanbanColumn
          title="IN PROGRESS"
          tasks={inProgressTasks}
          status="in_progress"
          selectedTask={selectedTask}
          onTaskSelect={onTaskSelect}
          allTasks={allTasks}
        />
        <KanbanColumn
          title="COMPLETED"
          tasks={completedTasks}
          status="completed"
          selectedTask={selectedTask}
          onTaskSelect={onTaskSelect}
          allTasks={allTasks}
        />
      </div>
    </div>
  )
}
