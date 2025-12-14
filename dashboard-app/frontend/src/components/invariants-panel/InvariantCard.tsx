import { ChevronDown, XCircle, Code } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { InvariantCardProps } from './types'
import { getSeverityBadge, getStatusBadge, getScopeBadge } from './utils'
import InvariantActions from './InvariantActions'

export default function InvariantCard({
  invariant,
  isExpanded,
  isLoading,
  onToggle,
  onValidate,
  onViolate,
}: InvariantCardProps) {
  return (
    <div
      className={`bg-slate-700/50 rounded-lg border transition-all
        ${invariant.status === 'violated' ? 'border-red-500/30' : 'border-transparent'}
        ${isExpanded ? 'ring-2 ring-emerald-500/50' : ''}`}
    >
      {/* Main row */}
      <div
        className="p-3 cursor-pointer hover:bg-slate-700/70 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-2 flex-wrap gap-1">
              {getSeverityBadge(invariant.severity)}
              {getStatusBadge(invariant.status)}
              {getScopeBadge(invariant.scope)}
              {invariant.domain && (
                <span className="px-2 py-0.5 rounded bg-slate-600 text-xs text-slate-300">
                  {invariant.domain}
                </span>
              )}
            </div>
            <div className="text-sm font-medium text-white">
              {invariant.statement}
            </div>
          </div>

          <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
            {/* Violation count */}
            {invariant.violation_count > 0 && (
              <div className="flex items-center space-x-1 px-2 py-1 bg-red-500/20 rounded text-red-400 text-xs">
                <XCircle className="w-3 h-3" />
                <span>{invariant.violation_count} violations</span>
              </div>
            )}

            {/* Validation type */}
            {invariant.validation_type && (
              <span className="text-xs text-slate-400">
                {invariant.validation_type}
              </span>
            )}

            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-slate-600">
          <div className="pt-3 space-y-3">
            {/* Rationale */}
            <div>
              <div className="text-xs text-slate-400 mb-1">Rationale</div>
              <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-2">
                {invariant.rationale}
              </div>
            </div>

            {/* Validation code */}
            {invariant.validation_code && (
              <div>
                <div className="flex items-center space-x-2 text-xs text-slate-400 mb-1">
                  <Code className="w-3 h-3" />
                  <span>Validation Code</span>
                </div>
                <pre className="text-xs text-slate-300 bg-slate-900 rounded p-2 overflow-x-auto">
                  {invariant.validation_code}
                </pre>
              </div>
            )}

            {/* Metadata */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-400">Created:</span>
                <span className="text-white ml-2">
                  {formatDistanceToNow(new Date(invariant.created_at), { addSuffix: true })}
                </span>
              </div>
              {invariant.last_validated_at && (
                <div>
                  <span className="text-slate-400">Last Validated:</span>
                  <span className="text-white ml-2">
                    {formatDistanceToNow(new Date(invariant.last_validated_at), { addSuffix: true })}
                  </span>
                </div>
              )}
              {invariant.last_violated_at && (
                <div>
                  <span className="text-slate-400">Last Violated:</span>
                  <span className="text-red-400 ml-2">
                    {formatDistanceToNow(new Date(invariant.last_violated_at), { addSuffix: true })}
                  </span>
                </div>
              )}
            </div>

            {/* Actions */}
            <InvariantActions
              isLoading={isLoading}
              onValidate={() => onValidate(invariant.id)}
              onViolate={() => onViolate(invariant.id)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
