import type { TooltipState } from './types'

interface TreemapTooltipProps {
  tooltipState: TooltipState
  dimensions: { width: number; height: number }
}

export default function TreemapTooltip({ tooltipState, dimensions }: TreemapTooltipProps) {
  if (!tooltipState.data) return null

  return (
    <div
      className="absolute z-10 bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl pointer-events-none"
      style={{
        left: Math.min(tooltipState.x + 10, dimensions.width - 200),
        top: tooltipState.y + 10,
        maxWidth: 300,
      }}
    >
      <div className="font-medium text-white mb-1">{tooltipState.data.location}</div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-slate-400">Trails:</span>
          <span className="text-white ml-1">{tooltipState.data.trail_count}</span>
        </div>
        <div>
          <span className="text-slate-400">Strength:</span>
          <span className="text-white ml-1">{tooltipState.data.total_strength?.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-slate-400">Agents:</span>
          <span className="text-white ml-1">{tooltipState.data.agent_count}</span>
        </div>
        <div>
          <span className="text-slate-400">Scents:</span>
          <span className="text-white ml-1">{tooltipState.data.scents?.join(', ') || 'none'}</span>
        </div>
      </div>
      <div className="mt-2 text-xs text-sky-400">
        Click to expand details
      </div>
    </div>
  )
}
