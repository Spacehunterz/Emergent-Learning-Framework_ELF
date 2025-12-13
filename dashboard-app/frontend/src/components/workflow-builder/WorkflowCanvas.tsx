import { WorkflowCanvasProps } from './types'
import { Zap } from 'lucide-react'

export default function WorkflowCanvas({
  nodes,
  selectedNode,
  onSelectNode,
  canvasRef,
  nodeTypes,
}: WorkflowCanvasProps) {
  return (
    <svg ref={canvasRef} className="w-full h-full">
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#475569" />
        </marker>
      </defs>

      {/* Nodes */}
      {nodes.map(node => {
        const config = nodeTypes[node.type]
        const Icon = config?.icon || Zap

        return (
          <g
            key={node.id}
            transform={`translate(${node.position.x}, ${node.position.y})`}
            className="cursor-pointer"
            onClick={() => onSelectNode(node)}
          >
            <rect
              width="160"
              height="60"
              rx="8"
              fill={selectedNode?.id === node.id ? '#1e3a5f' : '#1e293b'}
              stroke={selectedNode?.id === node.id ? '#0ea5e9' : '#334155'}
              strokeWidth="2"
            />
            <foreignObject x="8" y="8" width="144" height="44">
              <div className="flex items-center space-x-2">
                <div className={`p-1.5 rounded ${config?.color || 'bg-slate-500'}`}>
                  <Icon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <div className="text-sm font-medium text-white">{node.label}</div>
                  <div className="text-xs text-slate-400">{node.type}</div>
                </div>
              </div>
            </foreignObject>
          </g>
        )
      })}
    </svg>
  )
}
