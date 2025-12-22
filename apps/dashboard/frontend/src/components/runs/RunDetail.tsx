import { ExternalLink, RefreshCw, FileText } from 'lucide-react'
import { format } from 'date-fns'
import { RunDetailProps } from './types'

export default function RunDetail({
  run,
  onOpenInEditor,
  onRetry,
  onViewChanges,
  loadingDiff
}: RunDetailProps) {
  return (
    <div className="px-3 pb-3 border-t border-slate-600">
      <div className="pt-3 space-y-3">
        {/* Timestamps */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-400">Started:</span>
            <span className="text-white ml-2">{format(new Date(run.started_at), 'MMM d, HH:mm:ss')}</span>
          </div>
          {run.completed_at && (
            <div>
              <span className="text-slate-400">Completed:</span>
              <span className="text-white ml-2">{format(new Date(run.completed_at), 'MMM d, HH:mm:ss')}</span>
            </div>
          )}
        </div>

        {/* Outcome reason */}
        {run.outcome_reason && (
          <div>
            <div className="text-xs text-slate-400 mb-1">Outcome</div>
            <div className={`text-sm ${run.status === 'failure' ? 'text-red-400' : 'text-slate-300'}`}>
              {run.outcome_reason}
            </div>
          </div>
        )}

        {/* Heuristics used */}
        {run.heuristics_used.length > 0 && (
          <div>
            <div className="text-xs text-slate-400 mb-1">Heuristics Used ({run.heuristics_used.length})</div>
            <div className="flex flex-wrap gap-1">
              {run.heuristics_used.map(id => (
                <span key={id} className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-400 text-xs">
                  #{id}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Files touched */}
        {run.files_touched.length > 0 && (
          <div>
            <div className="text-xs text-slate-400 mb-1">Files Touched ({run.files_touched.length})</div>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {run.files_touched.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-sm bg-slate-800/50 rounded px-2 py-1 group"
                >
                  <span className="text-slate-300 truncate">{file}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); onOpenInEditor(file) }}
                    className="opacity-0 group-hover:opacity-100 text-sky-400 hover:text-sky-300 transition"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center space-x-2 pt-2">
          <button
            onClick={(e) => { e.stopPropagation(); onViewChanges(run.id) }}
            disabled={loadingDiff === run.id}
            className="flex items-center space-x-1 px-3 py-1.5 bg-violet-500/20 text-violet-400 rounded-lg text-sm hover:bg-violet-500/30 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FileText className="w-4 h-4" />
            <span>{loadingDiff === run.id ? 'Loading...' : 'View Changes'}</span>
          </button>
          {run.status === 'failure' && (
            <button
              onClick={(e) => { e.stopPropagation(); onRetry(run.id) }}
              className="flex items-center space-x-1 px-3 py-1.5 bg-sky-500/20 text-sky-400 rounded-lg text-sm hover:bg-sky-500/30 transition"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retry</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
