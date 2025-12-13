import { DrillDownProps } from './types'

export default function QueriesDrillDown({ data }: DrillDownProps) {
  const queries = data || []
  const successfulQueries = queries.filter((q: any) => q.status === 'success').length
  const totalQueries = queries.length
  const successRate = totalQueries > 0 ? ((successfulQueries / totalQueries) * 100).toFixed(1) : '0'
  const avgDuration = totalQueries > 0
    ? (queries.reduce((sum: number, q: any) => sum + (q.duration_ms || 0), 0) / totalQueries).toFixed(0)
    : '0'

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-indigo-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-indigo-400">{totalQueries}</div>
          <div className="text-xs text-slate-400">Total</div>
        </div>
        <div className="bg-emerald-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-emerald-400">{successRate}%</div>
          <div className="text-xs text-slate-400">Success</div>
        </div>
        <div className="bg-sky-500/10 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-sky-400">{avgDuration}ms</div>
          <div className="text-xs text-slate-400">Avg Duration</div>
        </div>
      </div>
      <div className="max-h-64 overflow-y-auto space-y-2">
        {queries.slice(0, 30).map((q: any, idx: number) => (
          <div key={q.id || idx} className="bg-slate-700/50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-white font-medium">{q.query_type || 'context'}</span>
              <span className={
                q.status === 'success' ? 'text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400' :
                q.status === 'error' ? 'text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400' :
                'text-xs px-2 py-0.5 rounded bg-sky-500/20 text-sky-400'
              }>
                {q.status}
              </span>
            </div>
            {q.domain && (
              <div className="mt-1">
                <span className="text-xs bg-slate-600 px-2 py-0.5 rounded text-slate-300">{q.domain}</span>
              </div>
            )}
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-slate-400">
                {q.created_at ? new Date(q.created_at + 'Z').toLocaleString() : 'No date'}
              </span>
              {q.duration_ms !== null && q.duration_ms !== undefined && (
                <span className="text-xs text-slate-500">{q.duration_ms}ms</span>
              )}
            </div>
            {q.query_summary && (
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">{q.query_summary}</p>
            )}
          </div>
        ))}
        {queries.length === 0 && (
          <div className="text-center text-slate-400 py-4">No queries found</div>
        )}
      </div>
    </div>
  )
}
