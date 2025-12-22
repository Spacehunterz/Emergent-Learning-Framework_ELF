import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { ApiHotspot, TreemapData, TooltipState } from './types'

interface UseD3TreemapProps {
  svgRef: React.RefObject<SVGSVGElement>
  hierarchy: TreemapData
  filteredHotspots: ApiHotspot[]
  dimensions: { width: number; height: number }
  onCellClick: (hotspot: ApiHotspot) => void
  onTooltipChange: (state: TooltipState) => void
}

const colorScale = (severity: string | undefined) => {
  switch (severity) {
    case 'critical': return '#ef4444'
    case 'high': return '#f97316'
    case 'medium': return '#eab308'
    case 'low': return '#22c55e'
    default: return '#64748b'
  }
}

export function useD3Treemap({
  svgRef,
  hierarchy,
  filteredHotspots,
  dimensions,
  onCellClick,
  onTooltipChange,
}: UseD3TreemapProps) {
  const isDrawingRef = useRef(false)
  const tooltipRef = useRef<TooltipState>({ x: 0, y: 0, data: null })

  // Use refs for callbacks to avoid stale closures and prevent effect re-runs
  const onCellClickRef = useRef(onCellClick)
  const onTooltipChangeRef = useRef(onTooltipChange)
  onCellClickRef.current = onCellClick
  onTooltipChangeRef.current = onTooltipChange

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    if (!filteredHotspots || filteredHotspots.length === 0) return

    const { width, height } = dimensions

    // Check if we have any data
    if (!hierarchy.children || hierarchy.children.length === 0) return

    const root = d3.hierarchy(hierarchy)
      .sum(d => d.value || 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0))

    const treemap = d3.treemap<TreemapData>()
      .size([width, height])
      .padding(2)
      .round(true)

    treemap(root)

    const leaves = root.leaves() as any[]

    // Create cells
    const cells = svg.selectAll('g')
      .data(leaves)
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'url("/ufo-cursor.svg") 16 16, pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        console.log('Treemap cell clicked:', d.data.path, d.data)
        const hotspot = filteredHotspots.find(h => h.location === d.data.path)
        console.log('Found hotspot:', hotspot)
        if (hotspot) {
          console.log('Calling onCellClick with:', hotspot.location)
          onCellClickRef.current(hotspot)
        }
      })
      .on('mouseenter', (event, d) => {
        if (isDrawingRef.current) return
        const hotspot = filteredHotspots.find(h => h.location === d.data.path)
        if (hotspot) {
          const rect = svgRef.current!.getBoundingClientRect()
          tooltipRef.current = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
            data: hotspot
          }
          onTooltipChangeRef.current(tooltipRef.current)
        }
      })
      .on('mousemove', (event) => {
        if (isDrawingRef.current || !tooltipRef.current.data) return
        const rect = svgRef.current!.getBoundingClientRect()
        tooltipRef.current.x = event.clientX - rect.left
        tooltipRef.current.y = event.clientY - rect.top
        onTooltipChangeRef.current({ ...tooltipRef.current })
      })
      .on('mouseleave', () => {
        tooltipRef.current = { x: 0, y: 0, data: null }
        onTooltipChangeRef.current({ x: 0, y: 0, data: null })
      })

    // Event capture layer - catches all pointer events and bubbles to parent <g>
    // This rect MUST have pointer-events enabled (no 'none') to catch clicks/hovers
    // All other children have pointer-events: none so they don't interfere
    cells.append('rect')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', 'transparent')
      .attr('class', 'event-capture')
      .style('cursor', 'url("/ufo-cursor.svg") 16 16, pointer')

    // Background rect (visual only)
    cells.append('rect')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', d => colorScale(d.data.severity))
      .attr('opacity', d => 0.3 + Math.min((d.data.strength || 0) * 0.1, 0.5))
      .attr('rx', 4)
      .attr('class', 'treemap-cell')
      .style('pointer-events', 'none')

    // Border
    cells.append('rect')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', 'none')
      .attr('stroke', d => colorScale(d.data.severity))
      .attr('stroke-width', 1.5)
      .attr('rx', 4)
      .style('pointer-events', 'none')

    // Text labels (only for cells large enough)
    cells.filter(d => (d.x1 - d.x0) > 60 && (d.y1 - d.y0) > 30)
      .append('text')
      .attr('x', 6)
      .attr('y', 16)
      .attr('fill', 'white')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .style('pointer-events', 'none')
      .text(d => {
        const name = d.data.name
        const maxLen = Math.floor((d.x1 - d.x0 - 12) / 6)
        return name.length > maxLen ? name.slice(0, maxLen - 2) + '..' : name
      })

    // Hit count badge
    cells.filter(d => (d.x1 - d.x0) > 40 && (d.y1 - d.y0) > 50)
      .append('text')
      .attr('x', 6)
      .attr('y', 32)
      .attr('fill', 'rgba(255,255,255,0.7)')
      .attr('font-size', '10px')
      .style('pointer-events', 'none')
      .text(d => `${d.value} hits`)

  }, [svgRef, filteredHotspots, dimensions, hierarchy])
}
