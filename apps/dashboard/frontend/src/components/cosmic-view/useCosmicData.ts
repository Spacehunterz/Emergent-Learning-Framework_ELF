import { useMemo } from 'react'
import type { ApiHotspot } from '../hotspot-treemap/types'
import type {
  CelestialBody,
  CelestialType,
  CosmicHierarchy,
  Severity,
  SolarSystem,
} from './types'
import {
  EVOLUTION_THRESHOLDS,
  GOLDEN_ANGLE,
  ORBIT_DISTANCES,
  ORBIT_SPEEDS,
  SEVERITY_WEIGHTS,
  SIZE_CONSTRAINTS,
} from './types'

/**
 * Extract severity from hotspot scents array.
 */
function getSeverity(scents: string[] | undefined): Severity {
  if (!scents || scents.length === 0) return 'low'
  if (scents.includes('blocker')) return 'blocker'
  if (scents.includes('warning')) return 'warning'
  if (scents.includes('discovery')) return 'discovery'
  return 'low'
}

/**
 * Calculate weighted score from hotspot metrics.
 * This drives both celestial type evolution and visual size.
 */
function calculateWeightedScore(hotspot: ApiHotspot): number {
  const severity = getSeverity(hotspot.scents)
  const severityWeight = SEVERITY_WEIGHTS[severity]

  return (
    hotspot.trail_count * 0.4 +
    hotspot.total_strength * 0.3 +
    severityWeight * 10 * 0.3
  )
}

/**
 * Determine celestial type based on severity and accumulated score.
 * Bodies can evolve: Moon -> Planet -> Sun as score increases.
 */
function determineCelestialType(
  hotspot: ApiHotspot,
  weightedScore: number
): CelestialType {
  const scents = hotspot.scents || []

  // Explicit blocker always becomes sun
  if (scents.includes('blocker')) return 'sun'

  // Score-based promotion (evolution)
  if (weightedScore > EVOLUTION_THRESHOLDS.SUN) return 'sun'
  if (weightedScore > EVOLUTION_THRESHOLDS.PLANET) return 'planet'

  // Warning severity defaults to planet
  if (scents.includes('warning')) return 'planet'

  // Everything else is a moon
  return 'moon'
}

/**
 * Calculate recency score (0-1) from last_activity timestamp.
 * More recent = higher score = more glow.
 */
function calculateRecency(lastActivity: string): number {
  const now = Date.now()
  const activityTime = new Date(lastActivity).getTime()
  const hoursSinceActivity = (now - activityTime) / (1000 * 60 * 60)

  // Decay over 7 days (168 hours)
  const maxHours = 168
  const recency = Math.max(0, 1 - hoursSinceActivity / maxHours)
  return recency
}

/**
 * Calculate volatility (0-1) from activity frequency.
 * Higher trail count in shorter time = more volatile = faster orbit.
 */
function calculateVolatility(hotspot: ApiHotspot): number {
  const firstTime = new Date(hotspot.first_activity).getTime()
  const lastTime = new Date(hotspot.last_activity).getTime()
  const durationHours = Math.max(1, (lastTime - firstTime) / (1000 * 60 * 60))

  // Trails per hour, capped at 1.0
  const trailsPerHour = hotspot.trail_count / durationHours
  return Math.min(1, trailsPerHour / 5) // 5+ trails/hour = max volatility
}

/**
 * Calculate visual radius based on celestial type and weighted score.
 */
function calculateRadius(type: CelestialType, weightedScore: number): number {


  const min =
    type === 'sun'
      ? SIZE_CONSTRAINTS.SUN_MIN
      : type === 'planet'
        ? SIZE_CONSTRAINTS.PLANET_MIN
        : SIZE_CONSTRAINTS.MOON_MIN

  const max =
    type === 'sun'
      ? SIZE_CONSTRAINTS.SUN_MAX
      : type === 'planet'
        ? SIZE_CONSTRAINTS.PLANET_MAX
        : SIZE_CONSTRAINTS.MOON_MAX

  // Log scale for more natural distribution
  const normalizedScore = Math.log(weightedScore + 1) / Math.log(100)
  const clampedScore = Math.min(1, Math.max(0, normalizedScore))

  return min + (max - min) * clampedScore
}

/**
 * Extract directory path from file location.
 */
function getDirectory(location: string): string {
  const parts = location.split(/[\/\\]/)
  parts.pop() // Remove filename
  return parts.join('/') || 'root'
}

/**
 * Extract filename from file location.
 */
function getFilename(location: string): string {
  const parts = location.split(/[\/\\]/)
  return parts[parts.length - 1] || location
}

/**
 * FIXED: Generate stable orbit phase from location string hash.
 * This prevents planets from jumping to new positions when data changes.
 */
function hashStringToAngle(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32bit integer
  }
  // Normalize to 0-2PI range
  return (Math.abs(hash) % 1000) / 1000 * Math.PI * 2
}

/**
 * Extract unique heuristic categories from related_heuristics.
 */
function extractHeuristicCategories(
  relatedHeuristics: any[] | undefined
): string[] {
  if (!relatedHeuristics || !Array.isArray(relatedHeuristics)) return []

  const categories = new Set<string>()
  relatedHeuristics.forEach((h) => {
    if (h.domain) categories.add(h.domain)
    if (h.category) categories.add(h.category)
  })

  return Array.from(categories)
}

/**
 * Transform a single hotspot into a CelestialBody.
 */
function transformHotspotToBody(hotspot: ApiHotspot): CelestialBody {
  const weightedScore = calculateWeightedScore(hotspot)
  const type = determineCelestialType(hotspot, weightedScore)
  const severity = getSeverity(hotspot.scents)

  return {
    id: hotspot.location,
    location: hotspot.location,
    name: getFilename(hotspot.location),
    type,
    severity,
    trailCount: hotspot.trail_count,
    totalStrength: hotspot.total_strength,
    weightedScore,
    recency: calculateRecency(hotspot.last_activity),
    volatility: calculateVolatility(hotspot),
    directory: getDirectory(hotspot.location),
    parentBody: null, // Set later during hierarchy building
    childLocations: [],
    radius: calculateRadius(type, weightedScore),
    glowIntensity: calculateRecency(hotspot.last_activity),
    orbitRadius: 0, // Set later during hierarchy building
    orbitSpeed: ORBIT_SPEEDS.PLANET_BASE + calculateVolatility(hotspot) * 0.1, // Slow base + volatility
    orbitPhase: hashStringToAngle(hotspot.location), // FIXED: stable phase from location hash
    heuristicCategories: extractHeuristicCategories(hotspot.related_heuristics),
    agents: hotspot.agents || [],
    agentCount: hotspot.agent_count || 0,
    hotspot,
  }
}

/**
 * Group bodies by directory and build solar system hierarchy.
 */
function buildSolarSystems(bodies: CelestialBody[]): SolarSystem[] {
  // Group by directory
  const byDirectory = new Map<string, CelestialBody[]>()

  bodies.forEach((body) => {
    const existing = byDirectory.get(body.directory) || []
    existing.push(body)
    byDirectory.set(body.directory, existing)
  })

  // Build solar systems
  const systems: SolarSystem[] = []
  let systemIndex = 0

  byDirectory.forEach((dirBodies, directory) => {
    // Sort by weighted score descending
    const sorted = [...dirBodies].sort(
      (a, b) => b.weightedScore - a.weightedScore
    )

    // Find suns (blockers or high score)
    const suns = sorted.filter((b) => b.type === 'sun')
    const planets = sorted.filter((b) => b.type === 'planet')
    const moons = sorted.filter((b) => b.type === 'moon')

    // The primary sun is the highest scoring one
    const primarySun = suns[0] || null

    // Additional suns become very large planets
    const extraSuns = suns.slice(1)
    extraSuns.forEach((s) => {
      s.type = 'planet' // Demote to planet
      planets.unshift(s) // Add to front of planets
    })

    // Assign orbit radii to planets with golden angle distribution
    planets.forEach((planet, idx) => {
      const minDist = ORBIT_DISTANCES.PLANET_MIN
      const spacing = ORBIT_DISTANCES.PLANET_SPACING
      // Each planet gets its own orbit lane
      planet.orbitRadius = minDist + (spacing * (idx + 1))
      planet.parentBody = primarySun?.location || null

      // Golden angle ensures even distribution around the sun
      planet.orbitPhase = idx * GOLDEN_ANGLE

      // Kepler-style: further planets orbit slower (inverse sqrt of distance)
      planet.orbitSpeed = ORBIT_SPEEDS.PLANET_BASE / Math.sqrt(planet.orbitRadius / minDist)
    })

    // Assign moons to planets (distribute evenly)
    moons.forEach((moon, idx) => {
      const parentPlanet = planets[idx % Math.max(1, planets.length)]
      if (parentPlanet) {
        moon.parentBody = parentPlanet.location
        parentPlanet.childLocations.push(moon.location)

        // Orbit around parent planet with spacing
        const moonIdx = parentPlanet.childLocations.length - 1
        const minMoonDist = ORBIT_DISTANCES.MOON_MIN
        moon.orbitRadius = minMoonDist + (moonIdx * 2)

        // Golden angle for moon distribution too
        moon.orbitPhase = moonIdx * GOLDEN_ANGLE

        // Moons orbit faster, Kepler-style
        moon.orbitSpeed = ORBIT_SPEEDS.MOON_BASE / Math.sqrt(moon.orbitRadius / minMoonDist)
      } else if (primarySun) {
        // No planets, orbit sun directly as distant body
        moon.parentBody = primarySun.location
        moon.orbitRadius = ORBIT_DISTANCES.PLANET_MIN + (idx * ORBIT_DISTANCES.PLANET_SPACING)
        moon.orbitPhase = idx * GOLDEN_ANGLE
        moon.orbitSpeed = ORBIT_SPEEDS.PLANET_BASE / Math.sqrt(moon.orbitRadius / ORBIT_DISTANCES.PLANET_MIN)
      }
    })

    // Calculate system position - first system at center, others in ring
    let position: [number, number, number]
    if (systemIndex === 0) {
      // Most active system at the center
      position = [0, 0, 0]
    } else {
      // Other systems arranged in a ring around center
      const ringAngle = ((systemIndex - 1) / Math.max(1, byDirectory.size - 1)) * Math.PI * 2
      const ringRadius = 150 + Math.floor((systemIndex - 1) / 6) * 100 // Expand rings as needed
      position = [
        Math.cos(ringAngle) * ringRadius,
        0, // All on same plane
        Math.sin(ringAngle) * ringRadius,
      ]
    }

    // Aggregate metrics
    const allBodies = [
      ...(primarySun ? [primarySun] : []),
      ...planets,
      ...moons,
    ]
    const totalTrails = allBodies.reduce((sum, b) => sum + b.trailCount, 0)
    const totalStrength = allBodies.reduce((sum, b) => sum + b.totalStrength, 0)

    // Determine max severity
    let maxSeverity: Severity = 'low'
    if (suns.length > 0 || allBodies.some((b) => b.severity === 'blocker')) {
      maxSeverity = 'blocker'
    } else if (allBodies.some((b) => b.severity === 'warning')) {
      maxSeverity = 'warning'
    } else if (allBodies.some((b) => b.severity === 'discovery')) {
      maxSeverity = 'discovery'
    }

    systems.push({
      id: directory,
      name: directory.split('/').pop() || directory,
      directory,
      position,
      sun: primarySun,
      planets,
      moons,
      allBodies,
      totalTrails,
      totalStrength,
      maxSeverity,
      bodyCount: allBodies.length,
    })

    systemIndex++
  })

  return systems
}

/**
 * Hook to transform hotspot data into cosmic hierarchy.
 */
export function useCosmicData(
  hotspots: ApiHotspot[],
  selectedDomain: string | null
): CosmicHierarchy {
  return useMemo(() => {
    if (!hotspots || !Array.isArray(hotspots) || hotspots.length === 0) {
      return {
        systems: [],
        totalBodies: 0,
        directories: [],
        maxSystemSize: 0,
      }
    }

    // Domain to Scent mapping for looser filtering
    const DOMAIN_SCENT_MAPPING: Record<string, string[]> = {
      'System Core': ['system', 'core', 'security', 'backend', 'api', 'performance', 'blocker'],
      'Agents': ['agent', 'agents', 'model', 'llm', 'ai'],
      'Knowledge': ['knowledge', 'data', 'database', 'store', 'memory', 'rag'],
      'User Ops': ['user', 'ui', 'frontend', 'interface', 'ux', 'interaction'],
    }

    // Filter by domain/scent if specified
    // Removed nested useMemo to fix "Rendered more hooks than during the previous render" error
    let filtered = hotspots
    if (selectedDomain) {
      const mappedScents = DOMAIN_SCENT_MAPPING[selectedDomain]

      filtered = hotspots.filter((h) => {
        // Direct match
        if (h.scents?.includes(selectedDomain)) return true

        // Case-insensitive match
        if (h.scents?.some(s => s.toLowerCase() === selectedDomain.toLowerCase())) return true

        // Mapped match
        if (mappedScents && h.scents?.some(s => mappedScents.includes(s.toLowerCase()))) return true

        return false
      })
    }

    // Transform hotspots to celestial bodies
    const bodies = filtered.map(transformHotspotToBody)

    // Build solar systems
    const systems = buildSolarSystems(bodies)

    // Collect all directories
    const directories = systems.map((s) => s.directory)

    // Find max system size for normalization
    const maxSystemSize = Math.max(...systems.map((s) => s.bodyCount), 1)

    return {
      systems,
      totalBodies: bodies.length,
      directories,
      maxSystemSize,
    }
  }, [hotspots, selectedDomain])
}

export default useCosmicData
