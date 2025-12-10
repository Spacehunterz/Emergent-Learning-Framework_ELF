import { useState, useEffect } from 'react'
import { TrendingUp, CheckCircle, XCircle, Brain, Star, Target, Zap, BarChart3, X, ChevronRight, Loader2, ArrowLeft, AlertCircle, RefreshCw, MessageSquare } from 'lucide-react'
import { Stats } from '../types'
import { useAPI } from '../hooks/useAPI'

interface StatsBarProps {
  stats: Stats | null
}

interface StatCardData {
  label: string
  value: string | number
  icon: any
  color: string
  bgColor: string
  description: string
  drillDownType?: 'runs' | 'heuristics' | 'hotspots' | 'golden' | 'learnings' | 'queries'
  details?: { label: string; value: string | number }[]
}

type DrillDownView = 'main' | 'runs' | 'heuristics' | 'golden' | 'hotspots' | 'learnings' | 'queries'

export default function StatsBar({ stats }: StatsBarProps) {
  const [expandedCard, setExpandedCard] = useState<string | null>(null)
  const [drillDownView, setDrillDownView] = useState<DrillDownView>('main')
  const [drillDownData, setDrillDownData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const api = useAPI()

  useEffect(() => {
    if (!expandedCard) {
      setDrillDownView('main')
      setDrillDownData(null)
      setError(null)
    }
  }, [expandedCard])

  const loadDrillDownData = async (type: DrillDownView) => {
    setLoading(true)
    setError(null)
    setDrillDownView(type)
    try {
      let data
      switch (type) {
        case 'runs':
          data = await api.get('/api/runs?limit=100')
          break
        case 'heuristics':
          data = await api.get('/api/heuristics?limit=100')
          break
        case 'golden':
          data = await api.get('/api/heuristics?golden_only=true&limit=100')
          break
        case 'hotspots':
          data = await api.get('/api/hotspots')
          break
        case 'learnings':
          data = await api.get('/api/learnings?limit=100')
          break
        case 'queries':
          data = await api.get('/api/queries?limit=100')
          break
      }
      setDrillDownData(data)
    } catch (err: any) {
      console.error('Failed to load drill-down data:', err)
      setError(err?.message || 'Failed to load data. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const goBack = () => {
    setDrillDownView('main')
    setDrillDownData(null)
    setError(null)
  }

  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="glass-panel rounded-lg p-4 animate-pulse">
            <div className="h-4 bg-slate-700 rounded w-1/2 mb-2" />
            <div className="h-8 bg-slate-700 rounded w-3/4" />
          </div>
        ))}
      </div>
    )
  }

  const statCards: StatCardData[] = [
    {
      label: 'Total Runs',
      value: stats.total_runs,
      icon: BarChart3,
      color: 'text-sky-400',
      bgColor: 'bg-sky-500/10',
      description: 'Total number of agent workflow runs recorded in the system.',
      drillDownType: 'runs',
      details: [
        { label: 'Successful', value: stats.successful_runs },
        { label: 'Failed', value: stats.failed_runs },
        { label: 'Success Rate', value: (stats.success_rate * 100).toFixed(1) + '%' },
      ],
    },
    {
      label: 'Success Rate',
      value: (stats.success_rate * 100).toFixed(1) + '%',
      icon: TrendingUp,
      color: stats.success_rate >= 0.8 ? 'text-emerald-400' : stats.success_rate >= 0.5 ? 'text-amber-400' : 'text-red-400',
      bgColor: stats.success_rate >= 0.8 ? 'bg-emerald-500/10' : stats.success_rate >= 0.5 ? 'bg-amber-500/10' : 'bg-red-500/10',
      description: 'Percentage of workflow runs that completed successfully.',
      drillDownType: 'runs',
      details: [
        { label: 'Total Runs', value: stats.total_runs },
        { label: 'Successful', value: stats.successful_runs },
        { label: 'Failed', value: stats.failed_runs },
      ],
    },
    {
      label: 'Successful',
      value: stats.successful_runs,
      icon: CheckCircle,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      description: 'Workflow runs that completed all tasks without failures.',
      drillDownType: 'runs',
    },
    {
      label: 'Failed',
      value: stats.failed_runs,
      icon: XCircle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
      description: 'Workflow runs that encountered errors or failed to complete.',
      drillDownType: 'runs',
    },
    {
      label: 'Heuristics',
      value: stats.total_heuristics,
      icon: Brain,
      color: 'text-violet-400',
      bgColor: 'bg-violet-500/10',
      description: 'Learned patterns and rules extracted from agent experiences.',
      drillDownType: 'heuristics',
      details: [
        { label: 'Golden Rules', value: stats.golden_rules },
        { label: 'Total Validations', value: stats.total_validations || 0 },
        { label: 'Avg Confidence', value: ((stats.avg_confidence || 0) * 100).toFixed(0) + '%' },
      ],
    },
    {
      label: 'Golden Rules',
      value: stats.golden_rules,
      icon: Star,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      description: 'High-confidence heuristics promoted to constitutional rules that guide all agents.',
      drillDownType: 'golden',
    },
    {
      label: 'Hotspots',
      value: stats.hotspot_count,
      icon: Target,
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10',
      description: 'Active areas in the codebase with concentrated agent activity trails.',
      drillDownType: 'hotspots',
    },
    {
      label: 'Queries',
      value: stats.queries_today || 0,
      icon: MessageSquare,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10',
      description: 'Building queries executed by agents to retrieve institutional knowledge.',
      drillDownType: 'queries',
      details: [
        { label: 'Total', value: stats.total_queries || 0 },
        { label: 'Success Rate', value: '100%' },
        { label: 'Avg Duration', value: (stats.avg_query_duration_ms || 0).toFixed(0) + 'ms' },
      ],
    },
  ]

  const renderDrillDownContent = (card: StatCardData) => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--theme-accent)' }} />
          <span className="text-sm text-slate-400">Loading data...</span>
        </div>
      )
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          <AlertCircle className="w-8 h-8 text-red-400" />
          <span className="text-sm text-red-400 text-center">{error}</span>
          <button
            onClick={() => loadDrillDownData(drillDownView)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      )
    }

    if (!drillDownData) return null

    switch (drillDownView) {
      case 'runs': {
        let runs = drillDownData || []
        if (card.label === 'Successful') {
          runs = runs.filter((r: any) => r.status === 'completed' || r.status === 'success')
        } else if (card.label === 'Failed') {
          runs = runs.filter((r: any) => r.status === 'failed' || r.status === 'error' || r.status === 'cancelled')
        } else if (card.label === 'Today') {
          const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
          runs = runs.filter((r: any) => new Date(r.created_at + 'Z') > oneDayAgo)
        }
        const statusCounts = {
          completed: drillDownData.filter((r: any) => r.status === 'completed' || r.status === 'success').length,
          failed: drillDownData.filter((r: any) => r.status === 'failed' || r.status === 'error' || r.status === 'cancelled').length,
          running: drillDownData.filter((r: any) => r.status === 'running' || r.status === 'in_progress' || r.status === 'pending').length,
        }
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-emerald-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-emerald-400">{statusCounts.completed}</div>
                <div className="text-xs text-slate-400">Completed</div>
              </div>
              <div className="bg-red-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-red-400">{statusCounts.failed}</div>
                <div className="text-xs text-slate-400">Failed</div>
              </div>
              <div className="bg-sky-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-sky-400">{statusCounts.running}</div>
                <div className="text-xs text-slate-400">Running</div>
              </div>
            </div>
            <div className="text-xs text-slate-500 text-center">
              Showing {runs.length} of {drillDownData.length} runs
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {runs.slice(0, 30).map((run: any, idx: number) => (
                <div key={run.id || idx} className="bg-slate-700/50 rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white font-medium">{run.workflow_name || 'Unknown Workflow'}</span>
                    <span className={
                      run.status === 'completed' || run.status === 'success' ? 'text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400' :
                      run.status === 'failed' || run.status === 'error' || run.status === 'cancelled' ? 'text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400' :
                      'text-xs px-2 py-0.5 rounded bg-sky-500/20 text-sky-400'
                    }>
                      {run.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-slate-400">
                      {run.started_at || run.created_at ? new Date((run.started_at || run.created_at) + 'Z').toLocaleString() : 'No date'}
                    </span>
                    {run.phase && <span className="text-xs text-slate-500">{run.phase}</span>}
                  </div>
                  {(run.total_nodes > 0 || run.completed_nodes > 0) && (
                    <div className="mt-2 text-xs text-slate-500">
                      Nodes: {run.completed_nodes || 0}/{run.total_nodes || 0} completed
                      {run.failed_nodes > 0 && <span className="text-red-400 ml-2">({run.failed_nodes} failed)</span>}
                    </div>
                  )}
                </div>
              ))}
              {runs.length === 0 && (
                <div className="text-center text-slate-400 py-4">No runs found matching criteria</div>
              )}
            </div>
          </div>
        )
      }

      case 'heuristics': {
        const heuristics = drillDownData || []
        const domains = [...new Set(heuristics.map((h: any) => h.domain))].filter(Boolean)
        const goldenCount = heuristics.filter((h: any) => h.is_golden).length
        const avgConfidence = heuristics.length > 0 ? (heuristics.reduce((sum: number, h: any) => sum + (h.confidence || 0), 0) / heuristics.length) : 0
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-violet-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-violet-400">{heuristics.length}</div>
                <div className="text-xs text-slate-400">Total</div>
              </div>
              <div className="bg-amber-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-amber-400">{goldenCount}</div>
                <div className="text-xs text-slate-400">Golden</div>
              </div>
              <div className="bg-sky-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-sky-400">{(avgConfidence * 100).toFixed(0)}%</div>
                <div className="text-xs text-slate-400">Avg Conf</div>
              </div>
            </div>
            <div className="text-xs text-slate-500 text-center">
              Across {domains.length} domains
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {heuristics.slice(0, 20).map((h: any, idx: number) => (
                <div key={h.id || idx} className="bg-slate-700/50 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm text-white flex-1">{h.rule}</span>
                    {h.is_golden && <Star className="w-4 h-4 text-amber-400 flex-shrink-0" />}
                  </div>
                  {h.explanation && (
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{h.explanation}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <span className="text-xs bg-slate-600 px-2 py-0.5 rounded text-slate-300">{h.domain || 'general'}</span>
                    <span className="text-xs text-slate-400">Conf: {((h.confidence || 0) * 100).toFixed(0)}%</span>
                    <span className="text-xs text-slate-500">✓{h.times_validated || 0} ✗{h.times_violated || 0}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      }

      case 'golden': {
        const goldenRules = drillDownData || []
        return (
          <div className="space-y-4">
            <div className="bg-amber-500/10 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-amber-400">{goldenRules.length}</div>
              <div className="text-sm text-slate-400">Constitutional Rules</div>
              <p className="text-xs text-slate-500 mt-1">These rules are loaded into EVERY agent context</p>
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {goldenRules.map((h: any, idx: number) => (
                <div key={h.id || idx} className="bg-slate-700/50 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <Star className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <span className="text-sm text-white font-medium">{h.rule}</span>
                      {h.explanation && (
                        <p className="text-xs text-slate-400 mt-1">{h.explanation}</p>
                      )}
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span className="text-xs bg-amber-500/20 px-2 py-0.5 rounded text-amber-300">{h.domain || 'general'}</span>
                        <span className="text-xs text-slate-500">Validated: {h.times_validated || 0}x</span>
                        <span className="text-xs text-slate-500">Conf: {((h.confidence || 0) * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {goldenRules.length === 0 && (
                <div className="text-center text-slate-400 py-4">
                  <p>No golden rules yet</p>
                  <p className="text-xs text-slate-500 mt-1">Promote high-confidence heuristics to create golden rules</p>
                </div>
              )}
            </div>
          </div>
        )
      }

      case 'hotspots': {
        const hotspots = drillDownData || []
        const totalTrails = hotspots.reduce((sum: number, h: any) => sum + (h.trail_count || 0), 0)
        const totalStrength = hotspots.reduce((sum: number, h: any) => sum + (h.total_strength || 0), 0)
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-orange-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-orange-400">{hotspots.length}</div>
                <div className="text-xs text-slate-400">Locations</div>
              </div>
              <div className="bg-red-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-red-400">{totalTrails}</div>
                <div className="text-xs text-slate-400">Trails</div>
              </div>
              <div className="bg-purple-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-purple-400">{totalStrength.toFixed(1)}</div>
                <div className="text-xs text-slate-400">Strength</div>
              </div>
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {hotspots.length > 0 ? hotspots.slice(0, 20).map((h: any, idx: number) => (
                <div key={idx} className="bg-slate-700/50 rounded-lg p-3">
                  <div className="text-sm text-white font-mono truncate" title={h.location}>{h.location}</div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-400 flex-wrap">
                    <span>Trails: {h.trail_count}</span>
                    <span>Strength: {(h.total_strength || 0).toFixed(1)}</span>
                    <span>Agents: {h.agent_count}</span>
                  </div>
                  {h.scents && h.scents.length > 0 && (
                    <div className="flex gap-1 mt-2 flex-wrap">
                      {h.scents.slice(0, 4).map((scent: string, i: number) => (
                        <span key={i} className="text-xs bg-slate-600 px-2 py-0.5 rounded text-slate-300">{scent}</span>
                      ))}
                    </div>
                  )}
                </div>
              )) : (
                <div className="text-center text-slate-400 py-4">
                  <p>No hotspots detected</p>
                  <p className="text-xs text-slate-500 mt-1">Trails are recorded when agents work in the codebase</p>
                </div>
              )}
            </div>
          </div>
        )
      }

      case 'queries': {
        const queries = drillDownData || []
        const successfulQueries = queries.filter((q: any) => q.status === 'success').length
        const totalQueries = queries.length
        const successRate = totalQueries > 0 ? ((successfulQueries / totalQueries) * 100).toFixed(1) : '0'
        const avgDuration = totalQueries > 0
          ? (queries.reduce((sum: number, q: any) => sum + (q.duration_ms || 0), 0) / totalQueries).toFixed(0)
          : '0'

        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-indigo-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-indigo-400">{totalQueries}</div>
                <div className="text-xs text-slate-400">Total</div>
              </div>
              <div className="bg-emerald-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-emerald-400">{successRate}%</div>
                <div className="text-xs text-slate-400">Success</div>
              </div>
              <div className="bg-sky-500/10 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-sky-400">{avgDuration}ms</div>
                <div className="text-xs text-slate-400">Avg Duration</div>
              </div>
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {queries.slice(0, 30).map((q: any, idx: number) => (
                <div key={q.id || idx} className="bg-slate-700/50 rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white font-medium">{q.query_type || 'context'}</span>
                    <span className={
                      q.status === 'success' ? 'text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400' :
                      q.status === 'error' ? 'text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400' :
                      'text-xs px-2 py-0.5 rounded bg-sky-500/20 text-sky-400'
                    }>
                      {q.status}
                    </span>
                  </div>
                  {q.domain && (
                    <div className="mt-1">
                      <span className="text-xs bg-slate-600 px-2 py-0.5 rounded text-slate-300">{q.domain}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-slate-400">
                      {q.created_at ? new Date(q.created_at + 'Z').toLocaleString() : 'No date'}
                    </span>
                    {q.duration_ms !== null && q.duration_ms !== undefined && (
                      <span className="text-xs text-slate-500">{q.duration_ms}ms</span>
                    )}
                  </div>
                  {q.query_summary && (
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{q.query_summary}</p>
                  )}
                </div>
              ))}
              {queries.length === 0 && (
                <div className="text-center text-slate-400 py-4">No queries found</div>
              )}
            </div>
          </div>
        )
      }

      default:
        return null
    }
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
        {statCards.map(({ label, value, icon: Icon, color, bgColor }) => (
          <div
            key={label}
            onClick={() => setExpandedCard(expandedCard === label ? null : label)}
            className="glass-panel rounded-lg p-4 card-glow transition-all hover:scale-105 cursor-pointer hover:ring-2 hover:ring-slate-600"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-400 font-medium">{label}</span>
              <div className={`p-1.5 rounded-md ${bgColor}`}>
                <Icon className={`w-3.5 h-3.5 ${color}`} />
              </div>
            </div>
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {expandedCard && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setExpandedCard(null)}
        >
          <div
            className="glass-panel rounded-xl p-6 max-w-lg w-full shadow-2xl max-h-[90vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {(() => {
              const card = statCards.find(c => c.label === expandedCard)
              if (!card) return null
              const Icon = card.icon
              return (
                <>
                  <div className="flex items-center justify-between mb-4">
                    {drillDownView !== 'main' ? (
                      <button onClick={goBack} className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                        <ArrowLeft className="w-4 h-4" />
                        <span className="text-sm">Back</span>
                      </button>
                    ) : (
                      <div className="flex items-center gap-3">
                        <div className={`p-3 rounded-lg ${card.bgColor}`}>
                          <Icon className={`w-6 h-6 ${card.color}`} />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-white">{card.label}</h3>
                          <div className={`text-3xl font-bold ${card.color}`}>{card.value}</div>
                        </div>
                      </div>
                    )}
                    <button onClick={() => setExpandedCard(null)} className="p-2 text-slate-400 hover:text-white transition-colors">
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <div className="flex-1 overflow-y-auto">
                    {drillDownView === 'main' ? (
                      <>
                        <p className="text-slate-300 text-sm mb-4">{card.description}</p>

                        {card.details && card.details.length > 0 && (
                          <div className="border-t border-slate-700 pt-4 mb-4">
                            <h4 className="text-xs font-medium text-slate-400 mb-3">DETAILS</h4>
                            <div className="space-y-2">
                              {card.details.map((detail, idx) => (
                                <div key={idx} className="flex items-center justify-between">
                                  <span className="text-sm text-slate-400">{detail.label}</span>
                                  <span className="text-sm font-medium text-white">{detail.value}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {card.drillDownType && (
                          <button
                            onClick={() => loadDrillDownData(card.drillDownType as DrillDownView)}
                            className="w-full flex items-center justify-between p-3 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-colors group"
                          >
                            <span className="text-sm text-slate-300 group-hover:text-white">
                              View all {card.label.toLowerCase()}
                            </span>
                            <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-white" />
                          </button>
                        )}
                      </>
                    ) : (
                      renderDrillDownContent(card)
                    )}
                  </div>
                </>
              )
            })()}
          </div>
        </div>
      )}
    </>
  )
}
