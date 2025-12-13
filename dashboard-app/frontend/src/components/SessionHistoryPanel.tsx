import { useState, useEffect } from 'react'
import { Session, SessionDetail } from '../types'
import { Clock } from 'lucide-react'
import { format } from 'date-fns'
import { useAPI } from '../hooks/useAPI'
import { SessionFilters, SessionCard, SessionDetail as SessionDetailComponent } from './session-history'
import type { DateFilter, SessionHistoryPanelProps } from './session-history/types'

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
      <SessionFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        projectFilter={projectFilter}
        onProjectFilterChange={setProjectFilter}
        dateFilter={dateFilter}
        onDateFilterChange={setDateFilter}
        projects={projects}
        filteredCount={filteredSessions.length}
        totalCount={sessions.length}
      />

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
                <SessionCard
                  session={session}
                  isExpanded={isExpanded}
                  isLoading={isLoading}
                  onToggle={loadFullSession}
                  formatTimestamp={formatTimestamp}
                />

                {isExpanded && expandedSession && (
                  <SessionDetailComponent
                    session={session}
                    sessionDetail={expandedSession}
                    isLoading={isLoading}
                    formatTimestamp={formatTimestamp}
                  />
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
