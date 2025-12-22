import { tabs, tabGroups, TabId, TabGroup } from './types'

interface TabNavProps {
  activeTab: string
  onTabChange: (tab: TabId) => void
}

export default function TabNav({ activeTab, onTabChange }: TabNavProps) {
  // Group tabs by their group
  const groupedTabs = tabs.reduce((acc, tab) => {
    if (!acc[tab.group]) acc[tab.group] = []
    acc[tab.group].push(tab)
    return acc
  }, {} as Record<TabGroup, typeof tabs>)

  const groupOrder: TabGroup[] = ['knowledge', 'research', 'operations', 'analysis']

  return (
    <nav className="flex items-center gap-1">
      {groupOrder.map((groupKey, groupIndex) => {
        const group = tabGroups[groupKey]
        const groupTabs = groupedTabs[groupKey] || []

        return (
          <div key={groupKey} className="flex items-center">
            {/* Group container with subtle background */}
            <div className={`flex items-center gap-0.5 px-1 py-1 rounded-lg bg-gradient-to-r ${group.gradient}`}>
              {groupTabs.map(({ id, label, icon: Icon }) => {
                const isActive = activeTab === id
                return (
                  <button
                    key={id}
                    onClick={() => onTabChange(id)}
                    className={`
                      relative flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                      transition-all duration-200 ease-out
                      ${isActive
                        ? 'bg-white/15 text-white shadow-lg shadow-black/20 scale-[1.02]'
                        : 'text-white/60 hover:text-white/90 hover:bg-white/5'
                      }
                    `}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : ''}`} />
                    <span className="hidden lg:inline">{label}</span>
                    {isActive && (
                      <span
                        className="absolute inset-x-0 -bottom-1 h-0.5 rounded-full"
                        style={{ backgroundColor: 'var(--theme-accent)' }}
                      />
                    )}
                  </button>
                )
              })}
            </div>

            {/* Divider between groups */}
            {groupIndex < groupOrder.length - 1 && (
              <div className="w-px h-6 mx-2 bg-white/10" />
            )}
          </div>
        )
      })}
    </nav>
  )
}
