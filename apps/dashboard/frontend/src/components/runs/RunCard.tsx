import { ChevronDown } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { RunCardProps } from './types'

export default function RunCard({
  run,
  isExpanded,
  onToggle,
  getStatusColor,
  getStatusIcon,
  formatDuration
}: RunCardProps) {
  const StatusIcon = getStatusIcon(run.status)

  return (
    <div
      className="p-3 cursor-pointer"
      onClick={() => onToggle(run.id)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          <div className={`p-2 rounded-lg ${getStatusColor(run.status)}`}>
            <StatusIcon className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-0.5">
              <span className="text-sm font-medium text-white truncate">{run.description}</span>
              <span className="px-1.5 py-0.5 rounded bg-slate-600 text-xs text-slate-300 flex-shrink-0">
                {run.agent_type}
              </span>
            </div>
            <div className="text-xs text-slate-400">
              {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
          <div className="text-right">
            <div className="text-sm font-medium text-white">{formatDuration(run.duration_ms)}</div>
            <div className="text-xs text-slate-400">{run.files_touched.length} files</div>
          </div>
          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
        </div>
      </div>
    </div>
  )
}
