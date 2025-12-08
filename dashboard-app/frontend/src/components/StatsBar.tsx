import { TrendingUp, CheckCircle, XCircle, Brain, Star, Target, Zap, BarChart3 } from 'lucide-react'
import { Stats } from '../types'

interface StatsBarProps {
  stats: Stats | null
}

export default function StatsBar({ stats }: StatsBarProps) {
  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="bg-slate-800 rounded-lg p-4 animate-pulse">
            <div className="h-4 bg-slate-700 rounded w-1/2 mb-2" />
            <div className="h-8 bg-slate-700 rounded w-3/4" />
          </div>
        ))}
      </div>
    )
  }

  const statCards = [
    {
      label: 'Total Runs',
      value: stats.total_runs,
      icon: BarChart3,
      color: 'text-sky-400',
      bgColor: 'bg-sky-500/10',
    },
    {
      label: 'Success Rate',
      value: `${(stats.success_rate * 100).toFixed(1)}%`,
      icon: TrendingUp,
      color: stats.success_rate >= 0.8 ? 'text-emerald-400' : stats.success_rate >= 0.5 ? 'text-amber-400' : 'text-red-400',
      bgColor: stats.success_rate >= 0.8 ? 'bg-emerald-500/10' : stats.success_rate >= 0.5 ? 'bg-amber-500/10' : 'bg-red-500/10',
    },
    {
      label: 'Successful',
      value: stats.successful_runs,
      icon: CheckCircle,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
    },
    {
      label: 'Failed',
      value: stats.failed_runs,
      icon: XCircle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
    },
    {
      label: 'Heuristics',
      value: stats.total_heuristics,
      icon: Brain,
      color: 'text-violet-400',
      bgColor: 'bg-violet-500/10',
    },
    {
      label: 'Golden Rules',
      value: stats.golden_rules,
      icon: Star,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
    },
    {
      label: 'Hotspots',
      value: stats.hotspot_count,
      icon: Target,
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10',
    },
    {
      label: 'Today',
      value: stats.runs_today,
      icon: Zap,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
      {statCards.map(({ label, value, icon: Icon, color, bgColor }) => (
        <div
          key={label}
          className="bg-slate-800 rounded-lg p-4 card-glow transition-all hover:scale-105"
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
  )
}
