import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

export function CosmicLegend() {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/90 backdrop-blur-sm">
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs text-slate-300 hover:bg-slate-800/50"
      >
        <span className="font-medium">Legend</span>
        {isExpanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronUp className="h-3 w-3" />
        )}
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-slate-700 p-3 text-xs">
          {/* Celestial Types */}
          <div className="mb-3">
            <div className="mb-1.5 font-medium text-slate-400">Body Types</div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 shadow-lg shadow-orange-500/30" />
                <span className="text-slate-300">
                  Sun = Blocker (critical severity)
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-full bg-orange-500" />
                <span className="text-slate-300">
                  Planet = Warning severity
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-400" />
                <span className="text-slate-300">
                  Moon = Discovery severity
                </span>
              </div>
            </div>
          </div>

          {/* Visual Properties */}
          <div className="mb-3">
            <div className="mb-1.5 font-medium text-slate-400">
              Visual Encoding
            </div>
            <div className="space-y-1 text-slate-400">
              <div>• Size → Accumulated trails + strength</div>
              <div>• Glow → Recency of activity</div>
              <div>• Orbit speed → Volatility</div>
              <div>• Rings → Heuristic categories</div>
            </div>
          </div>

          {/* Solar Systems */}
          <div>
            <div className="mb-1.5 font-medium text-slate-400">Grouping</div>
            <div className="text-slate-400">
              Bodies in the same directory form a solar system
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CosmicLegend
