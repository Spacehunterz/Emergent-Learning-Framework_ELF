import { Brain, Target, AlertTriangle } from 'lucide-react'
import { ResultItemProps } from './types'

export default function ResultItem({ item, index }: ResultItemProps) {
  // Detect type of result and render appropriately
  if (item._type === 'heuristic' || item.rule) {
    // Heuristic
    return (
      <div key={index} className="bg-slate-700/50 rounded-lg p-3">
        <div className="flex items-center space-x-2 mb-1">
          <Brain className="w-4 h-4 text-violet-400" />
          <span className="text-sm font-medium text-white">{item.rule}</span>
        </div>
        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <span>{item.domain}</span>
          <span>{((item.confidence || 0) * 100).toFixed(0)}% confidence</span>
          <span>{item.times_validated || 0} validations</span>
        </div>
      </div>
    )
  } else if (item._type === 'hotspot' || item.location) {
    // Hotspot - API returns location, strength, count
    return (
      <div key={index} className="bg-slate-700/50 rounded-lg p-3">
        <div className="flex items-center space-x-2 mb-1">
          <Target className="w-4 h-4 text-orange-400" />
          <span className="text-sm font-medium text-white">{item.location || item.file_path}</span>
        </div>
        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <span>{item.count || item.hit_count || 0} trails</span>
          <span>Strength: {(item.strength || 0).toFixed(1)}</span>
        </div>
      </div>
    )
  } else if (item._type === 'learning' || (item.title && item.type)) {
    // Learning/Failure
    return (
      <div key={index} className="bg-slate-700/50 rounded-lg p-3">
        <div className="flex items-center space-x-2 mb-1">
          <AlertTriangle className={`w-4 h-4 ${item.type === 'failure' ? 'text-red-400' : 'text-amber-400'}`} />
          <span className="text-sm font-medium text-white">{item.title}</span>
        </div>
        {item.summary && (
          <div className="text-sm text-slate-300 mt-1">{item.summary.slice(0, 200)}</div>
        )}
        <div className="flex items-center space-x-3 text-xs text-slate-400 mt-2">
          <span>{item.domain}</span>
          <span>{item.created_at}</span>
        </div>
      </div>
    )
  } else {
    // Generic
    return (
      <div key={index} className="bg-slate-700/50 rounded-lg p-3">
        <pre className="text-sm text-slate-300 overflow-x-auto">
          {JSON.stringify(item, null, 2)}
        </pre>
      </div>
    )
  }
}
