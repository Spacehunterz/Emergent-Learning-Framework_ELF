import { TimeframeControlsProps } from './types'

export default function TimeframeControls({ timeframe, onTimeframeChange }: TimeframeControlsProps) {
  return (
    <div className="flex gap-2">
      {[7, 14, 30, 60, 90].map(d => (
        <button
          key={d}
          onClick={() => onTimeframeChange(d)}
          className={`px-3 py-1 rounded text-sm transition-colors ${
            timeframe === d
              ? 'bg-amber-500 text-black'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          {d}d
        </button>
      ))}
    </div>
  )
}
