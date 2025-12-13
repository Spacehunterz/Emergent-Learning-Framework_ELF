import { useState, useEffect } from 'react'
import { Command, Sparkles } from 'lucide-react'
import { TabNav, ConnectionStatus, CeoInboxDropdown, CeoItemModal, CeoItem, TabId } from './header-components'

interface HeaderProps {
  isConnected: boolean
  activeTab: string
  onTabChange: (tab: TabId) => void
  onOpenCommandPalette?: () => void
}

export default function Header({ isConnected, activeTab, onTabChange, onOpenCommandPalette }: HeaderProps) {
  const [ceoItems, setCeoItems] = useState<CeoItem[]>([])
  const [showCeoDropdown, setShowCeoDropdown] = useState(false)
  const [selectedItem, setSelectedItem] = useState<CeoItem | null>(null)
  const [itemContent, setItemContent] = useState<string>('')
  const [loadingContent, setLoadingContent] = useState(false)

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
    const interval = setInterval(fetchCeoInbox, 30000)
    return () => clearInterval(interval)
  }, [])

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
    <>
      <header className="sticky top-0 z-50">
        {/* Top Bar - Branding & Actions */}
        <div className="glass-panel border-b border-white/5">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between h-14">
              {/* Logo & Brand */}
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Sparkles className="w-7 h-7 text-violet-400" />
                  <div className="absolute inset-0 blur-lg bg-violet-500/30 animate-pulse" />
                </div>
                <div>
                  <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-violet-200 to-violet-400 bg-clip-text text-transparent">
                    EMERGENT LEARNING
                  </h1>
                  <p className="text-[10px] text-white/40 tracking-widest uppercase -mt-0.5">
                    Knowledge Framework
                  </p>
                </div>
              </div>

              {/* Command Palette Trigger */}
              <button
                onClick={onOpenCommandPalette}
                className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg
                  bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20
                  text-white/50 hover:text-white/80 transition-all duration-200 group"
              >
                <Command className="w-3.5 h-3.5" />
                <span className="text-xs">Search...</span>
                <kbd className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-white/10 border border-white/10
                  group-hover:bg-white/15 group-hover:border-white/20">
                  Ctrl+K
                </kbd>
              </button>

              {/* Right side: CEO Inbox + Connection Status */}
              <div className="flex items-center gap-3">
                <CeoInboxDropdown
                  items={ceoItems}
                  isOpen={showCeoDropdown}
                  onToggle={() => setShowCeoDropdown(!showCeoDropdown)}
                  onClose={() => setShowCeoDropdown(false)}
                  onItemClick={handleItemClick}
                />
                <ConnectionStatus isConnected={isConnected} />
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Bar - Navigation */}
        <div className="bg-gradient-to-r from-slate-900/80 via-slate-800/80 to-slate-900/80 backdrop-blur-md border-b border-white/5">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-center h-12 overflow-x-auto scrollbar-hide">
              <TabNav activeTab={activeTab} onTabChange={onTabChange} />
            </div>
          </div>
        </div>
      </header>

      {/* CEO Item Detail Modal */}
      {selectedItem && (
        <CeoItemModal
          item={selectedItem}
          content={itemContent}
          loading={loadingContent}
          onClose={closeModal}
        />
      )}
    </>
  )
}
