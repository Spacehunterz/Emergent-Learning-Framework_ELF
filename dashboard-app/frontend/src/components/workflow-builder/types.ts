import { Workflow, WorkflowNode } from '../../types'
import { LucideIcon } from 'lucide-react'

export interface WorkflowBuilderProps {
  workflows: Workflow[]
  onSave: (workflow: Workflow) => void
  onDelete: (id: string) => void
  onRun: (id: string) => void
}

export interface NodeTypeConfig {
  icon: LucideIcon
  color: string
  label: string
}

export interface NodePaletteProps {
  nodeTypes: Record<string, NodeTypeConfig>
  onAddNode: (type: string) => void
}

export interface WorkflowCanvasProps {
  nodes: WorkflowNode[]
  edges: any[]
  selectedNode: WorkflowNode | null
  onSelectNode: (node: WorkflowNode | null) => void
  canvasRef: React.RefObject<SVGSVGElement>
  nodeTypes: Record<string, NodeTypeConfig>
}

export interface NodeConfigPanelProps {
  selectedNode: WorkflowNode | null
  nodes: WorkflowNode[]
  setNodes: (nodes: WorkflowNode[]) => void
  setSelectedNode: (node: WorkflowNode | null) => void
  setIsDirty: (dirty: boolean) => void
  onDeleteNode: (id: string) => void
  triggerOptions: Array<{ id: string; label: string; description: string }>
  actionOptions: Array<{ id: string; label: string; description: string }>
}

export interface WorkflowListProps {
  workflows: Workflow[]
  selectedWorkflow: Workflow | null
  onSelect: (workflow: Workflow) => void
}

export interface TriggerOption {
  id: string
  label: string
  description: string
}

export interface ActionOption {
  id: string
  label: string
  description: string
}
