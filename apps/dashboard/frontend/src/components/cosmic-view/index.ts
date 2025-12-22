// Main exports
export { HotspotVisualization } from './HotspotVisualization'
export { default as HotspotVisualizationDefault } from './HotspotVisualization'

// View components
export { CosmicView } from './CosmicView'
export { ViewToggle } from './ViewToggle'

// Canvas and scene
export { CosmicCanvas } from './CosmicCanvas'
export { CosmicBackground } from './CosmicBackground'
export { CosmicLighting } from './CosmicLighting'
export { CameraController } from './CameraController'

// Celestial bodies
export { Sun } from './Sun'
export { Planet } from './Planet'
export { Moon } from './Moon'
export { SolarSystemGroup } from './SolarSystemGroup'
export { OrbitPath } from './OrbitPath'
export { PlanetRings } from './PlanetRings'

// UI components
export { CosmicLegend } from './CosmicLegend'
export { CosmicFilters } from './CosmicFilters'
export { CosmicDetailPanel } from './CosmicDetailPanel'
export { SystemNavigator } from './SystemNavigator'

// Effects
export { UfoTrails } from './UfoTrails'

// Hooks
export { useCosmicData } from './useCosmicData'

// Types
export type {
  CelestialType,
  Severity,
  CelestialBody,
  SolarSystem,
  CosmicHierarchy,
  CosmicViewProps,
  HotspotVisualizationProps,
  CelestialBodyProps,
  SolarSystemGroupProps,
  CelestialColors,
  BodyPhysicsState,
} from './types'

export {
  EVOLUTION_THRESHOLDS,
  SEVERITY_WEIGHTS,
  SIZE_CONSTRAINTS,
  ORBIT_DISTANCES,
  ORBIT_SPEEDS,
} from './types'
