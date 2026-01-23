import { useState, useEffect } from 'react'
import { TrendingUp, CheckCircle, XCircle, Brain, Star, Target, BarChart3, MessageSquare } from 'lucide-react'
import { useAPI } from '../hooks/useAPI'
import { StatsDrillDownView, DrillDownType } from './stats'

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
  onNavigate?: (tab: string, domain?: string) => void
}

interface StatCardData {
  label: string
  value: string | number
  icon: any
  color: string
  bgColor: string
  glowColor: string
  drillDownType: DrillDownType
}

export default function StatsBar({ stats, onNavigate }: StatsBarProps) {
  const [expandedType, setExpandedType] = useState<DrillDownType | null>(null)
  const [drillDownData, setDrillDownData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const api = useAPI()

  const loadDrillDownData = async (type: DrillDownType) => {
    setLoading(true)
    try {
      let data
      switch (type) {
        case 'runs':
        case 'success_rate':
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
        case 'queries':
          data = await api.get('/api/queries?limit=100')
          break
      }
      setDrillDownData(data)
    } catch (err) {
      console.error('Failed to load drill-down data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCardClick = async (type: DrillDownType) => {
    setExpandedType(type)
    await loadDrillDownData(type)
  }

  const handleClose = () => {
    setExpandedType(null)
    setDrillDownData(null)
  }

  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="glass-panel rounded-xl p-4 animate-pulse">
            <div className="h-3 bg-slate-700 rounded w-1/2 mb-3" />
            <div className="h-7 bg-slate-700 rounded w-3/4" />
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
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
      glowColor: 'rgba(34, 211, 238, 0.4)',
      drillDownType: 'runs',
    },
    {
      label: 'Success Rate',
      value: (stats.success_rate * 100).toFixed(1) + '%',
      icon: TrendingUp,
      color: stats.success_rate >= 0.8 ? 'text-emerald-400' : stats.success_rate >= 0.5 ? 'text-amber-400' : 'text-red-400',
      bgColor: stats.success_rate >= 0.8 ? 'bg-emerald-500/10' : stats.success_rate >= 0.5 ? 'bg-amber-500/10' : 'bg-red-500/10',
      glowColor: stats.success_rate >= 0.8 ? 'rgba(74, 222, 128, 0.4)' : stats.success_rate >= 0.5 ? 'rgba(251, 191, 36, 0.4)' : 'rgba(248, 113, 113, 0.4)',
      drillDownType: 'success_rate',
    },
    {
      label: 'Successful',
      value: stats.successful_runs,
      icon: CheckCircle,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      glowColor: 'rgba(74, 222, 128, 0.4)',
      drillDownType: 'runs',
    },
    {
      label: 'Failed',
      value: stats.failed_runs,
      icon: XCircle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
      glowColor: 'rgba(248, 113, 113, 0.4)',
      drillDownType: 'runs',
    },
    {
      label: 'Heuristics',
      value: stats.total_heuristics,
      icon: Brain,
      color: 'text-violet-400',
      bgColor: 'bg-violet-500/10',
      glowColor: 'rgba(167, 139, 250, 0.4)',
      drillDownType: 'heuristics',
    },
    {
      label: 'Golden Rules',
      value: stats.golden_rules,
      icon: Star,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      glowColor: 'rgba(251, 191, 36, 0.4)',
      drillDownType: 'golden',
    },
    {
      label: 'Hotspots',
      value: stats.hotspot_count,
      icon: Target,
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10',
      glowColor: 'rgba(251, 146, 60, 0.4)',
      drillDownType: 'hotspots',
    },
    {
      label: 'Queries',
      value: stats.queries_today || 0,
      icon: MessageSquare,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10',
      glowColor: 'rgba(129, 140, 248, 0.4)',
      drillDownType: 'queries',
    },
  ]

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        {statCards.map(({ label, value, icon: Icon, color, bgColor, glowColor, drillDownType }) => (
          <div
            key={label}
            onClick={() => handleCardClick(drillDownType)}
            className="group relative rounded-xl p-4 cursor-pointer transition-all duration-300 hover:scale-105 overflow-hidden"
            style={{
              background: `linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.6) 100%)`,
              border: '1px solid rgba(100, 116, 139, 0.2)',
            }}
          >
            {/* Hover glow effect */}
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl"
              style={{
                background: `radial-gradient(circle at center, ${glowColor} 0%, transparent 70%)`,
              }}
            />

            {/* Top glow line on hover */}
            <div
              className="absolute top-0 left-0 right-0 h-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{
                background: `linear-gradient(90deg, transparent, ${glowColor.replace('0.4', '0.8')}, transparent)`,
              }}
            />

            <div className="relative z-10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 group-hover:text-slate-400 transition-colors">
                  {label}
                </span>
                <div className={`p-1.5 rounded-lg ${bgColor} group-hover:scale-110 transition-transform`}>
                  <Icon className={`w-3.5 h-3.5 ${color}`} />
                </div>
              </div>
              <div
                className={`text-2xl font-bold ${color} transition-all duration-300 group-hover:scale-105`}
                style={{
                  textShadow: `0 0 20px ${glowColor}`,
                }}
              >
                {value}
              </div>
            </div>

            {/* Click indicator */}
            <div className="absolute bottom-2 right-2 text-[8px] text-slate-600 group-hover:text-slate-400 transition-colors uppercase tracking-wider">
              Click to explore
            </div>
          </div>
        ))}
      </div>

      {/* Full-screen drill-down view */}
      {expandedType && (
        <StatsDrillDownView
          type={expandedType}
          stats={stats}
          data={drillDownData}
          loading={loading}
          onClose={handleClose}
          onNavigate={onNavigate}
        />
      )}
    </>
  )
}
