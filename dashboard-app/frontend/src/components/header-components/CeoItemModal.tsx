import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { CeoItem, priorityColors } from './types'

interface CeoItemModalProps {
  item: CeoItem
  content: string
  loading: boolean
  onClose: () => void
}

export default function CeoItemModal({ item, content, loading, onClose }: CeoItemModalProps) {
  return createPortal(
    <div
      className="fixed inset-0 bg-black/80 flex items-start justify-center pt-16 px-4 pb-4 overflow-y-auto"
      style={{ zIndex: 9999 }}
      onClick={onClose}
    >
      <div
        className="rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden my-auto"
        style={{ background: '#0f172a', border: '1px solid #334155' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-start justify-between p-4 border-b border-slate-700" style={{ background: '#1e293b' }}>
          <div className="flex-1 min-w-0 pr-4">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded border ${priorityColors[item.priority] || priorityColors.Medium}`}>
                {item.priority}
              </span>
              <span className={`text-xs ${item.status === 'Pending' ? 'text-amber-400' : 'text-emerald-400'}`}>
                {item.status}
              </span>
              {item.date && (
                <span className="text-xs text-slate-500">{item.date}</span>
              )}
            </div>
            <h2 className="text-lg font-semibold text-white">{item.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto max-h-[70vh]" style={{ background: '#0f172a' }}>
          {loading ? (
            <div className="text-center text-slate-400 py-8">Loading...</div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-headings:text-white prose-p:text-slate-300 prose-li:text-slate-300 prose-strong:text-white prose-code:text-amber-400 prose-pre:bg-slate-800 prose-pre:border prose-pre:border-slate-700">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  )
}
