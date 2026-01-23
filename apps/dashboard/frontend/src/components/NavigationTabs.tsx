import { Globe, Brain, BarChart3, Clock, LineChart, Sparkles } from 'lucide-react'

export type TabType = 'overview' | 'heuristics' | 'runs' | 'timeline' | 'analytics' | 'graph'

interface Tab {
  id: TabType
  label: string
  icon: any
  color: string
  glowColor: string
}

const tabs: Tab[] = [
  { id: 'overview', label: 'OVERVIEW', icon: Globe, color: '#a78bfa', glowColor: 'rgba(167, 139, 250, 0.5)' },
  { id: 'heuristics', label: 'HEURISTICS', icon: Brain, color: '#f472b6', glowColor: 'rgba(244, 114, 182, 0.5)' },
  { id: 'runs', label: 'RUNS', icon: BarChart3, color: '#22d3ee', glowColor: 'rgba(34, 211, 238, 0.5)' },
  { id: 'timeline', label: 'TIMELINE', icon: Clock, color: '#4ade80', glowColor: 'rgba(74, 222, 128, 0.5)' },
  { id: 'analytics', label: 'ANALYTICS', icon: LineChart, color: '#fb923c', glowColor: 'rgba(251, 146, 60, 0.5)' },
]

interface NavigationTabsProps {
  activeTab: TabType | string
  onTabChange: (tab: TabType) => void
  selectedDomain?: string | null
  onClearDomain?: () => void
}

export function NavigationTabs({ activeTab, onTabChange, selectedDomain, onClearDomain }: NavigationTabsProps) {
  return (
    <div className="relative">
      {/* Background glow line */}
      <div
        className="absolute bottom-0 left-0 right-0 h-[1px]"
        style={{
          background: 'linear-gradient(90deg, transparent 0%, rgba(167,139,250,0.3) 20%, rgba(34,211,238,0.3) 50%, rgba(167,139,250,0.3) 80%, transparent 100%)',
        }}
      />

      <div className="flex items-center justify-between px-6 py-2">
        {/* Tab Navigation */}
        <div className="flex items-center gap-1">
          {tabs.map((tab, index) => {
            const isActive = activeTab === tab.id
            const Icon = tab.icon

            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className="relative group px-4 py-2.5 rounded-lg transition-all duration-300"
                style={{
                  background: isActive
                    ? `linear-gradient(135deg, ${tab.color}20 0%, ${tab.color}10 100%)`
                    : 'transparent',
                }}
              >
                {/* Active indicator glow */}
                {isActive && (
                  <>
                    <div
                      className="absolute inset-0 rounded-lg opacity-50 blur-md"
                      style={{ background: tab.glowColor }}
                    />
                    <div
                      className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-[2px] rounded-full"
                      style={{
                        background: tab.color,
                        boxShadow: `0 0 10px ${tab.color}, 0 0 20px ${tab.color}`,
                      }}
                    />
                  </>
                )}

                <div className="relative flex items-center gap-2">
                  <Icon
                    className="w-4 h-4 transition-all duration-300"
                    style={{
                      color: isActive ? tab.color : 'rgba(148, 163, 184, 0.6)',
                      filter: isActive ? `drop-shadow(0 0 6px ${tab.color})` : 'none',
                    }}
                  />
                  <span
                    className="text-[11px] font-bold tracking-[0.15em] transition-all duration-300"
                    style={{
                      color: isActive ? tab.color : 'rgba(148, 163, 184, 0.6)',
                      textShadow: isActive ? `0 0 10px ${tab.glowColor}` : 'none',
                    }}
                  >
                    {tab.label}
                  </span>
                </div>

                {/* Hover effect */}
                <div
                  className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                  style={{
                    background: `linear-gradient(135deg, ${tab.color}10 0%, transparent 100%)`,
                  }}
                />
              </button>
            )
          })}
        </div>

        {/* Domain Filter Badge */}
        {selectedDomain && (
          <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-violet-500/10 border border-violet-500/30">
            <Sparkles className="w-3 h-3 text-violet-400" />
            <span className="text-[10px] font-bold tracking-wider text-violet-300 uppercase">
              Domain: {selectedDomain}
            </span>
            <button
              onClick={onClearDomain}
              className="ml-1 text-violet-400 hover:text-white transition-colors text-xs hover:bg-violet-500/20 rounded-full w-5 h-5 flex items-center justify-center"
            >
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
