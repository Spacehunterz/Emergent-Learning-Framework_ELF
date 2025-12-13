import { UnifiedDiffViewProps } from './types'

export default function UnifiedDiffView({ changes }: UnifiedDiffViewProps) {
  return (
    <div className="font-mono text-xs">
      {changes.map((change, idx) => {
        const bgColor =
          change.type === 'add'
            ? 'bg-emerald-500/10 border-l-2 border-emerald-500'
            : change.type === 'remove'
            ? 'bg-red-500/10 border-l-2 border-red-500'
            : 'bg-slate-800/50'

        const textColor =
          change.type === 'add'
            ? 'text-emerald-300'
            : change.type === 'remove'
            ? 'text-red-300'
            : 'text-slate-400'

        const linePrefix = change.type === 'add' ? '+' : change.type === 'remove' ? '-' : ' '

        return (
          <div key={idx} className={`flex ${bgColor}`}>
            <div className="flex-shrink-0 w-20 px-2 py-1 text-slate-500 text-right select-none border-r border-slate-700/50">
              {change.type === 'remove' && change.oldLineNumber && (
                <span>{change.oldLineNumber}</span>
              )}
              {change.type === 'add' && change.newLineNumber && (
                <span className="ml-2">{change.newLineNumber}</span>
              )}
              {change.type === 'context' && (
                <>
                  <span>{change.oldLineNumber}</span>
                  <span className="ml-2">{change.newLineNumber}</span>
                </>
              )}
            </div>
            <div className={`flex-1 px-2 py-1 whitespace-pre overflow-x-auto ${textColor}`}>
              <span className="select-none mr-2">{linePrefix}</span>
              {change.content}
            </div>
          </div>
        )
      })}
    </div>
  )
}
