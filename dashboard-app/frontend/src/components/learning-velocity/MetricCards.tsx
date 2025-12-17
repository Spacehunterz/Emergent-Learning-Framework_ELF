import { TrendingUp, TrendingDown, Minus, Flame, Calendar, CheckCircle, RefreshCw, Target, Zap } from 'lucide-react'
import { MetricCardsProps } from './types'

const getTrendIcon = (trend: number) => {
  if (trend > 5) return <TrendingUp className="w-4 h-4 text-green-400" />
  if (trend < -5) return <TrendingDown className="w-4 h-4 text-red-400" />
  return <Minus className="w-4 h-4 text-slate-400" />
}

const getTrendColor = (trend: number) => {
  if (trend > 5) return 'text-green-400'
  if (trend < -5) return 'text-red-400'
  return 'text-slate-400'
}

export default function MetricCards({ data, timeframe }: MetricCardsProps) {
  const periodLabel = timeframe === 7 ? 'week' : timeframe === 30 ? 'month' : timeframe === 90 ? 'quarter' : timeframe === 365 ? 'year' : 'period'

  return (
    <>
      {/* Primary Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* New Heuristics */}
        <div className="relative overflow-hidden bg-gradient-to-br from-blue-500/20 to-blue-600/5 border border-blue-500/30 rounded-xl p-4 group hover:border-blue-400/50 transition-all duration-300">
          <div className="absolute top-0 right-0 w-20 h-20 bg-blue-500/10 rounded-full blur-2xl group-hover:bg-blue-400/20 transition-colors" />
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">New Heuristics</span>
              {getTrendIcon(data.heuristics_trend)}
            </div>
            <div className="text-3xl font-bold text-blue-400 mb-1">{data.totals.heuristics}</div>
            <div className={`text-xs ${getTrendColor(data.heuristics_trend)}`}>
              {data.heuristics_trend > 0 ? '+' : ''}{data.heuristics_trend}% vs last {periodLabel}
            </div>
          </div>
        </div>

        {/* Total Learnings */}
        <div className="relative overflow-hidden bg-gradient-to-br from-purple-500/20 to-purple-600/5 border border-purple-500/30 rounded-xl p-4 group hover:border-purple-400/50 transition-all duration-300">
          <div className="absolute top-0 right-0 w-20 h-20 bg-purple-500/10 rounded-full blur-2xl group-hover:bg-purple-400/20 transition-colors" />
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">Total Learnings</span>
              <Calendar className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-3xl font-bold text-purple-400 mb-1">{data.totals.learnings}</div>
            <div className="text-xs text-slate-500">
              Successes + Failures
            </div>
          </div>
        </div>

        {/* Golden Rules */}
        <div className="relative overflow-hidden bg-gradient-to-br from-amber-500/20 to-amber-600/5 border border-amber-500/30 rounded-xl p-4 group hover:border-amber-400/50 transition-all duration-300">
          <div className="absolute top-0 right-0 w-20 h-20 bg-amber-500/10 rounded-full blur-2xl group-hover:bg-amber-400/20 transition-colors" />
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">Golden Rules</span>
              <CheckCircle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-3xl font-bold text-amber-400 mb-1">{data.totals.promotions}</div>
            <div className="text-xs text-slate-500">
              Promoted this {periodLabel}
            </div>
          </div>
        </div>

        {/* Learning Streak */}
        <div className="relative overflow-hidden bg-gradient-to-br from-orange-500/20 to-orange-600/5 border border-orange-500/30 rounded-xl p-4 group hover:border-orange-400/50 transition-all duration-300">
          <div className="absolute top-0 right-0 w-20 h-20 bg-orange-500/10 rounded-full blur-2xl group-hover:bg-orange-400/20 transition-colors" />
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">Learning Streak</span>
              <Flame className="w-4 h-4 text-orange-400" />
            </div>
            <div className="text-3xl font-bold text-orange-400 mb-1">{data.current_streak}</div>
            <div className="text-xs text-slate-500">
              Consecutive days
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Metrics Row - New Velocity Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Failure to Learning Conversion */}
        <div className="relative overflow-hidden bg-gradient-to-br from-cyan-500/15 to-teal-600/5 border border-cyan-500/20 rounded-xl p-4 group hover:border-cyan-400/40 transition-all duration-300">
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-2xl" />
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">Failure Conversion</span>
              <RefreshCw className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold text-cyan-400">
                {data.failure_to_learning_rate?.toFixed(1) ?? '0.0'}
              </span>
              <span className="text-sm text-cyan-400/70">%</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Failures converted to heuristics
            </div>
            {(data.totals.failures ?? 0) > 0 && (
              <div className="text-xs text-slate-600 mt-0.5">
                {data.totals.heuristics_from_failures ?? 0} of {data.totals.failures ?? 0} failures
              </div>
            )}
          </div>
        </div>

        {/* Confidence Improvement */}
        <div className="relative overflow-hidden bg-gradient-to-br from-emerald-500/15 to-green-600/5 border border-emerald-500/20 rounded-xl p-4 group hover:border-emerald-400/40 transition-all duration-300">
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl" />
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">Confidence Trend</span>
              <Target className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="flex items-baseline gap-1">
              <span className={`text-2xl font-bold ${(data.confidence_improvement ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {(data.confidence_improvement ?? 0) >= 0 ? '+' : ''}{(data.confidence_improvement ?? 0).toFixed(2)}
              </span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Avg confidence change
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-1.5 mt-2">
              <div
                className="bg-gradient-to-r from-emerald-500 to-green-400 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, 50 + (data.confidence_improvement ?? 0) * 50))}%` }}
              />
            </div>
          </div>
        </div>

        {/* Promotion Rate */}
        <div className="relative overflow-hidden bg-gradient-to-br from-pink-500/15 to-rose-600/5 border border-pink-500/20 rounded-xl p-4 group hover:border-pink-400/40 transition-all duration-300">
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-pink-500/5 rounded-full blur-2xl" />
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 text-sm font-medium">Promotion Rate</span>
              <Zap className="w-4 h-4 text-pink-400" />
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold text-pink-400">
                {data.promotion_rate?.toFixed(1) ?? '0.0'}
              </span>
              <span className="text-sm text-pink-400/70">%</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Eligible heuristics promoted
            </div>
          </div>
        </div>
      </div>

      {/* ROI Summary - Enhanced */}
      <div className="relative overflow-hidden bg-gradient-to-r from-green-500/15 via-emerald-500/10 to-teal-500/15 border border-green-500/30 rounded-xl p-5 mb-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-green-400/5 via-transparent to-transparent" />
        <div className="relative">
          <h3 className="text-lg font-semibold text-green-400 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Learning ROI Summary
          </h3>
          <p className="text-slate-300 leading-relaxed">
            Your AI learned <span className="text-green-400 font-bold">{data.totals.heuristics} new patterns</span> this {periodLabel}.
            {data.totals.promotions > 0 && (
              <span> Promoted <span className="text-amber-400 font-bold">{data.totals.promotions} to golden rules</span> - permanent institutional knowledge.</span>
            )}
            {data.current_streak > 1 && (
              <span> On a <span className="text-orange-400 font-bold">{data.current_streak}-day learning streak</span>!</span>
            )}
            {(data.failure_to_learning_rate ?? 0) > 0 && (
              <span> Converting <span className="text-cyan-400 font-bold">{data.failure_to_learning_rate?.toFixed(1)}%</span> of failures into wisdom.</span>
            )}
          </p>
        </div>
      </div>
    </>
  )
}
