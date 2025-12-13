import { Trash2 } from 'lucide-react'
import { NodeConfigPanelProps } from './types'

export default function NodeConfigPanel({
  selectedNode,
  nodes,
  setNodes,
  setSelectedNode,
  setIsDirty,
  onDeleteNode,
  triggerOptions,
  actionOptions,
}: NodeConfigPanelProps) {
  if (!selectedNode) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500 text-sm">
        Select a node to configure
      </div>
    )
  }

  return (
    <>
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-medium text-white">{selectedNode.label}</div>
        <button
          onClick={() => onDeleteNode(selectedNode.id)}
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
  )
}
