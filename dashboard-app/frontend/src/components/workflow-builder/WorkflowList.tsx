import { WorkflowListProps } from './types'

export default function WorkflowList({ workflows, selectedWorkflow, onSelect }: WorkflowListProps) {
  return (
    <>
      <div className="text-sm font-medium text-slate-400 mb-2">Workflows</div>
      <div className="space-y-1">
        {workflows.map(wf => (
          <button
            key={wf.id}
            onClick={() => onSelect(wf)}
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
    </>
  )
}
