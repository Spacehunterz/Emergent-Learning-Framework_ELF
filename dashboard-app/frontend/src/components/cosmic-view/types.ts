import type { ApiHotspot } from '../hotspot-treemap/types'

// Celestial body types based on severity
export type CelestialType = 'sun' | 'planet' | 'moon'

// Severity levels from hotspot scents
export type Severity = 'blocker' | 'warning' | 'discovery' | 'low'

// Thresholds for evolution (Moon -> Planet -> Sun)
export const EVOLUTION_THRESHOLDS = {
  SUN: 50, // Weighted score above this becomes a sun
  PLANET: 20, // Weighted score above this becomes a planet
} as const

// Severity weights for score calculation
export const SEVERITY_WEIGHTS: Record<Severity, number> = {
  blocker: 3.0,
  warning: 2.0,
  discovery: 1.0,
  low: 0.5,
}

// Visual size constraints - larger for easy clicking
export const SIZE_CONSTRAINTS = {
  SUN_MIN: 5.0,
  SUN_MAX: 10.0,
  PLANET_MIN: 2.5,
  PLANET_MAX: 5.0,
  MOON_MIN: 1.0,
  MOON_MAX: 2.0,
} as const

// Orbit distance ranges - scaled for larger bodies
export const ORBIT_DISTANCES = {
  PLANET_MIN: 25,      // Start further from sun
  PLANET_MAX: 100,     // Max orbit distance
  PLANET_SPACING: 20,  // More space for larger planets
  MOON_MIN: 6,         // Moons further from planets
  MOON_MAX: 12,
} as const

// Orbit speed multipliers - Kepler-style (further = slower)
export const ORBIT_SPEEDS = {
  PLANET_BASE: 0.15,   // Base speed (will be divided by sqrt of distance)
  MOON_BASE: 0.3,      // Moons orbit faster
} as const

// Golden angle for even distribution (137.5 degrees in radians)
export const GOLDEN_ANGLE = 2.39996322972865332

/**
 * A celestial body representing a hotspot in the cosmic visualization.
 * The type (sun/planet/moon) is determined by severity and accumulated score.
 */
export interface CelestialBody {
  // Identity
  id: string // Unique identifier (based on location)
  location: string // File path (from hotspot)
  name: string // Display name (filename)

  // Celestial classification
  type: CelestialType // sun/planet/moon
  severity: Severity // Primary severity from scents

  // Metrics (drive visual properties)
  trailCount: number // From hotspot.trail_count
  totalStrength: number // From hotspot.total_strength
  weightedScore: number // Combined weighted score
  recency: number // 0-1, how recent (drives glow)
  volatility: number // 0-1, change rate (drives orbit speed)

  // Relationships
  directory: string // Parent directory (solar system ID)
  parentBody: string | null // For moons: planet location; for planets: sun location
  childLocations: string[] // Locations of orbiting bodies

  // Calculated visual properties
  radius: number // Calculated from weightedScore
  glowIntensity: number // Calculated from recency
  orbitRadius: number // Distance from parent body
  orbitSpeed: number // Calculated from volatility
  orbitPhase: number // Starting angle in orbit (0-2PI)

  // Heuristic data (for rings)
  heuristicCategories: string[] // Distinct categories for rings

  // Agent data
  agents: string[] // Agent IDs that touched this hotspot
  agentCount: number

  // Original data reference
  hotspot: ApiHotspot
}

/**
 * A solar system represents a directory containing related hotspots.
 * Each system has at most one sun (highest severity blocker) at its center.
 */
export interface SolarSystem {
  id: string // Directory path
  name: string // Directory display name
  directory: string // Full directory path

  // Position in 3D space
  position: [number, number, number]

  // Celestial bodies
  sun: CelestialBody | null // Central blocker (if any)
  planets: CelestialBody[] // Warning-level bodies orbiting sun
  moons: CelestialBody[] // Discovery-level bodies orbiting planets
  allBodies: CelestialBody[] // All bodies in this system

  // Aggregate metrics
  totalTrails: number
  totalStrength: number
  maxSeverity: Severity
  bodyCount: number
}

/**
 * The complete cosmic hierarchy transformed from hotspot data.
 */
export interface CosmicHierarchy {
  systems: SolarSystem[]
  totalBodies: number
  directories: string[]
  maxSystemSize: number // For normalization
}

/**
 * Props for the main cosmic view component.
 */
export interface CosmicViewProps {
  hotspots: ApiHotspot[]
  onSelect: (path: string, line?: number) => void
  onOpenInEditor?: (path: string, line?: number) => void
  selectedDomain: string | null
  onDomainFilter: (domain: string | null) => void
}

/**
 * Props for the container that switches between cosmic and grid views.
 */
export interface HotspotVisualizationProps {
  hotspots: ApiHotspot[]
  onSelect: (path: string, line?: number) => void
  onOpenInEditor?: (path: string, line?: number) => void
  selectedDomain: string | null
  onDomainFilter: (domain: string | null) => void
}

/**
 * Props for individual celestial body components.
 */
export interface CelestialBodyProps {
  body: CelestialBody
  onSelect?: (location: string) => void
  onHover?: (location: string | null) => void
  isSelected?: boolean
  isHovered?: boolean
}

/**
 * Props for the solar system group component.
 */
export interface SolarSystemGroupProps {
  system: SolarSystem
  onSelectBody?: (location: string) => void
  onHoverBody?: (location: string | null) => void
  selectedBody?: string | null
  hoveredBody?: string | null
}

/**
 * Color scheme for celestial bodies based on theme.
 */
export interface CelestialColors {
  sunCore: string
  sunGlow: string
  planetBlocker: string
  planetWarning: string
  planetDiscovery: string
  planetLow: string
  moonSurface: string
  orbitPath: string
  ring: string
  background: string
}

/**
 * Physics state for a celestial body (updated via refs, not React state).
 */
export interface BodyPhysicsState {
  angle: number // Current orbital angle
  position: [number, number, number] // Current position
  velocity: [number, number, number] // Current velocity (for perturbations)
}
