import { TimeframeControlsProps } from './types'

const timeframeOptions = [
  { value: 7, label: '7d' },
  { value: 30, label: '30d' },
  { value: 90, label: '90d' },
  { value: 365, label: '1y' },
  { value: 9999, label: 'All' },
]

export default function TimeframeControls({ timeframe, onTimeframeChange }: TimeframeControlsProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {timeframeOptions.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => onTimeframeChange(value)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
            timeframe === value
              ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-black shadow-lg shadow-amber-500/30'
              : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/70 hover:text-white border border-slate-600/50'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
