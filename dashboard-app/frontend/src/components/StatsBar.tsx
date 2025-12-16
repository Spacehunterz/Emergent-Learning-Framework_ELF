import { useState, useEffect } from 'react'
import { TrendingUp, CheckCircle, XCircle, Brain, Star, Target, BarChart3, MessageSquare } from 'lucide-react'
import { useAPI } from '../hooks/useAPI'
import { DrillDownModal, DrillDownView } from './drilldowns'

export interface DashboardStats {
  total_runs: number
  successful_runs: number
  failed_runs: number
  success_rate: number
  total_heuristics: number
  golden_rules: number
  total_learnings: number
  hotspot_count: number
  avg_confidence: number
  total_validations: number
  runs_today: number
  active_domains: number
  queries_today: number
  total_queries: number
  avg_query_duration_ms: number
}

interface StatsBarProps {
  stats: DashboardStats | null
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

  const selectedCard = statCards.find(c => c.label === expandedCard)

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
        {statCards.map(({ label, value, icon: Icon, color, bgColor }) => (
          <div
            key={label}
            onClick={() => setExpandedCard(expandedCard === label ? null : label)}
            className="rounded-lg p-4 card-glow transition-all hover:scale-105 cursor-pointer"
            style={{
              background: `linear-gradient(135deg, rgba(var(--theme-accent-rgb), calc(var(--glass-opacity) * 0.3)), rgba(var(--theme-panel-rgb), var(--glass-opacity)))`,
              border: '1px solid rgba(var(--theme-accent-rgb), calc(var(--glass-opacity) * 0.5))',
              backdropFilter: 'blur(calc(var(--glass-opacity) * 20px))',
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium" style={{ color: 'var(--theme-text-secondary)' }}>{label}</span>
              <div className={`p-1.5 rounded-md ${bgColor}`}>
                <Icon className={`w-3.5 h-3.5 ${color}`} />
              </div>
            </div>
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {expandedCard && selectedCard && (
        <DrillDownModal
          card={selectedCard}
          drillDownView={drillDownView}
          drillDownData={drillDownData}
          loading={loading}
          error={error}
          onClose={() => setExpandedCard(null)}
          onBack={goBack}
          onLoadDrillDown={loadDrillDownData}
        />
      )}
    </>
  )
}
