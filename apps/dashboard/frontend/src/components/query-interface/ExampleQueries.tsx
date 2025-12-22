import { ExampleQueriesProps, exampleQueries } from './types'

export default function ExampleQueries({ onSelectQuery }: ExampleQueriesProps) {
  return (
    <div className="mb-6">
      <div className="text-sm text-slate-400 mb-3">Try asking:</div>
      <div className="grid grid-cols-2 gap-2">
        {exampleQueries.map(({ icon: Icon, text, category }) => (
          <button
            key={text}
            onClick={() => onSelectQuery(text)}
            className="flex items-center space-x-2 p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition text-left"
          >
            <Icon className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <div>
              <div className="text-sm text-white">{text}</div>
              <div className="text-xs text-slate-500">{category}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
