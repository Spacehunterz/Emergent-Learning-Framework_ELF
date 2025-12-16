import { X, ExternalLink, AlertTriangle, AlertCircle, Lightbulb, Clock, Users, Activity } from 'lucide-react'
import type { CelestialBody } from './types'

interface CosmicDetailPanelProps {
  body: CelestialBody
  onClose: () => void
  onOpenInEditor?: (path: string, line?: number) => void
}

export function CosmicDetailPanel({ body, onClose, onOpenInEditor }: CosmicDetailPanelProps) {
  // Format recency as human readable
  const getRecencyLabel = (recency: number) => {
    if (recency > 0.8) return 'Very Recent'
    if (recency > 0.5) return 'Recent'
    if (recency > 0.2) return 'Moderate'
    return 'Older'
  }

  // Severity config
  const severityConfig = {
    blocker: {
      label: 'Blocker',
      color: 'text-red-400',
      bg: 'bg-red-500/20',
      icon: AlertTriangle,
      description: 'Critical issue requiring immediate attention'
    },
    warning: {
      label: 'Warning',
      color: 'text-orange-400',
      bg: 'bg-orange-500/20',
      icon: AlertCircle,
      description: 'Issue accumulating attention over time'
    },
    discovery: {
      label: 'Discovery',
      color: 'text-green-400',
      bg: 'bg-green-500/20',
      icon: Lightbulb,
      description: 'Potential learning opportunity identified'
    },
    low: {
      label: 'Low',
      color: 'text-slate-400',
      bg: 'bg-slate-500/20',
      icon: Activity,
      description: 'Minor activity detected'
    },
  }

  const severity = severityConfig[body.severity] || severityConfig.low
  const SeverityIcon = severity.icon

  // Celestial type label
  const typeLabels = {
    sun: '☀️ Sun',
    planet: '🪐 Planet',
    moon: '🌙 Moon',
  }

  return (
    <div className="bg-slate-800/80 backdrop-blur-sm rounded-lg p-4 animate-in slide-in-from-bottom-2 duration-200">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-lg font-semibold text-white truncate">{body.name}</h3>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${severity.bg} ${severity.color}`}>
              <SeverityIcon className="w-3 h-3" />
              {severity.label}
            </span>
            <span className="text-xs text-slate-400">{typeLabels[body.type]}</span>
          </div>
          <p className="text-sm text-slate-400 truncate" title={body.location}>{body.location}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Activity className="w-3 h-3" />
            Trails
          </div>
          <div className="text-xl font-semibold text-white">{body.trailCount}</div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Activity className="w-3 h-3" />
            Strength
          </div>
          <div className="text-xl font-semibold text-white">{body.totalStrength.toFixed(1)}</div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Clock className="w-3 h-3" />
            Recency
          </div>
          <div className="text-xl font-semibold text-white">{getRecencyLabel(body.recency)}</div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Users className="w-3 h-3" />
            Agents
          </div>
          <div className="text-xl font-semibold text-white">{body.agentCount}</div>
        </div>
      </div>

      {/* Why this matters */}
      <div className="bg-amber-500/10 rounded-lg p-3 mb-4">
        <div className="text-xs font-medium text-amber-300 mb-1">Why this matters</div>
        <p className="text-sm text-amber-200">{severity.description}</p>
      </div>

      {/* Heuristic categories */}
      {body.heuristicCategories.length > 0 && (
        <div className="mb-4">
          <div className="text-xs text-slate-400 mb-2">Related Heuristic Categories</div>
          <div className="flex flex-wrap gap-2">
            {body.heuristicCategories.map((cat) => (
              <span
                key={cat}
                className="px-2 py-1 bg-slate-700 rounded text-xs text-slate-300"
              >
                {cat}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Footer with directory info */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-700">
        <div className="text-xs text-slate-500">
          Directory: <span className="text-slate-400">{body.directory}</span>
        </div>
        <button
          onClick={() => onOpenInEditor?.(body.location)}
          className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          Open in Editor
        </button>
      </div>
    </div>
  )
}

export default CosmicDetailPanel
