import { create } from 'zustand'
import { subscribeWithSelector, persist } from 'zustand/middleware'

export type ViewMode = 'cosmic' | 'grid'
export type Severity = 'blocker' | 'warning' | 'discovery'

export interface CosmicState {
  // View state
  viewMode: ViewMode

  // Camera state
  cameraTarget: [number, number, number]
  cameraDistance: number
  autoRotate: boolean

  // Selection state
  selectedBody: string | null // hotspot location
  hoveredBody: string | null
  focusedSystem: string | null // directory path

  // Filter state
  severityFilter: Severity[]
  directoryFilter: string | null
  timeRangeFilter: 'all' | '24h' | '7d' | '30d'

  // Physics config
  orbitSpeedMultiplier: number
  glowIntensity: number
}

export interface CosmicActions {
  // View actions
  setViewMode: (mode: ViewMode) => void
  toggleViewMode: () => void

  // Camera actions
  setCameraTarget: (target: [number, number, number]) => void
  setCameraDistance: (distance: number) => void
  setAutoRotate: (enabled: boolean) => void
  resetCamera: () => void

  // Selection actions
  selectBody: (location: string | null) => void
  hoverBody: (location: string | null) => void
  focusSystem: (directory: string | null) => void
  clearSelection: () => void

  // Filter actions
  setSeverityFilter: (severities: Severity[]) => void
  toggleSeverity: (severity: Severity) => void
  setDirectoryFilter: (dir: string | null) => void
  setTimeRangeFilter: (range: 'all' | '24h' | '7d' | '30d') => void
  resetFilters: () => void

  // Physics config
  setOrbitSpeedMultiplier: (multiplier: number) => void
  setGlowIntensity: (intensity: number) => void
}

const initialState: CosmicState = {
  viewMode: 'cosmic',
  cameraTarget: [0, 0, 0],
  cameraDistance: 50,
  autoRotate: true,
  selectedBody: null,
  hoveredBody: null,
  focusedSystem: null,
  severityFilter: ['blocker', 'warning', 'discovery'],
  directoryFilter: null,
  timeRangeFilter: 'all',
  orbitSpeedMultiplier: 1,
  glowIntensity: 1,
}

export const useCosmicStore = create<CosmicState & CosmicActions>()(
  persist(
    subscribeWithSelector((set, get) => ({
      ...initialState,

      // View actions
      setViewMode: (mode) => set({ viewMode: mode }),
    toggleViewMode: () =>
      set((state) => ({
        viewMode: state.viewMode === 'cosmic' ? 'grid' : 'cosmic',
      })),

    // Camera actions
    setCameraTarget: (target) => set({ cameraTarget: target }),
    setCameraDistance: (distance) => set({ cameraDistance: distance }),
    setAutoRotate: (enabled) => set({ autoRotate: enabled }),
    resetCamera: () =>
      set({
        cameraTarget: [0, 0, 0],
        cameraDistance: 50,
        autoRotate: true,
      }),

    // Selection actions
    selectBody: (location) => set({ selectedBody: location }),
    hoverBody: (location) => set({ hoveredBody: location }),
    focusSystem: (directory) => {
      set({ focusedSystem: directory })
      // When focusing a system, also update camera target
      // (actual position calculation happens in the 3D components)
    },
    clearSelection: () =>
      set({
        selectedBody: null,
        hoveredBody: null,
        focusedSystem: null,
      }),

    // Filter actions
    setSeverityFilter: (severities) => set({ severityFilter: severities }),
    toggleSeverity: (severity) =>
      set((state) => {
        const current = state.severityFilter
        if (current.includes(severity)) {
          // Don't allow removing all severities
          if (current.length === 1) return state
          return { severityFilter: current.filter((s) => s !== severity) }
        }
        return { severityFilter: [...current, severity] }
      }),
    setDirectoryFilter: (dir) => set({ directoryFilter: dir }),
    setTimeRangeFilter: (range) => set({ timeRangeFilter: range }),
    resetFilters: () =>
      set({
        severityFilter: ['blocker', 'warning', 'discovery'],
        directoryFilter: null,
        timeRangeFilter: 'all',
      }),

    // Physics config
    setOrbitSpeedMultiplier: (multiplier) =>
      set({ orbitSpeedMultiplier: multiplier }),
    setGlowIntensity: (intensity) => set({ glowIntensity: intensity }),
  })),
  {
    name: 'cosmic-store',
    partialize: (state) => ({
      viewMode: state.viewMode,
      autoRotate: state.autoRotate,
      orbitSpeedMultiplier: state.orbitSpeedMultiplier,
      glowIntensity: state.glowIntensity,
    }),
  }
  )
)

// Selector hooks for optimized subscriptions
export const useViewMode = () => useCosmicStore((s) => s.viewMode)
export const useSelectedBody = () => useCosmicStore((s) => s.selectedBody)
export const useHoveredBody = () => useCosmicStore((s) => s.hoveredBody)
export const useSeverityFilter = () => useCosmicStore((s) => s.severityFilter)

// Vanilla store access for use in R3F useFrame (outside React)
export const cosmicStore = useCosmicStore
