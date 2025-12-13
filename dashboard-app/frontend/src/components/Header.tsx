import { useState, useEffect } from 'react'
import { TabNav, ConnectionStatus, CeoInboxDropdown, CeoItemModal, CeoItem, TabId } from './header-components'

interface HeaderProps {
  isConnected: boolean
  activeTab: string
  onTabChange: (tab: TabId) => void
}

export default function Header({ isConnected, activeTab, onTabChange }: HeaderProps) {
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
      <header className="glass-panel border-b border-white/5 sticky top-0 z-50">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <h1 className="text-2xl font-black tracking-tight cosmic-title">
              COSMIC DASHBOARD
            </h1>

            {/* Navigation */}
            <TabNav activeTab={activeTab} onTabChange={onTabChange} />

            {/* Right side: CEO Inbox + Connection Status */}
            <div className="flex items-center space-x-3">
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
