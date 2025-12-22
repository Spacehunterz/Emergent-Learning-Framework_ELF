import { ChevronDown, Eye, TrendingUp } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ReportCardProps } from './types'
import { getClassificationBadge, calculateSuccessRate } from './utils'
import SignalList from './SignalList'

export default function ReportCard({
  report,
  isExpanded,
  isLoading,
  selectedReport,
  onToggle,
  onReview,
}: ReportCardProps) {
  const successRate = calculateSuccessRate(report)

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden hover:border-gray-600 transition-colors">
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              {getClassificationBadge(report.classification)}
              <span className="text-xs text-gray-500">
                Report #{report.id}
              </span>
              <span className="text-xs text-gray-500">•</span>
              <span className="text-xs text-gray-400">
                {formatDistanceToNow(new Date(report.created_at), { addSuffix: true })}
              </span>
            </div>

            <h3 className="text-sm font-medium text-gray-200 mb-1">
              [{report.domain}] {report.rule.substring(0, 80)}
              {report.rule.length > 80 && '...'}
            </h3>

            <div className="flex items-center space-x-4 text-xs text-gray-400">
              <div className="flex items-center space-x-1">
                <TrendingUp className="w-3 h-3" />
                <span>Fraud Score: {(report.fraud_score * 100).toFixed(1)}%</span>
              </div>
              <div>Success Rate: {successRate.toFixed(1)}%</div>
              <div>{report.signal_count} signals</div>
              <div>Confidence: {(report.confidence * 100).toFixed(0)}%</div>
            </div>
          </div>

          <div className="flex items-center space-x-2 ml-4">
            <button
              onClick={onToggle}
              className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
              title="View details"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 transform rotate-180" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-2 mt-4">
          <button
            onClick={() => onReview(report.id, 'true_positive')}
            disabled={isLoading}
            className="px-3 py-1.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Processing...' : 'Confirm Fraud'}
          </button>
          <button
            onClick={() => onReview(report.id, 'false_positive')}
            disabled={isLoading}
            className="px-3 py-1.5 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Processing...' : 'Mark as Safe'}
          </button>
        </div>
      </div>

      {isExpanded && selectedReport && (
        <SignalList
          signals={selectedReport.signals || []}
          performanceStats={{
            validated: selectedReport.times_validated || 0,
            violated: selectedReport.times_violated || 0,
            contradicted: selectedReport.times_contradicted || 0,
          }}
        />
      )}
    </div>
  )
}
