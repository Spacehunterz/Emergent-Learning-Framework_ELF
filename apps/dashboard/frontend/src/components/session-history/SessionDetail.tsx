import { Clock } from 'lucide-react'
import { SessionDetailProps } from './types'
import MessageItem from './MessageItem'

export default function SessionDetail({
  session,
  sessionDetail,
  isLoading,
  formatTimestamp
}: SessionDetailProps) {
  if (isLoading) {
    return (
      <div className="px-3 pb-3 border-t border-slate-600">
        <div className="text-center text-slate-400 py-8">
          <Clock className="w-6 h-6 mx-auto mb-2 animate-spin" />
          Loading conversation...
        </div>
      </div>
    )
  }

  if (!sessionDetail || !sessionDetail.messages || sessionDetail.messages.length === 0) {
    return (
      <div className="px-3 pb-3 border-t border-slate-600">
        <div className="text-center text-slate-400 py-8">
          No messages found
        </div>
      </div>
    )
  }

  return (
    <div className="px-3 pb-3 border-t border-slate-600">
      <div className="pt-3 space-y-3 max-h-96 overflow-y-auto">
        {/* Session info */}
        <div className="grid grid-cols-2 gap-4 text-sm pb-2 border-b border-slate-600">
          <div>
            <span className="text-slate-400">Started:</span>
            <span className="text-white ml-2">{formatTimestamp(session.first_timestamp)}</span>
          </div>
          <div>
            <span className="text-slate-400">Last Activity:</span>
            <span className="text-white ml-2">{formatTimestamp(session.last_timestamp)}</span>
          </div>
        </div>

        {/* Messages timeline */}
        <div className="space-y-3">
          {sessionDetail.messages.map((msg) => (
            <MessageItem key={msg.uuid} message={msg} formatTimestamp={formatTimestamp} />
          ))}
        </div>
      </div>
    </div>
  )
}
