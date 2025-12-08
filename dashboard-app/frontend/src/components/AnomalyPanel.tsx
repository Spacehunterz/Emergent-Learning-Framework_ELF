import { AlertTriangle, X, TrendingDown, Repeat, Target, AlertCircle, Zap } from 'lucide-react'

// API anomaly format
interface ApiAnomaly {
  type: string
  severity: string
  message: string
  data: Record<string, any>
}

interface AnomalyPanelProps {
  anomalies: ApiAnomaly[]
  onDismiss: (index: number) => void
}

const anomalyConfig: Record<string, { icon: any; color: string; bg: string; border: string }> = {
  repeated_failure: { icon: Repeat, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30' },
  confidence_drop: { icon: TrendingDown, color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  new_hotspot: { icon: Target, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  hotspot_surge: { icon: Target, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  heuristic_violations: { icon: AlertCircle, color: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/30' },
  stale_run: { icon: Zap, color: 'text-pink-400', bg: 'bg-pink-500/10', border: 'border-pink-500/30' },
}

const severityColors: Record<string, string> = {
  info: 'text-slate-400',
  warning: 'text-amber-400',
  error: 'text-red-400',
  low: 'text-slate-400',
  medium: 'text-amber-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
}

export default function AnomalyPanel({ anomalies, onDismiss }: AnomalyPanelProps) {
  if (!anomalies || anomalies.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <AlertTriangle className="w-5 h-5 text-slate-500" />
          <h3 className="text-lg font-semibold text-white">Anomalies</h3>
        </div>
        <div className="text-center text-slate-400 py-4 text-sm">
          No anomalies detected
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-semibold text-white">Anomalies</h3>
          <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full">
            {anomalies.length}
          </span>
        </div>
      </div>

      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
        {anomalies.map((anomaly, index) => {
          const config = anomalyConfig[anomaly.type] || {
            icon: AlertCircle,
            color: 'text-slate-400',
            bg: 'bg-slate-500/10',
            border: 'border-slate-500/30'
          }
          const Icon = config.icon

          return (
            <div
              key={`anomaly-${index}-${anomaly.type}`}
              className={`${config.bg} border ${config.border} rounded-lg p-3 relative animate-fade-in`}
            >
              <button
                onClick={() => onDismiss(index)}
                className="absolute top-2 right-2 p-1 text-slate-400 hover:text-white transition"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="flex items-start space-x-3 pr-6">
                <div className={`p-1.5 rounded ${config.bg}`}>
                  <Icon className={`w-4 h-4 ${config.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-sm font-medium text-white">{anomaly.type.replace(/_/g, ' ')}</span>
                    <span className={`text-xs ${severityColors[anomaly.severity] || 'text-slate-400'}`}>
                      {anomaly.severity}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300">{anomaly.message}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
