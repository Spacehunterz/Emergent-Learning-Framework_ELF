import { tabs, TabId } from './types'

interface TabNavProps {
  activeTab: string
  onTabChange: (tab: TabId) => void
}

export default function TabNav({ activeTab, onTabChange }: TabNavProps) {
  return (
    <nav className="flex items-center space-x-1">
      {tabs.map(({ id, label, icon: Icon }) => {
        const isActive = activeTab === id
        return (
          <button
            key={id}
            onClick={() => onTabChange(id as TabId)}
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
  )
}
