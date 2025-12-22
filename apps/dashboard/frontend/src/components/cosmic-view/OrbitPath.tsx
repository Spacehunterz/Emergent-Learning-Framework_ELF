import { useMemo } from 'react'
import * as THREE from 'three'

interface OrbitPathProps {
  radius: number
  opacity?: number
  color?: string
  segments?: number
}

export function OrbitPath({
  radius,
  opacity = 0.2,
  color = '#64748b',
  segments = 64,
}: OrbitPathProps) {
  // Create the orbit ring geometry
  const geometry = useMemo(() => {
    const points: THREE.Vector3[] = []

    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      points.push(
        new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius)
      )
    }

    return new THREE.BufferGeometry().setFromPoints(points)
  }, [radius, segments])

  return (
    <line geometry={geometry} rotation={[0, 0, 0]}>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </line>
  )
}

export default OrbitPath
