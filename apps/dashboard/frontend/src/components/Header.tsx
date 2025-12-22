import { useState, useEffect } from 'react'
import { Command, Sparkles, LayoutGrid, Globe, Gamepad2 } from 'lucide-react'
import { ConnectionStatus, NotificationCenter, CeoItemModal, CeoItem } from './header-components'
import { SettingsPanel } from './SettingsPanel'
import { useCosmicSettings } from '../context/CosmicSettingsContext'
import { useCosmicAudio } from '../context/CosmicAudioContext'
import { useDataContext } from '../context/DataContext'
import { useGame } from '../context/GameContext'
import ScopeToggle from './ScopeToggle'

interface HeaderProps {
  isConnected: boolean
  onOpenCommandPalette?: () => void
}

export default function Header({ isConnected, onOpenCommandPalette }: HeaderProps) {
  const [ceoItems, setCeoItems] = useState<CeoItem[]>([])
  const [selectedItem, setSelectedItem] = useState<CeoItem | null>(null)
  const [itemContent, setItemContent] = useState<string>('')
  const [loadingContent, setLoadingContent] = useState(false)
  const { viewMode, setViewMode } = useCosmicSettings()
  const { playHover, playClick } = useCosmicAudio()
  const { anomalies, heuristics, setAnomalies } = useDataContext()
  const { toggleMenu } = useGame()

  // Get golden rules for alerts panel
  const goldenRules = heuristics
    .filter(h => h.is_golden)
    .map(h => ({ ...h, id: String(h.id) }))

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
    playClick()
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
      <header className="sticky top-4 z-[9998] pointer-events-none transition-all duration-300 bg-transparent">
        {/* Pointer events on header container are none so clicks pass through to canvas on sides, 
            but we re-enable them on the actual content */}

        {/* Unified Pill Container */}
        <div className="container mx-auto px-4 flex justify-center pointer-events-auto">
          <div className="glass-panel border border-white/10 rounded-[2rem] shadow-2xl bg-black/60 backdrop-blur-xl flex flex-col md:flex-row items-center p-2 gap-4 md:gap-8 min-w-[320px] max-w-full overflow-visible">

            {/* Top Row (on Mobile) / Left Side (Desktop): Brand & View Toggle */}
            <div className="flex items-center gap-6 px-4">
              {/* Logo & Brand */}
              <div className="flex items-center gap-3 shrink-0">
                <div className="relative">
                  <Sparkles className="w-6 h-6 text-violet-400" />
                  <div className="absolute inset-0 blur-lg bg-violet-500/30 animate-pulse" />
                </div>
                <div>
                  <h1 className="text-sm font-bold tracking-tight bg-gradient-to-r from-white via-violet-200 to-violet-400 bg-clip-text text-transparent">
                    EMERGENT LEARNING
                  </h1>
                  <p className="text-[8px] text-white/40 tracking-[0.2em] uppercase -mt-0.5">
                    FRAMEWORK
                  </p>
                </div>
              </div>

              {/* View Toggle */}
              <div className="hidden md:flex bg-white/5 rounded-full p-1 border border-white/5 mx-2">
                <button
                  onClick={() => {
                    setViewMode('cosmic');
                    playClick();
                  }}
                  onMouseEnter={() => playHover()}
                  className={`p-1.5 rounded-full transition-all ${viewMode === 'cosmic' ? 'bg-violet-500 text-white shadow-lg' : 'text-white/40 hover:text-white'}`}
                  title="Cosmic View (3D)"
                >
                  <Globe className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setViewMode('grid');
                    playClick();
                  }}
                  onMouseEnter={() => playHover()}
                  className={`p-1.5 rounded-full transition-all ${viewMode === 'grid' ? 'bg-cyan-500 text-white shadow-lg' : 'text-white/40 hover:text-white'}`}
                  title="Grid View (2D)"
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
              </div>

              {/* Scope Toggle (Global/Project) */}
              <ScopeToggle />
            </div>

            {/* Middle: Cosmic Navigation / Search */}
            <div className="flex-1 w-full md:w-auto flex justify-center px-4">
              <button
                onClick={() => {
                  if (onOpenCommandPalette) onOpenCommandPalette();
                  playClick();
                }}
                onMouseEnter={() => playHover()}
                className="group relative flex items-center gap-3 px-8 py-3 w-full max-w-xl bg-white/5 border border-white/10 rounded-full hover:bg-white/10 hover:border-white/20 transition-all duration-300 shadow-inner"
              >
                <Command className="w-5 h-5 text-violet-400 group-hover:text-violet-300 transition-colors" />
                <span className="text-white/40 group-hover:text-white/70 text-sm font-medium tracking-wide transition-colors">
                  Search System...
                </span>
                <div className="ml-auto flex items-center gap-1">
                  <span className="text-[10px] bg-white/5 px-2 py-0.5 rounded text-white/30 border border-white/5">Example: "Overview"</span>
                  <span className="text-[10px] bg-white/5 px-1.5 py-0.5 rounded text-white/30 border border-white/5 hidden md:block">⌘K</span>
                </div>

                {/* Glow Effect */}
                <div className="absolute inset-0 rounded-full ring-1 ring-white/10 group-hover:ring-white/30 transition-all" />
              </button>
            </div>

            {/* Right Side: Actions */}
            <div className="flex items-center gap-4 px-4 border-l border-white/5 pl-6 shrink-0">

              <NotificationCenter
                ceoItems={ceoItems}
                onCeoItemClick={handleItemClick}
                anomalies={anomalies}
                goldenRules={goldenRules as any}
                onDismissAnomaly={(index) => setAnomalies(prev => prev.filter((_, i) => i !== index))}
              />

              <SettingsPanel />

              <div className="w-px h-6 bg-white/10 mx-1" />

              {/* Game Menu Toggle */}
              <button
                onClick={() => {
                  toggleMenu();
                  playClick();
                }}
                onMouseEnter={() => playHover()}
                className="p-2 rounded-full hover:bg-white/10 text-cyan-400 hover:text-cyan-300 transition-colors relative group"
                title="Cosmic Armory"
              >
                <Gamepad2 className="w-5 h-5" />
                <div className="absolute inset-0 rounded-full bg-cyan-400/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <ConnectionStatus isConnected={isConnected} />
            </div>
          </div>
        </div>
      </header>

      {/* CEO Item Detail Modal */}
      {
        selectedItem && (
          <CeoItemModal
            item={selectedItem}
            content={itemContent}
            loading={loadingContent}
            onClose={closeModal}
          />
        )
      }
    </>
  )
}
