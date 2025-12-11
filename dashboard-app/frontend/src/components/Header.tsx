import { Activity, Brain, Clock, Search, Workflow, Inbox, ChevronDown, ExternalLink, X, FileText } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

interface CeoItem {
  filename: string
  title: string
  priority: string
  status: string
  date: string | null
  summary: string
  path: string
}

interface HeaderProps {
  isConnected: boolean
  activeTab: string
  onTabChange: (tab: 'overview' | 'heuristics' | 'runs' | 'timeline' | 'query') => void
}

const tabs = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'heuristics', label: 'Heuristics', icon: Brain },
  { id: 'runs', label: 'Runs', icon: Workflow },
  { id: 'timeline', label: 'Timeline', icon: Clock },
  { id: 'query', label: 'Query', icon: Search },
] as const

const priorityColors: Record<string, string> = {
  Critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  High: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  Medium: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  Low: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

export default function Header({ isConnected, activeTab, onTabChange }: HeaderProps) {
  const [ceoItems, setCeoItems] = useState<CeoItem[]>([])
  const [showCeoDropdown, setShowCeoDropdown] = useState(false)
  const [selectedItem, setSelectedItem] = useState<CeoItem | null>(null)
  const [itemContent, setItemContent] = useState<string>('')
  const [loadingContent, setLoadingContent] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Fetch CEO inbox items
  useEffect(() => {
    const fetchCeoInbox = async () => {
      try {
        const res = await fetch('/api/ceo-inbox')
        if (res.ok) {
          const data = await res.json()
          setCeoItems(data)
        }
      } catch (e) {
        console.error('Failed to fetch CEO inbox:', e)
      }
    }
    fetchCeoInbox()
    const interval = setInterval(fetchCeoInbox, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowCeoDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const pendingItems = ceoItems.filter(item => item.status === 'Pending')

  // Fetch full content when item is selected
  const handleItemClick = async (item: CeoItem) => {
    setSelectedItem(item)
    setLoadingContent(true)
    try {
      const res = await fetch(`/api/ceo-inbox/${item.filename}`)
      if (res.ok) {
        const data = await res.json()
        setItemContent(data.content)
      }
    } catch (e) {
      console.error('Failed to fetch item content:', e)
      setItemContent('Failed to load content')
    }
    setLoadingContent(false)
  }

  const closeModal = () => {
    setSelectedItem(null)
    setItemContent('')
  }

  return (
    <header className="glass-panel border-b border-white/5 sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <h1 className="text-2xl font-black tracking-tight cosmic-title">
            COSMIC DASHBOARD
          </h1>

          {/* Navigation */}
          <nav className="flex items-center space-x-1">
            {tabs.map(({ id, label, icon: Icon }) => {
              const isActive = activeTab === id
              return (
                <button
                  key={id}
                  onClick={() => onTabChange(id)}
                  className={
                    isActive
                      ? 'flex items-center space-x-2 px-4 py-2 rounded-lg transition-all bg-white/10 text-white'
                      : 'flex items-center space-x-2 px-4 py-2 rounded-lg transition-all text-white/60 hover:text-white hover:bg-white/5'
                  }
                  style={isActive ? { color: 'var(--theme-accent)' } : {}}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-sm font-medium">{label}</span>
                </button>
              )
            })}
          </nav>

          {/* Right side: CEO Inbox + Connection Status */}
          <div className="flex items-center space-x-3">
            {/* CEO Inbox Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setShowCeoDropdown(!showCeoDropdown)}
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
                <ChevronDown className={`w-3 h-3 transition-transform ${showCeoDropdown ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown Panel - OPAQUE background */}
              {showCeoDropdown && (
                <div
                  className="absolute right-0 mt-2 w-96 rounded-lg shadow-2xl overflow-hidden z-50"
                  style={{ background: '#0f172a', border: '1px solid #334155' }}
                >
                  <div className="p-3 border-b border-slate-700" style={{ background: '#1e293b' }}>
                    <h3 className="text-sm font-semibold text-white">CEO Inbox</h3>
                  </div>
                  <div className="max-h-80 overflow-y-auto" style={{ background: '#0f172a' }}>
                    {ceoItems.length === 0 ? (
                      <div className="p-4 text-center text-slate-400 text-sm">
                        No items in CEO inbox
                      </div>
                    ) : (
                      ceoItems.map((item) => (
                        <button
                          key={item.filename}
                          onClick={() => handleItemClick(item)}
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
                      {pendingItems.length} pending · {ceoItems.length} total
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Connection Status */}
            <div className={
              isConnected
                ? 'flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400'
                : 'flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400'
            }>
              <span className={isConnected ? 'w-2 h-2 rounded-full bg-emerald-400 live-indicator' : 'w-2 h-2 rounded-full bg-red-400'} />
              <span>{isConnected ? 'Live' : 'Disconnected'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* CEO Item Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/80 flex items-start justify-center z-[100] pt-16 px-4 pb-4 overflow-y-auto" onClick={closeModal}>
          <div
            className="rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden my-auto"
            style={{ background: '#0f172a', border: '1px solid #334155' }}
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between p-4 border-b border-slate-700" style={{ background: '#1e293b' }}>
              <div className="flex-1 min-w-0 pr-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs px-2 py-0.5 rounded border ${priorityColors[selectedItem.priority] || priorityColors.Medium}`}>
                    {selectedItem.priority}
                  </span>
                  <span className={`text-xs ${selectedItem.status === 'Pending' ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {selectedItem.status}
                  </span>
                  {selectedItem.date && (
                    <span className="text-xs text-slate-500">{selectedItem.date}</span>
                  )}
                </div>
                <h2 className="text-lg font-semibold text-white">{selectedItem.title}</h2>
              </div>
              <button
                onClick={closeModal}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[70vh]" style={{ background: '#0f172a' }}>
              {loadingContent ? (
                <div className="text-center text-slate-400 py-8">Loading...</div>
              ) : (
                <div className="prose prose-invert prose-sm max-w-none prose-headings:text-white prose-p:text-slate-300 prose-li:text-slate-300 prose-strong:text-white prose-code:text-amber-400 prose-pre:bg-slate-800 prose-pre:border prose-pre:border-slate-700">
                  <ReactMarkdown>{itemContent}</ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
