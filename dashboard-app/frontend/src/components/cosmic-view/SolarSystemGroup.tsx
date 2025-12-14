import { useMemo } from 'react'
import { Html } from '@react-three/drei'
import type { SolarSystemGroupProps } from './types'
import { Sun } from './Sun'
import { Planet } from './Planet'

export function SolarSystemGroup({
  system,
  onSelectBody,
  onHoverBody,
  selectedBody,
  hoveredBody,
}: SolarSystemGroupProps) {
  // Group moons by their parent planet
  const moonsByPlanet = useMemo(() => {
    const map = new Map<string, typeof system.moons>()

    system.moons.forEach((moon) => {
      if (moon.parentBody) {
        const existing = map.get(moon.parentBody) || []
        existing.push(moon)
        map.set(moon.parentBody, existing)
      }
    })

    return map
  }, [system.moons])

  // Check if any body in this system is selected/hovered
  const hasSelectedBody = system.allBodies.some((b) => b.id === selectedBody)
  const hasHoveredBody = system.allBodies.some((b) => b.id === hoveredBody)

  return (
    <group position={system.position}>
      {/* System label (only visible when hovering/selected) */}
      {(hasSelectedBody || hasHoveredBody) && (
        <Html
          position={[0, system.sun ? system.sun.radius + 3 : 5, 0]}
          center
          distanceFactor={15}
          style={{
            pointerEvents: 'none',
            userSelect: 'none',
          }}
        >
          <div className="whitespace-nowrap rounded bg-slate-900/80 px-2 py-1 text-xs text-slate-300 backdrop-blur-sm">
            {system.name}
          </div>
        </Html>
      )}

      {/* Sun at center */}
      {system.sun && (
        <Sun
          body={system.sun}
          onSelect={onSelectBody}
          onHover={onHoverBody}
          isSelected={selectedBody === system.sun.id}
          isHovered={hoveredBody === system.sun.id}
        />
      )}

      {/* Planets orbiting sun */}
      {system.planets.map((planet) => (
        <Planet
          key={planet.id}
          body={planet}
          onSelect={onSelectBody}
          onHover={onHoverBody}
          isSelected={selectedBody === planet.id}
          isHovered={hoveredBody === planet.id}
          moons={moonsByPlanet.get(planet.id) || []}
        />
      ))}

      {/* Orphan moons (no parent planet) orbit the sun directly */}
      {system.moons
        .filter(
          (moon) =>
            !moon.parentBody ||
            !system.planets.some((p) => p.id === moon.parentBody)
        )
        .map((moon) => (
          <Planet
            key={moon.id}
            body={{ ...moon, type: 'planet' as const }}
            onSelect={onSelectBody}
            onHover={onHoverBody}
            isSelected={selectedBody === moon.id}
            isHovered={hoveredBody === moon.id}
            moons={[]}
          />
        ))}
    </group>
  )
}

export default SolarSystemGroup
