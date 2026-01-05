import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { ThemeProvider, NotificationProvider, useNotificationContext, DataProvider, useDataContext, CosmicSettingsProvider, CosmicAudioProvider, GameProvider, useGame, useCosmicSettings, useTheme } from './context'
import { DashboardLayout } from './layouts/DashboardLayout'
import { useWebSocket, useAPI } from './hooks'
import CosmicIntro from './components/CosmicIntro'
import { GameScene } from './components/game/cockpit/GameScene'
import {
  StatsBar,
  HotspotVisualization,
  HeuristicPanel,
  TimelineView,
  RunsPanel,
  QueryInterface,
  AlertsPanel,
  KnowledgeGraph,
  LearningVelocity,
  SessionHistoryPanel,
  AssumptionsPanel,
  SpikeReportsPanel,
  InvariantsPanel,
  FraudReviewPanel
} from './components'
import {
  TimelineEvent,
} from './types'


// Error boundary to prevent app-wide crashes
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Dashboard error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-900">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-red-400 mb-4">Dashboard Error</h1>
            <p className="text-slate-300 mb-4">Something went wrong. Please refresh the page.</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white"
            >
              Refresh
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

function AppContent() {
  const [activeTab, setActiveTab] = useState<'overview' | 'heuristics' | 'runs' | 'timeline' | 'query' | 'analytics' | 'graph' | 'sessions' | 'assumptions' | 'spikes' | 'invariants' | 'fraud'>('overview')
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)
  // Intro disabled - set to true to re-enable
  const [showIntro, setShowIntro] = useState(false)
  const [introMode, setIntroMode] = useState<'full' | 'short'>('full')

  const api = useAPI()
  const notifications = useNotificationContext()
  const { isGameEnabled } = useGame() // Get Game State

  const {
    stats,
    hotspots,
    runs,
    events,
    timeline: _timeline,
    anomalies,
    reload: reloadDashboardData,
    loadStats,
    setAnomalies,
    heuristics,
    promoteHeuristic,
    demoteHeuristic,
    deleteHeuristic,
    updateHeuristic,
    reloadHeuristics,
  } = useDataContext()

  // Handle WebSocket messages
  const handleMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'connected':
        break
      case 'metrics':
      case 'trails':
        // Trigger a refresh of relevant data
        reloadDashboardData()
        break
      case 'runs':
        // Refresh stats
        reloadDashboardData()
        // Notify about run status
        if (data.status === 'completed') {
          notifications.success(
            'Workflow Run Completed',
            `${data.workflow_name || 'Workflow'} finished successfully`
          )
        } else if (data.status === 'failed') {
          notifications.error(
            'Workflow Run Failed',
            `${data.workflow_name || 'Workflow'} encountered an error`
          )
        }
        break
      case 'heuristics':
        // Refresh heuristics
        reloadHeuristics()
        // Notify about new heuristic
        notifications.info(
          'New Heuristic Created',
          data.rule || 'A new heuristic has been added to the system'
        )
        break
      case 'heuristic_promoted':
        // Refresh heuristics
        reloadHeuristics()
        // Notify about promotion to golden rule
        notifications.success(
          'Heuristic Promoted to Golden Rule',
          data.rule || 'A heuristic has been promoted to a golden rule'
        )
        break
      case 'learnings':
        // Learnings changed, refresh stats
        reloadDashboardData()
        break
      case 'ceo_inbox':
        // New CEO inbox item
        notifications.warning(
          'New CEO Decision Required',
          data.message || 'A new item has been added to the CEO inbox'
        )
        break
    }
  }, [notifications, reloadDashboardData, reloadHeuristics])

  // Use relative path - hook handles URL building, Vite proxies in dev
  const { connectionStatus } = useWebSocket('/ws', handleMessage)

  useEffect(() => {
    setIsConnected(connectionStatus === 'connected')
  }, [connectionStatus])

  // Startup Check-in Handshake
  useEffect(() => {
    const performCheckIn = async () => {
      try {
        console.log('[Check-in] Initiating startup handshake...')
        const response = await api.post('/api/sessions/check-in')

        if (response?.status === 'initiated') {
          notifications.info(
            'Session Check-in',
            'Summarizing your last session in the background...'
          )
        } else if (response?.status === 'ready') {
          console.log('[Check-in] Last session summary ready:', response.session_id)
        }
      } catch (err) {
        console.error('[Check-in] Handshake failed:', err)
        notifications.error(
          'Check-in Failed',
          'Could not connect to session history. Some features may be unavailable.'
        )
      }
    }

    performCheckIn()
  }, [api, notifications])

  // Command Palette keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Command Palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(true)
      }

      // Escape to clear selection / navigate back
      if (e.key === 'Escape') {
        if (selectedDomain) {
          e.preventDefault()
          setSelectedDomain(null)
        } else if (activeTab === 'graph' || activeTab === 'analytics') {
          e.preventDefault()
          setActiveTab('overview')
        } else if (activeTab !== 'overview') {
          // Optional: Esc from other tabs could go back to overview?
          // user only mentioned "drill down into a card... cant esc key out"
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedDomain, activeTab])

  const handleRetryRun = async (runId: string) => {
    try {
      await api.post(`/api/runs/${runId}/retry`)
    } catch (err) {
      console.error('Failed to retry run:', err)
    }
  }

  const handleOpenInEditor = useCallback(async (path: string, line?: number) => {
    try {
      await api.post('/api/open-in-editor', { path, line })
    } catch (err) {
      console.error('Failed to open in editor:', err)
      notifications.error('Editor Error', `Could not open ${path.split('/').pop() || 'file'} in editor`)
    }
  }, [api, notifications])

  const { performanceMode } = useCosmicSettings()
  const { setParticleCount } = useTheme()

  // Performance Mode Logic
  useEffect(() => {
    switch (performanceMode) {
      case 'low': setParticleCount(50); break;
      case 'medium': setParticleCount(100); break;
      case 'high': setParticleCount(200); break;
    }
  }, [performanceMode, setParticleCount])

  // FIXED: Memoize normalized heuristics to avoid recalculation on every render
  const normalizedHeuristics = useMemo(() =>
    heuristics.map(h => ({
      ...h,
      is_golden: Boolean(h.is_golden)
    })),
    [heuristics]
  )

  // FIXED: Memoize active domains calculation
  const activeDomains = useMemo(() =>
    new Set(heuristics.map(h => h.domain)).size,
    [heuristics]
  )

  // FIXED: Memoize stats object to avoid recreation on every render
  const statsForBar = useMemo(() => {
    if (!stats) return null
    return {
      total_runs: stats.total_runs,
      successful_runs: stats.successful_runs,
      failed_runs: stats.failed_runs,
      success_rate: stats.total_runs > 0 ? stats.successful_runs / stats.total_runs : 0,
      total_heuristics: stats.total_heuristics,
      golden_rules: stats.golden_rules,
      total_learnings: stats.total_learnings,
      hotspot_count: hotspots.length,
      avg_confidence: stats.avg_confidence,
      total_validations: stats.total_validations,
      runs_today: stats.runs_today || 0,
      active_domains: activeDomains,
      queries_today: stats.queries_today || 0,
      total_queries: stats.total_queries || 0,
      avg_query_duration_ms: stats.avg_query_duration_ms || 0,
    }
  }, [stats, hotspots.length, activeDomains])

  // FIXED: Memoize command palette commands to avoid recreation on every render
  const commands = useMemo(() => [
    { id: 'overview', label: 'Go to Overview', category: 'Navigation', action: () => setActiveTab('overview') },
    { id: 'graph', label: 'View Knowledge Graph', category: 'Navigation', action: () => setActiveTab('graph') },
    { id: 'analytics', label: 'View Learning Analytics', category: 'Navigation', action: () => setActiveTab('analytics') },
    { id: 'runs', label: 'View Runs', category: 'Navigation', action: () => setActiveTab('runs') },
    { id: 'timeline', label: 'View Timeline', category: 'Navigation', action: () => setActiveTab('timeline') },
    { id: 'heuristics', label: 'View Heuristics', category: 'Navigation', action: () => setActiveTab('heuristics') },
    { id: 'assumptions', label: 'View Assumptions', category: 'Navigation', action: () => setActiveTab('assumptions') },
    { id: 'spikes', label: 'View Spike Reports', category: 'Navigation', action: () => setActiveTab('spikes') },
    { id: 'invariants', label: 'View Invariants', category: 'Navigation', action: () => setActiveTab('invariants') },
    { id: 'fraud', label: 'Review Fraud Reports', category: 'Navigation', action: () => setActiveTab('fraud') },
    { id: 'query', label: 'Query the Building', shortcut: '⌘Q', category: 'Actions', action: () => setActiveTab('query') },
    { id: 'refresh', label: 'Refresh Data', shortcut: '⌘R', category: 'Actions', action: () => { loadStats(); reloadHeuristics() } },
    { id: 'clearDomain', label: 'Clear Domain Filter', category: 'Actions', action: () => setSelectedDomain(null) },
    { id: 'toggleNotificationSound', label: notifications.soundEnabled ? 'Mute Notifications' : 'Unmute Notifications', category: 'Settings', action: notifications.toggleSound },
    { id: 'clearNotifications', label: 'Clear All Notifications', category: 'Actions', action: notifications.clearAll },
    { id: 'playIntroFull', label: 'Play Intro (Full)', category: 'System', action: () => { setIntroMode('full'); setShowIntro(true); setCommandPaletteOpen(false); } },
    { id: 'playIntroShort', label: 'Play Intro (Short)', category: 'System', action: () => { setIntroMode('short'); setShowIntro(true); setCommandPaletteOpen(false); } },
  ], [notifications.soundEnabled, notifications.toggleSound, notifications.clearAll, loadStats, reloadHeuristics])

  // GAME MODE OVERRIDE
  if (isGameEnabled) {
    return <GameScene />
  }

  return (
    <>
      <DashboardLayout
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab as any)}
        isConnected={isConnected}
        commandPaletteOpen={commandPaletteOpen}
        setCommandPaletteOpen={setCommandPaletteOpen}
        commands={commands}
        onDomainSelect={setSelectedDomain}
        selectedDomain={selectedDomain}
      >
        {/* Intro Layer */}
        {showIntro && (
          <div className="fixed inset-0 z-[100000] bg-black">
            <CosmicIntro
              mode={introMode}
              onComplete={() => setShowIntro(false)}
            />
          </div>
        )}

        <div className="space-y-6">
          {/* Stats Bar */}
          <StatsBar stats={statsForBar} />

          {/* Tab Content */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <HotspotVisualization
                  hotspots={hotspots}
                  onSelect={handleOpenInEditor}
                  selectedDomain={selectedDomain}
                  onDomainFilter={setSelectedDomain}
                />
              </div>
              <div className="space-y-6">
                <AlertsPanel
                  anomalies={anomalies}
                  goldenRules={normalizedHeuristics.filter(h => h.is_golden).map(h => ({ ...h, id: String(h.id) })) as any}
                  onDismissAnomaly={(index) => setAnomalies(prev => prev.filter((_, i) => i !== index))}
                />
              </div>
            </div>
          )}

          {activeTab === 'heuristics' && (
            <HeuristicPanel
              heuristics={normalizedHeuristics}
              onPromote={promoteHeuristic}
              onDemote={demoteHeuristic}
              onDelete={deleteHeuristic}
              onUpdate={updateHeuristic}
              selectedDomain={selectedDomain}
              onDomainFilter={setSelectedDomain}
            />
          )}

          {activeTab === 'graph' && (
            <KnowledgeGraph
              onNodeClick={(node) => {
                setSelectedDomain(node.domain)
              }}
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

          {activeTab === 'sessions' && <SessionHistoryPanel />}
          {activeTab === 'assumptions' && <AssumptionsPanel />}
          {activeTab === 'spikes' && <SpikeReportsPanel />}
          {activeTab === 'invariants' && <InvariantsPanel />}
          {activeTab === 'fraud' && <FraudReviewPanel />}

          {activeTab === 'timeline' && (
            <TimelineView
              events={events.map((e, idx) => {
                const validEventTypes = ['task_start', 'task_end', 'heuristic_consulted', 'heuristic_validated', 'heuristic_violated', 'failure_recorded', 'golden_promoted'] as const
                const rawType = e.event_type || e.type || 'task_start'
                const eventType = validEventTypes.includes(rawType as any) ? rawType as TimelineEvent['event_type'] : 'task_start'
                return {
                  id: idx,
                  timestamp: e.timestamp,
                  event_type: eventType,
                  description: e.description || e.message || '',
                  metadata: e.metadata || (e.tags ? { tags: e.tags } : {}),
                  file_path: e.file_path,
                  line_number: e.line_number,
                  domain: e.domain,
                }
              })}
              heuristics={normalizedHeuristics}
              onEventClick={() => { }}
            />
          )}

          {activeTab === 'query' && <QueryInterface />}

          {/* Analytics is handled by DashboardLayout for Cosmic mode, but we keep this for grid mode */}
          {activeTab === 'analytics' && <LearningVelocity days={30} />}
        </div>
      </DashboardLayout>
    </>
  )
}

function App() {
  return (
    <ThemeProvider>
      <NotificationProvider>
        <DataProvider>
          <CosmicSettingsProvider>
            <CosmicAudioProvider>
              <GameProvider>
                <AppContent />
              </GameProvider>
            </CosmicAudioProvider>
          </CosmicSettingsProvider>
        </DataProvider>
      </NotificationProvider>
    </ThemeProvider>
  )
}

export default function AppWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  )
}
