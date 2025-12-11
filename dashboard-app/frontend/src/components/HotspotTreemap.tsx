import { useEffect, useRef, useState, useMemo } from 'react'
import * as d3 from 'd3'
import { Target, Filter, X } from 'lucide-react'

// API returns this format from /api/hotspots
interface ApiHotspot {
  location: string
  trail_count: number
  total_strength: number
  scents: string[]
  agents: string[]
  agent_count: number
  last_activity: string
  first_activity: string
  related_heuristics: any[]
}

interface HotspotTreemapProps {
  hotspots: ApiHotspot[]
  onSelect: (path: string, line?: number) => void
  selectedDomain: string | null
  onDomainFilter: (domain: string | null) => void
}

interface TreemapData {
  name: string
  value?: number
  strength?: number
  severity?: string
  scents?: string[]
  path?: string
  children?: TreemapData[]
}

export default function HotspotTreemap({ hotspots, onSelect, selectedDomain, onDomainFilter }: HotspotTreemapProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; data: ApiHotspot | null }>({ x: 0, y: 0, data: null })
  const [selectedHotspot, setSelectedHotspot] = useState<ApiHotspot | null>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })

  // Safely get unique scents as "domains"
  const domains = useMemo(() => {
    const allScents = hotspots?.flatMap(h => h.scents || []) || []
    return Array.from(new Set(allScents)).filter(Boolean)
  }, [hotspots])

  // Filter hotspots by scent (domain)
  const filteredHotspots = useMemo(() => {
    if (!hotspots || !Array.isArray(hotspots)) return []
    if (!selectedDomain) return hotspots
    return hotspots.filter(h => h.scents?.includes(selectedDomain))
  }, [hotspots, selectedDomain])

  // Determine severity from scents
  const getSeverity = (scents: string[]): string => {
    if (!scents) return 'low'
    if (scents.includes('blocker')) return 'critical'
    if (scents.includes('warning')) return 'high'
    if (scents.includes('discovery')) return 'medium'
    return 'low'
  }

  // Convert hotspots to hierarchical data
  const buildHierarchy = (data: ApiHotspot[]): TreemapData => {
    const root: TreemapData = { name: 'root', children: [] }

    if (!data || !Array.isArray(data)) return root

    data.forEach(hotspot => {
      if (!hotspot.location) return

      const parts = hotspot.location.split(/[\/\\]/).filter(Boolean)
      let currentLevel = root.children!

      parts.forEach((part, index) => {
        const isFile = index === parts.length - 1

        let existing = currentLevel.find(c => c.name === part)

        if (!existing) {
          existing = {
            name: part,
            children: isFile ? undefined : [],
            value: isFile ? hotspot.trail_count : undefined,
            strength: isFile ? hotspot.total_strength : undefined,
            severity: isFile ? getSeverity(hotspot.scents) : undefined,
            scents: isFile ? hotspot.scents : undefined,
            path: isFile ? hotspot.location : undefined,
          }
          currentLevel.push(existing)
        }

        if (!isFile && existing.children) {
          currentLevel = existing.children
        }
      })
    })

    return root
  }

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

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    if (!filteredHotspots || filteredHotspots.length === 0) return

    const { width, height } = dimensions
    const hierarchy = buildHierarchy(filteredHotspots)

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

    const colorScale = (severity: string | undefined) => {
      switch (severity) {
        case 'critical': return '#ef4444'
        case 'high': return '#f97316'
        case 'medium': return '#eab308'
        case 'low': return '#22c55e'
        default: return '#64748b'
      }
    }

    const leaves = root.leaves() as any[]

    // Create cells
    const cells = svg.selectAll('g')
      .data(leaves)
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'url("/ufo-cursor.svg") 16 16, pointer')
      .on('click', (_, d) => {
        const hotspot = filteredHotspots.find(h => h.location === d.data.path)
        if (hotspot) {
          setSelectedHotspot(selectedHotspot?.location === hotspot.location ? null : hotspot)
        }
      })
      .on('mouseenter', (event, d) => {
        const hotspot = filteredHotspots.find(h => h.location === d.data.path)
        if (hotspot) {
          const rect = svgRef.current!.getBoundingClientRect()
          setTooltip({
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
            data: hotspot
          })
        }
      })
      .on('mouseleave', () => {
        setTooltip({ x: 0, y: 0, data: null })
      })

    // Background rect
    cells.append('rect')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', d => colorScale(d.data.severity))
      .attr('opacity', d => 0.3 + Math.min((d.data.strength || 0) * 0.1, 0.5))
      .attr('rx', 4)
      .attr('class', 'treemap-cell')

    // Border
    cells.append('rect')
      .attr('width', d => Math.max(0, d.x1 - d.x0))
      .attr('height', d => Math.max(0, d.y1 - d.y0))
      .attr('fill', 'none')
      .attr('stroke', d => colorScale(d.data.severity))
      .attr('stroke-width', 1.5)
      .attr('rx', 4)

    // Text labels (only for cells large enough)
    cells.filter(d => (d.x1 - d.x0) > 60 && (d.y1 - d.y0) > 30)
      .append('text')
      .attr('x', 6)
      .attr('y', 16)
      .attr('fill', 'white')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
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
      .text(d => `${d.value} hits`)

  }, [filteredHotspots, dimensions, onSelect])

  return (
    <div ref={containerRef} className="bg-slate-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Target className="w-5 h-5 text-orange-400" />
          <h3 className="text-lg font-semibold text-white">Hot Spots</h3>
          <span className="text-sm text-slate-400">({filteredHotspots?.length || 0} locations)</span>
        </div>

        {/* Domain filter */}
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={selectedDomain || ''}
            onChange={(e) => onDomainFilter(e.target.value || null)}
            className="bg-slate-700 text-sm text-white rounded-md px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value="">All Scents</option>
            {domains.map((domain, idx) => (
              <option key={`${domain}-${idx}`} value={domain}>{domain}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center space-x-4 mb-4 text-xs">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 rounded bg-emerald-500" />
          <span className="text-slate-400">Low</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 rounded bg-yellow-500" />
          <span className="text-slate-400">Medium</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 rounded bg-orange-500" />
          <span className="text-slate-400">High</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 rounded bg-red-500" />
          <span className="text-slate-400">Critical</span>
        </div>
      </div>

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

        {/* Tooltip */}
        {tooltip.data && (
          <div
            className="absolute z-10 bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl pointer-events-none"
            style={{
              left: tooltip.x + 10,
              top: tooltip.y + 10,
              maxWidth: 300,
            }}
          >
            <div className="font-medium text-white mb-1">{tooltip.data.location}</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-400">Trails:</span>
                <span className="text-white ml-1">{tooltip.data.trail_count}</span>
              </div>
              <div>
                <span className="text-slate-400">Strength:</span>
                <span className="text-white ml-1">{tooltip.data.total_strength?.toFixed(1)}</span>
              </div>
              <div>
                <span className="text-slate-400">Agents:</span>
                <span className="text-white ml-1">{tooltip.data.agent_count}</span>
              </div>
              <div>
                <span className="text-slate-400">Scents:</span>
                <span className="text-white ml-1">{tooltip.data.scents?.join(', ') || 'none'}</span>
              </div>
            </div>
            <div className="mt-2 text-xs text-sky-400">
              Click for details
            </div>
          </div>
        )}

        {/* Selected hotspot detail panel */}
        {selectedHotspot && (
          <div className="mt-4 bg-slate-900 border border-slate-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-white font-medium">{selectedHotspot.location}</h4>
              <button 
                onClick={() => setSelectedHotspot(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-400">Trail Count:</span>
                <span className="text-white ml-2">{selectedHotspot.trail_count}</span>
              </div>
              <div>
                <span className="text-slate-400">Total Strength:</span>
                <span className="text-white ml-2">{selectedHotspot.total_strength?.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-slate-400">Agents:</span>
                <span className="text-white ml-2">{selectedHotspot.agents?.join(', ') || 'none'}</span>
              </div>
              <div>
                <span className="text-slate-400">Scents:</span>
                <span className="text-white ml-2">{selectedHotspot.scents?.join(', ') || 'none'}</span>
              </div>
              <div>
                <span className="text-slate-400">First Activity:</span>
                <span className="text-white ml-2">{new Date(selectedHotspot.first_activity).toLocaleString()}</span>
              </div>
              <div>
                <span className="text-slate-400">Last Activity:</span>
                <span className="text-white ml-2">{new Date(selectedHotspot.last_activity).toLocaleString()}</span>
              </div>
            </div>
            {selectedHotspot.related_heuristics?.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-700">
                <span className="text-slate-400 text-sm">Related Heuristics:</span>
                <div className="mt-1 space-y-1">
                  {selectedHotspot.related_heuristics.map((h, i) => (
                    <div key={i} className="text-xs text-slate-300 bg-slate-800 rounded px-2 py-1">
                      {typeof h === 'object' ? (h.rule || JSON.stringify(h)) : String(h)}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
