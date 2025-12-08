import { useState, useRef, useEffect } from 'react'
import * as d3 from 'd3'
import { Workflow, WorkflowNode, WorkflowEdge } from '../types'
import { Plus, Play, Save, Trash2, Settings, Zap, GitBranch, Bell, Filter, X } from 'lucide-react'
import { useAPI } from '../hooks/useAPI'

const nodeTypes = {
  trigger: { icon: Zap, color: 'bg-sky-500', label: 'Trigger' },
  condition: { icon: Filter, color: 'bg-amber-500', label: 'Condition' },
  action: { icon: Play, color: 'bg-emerald-500', label: 'Action' },
  notification: { icon: Bell, color: 'bg-violet-500', label: 'Notify' },
}

const triggerOptions = [
  { id: 'on_failure', label: 'On Failure', description: 'When a task fails' },
  { id: 'on_low_confidence', label: 'On Low Confidence', description: 'When heuristic confidence drops' },
  { id: 'on_hotspot', label: 'On Hotspot Hit', description: 'When a hotspot is triggered' },
  { id: 'on_golden_candidate', label: 'On Golden Candidate', description: 'When a heuristic is ready for promotion' },
]

const actionOptions = [
  { id: 'promote_heuristic', label: 'Promote to Golden', description: 'Auto-promote heuristic' },
  { id: 'record_failure', label: 'Record Failure', description: 'Log failure details' },
  { id: 'notify_slack', label: 'Notify Slack', description: 'Send Slack message' },
  { id: 'open_issue', label: 'Open Issue', description: 'Create GitHub issue' },
  { id: 'run_command', label: 'Run Command', description: 'Execute shell command' },
]

interface WorkflowBuilderProps {
  workflows: Workflow[]
  onSave: (workflow: Workflow) => void
  onDelete: (id: string) => void
  onRun: (id: string) => void
}

export default function WorkflowBuilder({ workflows, onSave, onDelete, onRun }: WorkflowBuilderProps) {
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [nodes, setNodes] = useState<WorkflowNode[]>([])
  const [edges, setEdges] = useState<WorkflowEdge[]>([])
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null)
  const [isAddingNode, setIsAddingNode] = useState(false)
  const [addingNodeType, setAddingNodeType] = useState<string | null>(null)
  const [isDirty, setIsDirty] = useState(false)
  const canvasRef = useRef<SVGSVGElement>(null)

  // Initialize with selected workflow
  useEffect(() => {
    if (selectedWorkflow) {
      setNodes(selectedWorkflow.nodes)
      setEdges(selectedWorkflow.edges)
    } else {
      setNodes([])
      setEdges([])
    }
    setIsDirty(false)
  }, [selectedWorkflow])

  // Draw edges
  useEffect(() => {
    if (!canvasRef.current) return

    const svg = d3.select(canvasRef.current)
    svg.selectAll('.edge').remove()

    edges.forEach(edge => {
      const sourceNode = nodes.find(n => n.id === edge.source)
      const targetNode = nodes.find(n => n.id === edge.target)

      if (sourceNode && targetNode) {
        svg.insert('path', ':first-child')
          .attr('class', 'edge')
          .attr('d', `M ${sourceNode.position.x + 80} ${sourceNode.position.y + 30}
                      Q ${(sourceNode.position.x + targetNode.position.x) / 2 + 80} ${sourceNode.position.y + 30}
                        ${targetNode.position.x + 80} ${targetNode.position.y + 30}`)
          .attr('fill', 'none')
          .attr('stroke', '#475569')
          .attr('stroke-width', 2)
          .attr('marker-end', 'url(#arrowhead)')
      }
    })
  }, [nodes, edges])

  const handleAddNode = (type: string) => {
    const newNode: WorkflowNode = {
      id: `node_${Date.now()}`,
      type: type as 'trigger' | 'condition' | 'action' | 'notification',
      label: nodeTypes[type as keyof typeof nodeTypes]?.label || type,
      config: {},
      position: { x: 100 + nodes.length * 50, y: 100 + nodes.length * 30 },
    }
    setNodes([...nodes, newNode])
    setIsAddingNode(false)
    setAddingNodeType(null)
    setIsDirty(true)
  }

  const handleDeleteNode = (id: string) => {
    setNodes(nodes.filter(n => n.id !== id))
    setEdges(edges.filter(e => e.source !== id && e.target !== id))
    if (selectedNode?.id === id) setSelectedNode(null)
    setIsDirty(true)
  }

  const handleNodeDrag = (id: string, x: number, y: number) => {
    setNodes(nodes.map(n => n.id === id ? { ...n, position: { x, y } } : n))
    setIsDirty(true)
  }

  const handleSave = () => {
    if (!selectedWorkflow) return
    const updated: Workflow = {
      ...selectedWorkflow,
      nodes,
      edges,
    }
    onSave(updated)
    setIsDirty(false)
  }

  const handleNewWorkflow = () => {
    const newWorkflow: Workflow = {
      id: `workflow_${Date.now()}`,
      name: 'New Workflow',
      description: '',
      nodes: [],
      edges: [],
      is_active: false,
      created_at: new Date().toISOString(),
    }
    setSelectedWorkflow(newWorkflow)
    setNodes([])
    setEdges([])
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <GitBranch className="w-5 h-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-white">Workflow Builder</h3>
        </div>

        <div className="flex items-center space-x-2">
          {selectedWorkflow && (
            <>
              <button
                onClick={() => onRun(selectedWorkflow.id)}
                className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition"
              >
                <Play className="w-4 h-4" />
                <span>Run</span>
              </button>
              <button
                onClick={handleSave}
                disabled={!isDirty}
                className="flex items-center space-x-1 px-3 py-1.5 bg-sky-500/20 text-sky-400 rounded-lg text-sm hover:bg-sky-500/30 transition disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                <span>Save</span>
              </button>
            </>
          )}
          <button
            onClick={handleNewWorkflow}
            className="flex items-center space-x-1 px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg text-sm hover:bg-slate-600 transition"
          >
            <Plus className="w-4 h-4" />
            <span>New</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {/* Workflow list */}
        <div className="col-span-1 bg-slate-700/50 rounded-lg p-3">
          <div className="text-sm font-medium text-slate-400 mb-2">Workflows</div>
          <div className="space-y-1">
            {workflows.map(wf => (
              <button
                key={wf.id}
                onClick={() => setSelectedWorkflow(wf)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition
                  ${selectedWorkflow?.id === wf.id
                    ? 'bg-sky-500/20 text-sky-400'
                    : 'text-slate-300 hover:bg-slate-700'
                  }`}
              >
                <div className="font-medium">{wf.name}</div>
                <div className="text-xs text-slate-500">{wf.nodes.length} nodes</div>
              </button>
            ))}
            {workflows.length === 0 && (
              <div className="text-sm text-slate-500 py-4 text-center">
                No workflows yet
              </div>
            )}
          </div>
        </div>

        {/* Canvas */}
        <div className="col-span-2 bg-slate-900/50 rounded-lg relative h-[500px] overflow-hidden">
          {selectedWorkflow ? (
            <>
              {/* Node palette */}
              <div className="absolute top-2 left-2 flex space-x-2 z-10">
                {Object.entries(nodeTypes).map(([type, config]) => {
                  const Icon = config.icon
                  return (
                    <button
                      key={type}
                      onClick={() => handleAddNode(type)}
                      className={`flex items-center space-x-1 px-2 py-1 ${config.color} text-white rounded text-xs font-medium hover:opacity-80 transition`}
                    >
                      <Icon className="w-3 h-3" />
                      <span>{config.label}</span>
                    </button>
                  )
                })}
              </div>

              {/* SVG canvas */}
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
                      onClick={() => setSelectedNode(node)}
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

              {nodes.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center text-slate-500">
                  Click a node type above to add it to the canvas
                </div>
              )}
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500">
              Select a workflow or create a new one
            </div>
          )}
        </div>

        {/* Node config panel */}
        <div className="col-span-1 bg-slate-700/50 rounded-lg p-3">
          {selectedNode ? (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-medium text-white">{selectedNode.label}</div>
                <button
                  onClick={() => handleDeleteNode(selectedNode.id)}
                  className="p-1 text-red-400 hover:text-red-300 transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Label</label>
                  <input
                    type="text"
                    value={selectedNode.label}
                    onChange={(e) => {
                      setNodes(nodes.map(n =>
                        n.id === selectedNode.id ? { ...n, label: e.target.value } : n
                      ))
                      setSelectedNode({ ...selectedNode, label: e.target.value })
                      setIsDirty(true)
                    }}
                    className="w-full bg-slate-800 text-white text-sm rounded px-2 py-1.5 border border-slate-600"
                  />
                </div>

                {selectedNode.type === 'trigger' && (
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Trigger Type</label>
                    <select
                      value={selectedNode.config.trigger_type || ''}
                      onChange={(e) => {
                        const updated = { ...selectedNode, config: { ...selectedNode.config, trigger_type: e.target.value } }
                        setNodes(nodes.map(n => n.id === selectedNode.id ? updated : n))
                        setSelectedNode(updated)
                        setIsDirty(true)
                      }}
                      className="w-full bg-slate-800 text-white text-sm rounded px-2 py-1.5 border border-slate-600"
                    >
                      <option value="">Select trigger...</option>
                      {triggerOptions.map(opt => (
                        <option key={opt.id} value={opt.id}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                )}

                {selectedNode.type === 'action' && (
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Action Type</label>
                    <select
                      value={selectedNode.config.action_type || ''}
                      onChange={(e) => {
                        const updated = { ...selectedNode, config: { ...selectedNode.config, action_type: e.target.value } }
                        setNodes(nodes.map(n => n.id === selectedNode.id ? updated : n))
                        setSelectedNode(updated)
                        setIsDirty(true)
                      }}
                      className="w-full bg-slate-800 text-white text-sm rounded px-2 py-1.5 border border-slate-600"
                    >
                      <option value="">Select action...</option>
                      {actionOptions.map(opt => (
                        <option key={opt.id} value={opt.id}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                )}

                {selectedNode.type === 'condition' && (
                  <div>
                    <label className="text-xs text-slate-400 mb-1 block">Condition</label>
                    <input
                      type="text"
                      placeholder="e.g., confidence > 0.9"
                      value={selectedNode.config.expression || ''}
                      onChange={(e) => {
                        const updated = { ...selectedNode, config: { ...selectedNode.config, expression: e.target.value } }
                        setNodes(nodes.map(n => n.id === selectedNode.id ? updated : n))
                        setSelectedNode(updated)
                        setIsDirty(true)
                      }}
                      className="w-full bg-slate-800 text-white text-sm rounded px-2 py-1.5 border border-slate-600"
                    />
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm">
              Select a node to configure
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
