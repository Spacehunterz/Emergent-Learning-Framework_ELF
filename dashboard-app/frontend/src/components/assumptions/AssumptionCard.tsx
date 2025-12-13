import { CheckCircle, AlertTriangle, ChevronDown, ThumbsUp, HelpCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { AssumptionCardProps } from './types'
import { getStatusBadge, getConfidenceColor } from './utils'

export default function AssumptionCard({
  assumption,
  isExpanded,
  isLoading,
  onToggle,
  onVerify,
  onChallenge,
}: AssumptionCardProps) {
  return (
    <div
      className={`bg-slate-700/50 rounded-lg border border-transparent transition-all
        ${isExpanded ? 'ring-2 ring-sky-500/50' : ''}`}
    >
      <div
        className="p-3 cursor-pointer hover:bg-slate-700/70 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              {getStatusBadge(assumption.status)}
              {assumption.domain && (
                <span className="px-2 py-0.5 rounded bg-slate-600 text-xs text-slate-300">
                  {assumption.domain}
                </span>
              )}
            </div>
            <div className="text-sm font-medium text-white">
              {assumption.assumption}
            </div>
            {assumption.source && (
              <div className="text-xs text-slate-400 mt-1">
                Source: {assumption.source}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
            <div className="w-24">
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-400">Confidence</span>
                <span className="text-white font-medium">{Math.round(assumption.confidence * 100)}%</span>
              </div>
              <div className="h-2 bg-slate-600 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getConfidenceColor(assumption.confidence)} transition-all`}
                  style={{ width: `${assumption.confidence * 100}%` }}
                />
              </div>
            </div>

            <div className="flex items-center space-x-3 text-xs">
              <div className="flex items-center space-x-1 text-emerald-400">
                <ThumbsUp className="w-3 h-3" />
                <span>{assumption.verified_count}</span>
              </div>
              <div className="flex items-center space-x-1 text-amber-400">
                <HelpCircle className="w-3 h-3" />
                <span>{assumption.challenged_count}</span>
              </div>
            </div>

            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="px-3 pb-3 border-t border-slate-600">
          <div className="pt-3 space-y-3">
            <div>
              <div className="text-xs text-slate-400 mb-1">Context</div>
              <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-2">
                {assumption.context}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-400">Created:</span>
                <span className="text-white ml-2">
                  {formatDistanceToNow(new Date(assumption.created_at), { addSuffix: true })}
                </span>
              </div>
              {assumption.last_verified_at && (
                <div>
                  <span className="text-slate-400">Last Verified:</span>
                  <span className="text-white ml-2">
                    {formatDistanceToNow(new Date(assumption.last_verified_at), { addSuffix: true })}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2 pt-2">
              <button
                onClick={(e) => { e.stopPropagation(); onVerify(assumption.id) }}
                disabled={isLoading}
                className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition disabled:opacity-50"
              >
                <CheckCircle className="w-4 h-4" />
                <span>Verify</span>
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onChallenge(assumption.id) }}
                disabled={isLoading}
                className="flex items-center space-x-1 px-3 py-1.5 bg-amber-500/20 text-amber-400 rounded-lg text-sm hover:bg-amber-500/30 transition disabled:opacity-50"
              >
                <AlertTriangle className="w-4 h-4" />
                <span>Challenge</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
