import { Clock, Tag, BookOpen, AlertCircle, ExternalLink } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ReportCardProps } from './types'
import StarRating from './StarRating'

export default function ReportCard({
  report,
  isExpanded,
  isRating,
  onToggle,
  onRate,
}: ReportCardProps) {
  return (
    <div
      className={`bg-slate-700/50 rounded-lg border border-transparent transition-all cursor-pointer hover:bg-slate-700/70
        ${isExpanded ? 'ring-2 ring-violet-500/50 md:col-span-2' : ''}`}
      onClick={onToggle}
    >
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              {report.domain && (
                <span className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-400 text-xs">
                  {report.domain}
                </span>
              )}
              <span className="px-2 py-0.5 rounded bg-slate-600 text-slate-300 text-xs">
                {report.topic}
              </span>
            </div>
            <h4 className="text-sm font-medium text-white truncate">{report.title}</h4>
          </div>

          {report.time_invested_minutes && (
            <div className="flex items-center space-x-1 px-2 py-1 bg-sky-500/20 rounded text-sky-400 text-xs flex-shrink-0 ml-2">
              <Clock className="w-3 h-3" />
              <span>{report.time_invested_minutes} min</span>
            </div>
          )}
        </div>

        <div className="text-sm text-slate-300 mb-3">
          <span className="text-slate-400">Q: </span>
          {report.question}
        </div>

        {report.tags && (
          <div className="flex flex-wrap gap-1 mb-3">
            {report.tags.split(',').map((tag, idx) => (
              <span key={idx} className="flex items-center space-x-1 px-1.5 py-0.5 bg-slate-600 rounded text-xs text-slate-300">
                <Tag className="w-2.5 h-2.5" />
                <span>{tag.trim()}</span>
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <StarRating
              score={report.usefulness_score}
              onChange={(score) => onRate(report.id, score)}
              loading={isRating}
            />
            <span className="text-xs text-slate-400">
              {report.access_count} views
            </span>
          </div>
          <div className="text-xs text-slate-400">
            {formatDistanceToNow(new Date(report.created_at), { addSuffix: true })}
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="px-4 pb-4 border-t border-slate-600">
          <div className="pt-4 space-y-4">
            <div>
              <div className="flex items-center space-x-2 text-sm font-medium text-white mb-2">
                <BookOpen className="w-4 h-4 text-emerald-400" />
                <span>Findings</span>
              </div>
              <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-3 whitespace-pre-wrap">
                {report.findings}
              </div>
            </div>

            {report.gotchas && (
              <div>
                <div className="flex items-center space-x-2 text-sm font-medium text-white mb-2">
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                  <span>Gotchas</span>
                </div>
                <div className="text-sm text-slate-300 bg-amber-500/10 rounded p-3 border border-amber-500/20 whitespace-pre-wrap">
                  {report.gotchas}
                </div>
              </div>
            )}

            {report.resources && (
              <div>
                <div className="flex items-center space-x-2 text-sm font-medium text-white mb-2">
                  <ExternalLink className="w-4 h-4 text-sky-400" />
                  <span>Resources</span>
                </div>
                <div className="text-sm text-slate-300 bg-slate-800/50 rounded p-3 whitespace-pre-wrap">
                  {report.resources}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
