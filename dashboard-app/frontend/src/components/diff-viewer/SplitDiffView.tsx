import { SplitDiffViewProps, DiffChange } from './types'

export default function SplitDiffView({ changes }: SplitDiffViewProps) {
  // Group changes into pairs for side-by-side display
  const pairs: Array<{ left: DiffChange | null; right: DiffChange | null }> = []
  let i = 0

  while (i < changes.length) {
    const change = changes[i]

    if (change.type === 'context') {
      pairs.push({ left: change, right: change })
      i++
    } else if (change.type === 'remove') {
      // Look for a matching add
      const nextAdd = changes[i + 1]?.type === 'add' ? changes[i + 1] : null
      pairs.push({ left: change, right: nextAdd })
      i += nextAdd ? 2 : 1
    } else if (change.type === 'add') {
      pairs.push({ left: null, right: change })
      i++
    }
  }

  return (
    <div className="grid grid-cols-2 font-mono text-xs">
      {pairs.map((pair, idx) => (
        <div key={idx} className="contents">
          {/* Left side (removals) */}
          <div
            className={`border-r border-slate-700 ${
              pair.left?.type === 'remove'
                ? 'bg-red-500/10 border-l-2 border-l-red-500'
                : pair.left?.type === 'context'
                ? 'bg-slate-800/50'
                : 'bg-slate-900'
            }`}
          >
            {pair.left && (
              <div className="flex">
                <div className="flex-shrink-0 w-12 px-2 py-1 text-slate-500 text-right select-none border-r border-slate-700/50">
                  {pair.left.oldLineNumber}
                </div>
                <div
                  className={`flex-1 px-2 py-1 whitespace-pre overflow-x-auto ${
                    pair.left.type === 'remove' ? 'text-red-300' : 'text-slate-400'
                  }`}
                >
                  {pair.left.type === 'remove' && <span className="select-none mr-2">-</span>}
                  {pair.left.content}
                </div>
              </div>
            )}
          </div>

          {/* Right side (additions) */}
          <div
            className={
              pair.right?.type === 'add'
                ? 'bg-emerald-500/10 border-l-2 border-emerald-500'
                : pair.right?.type === 'context'
                ? 'bg-slate-800/50'
                : 'bg-slate-900'
            }
          >
            {pair.right && (
              <div className="flex">
                <div className="flex-shrink-0 w-12 px-2 py-1 text-slate-500 text-right select-none border-r border-slate-700/50">
                  {pair.right.newLineNumber}
                </div>
                <div
                  className={`flex-1 px-2 py-1 whitespace-pre overflow-x-auto ${
                    pair.right.type === 'add' ? 'text-emerald-300' : 'text-slate-400'
                  }`}
                >
                  {pair.right.type === 'add' && <span className="select-none mr-2">+</span>}
                  {pair.right.content}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
