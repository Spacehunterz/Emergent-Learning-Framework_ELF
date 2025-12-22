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
  const buttonRef = useRef<HTMLButtonElement>(null)
  // We don't strictly need a ref for the dropdown content div if we just check the event target
  const dropdownPanelRef = useRef<HTMLDivElement>(null)

  const pendingItems = items.filter(item => item.status === 'Pending')

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent immediate close
    onToggle()
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // If clicking inside the button or the dropdown panel, do nothing
      if (
        buttonRef.current?.contains(event.target as Node) ||
        dropdownPanelRef.current?.contains(event.target as Node)
      ) {
        return
      }
      onClose()
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen, onClose])

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${pendingItems.length > 0
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

      {/* Dropdown Panel - Standard Absolute Position */}
      {isOpen && (
        <div
          ref={dropdownPanelRef}
          className="absolute right-0 top-full mt-2 w-96 rounded-xl shadow-2xl overflow-hidden z-[9999] glass-panel border border-white/10"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.95)' }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="p-3 border-b border-white/10 bg-black/20">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Inbox className="w-4 h-4 text-violet-400" />
              CEO Inbox
            </h3>
          </div>
          <div className="max-h-80 overflow-y-auto custom-scrollbar">
            {items.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-sm">
                <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-3">
                  <Inbox className="w-6 h-6 opacity-50" />
                </div>
                No items in inbox
              </div>
            ) : (
              items.map((item) => (
                <button
                  key={item.filename}
                  onClick={() => onItemClick(item)}
                  className="w-full text-left p-3 border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase tracking-wider ${priorityColors[item.priority] || priorityColors.Medium}`}>
                          {item.priority}
                        </span>
                        <span className={`text-[10px] uppercase tracking-wider ${item.status === 'Pending' ? 'text-amber-400' : 'text-emerald-400'}`}>
                          {item.status}
                        </span>
                      </div>
                      <h4 className="text-sm font-medium text-white truncate group-hover:text-violet-300 transition-colors">{item.title}</h4>
                      {item.summary && (
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2">{item.summary}</p>
                      )}
                      {item.date && (
                        <p className="text-[10px] text-slate-500 mt-2 font-mono">{item.date}</p>
                      )}
                    </div>
                    <FileText className="w-4 h-4 text-slate-600 flex-shrink-0 mt-1 group-hover:text-white transition-colors" />
                  </div>
                </button>
              ))
            )}
          </div>
          <div className="p-2 border-t border-white/10 bg-black/20">
            <p className="text-[10px] text-slate-500 text-center uppercase tracking-widest">
              {pendingItems.length} pending · {items.length} total
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
