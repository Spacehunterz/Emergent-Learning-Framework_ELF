import { useRef, useState } from 'react'
import { KnowledgeGraphProps, GraphNode } from './types'
import { useGraphData } from './useGraphData'
import { useD3Graph } from './useD3Graph'
import GraphControls from './GraphControls'
import GraphLegend from './GraphLegend'
import GraphInstructions from './GraphInstructions'
import NodeInfoPanel from './NodeInfoPanel'

export default function KnowledgeGraph({ onNodeClick }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)
  const [filterDomain, setFilterDomain] = useState<string | null>(null)
  const [showGoldenOnly, setShowGoldenOnly] = useState(false)

  // Fetch graph data
  const { graphData, loading, error } = useGraphData()

  // Setup D3 visualization
  const { svgRef, handleZoomIn, handleZoomOut, handleResetZoom } = useD3Graph({
    graphData,
    containerRef,
    filterDomain,
    showGoldenOnly,
    onNodeClick,
    onHoverChange: setHoveredNode,
    onSelectedChange: setSelectedNode,
  })

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
      <GraphControls
        graphData={graphData}
        showGoldenOnly={showGoldenOnly}
        filterDomain={filterDomain}
        onShowGoldenToggle={() => setShowGoldenOnly(!showGoldenOnly)}
        onDomainFilter={setFilterDomain}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onResetZoom={handleResetZoom}
      />

      {/* Graph */}
      <div className="glass-panel relative" style={{ height: '700px' }}>
        <div ref={containerRef} className="w-full h-full">
          <svg ref={svgRef} className="w-full h-full" />
        </div>

        {/* Hovered/Selected Node Info */}
        {(hoveredNode || selectedNode) && (
          <NodeInfoPanel
            node={(selectedNode || hoveredNode)!}
            isSelected={!!selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        )}

        {/* Legend */}
        <GraphLegend />
      </div>

      {/* Instructions */}
      <GraphInstructions />
    </div>
  )
}
