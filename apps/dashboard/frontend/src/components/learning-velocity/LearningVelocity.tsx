import { useState } from 'react'
import { Brain } from 'lucide-react'
import { LearningVelocityProps } from './types'
import { useVelocityData } from './useVelocityData'
import TimeframeControls from './TimeframeControls'
import MetricCards from './MetricCards'
import VelocityCharts from './VelocityCharts'

export function LearningVelocity({ days = 30 }: LearningVelocityProps) {
  const [timeframe, setTimeframe] = useState(days)
  const { data, loading } = useVelocityData(timeframe)

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-700 rounded w-1/3 mb-4"></div>
          <div className="h-40 bg-slate-700 rounded mb-4"></div>
          <div className="h-40 bg-slate-700 rounded"></div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <p className="text-slate-400">Failed to load learning velocity data</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with timeframe selector */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-amber-400 flex items-center gap-2">
              <Brain className="w-6 h-6" />
              Learning Velocity
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Track how fast your AI is learning and improving
            </p>
          </div>
          <TimeframeControls timeframe={timeframe} onTimeframeChange={setTimeframe} />
        </div>

        <MetricCards data={data} timeframe={timeframe} />
      </div>

      {/* Charts */}
      <VelocityCharts data={data} />

      {/* Weekly Summary */}
      {data.heuristics_by_week && data.heuristics_by_week.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-indigo-400 mb-4">Weekly Activity</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {data.heuristics_by_week.map((week, idx) => (
              <div
                key={week.week}
                className="bg-slate-700/50 rounded-lg p-3 text-center"
              >
                <div className="text-xs text-slate-400 mb-1">Week {idx + 1}</div>
                <div className="text-2xl font-bold text-indigo-400">
                  {week.heuristics_count}
                </div>
                <div className="text-xs text-slate-500">heuristics</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
