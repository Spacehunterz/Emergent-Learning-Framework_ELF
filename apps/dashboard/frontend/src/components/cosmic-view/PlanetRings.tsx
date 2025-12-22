import { useMemo } from 'react'
import * as THREE from 'three'

interface PlanetRingsProps {
  categories: string[]
  planetRadius: number
}

// Color palette for ring categories
const RING_COLORS = [
  '#f472b6', // Pink
  '#818cf8', // Indigo
  '#34d399', // Emerald
  '#fbbf24', // Amber
  '#f87171', // Red
  '#60a5fa', // Blue
  '#a78bfa', // Purple
  '#fb923c', // Orange
]

export function PlanetRings({ categories, planetRadius }: PlanetRingsProps) {
  const rings = useMemo(() => {
    if (categories.length === 0) return []

    return categories.slice(0, 4).map((category, index) => {
      const innerRadius = planetRadius * (1.4 + index * 0.3)
      const outerRadius = innerRadius + planetRadius * 0.15
      const color = RING_COLORS[index % RING_COLORS.length]
      const tiltAngle = (index * 0.1 - 0.15) * Math.PI

      return {
        key: category,
        innerRadius,
        outerRadius,
        color,
        tiltAngle,
        opacity: 0.4 - index * 0.08,
      }
    })
  }, [categories, planetRadius])

  if (rings.length === 0) return null

  return (
    <group>
      {rings.map((ring) => (
        <mesh key={ring.key} rotation={[Math.PI / 2 + ring.tiltAngle, 0, 0]}>
          <ringGeometry args={[ring.innerRadius, ring.outerRadius, 64]} />
          <meshBasicMaterial
            color={ring.color}
            transparent
            opacity={ring.opacity}
            side={THREE.DoubleSide}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  )
}

export default PlanetRings
