import { useEffect, useRef, useState, useMemo } from 'react'
import { Target } from 'lucide-react'
import { useTreemapData } from './useTreemapData'
import { useD3Treemap } from './useD3Treemap'
import TreemapTooltip from './TreemapTooltip'
import TreemapFilters from './TreemapFilters'
import TreemapLegend from './TreemapLegend'
import HotspotDetailPanel from './HotspotDetailPanel'
import type { HotspotTreemapProps, TooltipState, ApiHotspot } from './types'

export default function HotspotTreemap({ hotspots, onSelect, selectedDomain, onDomainFilter }: HotspotTreemapProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [tooltipState, setTooltipState] = useState<TooltipState>({ x: 0, y: 0, data: null })
  const [expandedHotspot, setExpandedHotspot] = useState<string | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })

  // Get data from hook
  const { domains, filteredHotspots, hierarchy } = useTreemapData(hotspots, selectedDomain)

  // Handle cell click - toggle expanded hotspot and call onSelect
  const handleCellClick = (hotspot: ApiHotspot) => {
    console.log('handleCellClick called with:', hotspot.location)
    setExpandedHotspot(prev => prev === hotspot.location ? null : hotspot.location)
    console.log('Calling onSelect with:', hotspot.location)
    onSelect(hotspot.location)
  }

  // Render D3 treemap
  useD3Treemap({
    svgRef,
    hierarchy,
    filteredHotspots,
    dimensions,
    onCellClick: handleCellClick,
    onTooltipChange: setTooltipState,
  })

  // Handle window resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width } = containerRef.current.getBoundingClientRect()
        setDimensions({ width: Math.max(width - 32, 200), height: 500 })
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  // Get expanded hotspot data
  const expandedHotspotData = useMemo(() => {
    if (!expandedHotspot) return null
    return filteredHotspots.find(h => h.location === expandedHotspot) || null
  }, [filteredHotspots, expandedHotspot])

  return (
    <div ref={containerRef} className="bg-slate-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Target className="w-5 h-5 text-orange-400" />
          <h3 className="text-lg font-semibold text-white">Hot Spots</h3>
          <span className="text-sm text-slate-400">({filteredHotspots?.length || 0} locations)</span>
        </div>

        <TreemapFilters
          selectedDomain={selectedDomain}
          domains={domains}
          onDomainFilter={onDomainFilter}
        />
      </div>

      <TreemapLegend />

      {/* Treemap */}
      <div className="relative">
        {filteredHotspots && filteredHotspots.length > 0 ? (
          <svg
            ref={svgRef}
            width={dimensions.width}
            height={dimensions.height}
            className="rounded-lg overflow-hidden"
          />
        ) : (
          <div className="h-[500px] flex items-center justify-center text-slate-400">
            No hotspots found
          </div>
        )}

        <TreemapTooltip tooltipState={tooltipState} dimensions={dimensions} />

        <HotspotDetailPanel
          hotspot={expandedHotspotData}
          onClose={() => setExpandedHotspot(null)}
        />
      </div>
    </div>
  )
}
