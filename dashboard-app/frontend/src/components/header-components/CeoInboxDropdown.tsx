import { useRef, useEffect } from 'react'
import { Inbox, ChevronDown, FileText } from 'lucide-react'
import { CeoItem, priorityColors } from './types'

interface CeoInboxDropdownProps {
  items: CeoItem[]
  isOpen: boolean
  onToggle: () => void
  onClose: () => void
  onItemClick: (item: CeoItem) => void
}

export default function CeoInboxDropdown({
  items,
  isOpen,
  onToggle,
  onClose,
  onItemClick,
}: CeoInboxDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null)
  const pendingItems = items.filter(item => item.status === 'Pending')

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={onToggle}
        className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          pendingItems.length > 0
            ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
            : 'bg-white/5 text-white/60 hover:text-white hover:bg-white/10'
        }`}
      >
        <Inbox className="w-4 h-4" />
        <span>CEO Inbox</span>
        {pendingItems.length > 0 && (
          <span className="bg-amber-500 text-black text-xs font-bold px-1.5 py-0.5 rounded-full">
            {pendingItems.length}
          </span>
        )}
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          className="fixed right-4 w-96 rounded-lg shadow-2xl overflow-hidden z-[100]"
          style={{ background: '#0f172a', border: '1px solid #334155', top: '70px' }}
        >
          <div className="p-3 border-b border-slate-700" style={{ background: '#1e293b' }}>
            <h3 className="text-sm font-semibold text-white">CEO Inbox</h3>
          </div>
          <div className="max-h-80 overflow-y-auto" style={{ background: '#0f172a' }}>
            {items.length === 0 ? (
              <div className="p-4 text-center text-slate-400 text-sm">
                No items in CEO inbox
              </div>
            ) : (
              items.map((item) => (
                <button
                  key={item.filename}
                  onClick={() => onItemClick(item)}
                  className="w-full text-left p-3 border-b border-slate-800 hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs px-2 py-0.5 rounded border ${priorityColors[item.priority] || priorityColors.Medium}`}>
                          {item.priority}
                        </span>
                        <span className={`text-xs ${item.status === 'Pending' ? 'text-amber-400' : 'text-emerald-400'}`}>
                          {item.status}
                        </span>
                      </div>
                      <h4 className="text-sm font-medium text-white truncate">{item.title}</h4>
                      {item.summary && (
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2">{item.summary}</p>
                      )}
                      {item.date && (
                        <p className="text-xs text-slate-500 mt-1">{item.date}</p>
                      )}
                    </div>
                    <FileText className="w-4 h-4 text-slate-500 flex-shrink-0 mt-1" />
                  </div>
                </button>
              ))
            )}
          </div>
          <div className="p-2 border-t border-slate-700" style={{ background: '#1e293b' }}>
            <p className="text-xs text-slate-500 text-center">
              {pendingItems.length} pending · {items.length} total
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
