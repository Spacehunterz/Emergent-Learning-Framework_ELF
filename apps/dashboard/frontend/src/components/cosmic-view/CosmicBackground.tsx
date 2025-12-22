import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const STAR_COUNT = 2000
const STAR_SPREAD = 500

export function CosmicBackground() {
  const pointsRef = useRef<THREE.Points>(null)

  // Generate star positions
  const { positions, colors, sizes } = useMemo(() => {
    const positions = new Float32Array(STAR_COUNT * 3)
    const colors = new Float32Array(STAR_COUNT * 3)
    const sizes = new Float32Array(STAR_COUNT)

    for (let i = 0; i < STAR_COUNT; i++) {
      const i3 = i * 3

      // Distribute stars in a sphere
      const radius = STAR_SPREAD * (0.3 + Math.random() * 0.7)
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)

      positions[i3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i3 + 2] = radius * Math.cos(phi)

      // Vary star colors (white to blue to yellow)
      const colorType = Math.random()
      if (colorType < 0.6) {
        // White/blue stars
        colors[i3] = 0.9 + Math.random() * 0.1
        colors[i3 + 1] = 0.9 + Math.random() * 0.1
        colors[i3 + 2] = 1.0
      } else if (colorType < 0.85) {
        // Yellow/orange stars
        colors[i3] = 1.0
        colors[i3 + 1] = 0.8 + Math.random() * 0.2
        colors[i3 + 2] = 0.6 + Math.random() * 0.2
      } else {
        // Red/pink stars
        colors[i3] = 1.0
        colors[i3 + 1] = 0.5 + Math.random() * 0.3
        colors[i3 + 2] = 0.5 + Math.random() * 0.3
      }

      // Vary star sizes
      sizes[i] = Math.random() * 1.5 + 0.5
    }

    return { positions, colors, sizes }
  }, [])

  // Very subtle rotation for parallax effect
  useFrame((_, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.001
    }
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={STAR_COUNT}
          array={positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={STAR_COUNT}
          array={colors}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-size"
          count={STAR_COUNT}
          array={sizes}
          itemSize={1}
        />
      </bufferGeometry>
      <pointsMaterial
        size={1.5}
        sizeAttenuation
        transparent
        opacity={0.8}
        vertexColors
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}

export default CosmicBackground
