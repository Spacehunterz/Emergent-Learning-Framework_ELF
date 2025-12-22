import { Star } from 'lucide-react'
import { DrillDownProps } from './types'

export default function GoldenRulesDrillDown({ data }: DrillDownProps) {
  const goldenRules = data || []

  return (
    <div className="space-y-4">
      <div className="bg-amber-500/10 rounded-lg p-4 text-center">
        <div className="text-3xl font-bold text-amber-400">{goldenRules.length}</div>
        <div className="text-sm text-slate-400">Constitutional Rules</div>
        <p className="text-xs text-slate-500 mt-1">These rules are loaded into EVERY agent context</p>
      </div>
      <div className="max-h-64 overflow-y-auto space-y-2">
        {goldenRules.map((h: any, idx: number) => (
          <div key={h.id || idx} className="bg-slate-700/50 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Star className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="text-sm text-white font-medium">{h.rule}</span>
                {h.explanation && (
                  <p className="text-xs text-slate-400 mt-1">{h.explanation}</p>
                )}
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span className="text-xs bg-amber-500/20 px-2 py-0.5 rounded text-amber-300">{h.domain || 'general'}</span>
                  <span className="text-xs text-slate-500">Validated: {h.times_validated || 0}x</span>
                  <span className="text-xs text-slate-500">Conf: {((h.confidence || 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        {goldenRules.length === 0 && (
          <div className="text-center text-slate-400 py-4">
            <p>No golden rules yet</p>
            <p className="text-xs text-slate-500 mt-1">Promote high-confidence heuristics to create golden rules</p>
          </div>
        )}
      </div>
    </div>
  )
}
