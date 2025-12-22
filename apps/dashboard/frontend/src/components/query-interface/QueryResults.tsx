import { Sparkles, Brain, Lightbulb, Target } from 'lucide-react'
import { QueryResultsProps } from './types'
import ResultItem from './ResultItem'

export default function QueryResults({ result }: QueryResultsProps) {
  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="bg-sky-500/10 border border-sky-500/20 rounded-lg p-4">
        <div className="flex items-start space-x-2">
          <Sparkles className="w-4 h-4 text-sky-400 mt-0.5 flex-shrink-0" />
          <div>
            <div className="text-sm font-medium text-sky-400 mb-1">Results Summary</div>
            <div className="text-sm text-slate-300">{result.summary}</div>
          </div>
        </div>
      </div>

      {/* Results by category */}
      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
        {/* Heuristics */}
        {result.heuristics.length > 0 && (
          <div>
            <div className="text-sm text-slate-400 mb-2 flex items-center space-x-2">
              <Brain className="w-4 h-4" />
              <span>Heuristics ({result.heuristics.length})</span>
            </div>
            <div className="space-y-2">
              {result.heuristics.map((item, idx) => (
                <ResultItem key={idx} item={{ ...item, _type: 'heuristic' }} index={idx} />
              ))}
            </div>
          </div>
        )}

        {/* Learnings */}
        {result.learnings.length > 0 && (
          <div>
            <div className="text-sm text-slate-400 mb-2 flex items-center space-x-2">
              <Lightbulb className="w-4 h-4" />
              <span>Learnings ({result.learnings.length})</span>
            </div>
            <div className="space-y-2">
              {result.learnings.map((item, idx) => (
                <ResultItem key={idx} item={{ ...item, _type: 'learning' }} index={idx} />
              ))}
            </div>
          </div>
        )}

        {/* Hotspots */}
        {result.hotspots.length > 0 && (
          <div>
            <div className="text-sm text-slate-400 mb-2 flex items-center space-x-2">
              <Target className="w-4 h-4" />
              <span>Hotspots ({result.hotspots.length})</span>
            </div>
            <div className="space-y-2">
              {result.hotspots.map((item, idx) => (
                <ResultItem key={idx} item={{ ...item, _type: 'hotspot' }} index={idx} />
              ))}
            </div>
          </div>
        )}

        {/* No results message */}
        {result.heuristics.length === 0 && result.learnings.length === 0 && result.hotspots.length === 0 && (
          <div className="text-center text-slate-400 py-8">
            No results found. Try a different query.
          </div>
        )}
      </div>
    </div>
  )
}
