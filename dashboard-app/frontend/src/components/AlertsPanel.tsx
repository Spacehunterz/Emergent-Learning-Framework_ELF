import { useState } from 'react'
import { AlertTriangle, Star, X, TrendingDown, Repeat, Target, AlertCircle, Zap, Bell, ChevronUp, ChevronDown } from 'lucide-react'

// API anomaly format
interface ApiAnomaly {
  type: string
  severity: string
  message: string
  data: Record<string, any>
}

interface GoldenRule {
  id: string
  rule: string
  explanation?: string
  domain?: string
  times_validated?: number
  confidence?: number
}

interface AlertsPanelProps {
  anomalies: ApiAnomaly[]
  goldenRules: GoldenRule[]
  onDismissAnomaly: (index: number) => void
}

type TabType = 'anomalies' | 'rules'

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

export default function AlertsPanel({ anomalies, goldenRules, onDismissAnomaly }: AlertsPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<TabType>('anomalies')

  const anomalyCount = anomalies?.length || 0
  const rulesCount = goldenRules?.length || 0
  const totalCount = anomalyCount + rulesCount

  return (
    <div className="relative">
      {/* Toggle Button - always visible */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-4 py-3 rounded-lg transition-all ${
          isOpen
            ? 'bg-slate-700 text-white'
            : 'bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white'
        }`}
      >
        <Bell className="w-5 h-5 text-amber-400" />
        <span className="font-medium">Alerts</span>
        {totalCount > 0 && (
          <span className="text-xs bg-amber-500/30 text-amber-300 px-2 py-0.5 rounded-full">
            {totalCount}
          </span>
        )}
        {isOpen ? (
          <ChevronUp className="w-4 h-4 ml-1" />
        ) : (
          <ChevronDown className="w-4 h-4 ml-1" />
        )}
      </button>

      {/* Slide-out Panel */}
      <div
        className={`absolute top-full left-0 mt-2 w-80 bg-slate-800 rounded-lg shadow-xl border border-slate-700 transition-all duration-300 ease-out origin-top z-50 ${
          isOpen
            ? 'opacity-100 scale-y-100 translate-y-0'
            : 'opacity-0 scale-y-0 -translate-y-2 pointer-events-none'
        }`}
      >
        {/* Panel Header */}
        <div className="flex items-center justify-between p-3 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-amber-400" />
            <span className="font-medium text-white">Alerts</span>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 text-slate-400 hover:text-white rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab buttons */}
        <div className="flex border-b border-slate-700">
          <button
            type="button"
            onClick={() => setActiveTab('anomalies')}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium transition-colors cursor-pointer ${
              activeTab === 'anomalies'
                ? 'text-amber-400 bg-amber-500/10 border-b-2 border-amber-400'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Anomalies</span>
            {anomalyCount > 0 && (
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                activeTab === 'anomalies'
                  ? 'bg-amber-500/30 text-amber-300'
                  : 'bg-slate-600 text-slate-300'
              }`}>
                {anomalyCount}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('rules')}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium transition-colors cursor-pointer ${
              activeTab === 'rules'
                ? 'text-amber-400 bg-amber-500/10 border-b-2 border-amber-400'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <Star className="w-4 h-4" />
            <span>Golden Rules</span>
            {rulesCount > 0 && (
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                activeTab === 'rules'
                  ? 'bg-amber-500/30 text-amber-300'
                  : 'bg-slate-600 text-slate-300'
              }`}>
                {rulesCount}
              </span>
            )}
          </button>
        </div>

        {/* Content area */}
        <div className="p-3">
          {activeTab === 'anomalies' && (
            <AnomaliesContent anomalies={anomalies} onDismiss={onDismissAnomaly} />
          )}
          {activeTab === 'rules' && (
            <GoldenRulesContent rules={goldenRules} />
          )}
        </div>
      </div>
    </div>
  )
}

function AnomaliesContent({
  anomalies,
  onDismiss
}: {
  anomalies: ApiAnomaly[]
  onDismiss: (index: number) => void
}) {
  if (!anomalies || anomalies.length === 0) {
    return (
      <div className="text-center text-slate-400 py-6 text-sm">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-slate-500" />
        <p>No anomalies detected</p>
        <p className="text-xs text-slate-500 mt-1">System is running normally</p>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
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
            className={`${config.bg} border ${config.border} rounded-lg p-2.5 relative`}
          >
            <button
              onClick={() => onDismiss(index)}
              className="absolute top-2 right-2 p-1 text-slate-400 hover:text-white transition"
            >
              <X className="w-3 h-3" />
            </button>

            <div className="flex items-start space-x-2 pr-5">
              <div className={`p-1 rounded ${config.bg}`}>
                <Icon className={`w-3.5 h-3.5 ${config.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-0.5">
                  <span className="text-xs font-medium text-white">
                    {anomaly.type.replace(/_/g, ' ')}
                  </span>
                  <span className={`text-xs ${severityColors[anomaly.severity] || 'text-slate-400'}`}>
                    {anomaly.severity}
                  </span>
                </div>
                <p className="text-xs text-slate-300 line-clamp-2">{anomaly.message}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function GoldenRulesContent({ rules }: { rules: GoldenRule[] }) {
  if (!rules || rules.length === 0) {
    return (
      <div className="text-center text-slate-400 py-6 text-sm">
        <Star className="w-8 h-8 mx-auto mb-2 text-slate-500" />
        <p>No golden rules yet</p>
        <p className="text-xs text-slate-500 mt-1">Promote high-confidence heuristics</p>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
      {rules.map((rule, idx) => (
        <div
          key={rule.id || idx}
          className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-2.5"
        >
          <div className="flex items-start gap-2">
            <Star className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-white font-medium line-clamp-2">{rule.rule}</p>
              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                <span className="text-xs bg-amber-500/20 px-1.5 py-0.5 rounded text-amber-300">
                  {rule.domain || 'general'}
                </span>
                {rule.times_validated !== undefined && rule.times_validated > 0 && (
                  <span className="text-xs text-slate-500">
                    {rule.times_validated}x
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
