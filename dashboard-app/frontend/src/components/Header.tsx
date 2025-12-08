import { Brain, Activity, BookOpen, Clock, Search, Workflow } from 'lucide-react'

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
    <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-500 flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Emergent Learning</h1>
              <p className="text-xs text-slate-400">Agent Intelligence Dashboard</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex items-center space-x-1">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => onTabChange(id)}
                className={`
                  flex items-center space-x-2 px-4 py-2 rounded-lg transition-all
                  ${activeTab === id
                    ? 'bg-sky-500/20 text-sky-400'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                <span className="text-sm font-medium">{label}</span>
              </button>
            ))}
          </nav>

          {/* Connection Status */}
          <div className="flex items-center space-x-3">
            <div className={`
              flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium
              ${isConnected
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-red-500/20 text-red-400'
              }
            `}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 live-indicator' : 'bg-red-400'}`} />
              <span>{isConnected ? 'Live' : 'Disconnected'}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
