import { Html } from '@react-three/drei'
import { useCosmicStore } from '../../stores'
import type { CelestialBody } from './types'

interface SelectionOverlayProps {
  body: CelestialBody | null
  position: [number, number, number]
}

export function SelectionOverlay({ body, position }: SelectionOverlayProps) {
  const clearSelection = useCosmicStore((s) => s.clearSelection)

  if (!body) return null

  // Format recency as human readable
  const recencyLabel =
    body.recency > 0.8
      ? 'Very Recent'
      : body.recency > 0.5
        ? 'Recent'
        : body.recency > 0.2
          ? 'Moderate'
          : 'Older'

  // Format severity with color
  const severityConfig = {
    blocker: { label: 'Blocker', color: 'text-red-400', bg: 'bg-red-500/20' },
    warning: {
      label: 'Warning',
      color: 'text-orange-400',
      bg: 'bg-orange-500/20',
    },
    discovery: {
      label: 'Discovery',
      color: 'text-green-400',
      bg: 'bg-green-500/20',
    },
    low: { label: 'Low', color: 'text-slate-400', bg: 'bg-slate-500/20' },
  }

  const severity = severityConfig[body.severity] || severityConfig.low

  return (
    <Html
      position={position}
      center
      distanceFactor={10}
      style={{ pointerEvents: 'auto' }}
    >
      <div className="w-64 rounded-lg border border-slate-600 bg-slate-900/95 p-3 text-sm shadow-xl backdrop-blur-sm">
        {/* Header */}
        <div className="mb-2 flex items-start justify-between">
          <div className="flex-1 truncate pr-2">
            <div className="truncate font-medium text-white" title={body.name}>
              {body.name}
            </div>
            <div
              className="truncate text-xs text-slate-400"
              title={body.location}
            >
              {body.directory}
            </div>
          </div>
          <button
            onClick={clearSelection}
            className="rounded p-1 text-slate-400 hover:bg-slate-700 hover:text-white"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Severity badge */}
        <div className="mb-3">
          <span
            className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${severity.bg} ${severity.color}`}
          >
            {severity.label}
          </span>
          <span className="ml-2 text-xs capitalize text-slate-400">
            {body.type}
          </span>
        </div>

        {/* Metrics grid */}
        <div className="mb-3 grid grid-cols-2 gap-2 text-xs">
          <div className="rounded bg-slate-800 p-2">
            <div className="text-slate-400">Trails</div>
            <div className="font-medium text-white">{body.trailCount}</div>
          </div>
          <div className="rounded bg-slate-800 p-2">
            <div className="text-slate-400">Strength</div>
            <div className="font-medium text-white">
              {body.totalStrength.toFixed(1)}
            </div>
          </div>
          <div className="rounded bg-slate-800 p-2">
            <div className="text-slate-400">Recency</div>
            <div className="font-medium text-white">{recencyLabel}</div>
          </div>
          <div className="rounded bg-slate-800 p-2">
            <div className="text-slate-400">Agents</div>
            <div className="font-medium text-white">{body.agentCount}</div>
          </div>
        </div>

        {/* Heuristic categories */}
        {body.heuristicCategories.length > 0 && (
          <div className="mb-3">
            <div className="mb-1 text-xs text-slate-400">
              Heuristic Categories
            </div>
            <div className="flex flex-wrap gap-1">
              {body.heuristicCategories.slice(0, 4).map((cat) => (
                <span
                  key={cat}
                  className="rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-300"
                >
                  {cat}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Why this matters */}
        <div className="rounded bg-amber-500/10 p-2 text-xs text-amber-200">
          <span className="font-medium">Why it matters: </span>
          {body.severity === 'blocker' && (
            <span>
              Critical blocker with {body.trailCount} trails. Needs immediate
              attention.
            </span>
          )}
          {body.severity === 'warning' && (
            <span>
              Warning-level issue accumulating {body.trailCount} interactions.
            </span>
          )}
          {body.severity === 'discovery' && (
            <span>Discovery point - potential learning opportunity.</span>
          )}
          {body.severity === 'low' && (
            <span>Minor activity detected. Monitor for patterns.</span>
          )}
        </div>

        {/* Click hint */}
        <div className="mt-2 text-center text-xs text-slate-500">
          Click body to view details
        </div>
      </div>
    </Html>
  )
}

export default SelectionOverlay
