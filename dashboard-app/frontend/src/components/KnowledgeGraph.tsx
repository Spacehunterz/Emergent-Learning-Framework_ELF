import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import { ZoomIn, ZoomOut, Maximize2, Filter, X } from 'lucide-react'

interface GraphNode {
  id: number
  label: string
  fullText: string
  domain: string
  confidence: number
  is_golden: boolean
  times_validated: number
  times_violated: number
  explanation?: string
  created_at: string
  // D3 simulation properties
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

interface GraphEdge {
  id: number
  source: number | GraphNode
  target: number | GraphNode
  strength: number
  type: string
  label: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: {
    total_nodes: number
    total_edges: number
    golden_rules: number
    domains: number
  }
}

interface KnowledgeGraphProps {
  onNodeClick?: (node: GraphNode) => void
}

// Domain color palette
const DOMAIN_COLORS: Record<string, string> = {
  'general': '#8b5cf6',      // Purple
  'code': '#3b82f6',         // Blue
  'testing': '#10b981',      // Green
  'debugging': '#f59e0b',    // Amber
  'architecture': '#06b6d4', // Cyan
  'performance': '#ec4899',  // Pink
  'security': '#ef4444',     // Red
  'documentation': '#6366f1', // Indigo
  'workflow': '#14b8a6',     // Teal
  'learning': '#a855f7',     // Purple-500
}

const getColorForDomain = (domain: string): string => {
  if (DOMAIN_COLORS[domain]) return DOMAIN_COLORS[domain]
  // Generate consistent color based on domain name
  const hash = domain.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  const hue = hash % 360
  return `hsl(${hue}, 70%, 60%)`
}

export default function KnowledgeGraph({ onNodeClick }: KnowledgeGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
  const currentTransformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity)
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null)
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)
  const [filterDomain, setFilterDomain] = useState<string | null>(null)
  const [showGoldenOnly, setShowGoldenOnly] = useState(false)

  // Fetch graph data
  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        setLoading(true)
        const response = await fetch('/api/heuristic-graph')
        if (!response.ok) throw new Error('Failed to fetch graph data')
        const data = await response.json()
        setGraphData(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }
    fetchGraphData()
  }, [])

  // Initialize and update D3 visualization
  useEffect(() => {
    if (!graphData || !svgRef.current || !containerRef.current) return

    const svg = d3.select(svgRef.current)
    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight

    // Clear previous content
    svg.selectAll('*').remove()

    // Filter data
    let filteredNodes = graphData.nodes
    let filteredEdges = graphData.edges

    if (filterDomain) {
      filteredNodes = filteredNodes.filter(n => n.domain === filterDomain)
      const nodeIds = new Set(filteredNodes.map(n => n.id))
      filteredEdges = filteredEdges.filter(e => {
        const sourceId = typeof e.source === 'number' ? e.source : e.source.id
        const targetId = typeof e.target === 'number' ? e.target : e.target.id
        return nodeIds.has(sourceId) && nodeIds.has(targetId)
      })
    }

    if (showGoldenOnly) {
      filteredNodes = filteredNodes.filter(n => n.is_golden)
      const nodeIds = new Set(filteredNodes.map(n => n.id))
      filteredEdges = filteredEdges.filter(e => {
        const sourceId = typeof e.source === 'number' ? e.source : e.source.id
        const targetId = typeof e.target === 'number' ? e.target : e.target.id
        return nodeIds.has(sourceId) && nodeIds.has(targetId)
      })
    }

    // Create a group for zoom/pan
    const g = svg.append('g')
    gRef.current = g

    // Setup zoom behavior with scroll wheel support
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .filter((event) => {
        // Allow scroll wheel zoom and drag, but not double-click
        return event.type === 'wheel' || event.type === 'mousedown' || event.type === 'touchstart'
      })
      .on('zoom', (event) => {
        currentTransformRef.current = event.transform
        g.attr('transform', event.transform)
      })

    // Store zoom reference for button controls
    zoomRef.current = zoom

    // Apply zoom to SVG - restore previous transform if exists
    svg
      .call(zoom)
      .on('dblclick.zoom', null) // Disable double-click zoom

    // Apply current transform (preserves zoom state across re-renders)
    g.attr('transform', currentTransformRef.current.toString())

    // Create arrow markers for edges
    svg.append('defs').selectAll('marker')
      .data(['same_domain', 'keyword_similarity'])
      .join('marker')
      .attr('id', d => `arrow-${d}`)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', d => d === 'same_domain' ? '#64748b' : '#475569')
      .attr('opacity', 0.6)

    // Initialize node positions if not set
    filteredNodes.forEach((node, i) => {
      if (node.x === undefined || node.y === undefined) {
        const angle = (i / filteredNodes.length) * 2 * Math.PI
        const radius = Math.min(width, height) * 0.25
        node.x = width / 2 + radius * Math.cos(angle)
        node.y = height / 2 + radius * Math.sin(angle)
      }
    })

    // Create force simulation - optimized for smoothness and minimal jitter
    const simulation = d3.forceSimulation<GraphNode>(filteredNodes)
      .force('link', d3.forceLink<GraphNode, GraphEdge>(filteredEdges)
        .id(d => d.id)
        .distance(120)
        .strength(0.15))
      .force('charge', d3.forceManyBody<GraphNode>().strength(-80).distanceMax(200))
      .force('center', d3.forceCenter(width / 2, height / 2).strength(0.05))
      .force('collision', d3.forceCollide<GraphNode>().radius(40).strength(0.8))
      .force('x', d3.forceX(width / 2).strength(0.02))
      .force('y', d3.forceY(height / 2).strength(0.02))
      .alphaMin(0.005)
      .alphaDecay(0.02)
      .velocityDecay(0.7)

    simulationRef.current = simulation

    // Create edges
    const links = g.append('g')
      .selectAll('line')
      .data(filteredEdges)
      .join('line')
      .attr('stroke', d => d.type === 'same_domain' ? '#64748b' : '#475569')
      .attr('stroke-opacity', d => d.type === 'same_domain' ? 0.6 : 0.3)
      .attr('stroke-width', d => Math.max(1, d.strength * 3))
      .attr('marker-end', d => `url(#arrow-${d.type})`)

    // Create nodes
    const nodes = g.append('g')
      .selectAll<SVGGElement, GraphNode>('g')
      .data(filteredNodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag<SVGGElement, GraphNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        }))

    // Add node circles
    nodes.append('circle')
      .attr('r', d => {
        // Size by confidence, with golden rules larger
        const baseSize = 8 + (d.confidence * 12)
        return d.is_golden ? baseSize * 1.5 : baseSize
      })
      .attr('fill', d => getColorForDomain(d.domain))
      .attr('stroke', d => d.is_golden ? '#fbbf24' : '#1e293b')
      .attr('stroke-width', d => d.is_golden ? 3 : 1.5)
      .attr('opacity', 0.9)

    // Add golden rule glow effect
    nodes.filter(d => d.is_golden)
      .insert('circle', 'circle')
      .attr('r', d => 8 + (d.confidence * 12) * 1.5 + 5)
      .attr('fill', 'none')
      .attr('stroke', '#fbbf24')
      .attr('stroke-width', 2)
      .attr('opacity', 0.3)
      .attr('class', 'golden-glow')

    // Add node labels (only show for golden rules or on hover)
    nodes.append('text')
      .attr('dx', 12)
      .attr('dy', 4)
      .attr('font-size', '11px')
      .attr('font-weight', d => d.is_golden ? 'bold' : 'normal')
      .attr('fill', '#e2e8f0')
      .attr('opacity', d => d.is_golden ? 0.9 : 0)
      .text(d => d.label)
      .attr('pointer-events', 'none')

    // Node interactions
    nodes
      .on('mouseenter', (event, d) => {
        setHoveredNode(d)
        // Show label on hover
        d3.select(event.currentTarget)
          .select('text')
          .attr('opacity', 0.9)
        // Highlight connected nodes
        const connectedNodeIds = new Set<number>()
        filteredEdges.forEach(e => {
          const sourceId = typeof e.source === 'number' ? e.source : e.source.id
          const targetId = typeof e.target === 'number' ? e.target : e.target.id
          if (sourceId === d.id) connectedNodeIds.add(targetId)
          if (targetId === d.id) connectedNodeIds.add(sourceId)
        })

        nodes.attr('opacity', n => n.id === d.id || connectedNodeIds.has(n.id) ? 1 : 0.2)
        links.attr('opacity', e => {
          const sourceId = typeof e.source === 'number' ? e.source : e.source.id
          const targetId = typeof e.target === 'number' ? e.target : e.target.id
          return sourceId === d.id || targetId === d.id ? 0.8 : 0.1
        })
      })
      .on('mouseleave', (event, d) => {
        if (!selectedNode || selectedNode.id !== d.id) {
          setHoveredNode(null)
          // Hide label unless golden
          if (!d.is_golden) {
            d3.select(event.currentTarget)
              .select('text')
              .attr('opacity', 0)
          }
        }
        // Reset highlights
        nodes.attr('opacity', 1)
        links.attr('opacity', e => e.type === 'same_domain' ? 0.6 : 0.3)
      })
      .on('click', (_, d) => {
        setSelectedNode(d)
        onNodeClick?.(d)
      })

    // Update positions on simulation tick with boundary constraints
    const padding = 50
    simulation.on('tick', () => {
      // Keep nodes within bounds
      filteredNodes.forEach(d => {
        d.x = Math.max(padding, Math.min(width - padding, d.x || width / 2))
        d.y = Math.max(padding, Math.min(height - padding, d.y || height / 2))
      })

      links
        .attr('x1', d => (d.source as GraphNode).x || width / 2)
        .attr('y1', d => (d.source as GraphNode).y || height / 2)
        .attr('x2', d => (d.target as GraphNode).x || width / 2)
        .attr('y2', d => (d.target as GraphNode).y || height / 2)

      nodes.attr('transform', d => `translate(${d.x || width / 2},${d.y || height / 2})`)
    })

    // Cleanup
    return () => {
      simulation.stop()
    }
  }, [graphData, filterDomain, showGoldenOnly, onNodeClick])

  // Zoom controls
  const handleZoomIn = () => {
    if (svgRef.current && zoomRef.current && gRef.current) {
      const svgSelection = d3.select(svgRef.current)
      const newTransform = currentTransformRef.current.scale(1.5)
      currentTransformRef.current = newTransform
      gRef.current.transition().duration(300).attr('transform', newTransform.toString())
      svgSelection.call(zoomRef.current.transform, newTransform)
    }
  }

  const handleZoomOut = () => {
    if (svgRef.current && zoomRef.current && gRef.current) {
      const svgSelection = d3.select(svgRef.current)
      const newTransform = currentTransformRef.current.scale(0.67)
      currentTransformRef.current = newTransform
      gRef.current.transition().duration(300).attr('transform', newTransform.toString())
      svgSelection.call(zoomRef.current.transform, newTransform)
    }
  }

  const handleResetZoom = () => {
    if (svgRef.current && zoomRef.current && gRef.current) {
      const svgSelection = d3.select(svgRef.current)
      currentTransformRef.current = d3.zoomIdentity
      gRef.current.transition().duration(500).attr('transform', d3.zoomIdentity.toString())
      svgSelection.call(zoomRef.current.transform, d3.zoomIdentity)
    }
  }

  const domains = graphData ? Array.from(new Set(graphData.nodes.map(n => n.domain))) : []

  if (loading) {
    return (
      <div className="glass-panel h-[800px] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full mb-4 mx-auto"></div>
          <p className="text-slate-400">Loading knowledge graph...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-panel h-[800px] flex items-center justify-center">
        <div className="text-center text-red-400">
          <p className="text-lg mb-2">Failed to load graph</p>
          <p className="text-sm text-slate-400">{error}</p>
        </div>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="glass-panel h-[800px] flex items-center justify-center">
        <p className="text-slate-400">No heuristics to visualize</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          {/* Stats */}
          <div className="flex items-center space-x-6 text-sm">
            <div>
              <span className="text-slate-400">Nodes:</span>
              <span className="ml-2 font-semibold" style={{ color: 'var(--theme-accent)' }}>
                {graphData.stats.total_nodes}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Edges:</span>
              <span className="ml-2 font-semibold text-blue-400">
                {graphData.stats.total_edges}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Golden:</span>
              <span className="ml-2 font-semibold text-amber-400">
                {graphData.stats.golden_rules}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Domains:</span>
              <span className="ml-2 font-semibold text-emerald-400">
                {graphData.stats.domains}
              </span>
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowGoldenOnly(!showGoldenOnly)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                showGoldenOnly
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              Golden Only
            </button>

            <div className="relative">
              <select
                value={filterDomain || ''}
                onChange={(e) => setFilterDomain(e.target.value || null)}
                className="px-3 py-1.5 rounded-lg text-sm font-medium bg-white/5 text-slate-300 border border-white/10 hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-purple-500/50 appearance-none pr-8"
              >
                <option value="">All Domains</option>
                {domains.map(domain => (
                  <option key={domain} value={domain}>{domain}</option>
                ))}
              </select>
              <Filter className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
          </div>

          {/* Zoom controls */}
          <div className="flex items-center space-x-2">
            <button
              onClick={handleZoomIn}
              className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={handleResetZoom}
              className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all"
              title="Reset View"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Graph */}
      <div className="glass-panel relative" style={{ height: '700px' }}>
        <div ref={containerRef} className="w-full h-full">
          <svg ref={svgRef} className="w-full h-full" />
        </div>

        {/* Hovered/Selected Node Info */}
        {(hoveredNode || selectedNode) && (
          <div className="absolute top-4 right-4 glass-panel p-4 max-w-sm">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1 min-w-0 pr-2">
                <div className="flex items-center space-x-2 mb-1">
                  {(selectedNode || hoveredNode)?.is_golden && (
                    <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 font-medium">
                      GOLDEN
                    </span>
                  )}
                  <span className="text-xs px-2 py-0.5 rounded" style={{
                    backgroundColor: getColorForDomain((selectedNode || hoveredNode)!.domain) + '20',
                    color: getColorForDomain((selectedNode || hoveredNode)!.domain),
                    borderColor: getColorForDomain((selectedNode || hoveredNode)!.domain) + '30',
                    borderWidth: '1px'
                  }}>
                    {(selectedNode || hoveredNode)!.domain}
                  </span>
                </div>
                <h4 className="text-sm font-medium text-white mb-2">
                  {(selectedNode || hoveredNode)!.fullText}
                </h4>
                {(selectedNode || hoveredNode)!.explanation && (
                  <p className="text-xs text-slate-400 mb-2">
                    {(selectedNode || hoveredNode)!.explanation}
                  </p>
                )}
                <div className="flex items-center space-x-3 text-xs text-slate-400">
                  <div>
                    <span className="text-emerald-400">{(selectedNode || hoveredNode)!.times_validated}</span> validated
                  </div>
                  <div>
                    <span className="text-red-400">{(selectedNode || hoveredNode)!.times_violated}</span> violated
                  </div>
                  <div>
                    <span className="text-purple-400">{((selectedNode || hoveredNode)!.confidence * 100).toFixed(0)}%</span> confidence
                  </div>
                </div>
              </div>
              {selectedNode && (
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors flex-shrink-0"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-4 left-4 glass-panel p-3 text-xs space-y-2">
          <div className="font-semibold text-white mb-2">Legend</div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded-full bg-purple-500 border-2 border-amber-400"></div>
            <span className="text-slate-300">Golden Rule</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="text-slate-300">Regular Heuristic</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-8 h-0.5 bg-slate-500"></div>
            <span className="text-slate-300">Same Domain</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-8 h-0.5 bg-slate-600 opacity-50"></div>
            <span className="text-slate-300">Related Concepts</span>
          </div>
        </div>
      </div>

      {/* Instructions */}
      <div className="glass-panel p-4">
        <p className="text-sm text-slate-400 text-center">
          <strong className="text-white">Tip:</strong> Drag nodes to reposition • Scroll to zoom • Hover for details • Click to pin info
        </p>
      </div>
    </div>
  )
}
