import HotspotTreemap from '../hotspot-treemap'
import type { HotspotVisualizationProps } from './types'

export function HotspotVisualization({
  hotspots,
  onSelect,
  selectedDomain,
  onDomainFilter,
}: HotspotVisualizationProps) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <h2 className="text-lg font-semibold text-white">Hotspots</h2>

      {/* Treemap view */}
      <HotspotTreemap
        hotspots={hotspots}
        onSelect={onSelect}
        selectedDomain={selectedDomain}
        onDomainFilter={onDomainFilter}
      />
    </div>
  )
}

export default HotspotVisualization
