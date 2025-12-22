import { Star } from 'lucide-react'
import { DrillDownProps } from './types'

export default function HeuristicsDrillDown({ data }: DrillDownProps) {
  const heuristics = data || []
  const domains = [...new Set(heuristics.map((h: any) => h.domain))].filter(Boolean)
  const goldenCount = heuristics.filter((h: any) => h.is_golden).length
  const avgConfidence = heuristics.length > 0
    ? (heuristics.reduce((sum: number, h: any) => sum + (h.confidence || 0), 0) / heuristics.length)
    : 0

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-violet-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-violet-400">{heuristics.length}</div>
          <div className="text-xs text-slate-400">Total</div>
        </div>
        <div className="bg-amber-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-amber-400">{goldenCount}</div>
          <div className="text-xs text-slate-400">Golden</div>
        </div>
        <div className="bg-sky-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-sky-400">{(avgConfidence * 100).toFixed(0)}%</div>
          <div className="text-xs text-slate-400">Avg Conf</div>
        </div>
      </div>
      <div className="text-xs text-slate-500 text-center">
        Across {domains.length} domains
      </div>
      <div className="max-h-64 overflow-y-auto space-y-2">
        {heuristics.slice(0, 20).map((h: any, idx: number) => (
          <div key={h.id || idx} className="bg-slate-700/50 rounded-lg p-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm text-white flex-1">{h.rule}</span>
              {h.is_golden && <Star className="w-4 h-4 text-amber-400 flex-shrink-0" />}
            </div>
            {h.explanation && (
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">{h.explanation}</p>
            )}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className="text-xs bg-slate-600 px-2 py-0.5 rounded text-slate-300">{h.domain || 'general'}</span>
              <span className="text-xs text-slate-400">Conf: {((h.confidence || 0) * 100).toFixed(0)}%</span>
              <span className="text-xs text-slate-500">✓{h.times_validated || 0} ✗{h.times_violated || 0}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
