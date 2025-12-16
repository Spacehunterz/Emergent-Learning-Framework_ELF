import { useCallback, useEffect, useMemo } from 'react'
import { useCosmicStore } from '../../stores'
import { useCosmicData } from './useCosmicData'
import { CosmicCanvas } from './CosmicCanvas'
import { CosmicLegend } from './CosmicLegend'
import { CosmicFilters } from './CosmicFilters'
import { CosmicDetailPanel } from './CosmicDetailPanel'
import { SystemNavigator } from './SystemNavigator'
import { ViewToggle } from './ViewToggle'
import type { CosmicViewProps } from './types'

export function CosmicView({
  hotspots,
  onSelect,
  onOpenInEditor,
  selectedDomain,
  onDomainFilter,
}: CosmicViewProps) {
  const selectedBody = useCosmicStore((s) => s.selectedBody)
  const clearSelection = useCosmicStore((s) => s.clearSelection)

  // Transform hotspot data to cosmic hierarchy
  const cosmicData = useCosmicData(hotspots, selectedDomain)

  // Find selected body data for detail panel
  const selectedBodyData = useMemo(() => {
    if (!selectedBody) return null
    for (const system of cosmicData.systems) {
      const body = system.allBodies.find((b) => b.id === selectedBody)
      if (body) return body
    }
    return null
  }, [selectedBody, cosmicData])

  // Handle body selection - trigger external onSelect
  const handleSelectBody = useCallback(
    (location: string) => {
      onSelect(location)
    },
    [onSelect]
  )

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedBody) {
        clearSelection()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedBody, clearSelection])

  // No data state
  if (cosmicData.totalBodies === 0) {
    return (
      <div className="relative h-[600px] flex items-center justify-center bg-slate-900/30 rounded-lg border border-slate-700">
        <div className="text-center">
          <div className="mb-2 text-4xl">🌌</div>
          <p className="text-slate-400">No hotspots to visualize</p>
          <p className="mt-1 text-sm text-slate-500">
            Hotspots will appear here as celestial bodies
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative h-[600px] flex flex-col rounded-lg overflow-hidden border border-slate-700">
      {/* 3D canvas container */}
      <div className="relative flex-1">
        <CosmicCanvas cosmicData={cosmicData} onSelectBody={handleSelectBody} />

        {/* System navigator - bottom left */}
        <div className="absolute bottom-4 left-4">
          <SystemNavigator systems={cosmicData.systems} totalBodies={cosmicData.totalBodies} />
        </div>

        {/* Legend overlay - above navigator */}
        <div className="absolute bottom-20 left-4">
          <CosmicLegend />
        </div>

        {/* View toggle - top left */}
        <div className="absolute left-4 top-4 z-20">
          <ViewToggle />
        </div>

        {/* Filters overlay - top right */}
        <div className="absolute right-4 top-4">
          <CosmicFilters
            selectedDomain={selectedDomain}
            onDomainFilter={onDomainFilter}
            domains={cosmicData.directories}
          />
        </div>

        {/* Help text - bottom center */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-slate-500 bg-slate-900/50 px-3 py-1 rounded-full">
          Left-drag orbit • Right-drag pan • Scroll zoom • Click body for details • Esc close
        </div>
      </div>

      {/* Detail panel - slides up from bottom */}
      {selectedBodyData && (
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-slate-900 to-transparent">
          <div className="max-w-4xl mx-auto">
            <CosmicDetailPanel
              body={selectedBodyData}
              onClose={clearSelection}
              onOpenInEditor={onOpenInEditor}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default CosmicView
