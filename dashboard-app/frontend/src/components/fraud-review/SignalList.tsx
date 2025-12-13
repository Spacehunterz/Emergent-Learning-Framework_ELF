import { SignalListProps } from './types'
import { getSeverityBadge } from './utils'

export default function SignalList({ signals, performanceStats }: SignalListProps) {
  return (
    <div className="border-t border-gray-700 bg-gray-900/50 p-4">
      <h4 className="text-sm font-medium text-gray-300 mb-3">Anomaly Signals</h4>

      {signals && signals.length > 0 ? (
        <div className="space-y-3">
          {signals.map(signal => (
            <div
              key={signal.id}
              className="bg-gray-800/50 border border-gray-700 rounded p-3"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-xs font-mono text-gray-400">{signal.detector_name}</span>
                    {getSeverityBadge(signal.severity)}
                  </div>
                  <p className="text-sm text-gray-300">{signal.reason}</p>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium text-orange-400">
                    {(signal.score * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-500">score</div>
                </div>
              </div>

              {signal.evidence && Object.keys(signal.evidence).length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-700">
                  <div className="text-xs text-gray-500 mb-1">Evidence:</div>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(signal.evidence).map(([key, value]) => (
                      <div key={key} className="text-xs">
                        <span className="text-gray-500">{key}:</span>{' '}
                        <span className="text-gray-300">
                          {typeof value === 'number'
                            ? value.toFixed(3)
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-gray-500 italic">No signals available</div>
      )}

      <div className="mt-4 pt-4 border-t border-gray-700">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Heuristic Performance</h4>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Validated</div>
            <div className="text-gray-200 font-medium">{performanceStats.validated}</div>
          </div>
          <div>
            <div className="text-gray-500">Violated</div>
            <div className="text-gray-200 font-medium">{performanceStats.violated}</div>
          </div>
          <div>
            <div className="text-gray-500">Contradicted</div>
            <div className="text-gray-200 font-medium">{performanceStats.contradicted}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
