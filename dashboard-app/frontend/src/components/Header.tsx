import { Activity, Brain, Clock, Search, Workflow } from 'lucide-react'

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

export default function Header({ isConnected, activeTab, onTabChange }: HeaderProps) {
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

          {/* Connection Status */}
          <div className="flex items-center space-x-3">
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
    </header>
  )
}
