import { createContext, useContext, ReactNode, useEffect } from 'react'
import { Stats, Hotspot, ApiRun, RawEvent, TimelineData, ApiAnomaly, Heuristic } from '../types'
import { useDashboardData } from '../hooks/useDashboardData'
import { useHeuristics } from '../hooks/useHeuristics'
import { useScopeStore } from '../store/scopeStore'

interface DataContextType {
  // Dashboard data
  stats: Stats | null
  hotspots: Hotspot[]
  runs: ApiRun[]
  events: RawEvent[]
  timeline: TimelineData | null
  anomalies: ApiAnomaly[]
  isLoading: boolean
  reload: () => void
  loadStats: () => Promise<void>
  setStats: React.Dispatch<React.SetStateAction<Stats | null>>
  setAnomalies: React.Dispatch<React.SetStateAction<ApiAnomaly[]>>

  // Heuristics data
  heuristics: Heuristic[]
  setHeuristics: React.Dispatch<React.SetStateAction<Heuristic[]>>
  promoteHeuristic: (id: number) => Promise<void>
  demoteHeuristic: (id: number) => Promise<void>
  deleteHeuristic: (id: number) => Promise<void>
  updateHeuristic: (id: number, updates: { rule?: string; explanation?: string; domain?: string }) => Promise<void>
  reloadHeuristics: () => Promise<void>
}

const DataContext = createContext<DataContextType | undefined>(undefined)

export function DataProvider({ children }: { children: ReactNode }) {
  // Get scope from store
  const { scope, fetchProjectContext } = useScopeStore()

  // Fetch project context on mount
  useEffect(() => {
    fetchProjectContext()
  }, [fetchProjectContext])

  // Use existing dashboard data hook
  const dashboardData = useDashboardData()

  // Use heuristics hook with stats reload callback and scope
  const heuristicsData = useHeuristics({
    onStatsChange: dashboardData.loadStats,
    scope
  })

  const value: DataContextType = {
    // Dashboard data
    stats: dashboardData.stats,
    hotspots: dashboardData.hotspots,
    runs: dashboardData.runs,
    events: dashboardData.events,
    timeline: dashboardData.timeline,
    anomalies: dashboardData.anomalies,
    isLoading: dashboardData.isLoading,
    reload: dashboardData.reload,
    loadStats: dashboardData.loadStats,
    setStats: dashboardData.setStats,
    setAnomalies: dashboardData.setAnomalies,

    // Heuristics data
    heuristics: heuristicsData.heuristics,
    setHeuristics: heuristicsData.setHeuristics,
    promoteHeuristic: heuristicsData.promoteHeuristic,
    demoteHeuristic: heuristicsData.demoteHeuristic,
    deleteHeuristic: heuristicsData.deleteHeuristic,
    updateHeuristic: heuristicsData.updateHeuristic,
    reloadHeuristics: heuristicsData.reloadHeuristics,
  }

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  )
}

export const useDataContext = () => {
  const context = useContext(DataContext)
  if (!context) {
    throw new Error('useDataContext must be used within DataProvider')
  }
  return context
}
