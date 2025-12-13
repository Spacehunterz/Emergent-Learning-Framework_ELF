import { useState, useRef, useEffect } from 'react'
import * as d3 from 'd3'
import { Workflow, WorkflowNode, WorkflowEdge } from '../types'
import { Plus, Play, Save, GitBranch, Zap, Filter, Bell } from 'lucide-react'
import {
  NodePalette,
  WorkflowCanvas,
  NodeConfigPanel,
  WorkflowList,
  WorkflowBuilderProps,
  NodeTypeConfig,
} from './workflow-builder'

const nodeTypes: Record<string, NodeTypeConfig> = {
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

export default function WorkflowBuilder({ workflows, onSave, onRun }: WorkflowBuilderProps) {
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [nodes, setNodes] = useState<WorkflowNode[]>([])
  const [edges, setEdges] = useState<WorkflowEdge[]>([])
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null)
  const [isAddingNode, setIsAddingNode] = useState(false)
  const [addingNodeType, setAddingNodeType] = useState<string | null>(null)
  void isAddingNode
  void addingNodeType
  const [isDirty, setIsDirty] = useState(false)
  const canvasRef = useRef<SVGSVGElement>(null)

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
  void handleNodeDrag

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
        <div className="col-span-1 bg-slate-700/50 rounded-lg p-3">
          <WorkflowList
            workflows={workflows}
            selectedWorkflow={selectedWorkflow}
            onSelect={setSelectedWorkflow}
          />
        </div>

        <div className="col-span-2 bg-slate-900/50 rounded-lg relative h-[500px] overflow-hidden">
          {selectedWorkflow ? (
            <>
              <NodePalette nodeTypes={nodeTypes} onAddNode={handleAddNode} />
              <WorkflowCanvas
                nodes={nodes}
                edges={edges}
                selectedNode={selectedNode}
                onSelectNode={setSelectedNode}
                canvasRef={canvasRef}
                nodeTypes={nodeTypes}
              />
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

        <div className="col-span-1 bg-slate-700/50 rounded-lg p-3">
          <NodeConfigPanel
            selectedNode={selectedNode}
            nodes={nodes}
            setNodes={setNodes}
            setSelectedNode={setSelectedNode}
            setIsDirty={setIsDirty}
            onDeleteNode={handleDeleteNode}
            triggerOptions={triggerOptions}
            actionOptions={actionOptions}
          />
        </div>
      </div>
    </div>
  )
}
