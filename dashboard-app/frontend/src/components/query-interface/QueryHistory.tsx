import { Clock } from 'lucide-react'
import { QueryHistoryProps } from './types'

export default function QueryHistory({ history, onSelectQuery }: QueryHistoryProps) {
  return (
    <div className="border-t border-slate-700 pt-4 mt-4">
      <div className="flex items-center space-x-2 text-sm text-slate-400 mb-2">
        <Clock className="w-4 h-4" />
        <span>Recent queries</span>
      </div>
      <div className="space-y-1">
        {history.map((h, idx) => (
          <button
            key={idx}
            onClick={() => onSelectQuery(h)}
            className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-700 transition"
          >
            {h}
          </button>
        ))}
      </div>
    </div>
  )
}
