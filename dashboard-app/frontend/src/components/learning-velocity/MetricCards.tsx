import { TrendingUp, TrendingDown, Minus, Flame, Calendar, CheckCircle } from 'lucide-react'
import { MetricCardsProps } from './types'

const getTrendIcon = (trend: number) => {
  if (trend > 5) return <TrendingUp className="w-4 h-4 text-green-500" />
  if (trend < -5) return <TrendingDown className="w-4 h-4 text-red-500" />
  return <Minus className="w-4 h-4 text-slate-400" />
}

export default function MetricCards({ data, timeframe }: MetricCardsProps) {
  return (
    <>
      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {/* Total Heuristics */}
        <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">New Heuristics</span>
            {getTrendIcon(data.heuristics_trend)}
          </div>
          <div className="text-3xl font-bold text-blue-400">{data.totals.heuristics}</div>
          <div className="text-xs text-slate-500 mt-1">
            {data.heuristics_trend > 0 ? '+' : ''}{data.heuristics_trend}% vs last period
          </div>
        </div>

        {/* Total Learnings */}
        <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border border-purple-500/20 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Total Learnings</span>
            <Calendar className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-3xl font-bold text-purple-400">{data.totals.learnings}</div>
          <div className="text-xs text-slate-500 mt-1">
            Successes + Failures
          </div>
        </div>

        {/* Golden Rules */}
        <div className="bg-gradient-to-br from-amber-500/10 to-amber-600/5 border border-amber-500/20 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Golden Rules</span>
            <CheckCircle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-bold text-amber-400">{data.totals.promotions}</div>
          <div className="text-xs text-slate-500 mt-1">
            Promoted in period
          </div>
        </div>

        {/* Learning Streak */}
        <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 border border-orange-500/20 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm">Learning Streak</span>
            <Flame className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-3xl font-bold text-orange-400">{data.current_streak}</div>
          <div className="text-xs text-slate-500 mt-1">
            Consecutive days
          </div>
        </div>
      </div>

      {/* ROI Summary */}
      <div className="bg-gradient-to-r from-green-500/10 to-emerald-600/10 border border-green-500/30 rounded-lg p-4 mb-6">
        <h3 className="text-lg font-semibold text-green-400 mb-2">Learning ROI</h3>
        <p className="text-slate-300">
          Your AI learned <span className="text-green-400 font-bold">{data.totals.heuristics} new patterns</span> this {timeframe === 7 ? 'week' : timeframe === 30 ? 'month' : 'period'}.
          {data.totals.promotions > 0 && (
            <span> Promoted <span className="text-amber-400 font-bold">{data.totals.promotions} to golden rules</span> - permanent institutional knowledge.</span>
          )}
          {data.current_streak > 1 && (
            <span> On a <span className="text-orange-400 font-bold">{data.current_streak}-day learning streak</span>!</span>
          )}
        </p>
      </div>
    </>
  )
}
