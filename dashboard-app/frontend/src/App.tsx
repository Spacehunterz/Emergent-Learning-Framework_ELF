import { useState, useEffect, useCallback } from 'react'
import { ThemeProvider, NotificationProvider, useNotificationContext, DataProvider, useDataContext } from './context'
import { useWebSocket, useAPI } from './hooks'
import {
  SettingsPanel,
  ParticleBackground,
  Header,
  StatsBar,
  HotspotTreemap,
  HeuristicPanel,
  TimelineView,
  RunsPanel,
  QueryInterface,
  AnomalyPanel,
  KnowledgeGraph,
  CommandPalette,
  NotificationPanel,
  LearningVelocity,
  SessionHistoryPanel,
  AssumptionsPanel,
  SpikeReportsPanel,
  InvariantsPanel,
  FraudReviewPanel
} from './components'
import {
  TimelineEvent,
  Stats,
  Heuristic,
  Hotspot,
  ApiRun,
  ApiAnomaly,
  TimelineData,
  RawEvent
} from './types'

function AppContent() {
  const [activeTab, setActiveTab] = useState<'overview' | 'heuristics' | 'runs' | 'timeline' | 'query' | 'analytics' | 'graph' | 'sessions' | 'assumptions' | 'spikes' | 'invariants' | 'fraud'>('overview')
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)

  const api = useAPI()
  const notifications = useNotificationContext()
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

  // Command Palette keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleRetryRun = async (runId: string) => {
    try {
      await api.post(`/api/runs/${runId}/retry`)
    } catch (err) {
      console.error('Failed to retry run:', err)
    }
  }

  const handleOpenInEditor = async (path: string, line?: number) => {
    try {
      await api.post('/api/open-in-editor', { path, line })
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

  // Command palette commands
  const commands = [
    { id: 'overview', label: 'Go to Overview', category: 'Navigation', action: () => setActiveTab('overview') },
    { id: 'heuristics', label: 'View Heuristics', category: 'Navigation', action: () => setActiveTab('heuristics') },
    { id: 'assumptions', label: 'View Assumptions', category: 'Navigation', action: () => setActiveTab('assumptions') },
    { id: 'spikes', label: 'View Spike Reports', category: 'Navigation', action: () => setActiveTab('spikes') },
    { id: 'invariants', label: 'View Invariants', category: 'Navigation', action: () => setActiveTab('invariants') },
    { id: 'fraud', label: 'Review Fraud Reports', category: 'Navigation', action: () => setActiveTab('fraud') },
    { id: 'graph', label: 'View Knowledge Graph', category: 'Navigation', action: () => setActiveTab('graph') },
    { id: 'runs', label: 'View Runs', category: 'Navigation', action: () => setActiveTab('runs') },
    { id: 'timeline', label: 'View Timeline', category: 'Navigation', action: () => setActiveTab('timeline') },
    { id: 'analytics', label: 'View Learning Analytics', category: 'Navigation', action: () => setActiveTab('analytics') },
    { id: 'query', label: 'Query the Building', shortcut: '⌘Q', category: 'Actions', action: () => setActiveTab('query') },
    { id: 'refresh', label: 'Refresh Data', shortcut: '⌘R', category: 'Actions', action: () => { loadStats(); reloadHeuristics() } },
    { id: 'clearDomain', label: 'Clear Domain Filter', category: 'Actions', action: () => setSelectedDomain(null) },
    { id: 'toggleNotificationSound', label: notifications.soundEnabled ? 'Mute Notifications' : 'Unmute Notifications', category: 'Settings', action: notifications.toggleSound },
    { id: 'clearNotifications', label: 'Clear All Notifications', category: 'Actions', action: notifications.clearAll },
  ]

  return (
    <div className="min-h-screen relative overflow-hidden transition-colors duration-500" style={{ backgroundColor: "var(--theme-bg-primary)" }}>
      <ParticleBackground />
      <SettingsPanel />
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        commands={commands}
      />
      <NotificationPanel
        notifications={notifications.notifications}
        onDismiss={notifications.removeNotification}
        onClearAll={notifications.clearAll}
        soundEnabled={notifications.soundEnabled}
        onToggleSound={notifications.toggleSound}
      />
      <div className="relative z-10">
        <Header
          isConnected={isConnected}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenCommandPalette={() => setCommandPaletteOpen(true)}
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
                  <h3 className="text-lg font-semibold text-amber-400 mb-3">Golden Rules</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {normalizedHeuristics.filter(h => h.is_golden).map(h => (
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
                // Optionally switch to heuristics tab and filter by domain
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
              events={events.map((e, idx) => ({
                id: idx,
                timestamp: e.timestamp,
                event_type: (e.event_type || e.type || 'task_start') as TimelineEvent['event_type'],
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

          {activeTab === 'analytics' && (
            <LearningVelocity days={30} />
          )}
        </div>
      </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <ThemeProvider>
      <NotificationProvider>
        <DataProvider>
          <AppContent />
        </DataProvider>
      </NotificationProvider>
    </ThemeProvider>
  )
}

export default App
