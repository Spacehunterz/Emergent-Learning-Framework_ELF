import { Suspense, lazy } from 'react'
import { useCosmicStore } from '../../stores'
import HotspotTreemap from '../hotspot-treemap'
import { ViewToggle } from './ViewToggle'
import type { HotspotVisualizationProps } from './types'

// Lazy load the cosmic view to avoid loading Three.js when not needed
const CosmicView = lazy(() => import('./CosmicView'))

// Loading fallback for the cosmic view
function CosmicLoadingFallback() {
  return (
    <div className="flex h-[500px] items-center justify-center rounded-lg border border-slate-700 bg-slate-900/50">
      <div className="text-center">
        <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-amber-500 mx-auto" />
        <p className="text-sm text-slate-400">Loading cosmic view...</p>
      </div>
    </div>
  )
}

export function HotspotVisualization({
  hotspots,
  onSelect,
  onOpenInEditor,
  selectedDomain,
  onDomainFilter,
}: HotspotVisualizationProps) {
  const viewMode = useCosmicStore((s) => s.viewMode)

  return (
    <div className="space-y-4">
      {/* Header with toggle */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Hotspots</h2>
        <ViewToggle />
      </div>

      {/* View container */}
      <div className="relative">
        {viewMode === 'grid' ? (
          <HotspotTreemap
            hotspots={hotspots}
            onSelect={onSelect}
            selectedDomain={selectedDomain}
            onDomainFilter={onDomainFilter}
          />
        ) : (
          <Suspense fallback={<CosmicLoadingFallback />}>
            <CosmicView
              hotspots={hotspots}
              onSelect={onSelect}
              onOpenInEditor={onOpenInEditor}
              selectedDomain={selectedDomain}
              onDomainFilter={onDomainFilter}
            />
          </Suspense>
        )}
      </div>
    </div>
  )
}

export default HotspotVisualization
