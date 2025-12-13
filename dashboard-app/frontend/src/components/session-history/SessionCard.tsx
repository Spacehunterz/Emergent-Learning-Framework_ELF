import { User, Bot, GitBranch, MessageSquare, ChevronDown } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { SessionCardProps } from './types'

export default function SessionCard({
  session,
  isExpanded,
  isLoading,
  onToggle,
  formatTimestamp
}: SessionCardProps) {
  return (
    <div
      className="p-3 cursor-pointer hover:bg-slate-700/70 transition-colors"
      onClick={() => onToggle(session.session_id)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3 flex-1 min-w-0">
          <div className={`p-2 rounded-lg ${session.is_agent ? 'bg-violet-500/20 text-violet-400' : 'bg-sky-500/20 text-sky-400'}`}>
            {session.is_agent ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-0.5">
              <span className="text-sm font-medium text-white truncate">{session.project}</span>
              {session.git_branch && (
                <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-slate-600 text-xs text-slate-300 flex-shrink-0">
                  <GitBranch className="w-3 h-3" />
                  <span>{session.git_branch}</span>
                </span>
              )}
            </div>
            <div className="text-xs text-slate-400 truncate">
              {session.first_prompt_preview}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4 flex-shrink-0 ml-4">
          <div className="text-right">
            <div className="text-sm font-medium text-white">
              {formatDistanceToNow(new Date(session.first_timestamp), { addSuffix: true })}
            </div>
            <div className="flex items-center space-x-1 text-xs text-slate-400">
              <MessageSquare className="w-3 h-3" />
              <span>{session.prompt_count} prompts</span>
            </div>
          </div>
          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
        </div>
      </div>
    </div>
  )
}
