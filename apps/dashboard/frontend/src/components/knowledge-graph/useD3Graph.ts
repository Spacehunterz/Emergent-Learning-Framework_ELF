import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { GraphNode, GraphEdge, GraphData } from './types'
import { getColorForDomain } from './types'

interface UseD3GraphProps {
  graphData: GraphData | null
  containerRef: React.RefObject<HTMLDivElement>
  filterDomain: string | null
  showGoldenOnly: boolean
  onNodeClick?: (node: GraphNode) => void
  onHoverChange: (node: GraphNode | null) => void
  onSelectedChange: (node: GraphNode | null) => void
}

interface UseD3GraphReturn {
  svgRef: React.RefObject<SVGSVGElement>
  handleZoomIn: () => void
  handleZoomOut: () => void
  handleResetZoom: () => void
}

export function useD3Graph({
  graphData,
  containerRef,
  filterDomain,
  showGoldenOnly,
  onNodeClick,
  onHoverChange,
  onSelectedChange,
}: UseD3GraphProps): UseD3GraphReturn {
  const svgRef = useRef<SVGSVGElement>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
  const currentTransformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity)
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null)
  const selectedNodeRef = useRef<GraphNode | null>(null)

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
        onHoverChange(d)
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
        if (!selectedNodeRef.current || selectedNodeRef.current.id !== d.id) {
          onHoverChange(null)
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
        selectedNodeRef.current = d
        onSelectedChange(d)
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

      nodes.attr('transform', d => `translate(${d.x || width / 2},${d.y || width / 2})`)
    })

    // Cleanup
    return () => {
      simulation.stop()
    }
  }, [graphData, filterDomain, showGoldenOnly, onNodeClick, onHoverChange, onSelectedChange])

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

  return {
    svgRef,
    handleZoomIn,
    handleZoomOut,
    handleResetZoom,
  }
}
