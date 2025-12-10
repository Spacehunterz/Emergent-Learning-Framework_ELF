import { useState, useEffect, useCallback } from 'react'
import { ThemeProvider } from './context/ThemeContext'
import { SettingsPanel } from './components/SettingsPanel'
import { ParticleBackground } from './components/ParticleBackground'
import { useWebSocket } from './hooks/useWebSocket'
import { useAPI } from './hooks/useAPI'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import HotspotTreemap from './components/HotspotTreemap'
import HeuristicPanel from './components/HeuristicPanel'
import TimelineView from './components/TimelineView'
import RunsPanel from './components/RunsPanel'
import QueryInterface from './components/QueryInterface'
import AnomalyPanel from './components/AnomalyPanel'

// Simplified types matching API responses
interface Stats {
  total_runs: number
  total_executions: number
  total_trails: number
  total_heuristics: number
  golden_rules: number
  total_learnings: number
  failures: number
  successes: number
  successful_runs: number
  failed_runs: number
  avg_confidence: number
  total_validations: number
  total_violations: number
  metrics_last_hour: number
  runs_today: number
  // Query stats
  queries_today: number
  total_queries: number
  avg_query_duration_ms: number
}

interface Heuristic {
  id: number
  domain: string
  rule: string
  explanation: string | null
  confidence: number
  times_validated: number
  times_violated: number
  is_golden: boolean | number
  source_type: string
  created_at: string
  updated_at: string
}

interface Hotspot {
  location: string
  trail_count: number
  total_strength: number
  scents: string[]
  agents: string[]
  agent_count: number
  last_activity: string
  first_activity: string
  related_heuristics: any[]
}

interface Run {
  id: number
  workflow_id: number | null
  workflow_name: string
  status: string
  phase: string
  total_nodes: number
  completed_nodes: number
  failed_nodes: number
  started_at: string
  completed_at: string | null
  created_at: string
}

interface Anomaly {
  type: string
  severity: string
  message: string
  data: Record<string, any>
}

interface TimelineData {
  runs: { date: string; runs: number }[]
  trails: { date: string; trails: number; strength: number }[]
  validations: { date: string; validations: number }[]
  failures: { date: string; failures: number }[]
}

// Raw event from API (may have different field names)
interface RawEvent {
  id?: number
  timestamp: string
  event_type?: string
  type?: string  // API uses 'type' instead of 'event_type'
  description?: string
  message?: string  // API uses 'message' instead of 'description'
  metadata?: Record<string, any>
  tags?: string  // API uses 'tags'
  context?: string
  file_path?: string
  line_number?: number
  domain?: string
}

function App() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [heuristics, setHeuristics] = useState<Heuristic[]>([])
  const [hotspots, setHotspots] = useState<Hotspot[]>([])
  const [runs, setRuns] = useState<Run[]>([])
  const [events, setEvents] = useState<RawEvent[]>([])
  const [timeline, setTimeline] = useState<TimelineData | null>(null)
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [activeTab, setActiveTab] = useState<'overview' | 'heuristics' | 'runs' | 'timeline' | 'query'>('overview')
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  const api = useAPI()

  // Handle WebSocket messages
  const handleMessage = useCallback((data: any) => {
    console.log('WebSocket message:', data.type)
    switch (data.type) {
      case 'connected':
        console.log('WebSocket connected:', data.message)
        break
      case 'metrics':
      case 'trails':
      case 'runs':
        // Trigger a refresh of relevant data
        loadStats()
        break
      case 'heuristic_promoted':
        // Refresh heuristics
        loadHeuristics()
        break
    }
  }, [])

  // Use relative path - hook handles URL building, Vite proxies in dev
  const { connectionStatus } = useWebSocket('/ws', handleMessage)

  useEffect(() => {
    setIsConnected(connectionStatus === 'connected')
  }, [connectionStatus])

  const loadStats = async () => {
    try {
      const data = await api.get('/api/stats')
      setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }

  const loadHeuristics = async () => {
    try {
      const data = await api.get('/api/heuristics')
      setHeuristics(data || [])
    } catch (err) {
      console.error('Failed to load heuristics:', err)
    }
  }

  // Initial data load
  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsData, heuristicsData, hotspotsData, runsData, timelineData, anomaliesData, eventsData] = await Promise.all([
          api.get('/api/stats').catch(() => null),
          api.get('/api/heuristics').catch(() => []),
          api.get('/api/hotspots').catch(() => []),
          api.get('/api/runs?limit=100').catch(() => []),
          api.get('/api/timeline').catch(() => null),
          api.get('/api/anomalies').catch(() => []),
          api.get('/api/events?limit=100').catch(() => []),
        ])
        if (statsData) setStats(statsData)
        setHeuristics(heuristicsData || [])
        setHotspots(hotspotsData || [])
        setRuns(runsData || [])
        if (timelineData) setTimeline(timelineData)
        setAnomalies(anomaliesData || [])
        setEvents(eventsData || [])
      } catch (err) {
        console.error('Failed to load initial data:', err)
      }
    }
    loadData()

    // Auto-refresh stats and runs every 10 seconds
    const interval = setInterval(() => {
      // Refresh stats
      api.get('/api/stats').then(data => {
        if (data) setStats(data)
      }).catch(() => {})
      // Refresh runs
      api.get('/api/runs?limit=100').then(data => {
        if (data) setRuns(data)
      }).catch(() => {})
      // Refresh events
      api.get('/api/events?limit=100').then(data => {
        if (data) setEvents(data)
      }).catch(() => {})
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  // Action handlers
  const handlePromoteHeuristic = async (id: number) => {
    try {
      await api.post(`/api/heuristics/${id}/promote`)
      setHeuristics(prev => prev.map(h =>
        h.id === id ? { ...h, is_golden: true } : h
      ))
      // Reload stats to update golden rules count
      loadStats()
    } catch (err) {
      console.error('Failed to promote heuristic:', err)
    }
  }

  const handleDemoteHeuristic = async (id: number) => {
    try {
      await api.post(`/api/heuristics/${id}/demote`)
      setHeuristics(prev => prev.map(h =>
        h.id === id ? { ...h, is_golden: false } : h
      ))
      // Reload stats to update golden rules count
      loadStats()
    } catch (err) {
      console.error('Failed to demote heuristic:', err)
    }
  }

  const handleRetryRun = async (runId: string) => {
    try {
      await api.post(`/api/runs/${runId}/retry`)
    } catch (err) {
      console.error('Failed to retry run:', err)
    }
  }

  const handleOpenInEditor = async (path: string, line?: number) => {
    try {
      // API expects path as query parameter
      const params = new URLSearchParams({ path })
      if (line) params.append('line', String(line))
      await api.post(`/api/open-in-editor?${params.toString()}`)
    } catch (err) {
      console.error('Failed to open in editor:', err)
    }
  }

  // Convert stats to expected format for StatsBar
  // FIX: Use successful_runs/failed_runs from backend (actual workflow runs), not successes/failures (learnings)
  const statsForBar = stats ? {
    total_runs: stats.total_runs,
    successful_runs: stats.successful_runs,  // FIXED: was stats.successes (learning count)
    failed_runs: stats.failed_runs,          // FIXED: was stats.failures (learning count)
    success_rate: stats.total_runs > 0 ? stats.successful_runs / stats.total_runs : 0,  // FIXED: use run counts
    total_heuristics: stats.total_heuristics,
    golden_rules: stats.golden_rules,
    total_learnings: stats.total_learnings,
    hotspot_count: hotspots.length,
    avg_confidence: stats.avg_confidence,
    total_validations: stats.total_validations,
    runs_today: stats.runs_today || 0,       // FIXED: use runs_today from backend
    active_domains: new Set(heuristics.map(h => h.domain)).size,
    // Query stats
    queries_today: stats.queries_today || 0,
    total_queries: stats.total_queries || 0,
    avg_query_duration_ms: stats.avg_query_duration_ms || 0,
  } : null

  // Convert heuristics to expected format (normalize is_golden)
  const normalizedHeuristics = heuristics.map(h => ({
    ...h,
    is_golden: Boolean(h.is_golden)
  }))

  return (
    <ThemeProvider>
    <div className="min-h-screen relative overflow-hidden transition-colors duration-500" style={{ backgroundColor: "var(--theme-bg-primary)" }}>
        <ParticleBackground />
        <SettingsPanel />
        <div className="relative z-10">
      <Header
        isConnected={isConnected}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <main className="container mx-auto px-4 py-6">
        {/* Stats Bar - Always visible */}
        <StatsBar stats={statsForBar} />

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main area - Treemap */}
              <div className="lg:col-span-2">
                <HotspotTreemap
                  hotspots={hotspots}
                  onSelect={(path) => handleOpenInEditor(path)}
                  selectedDomain={selectedDomain}
                  onDomainFilter={setSelectedDomain}
                />
              </div>

              {/* Sidebar */}
              <div className="space-y-6">
                <AnomalyPanel
                  anomalies={anomalies}
                  onDismiss={(index) => setAnomalies(prev => prev.filter((_, i) => i !== index))}
                />
                <div className="bg-slate-800 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-white mb-3">Golden Rules</h3>
                  <div className="space-y-2">
                    {normalizedHeuristics.filter(h => h.is_golden).slice(0, 5).map(h => (
                      <div key={h.id} className="text-sm text-slate-300 p-2 bg-slate-700/50 rounded">
                        {h.rule}
                      </div>
                    ))}
                    {normalizedHeuristics.filter(h => h.is_golden).length === 0 && (
                      <div className="text-sm text-slate-400">No golden rules yet</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'heuristics' && (
            <HeuristicPanel
              heuristics={normalizedHeuristics}
              onPromote={handlePromoteHeuristic}
              onDemote={handleDemoteHeuristic}
              selectedDomain={selectedDomain}
              onDomainFilter={setSelectedDomain}
            />
          )}

          {activeTab === 'runs' && (
            <RunsPanel
              runs={runs.map(r => ({
                id: String(r.id),
                agent_type: r.workflow_name || 'unknown',
                description: `${r.workflow_name || 'Run'} - ${r.phase || r.status}`,
                status: r.status as any,
                started_at: r.started_at || r.created_at,
                completed_at: r.completed_at,
                duration_ms: r.completed_at && r.started_at
                  ? new Date(r.completed_at).getTime() - new Date(r.started_at).getTime()
                  : null,
                heuristics_used: [],
                files_touched: [],
                outcome_reason: r.failed_nodes > 0 ? `${r.failed_nodes} nodes failed` : null,
              }))}
              onRetry={handleRetryRun}
              onOpenInEditor={handleOpenInEditor}
            />
          )}

          {activeTab === 'timeline' && (
            <TimelineView
              events={events.map((e, idx) => ({
                id: idx,
                timestamp: e.timestamp,
                event_type: e.event_type || e.type || 'unknown',
                description: e.description || e.message || '',
                metadata: e.metadata || (e.tags ? { tags: e.tags } : {}),
                file_path: e.file_path,
                line_number: e.line_number,
                domain: e.domain,
              }))}
              heuristics={normalizedHeuristics}
              onEventClick={() => {}}
            />
          )}

          {activeTab === 'query' && (
            <QueryInterface />
          )}
        </div>
      </main>
        </div>
      </div>
    </ThemeProvider>
  )
}

export default App
