import { useState, useEffect } from 'react'
import { Session, SessionMessage, SessionDetail } from '../types'
import { History, Search, Filter, ChevronDown, Clock, MessageSquare, GitBranch, User, Bot, Terminal } from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { useAPI } from '../hooks/useAPI'

type DateFilter = 'today' | '7days' | '30days' | 'all'

interface SessionHistoryPanelProps {
  className?: string
}

export default function SessionHistoryPanel({ className = '' }: SessionHistoryPanelProps) {
  const api = useAPI()

  const [sessions, setSessions] = useState<Session[]>([])
  const [projects, setProjects] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [projectFilter, setProjectFilter] = useState<string>('all')
  const [dateFilter, setDateFilter] = useState<DateFilter>('7days')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [expandedSession, setExpandedSession] = useState<SessionDetail | null>(null)
  const [loadingSession, setLoadingSession] = useState<string | null>(null)

  // Load sessions
  useEffect(() => {
    loadSessions()
    loadProjects()
  }, [dateFilter])

  const loadSessions = async () => {
    setLoading(true)
    try {
      const days = dateFilter === 'today' ? 1 : dateFilter === '7days' ? 7 : dateFilter === '30days' ? 30 : 0
      const params = days > 0 ? `?limit=50&days=${days}` : '?limit=50'
      const data = await api.get(`/api/sessions${params}`)
      setSessions(data?.sessions || [])
    } catch (err) {
      console.error('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadProjects = async () => {
    try {
      const data = await api.get('/api/projects')
      setProjects(data?.map((p: any) => p.name) || [])
    } catch (err) {
      console.error('Failed to load projects:', err)
    }
  }

  const loadFullSession = async (sessionId: string) => {
    if (expandedId === sessionId) {
      // Collapse
      setExpandedId(null)
      setExpandedSession(null)
      return
    }

    setLoadingSession(sessionId)
    try {
      const data: SessionDetail = await api.get(`/api/sessions/${sessionId}`)
      setExpandedSession(data)
      setExpandedId(sessionId)
    } catch (err) {
      console.error('Failed to load session details:', err)
    } finally {
      setLoadingSession(null)
    }
  }

  // Filter sessions
  const filteredSessions = sessions.filter(session => {
    if (projectFilter !== 'all' && session.project !== projectFilter) return false
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        session.first_prompt_preview.toLowerCase().includes(query) ||
        session.project.toLowerCase().includes(query) ||
        (session.git_branch && session.git_branch.toLowerCase().includes(query))
      )
    }
    return true
  })

  const formatTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'MMM d, HH:mm:ss')
    } catch {
      return timestamp
    }
  }

  return (
    <div className={`bg-slate-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <History className="w-5 h-5 text-sky-400" />
          <h3 className="text-lg font-semibold text-white">Sessions</h3>
          <span className="text-sm text-slate-400">({filteredSessions.length} of {sessions.length})</span>
        </div>

        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search sessions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-700 text-sm text-white rounded-lg pl-9 pr-4 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 w-64"
            />
          </div>

          {/* Project filter */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={projectFilter}
              onChange={(e) => setProjectFilter(e.target.value)}
              className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              <option value="all">All Projects</option>
              {projects.map(project => (
                <option key={project} value={project}>{project}</option>
              ))}
            </select>
          </div>

          {/* Date range filter */}
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value as DateFilter)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="today">Today</option>
            <option value="7days">Last 7 days</option>
            <option value="30days">Last 30 days</option>
            <option value="all">All time</option>
          </select>
        </div>
      </div>

      {/* Sessions list */}
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
        {loading ? (
          <div className="text-center text-slate-400 py-12">
            <Clock className="w-8 h-8 mx-auto mb-2 animate-spin" />
            Loading sessions...
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="text-center text-slate-400 py-12">
            No sessions found
          </div>
        ) : (
          filteredSessions.map(session => {
            const isExpanded = expandedId === session.session_id
            const isLoading = loadingSession === session.session_id

            return (
              <div
                key={session.session_id}
                className={`bg-slate-700/50 rounded-lg border border-transparent transition-all
                  ${isExpanded ? 'ring-2 ring-sky-500/50' : ''}`}
              >
                {/* Main row */}
                <div
                  className="p-3 cursor-pointer hover:bg-slate-700/70 transition-colors"
                  onClick={() => loadFullSession(session.session_id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <div className={`p-2 rounded-lg ${session.is_agent ? 'bg-violet-500/20 text-violet-400' : 'bg-sky-500/20 text-sky-400'}`}>
                        {session.is_agent ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-0.5">
                          <span className="text-sm font-medium text-white truncate">{session.project}</span>
                          {session.git_branch && (
                            <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-slate-600 text-xs text-slate-300 flex-shrink-0">
                              <GitBranch className="w-3 h-3" />
                              <span>{session.git_branch}</span>
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-400 truncate">
                          {session.first_prompt_preview}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
                      <div className="text-right">
                        <div className="text-sm font-medium text-white">
                          {formatDistanceToNow(new Date(session.first_timestamp), { addSuffix: true })}
                        </div>
                        <div className="flex items-center space-x-1 text-xs text-slate-400">
                          <MessageSquare className="w-3 h-3" />
                          <span>{session.prompt_count} prompts</span>
                        </div>
                      </div>
                      <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-3 pb-3 border-t border-slate-600">
                    {isLoading ? (
                      <div className="text-center text-slate-400 py-8">
                        <Clock className="w-6 h-6 mx-auto mb-2 animate-spin" />
                        Loading conversation...
                      </div>
                    ) : expandedSession && expandedSession.messages && expandedSession.messages.length > 0 ? (
                      <div className="pt-3 space-y-3 max-h-96 overflow-y-auto">
                        {/* Session info */}
                        <div className="grid grid-cols-2 gap-4 text-sm pb-2 border-b border-slate-600">
                          <div>
                            <span className="text-slate-400">Started:</span>
                            <span className="text-white ml-2">{formatTimestamp(session.first_timestamp)}</span>
                          </div>
                          <div>
                            <span className="text-slate-400">Last Activity:</span>
                            <span className="text-white ml-2">{formatTimestamp(session.last_timestamp)}</span>
                          </div>
                        </div>

                        {/* Messages timeline */}
                        <div className="space-y-3">
                          {expandedSession.messages.map((msg, idx) => (
                            <div key={msg.uuid} className={`${msg.type === 'user' ? 'bg-slate-800/50' : 'bg-slate-700/30'} rounded-lg p-3`}>
                              {/* Message header */}
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center space-x-2">
                                  {msg.type === 'user' ? (
                                    <>
                                      <User className="w-4 h-4 text-sky-400" />
                                      <span className="text-sm font-medium text-sky-400">User</span>
                                    </>
                                  ) : (
                                    <>
                                      <Bot className="w-4 h-4 text-violet-400" />
                                      <span className="text-sm font-medium text-violet-400">Claude</span>
                                    </>
                                  )}
                                  {msg.is_command && msg.command_name && (
                                    <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 text-xs">
                                      /{msg.command_name}
                                    </span>
                                  )}
                                </div>
                                <span className="text-xs text-slate-400">{formatTimestamp(msg.timestamp)}</span>
                              </div>

                              {/* Message content */}
                              <div className={`text-sm ${msg.type === 'user' ? 'text-white font-medium' : 'text-slate-300'} whitespace-pre-wrap`}>
                                {msg.content}
                              </div>

                              {/* Tool uses */}
                              {msg.tool_use && msg.tool_use.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-slate-600">
                                  <div className="flex flex-wrap gap-1">
                                    {msg.tool_use.map((tool, toolIdx) => (
                                      <details key={toolIdx} className="inline-block">
                                        <summary className="cursor-pointer inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 transition-colors">
                                          <Terminal className="w-3 h-3" />
                                          <span>{tool.name}</span>
                                        </summary>
                                        <div className="mt-1 p-2 bg-slate-800 rounded text-xs text-slate-300 max-w-md">
                                          <pre className="overflow-x-auto">{JSON.stringify(tool.input, null, 2)}</pre>
                                        </div>
                                      </details>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="text-center text-slate-400 py-8">
                        No messages found
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
