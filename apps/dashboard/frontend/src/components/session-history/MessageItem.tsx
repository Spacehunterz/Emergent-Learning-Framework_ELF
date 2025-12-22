import { User, Bot, Terminal } from 'lucide-react'
import { MessageItemProps } from './types'

export default function MessageItem({ message, formatTimestamp }: MessageItemProps) {
  return (
    <div className={`${message.type === 'user' ? 'bg-slate-800/50' : 'bg-slate-700/30'} rounded-lg p-3`}>
      {/* Message header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          {message.type === 'user' ? (
            <>
              <User className="w-4 h-4 text-sky-400" />
              <span className="text-sm font-medium text-sky-400">User</span>
            </>
          ) : (
            <>
              <Bot className="w-4 h-4 text-violet-400" />
              <span className="text-sm font-medium text-violet-400">Claude</span>
            </>
          )}
          {message.is_command && message.command_name && (
            <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 text-xs">
              /{message.command_name}
            </span>
          )}
        </div>
        <span className="text-xs text-slate-400">{formatTimestamp(message.timestamp)}</span>
      </div>

      {/* Message content */}
      <div className={`text-sm ${message.type === 'user' ? 'text-white font-medium' : 'text-slate-300'} whitespace-pre-wrap`}>
        {message.content}
      </div>

      {/* Tool uses */}
      {message.tool_use && message.tool_use.length > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-600">
          <div className="flex flex-wrap gap-1">
            {message.tool_use.map((tool: any, toolIdx: number) => (
              <details key={toolIdx} className="inline-block">
                <summary className="cursor-pointer inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 transition-colors">
                  <Terminal className="w-3 h-3" />
                  <span>{tool.name}</span>
                </summary>
                <div className="mt-1 p-2 bg-slate-800 rounded text-xs text-slate-300 max-w-md">
                  <pre className="overflow-x-auto">{JSON.stringify(tool.input, null, 2)}</pre>
                </div>
              </details>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
