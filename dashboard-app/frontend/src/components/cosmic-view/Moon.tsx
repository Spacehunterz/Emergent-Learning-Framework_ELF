import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { CelestialBodyProps } from './types'
import { OrbitPath } from './OrbitPath'

export function Moon({
  body,
  onSelect,
  onHover,
  isSelected,
  isHovered,
}: CelestialBodyProps) {
  const groupRef = useRef<THREE.Group>(null)
  const meshRef = useRef<THREE.Mesh>(null)
  const angleRef = useRef(body.orbitPhase)

  // Moon color - more muted than planets
  const color = useMemo(() => {
    switch (body.severity) {
      case 'blocker':
        return new THREE.Color('#fca5a5') // Light red
      case 'warning':
        return new THREE.Color('#fdba74') // Light orange
      case 'discovery':
        return new THREE.Color('#86efac') // Light green
      default:
        return new THREE.Color('#94a3b8') // Light gray
    }
  }, [body.severity])

  // Orbital animation - orbitSpeed already calibrated for moons
  useFrame((state, delta) => {
    if (!groupRef.current) return

    // Moon orbits - Kepler speed already applied
    angleRef.current += body.orbitSpeed * delta

    // Calculate position on flat orbital plane (relative to parent planet)
    const x = Math.cos(angleRef.current) * body.orbitRadius
    const z = Math.sin(angleRef.current) * body.orbitRadius

    groupRef.current.position.set(x, 0, z)

    // Slow axial rotation
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.08
    }
  })

  const handleClick = (e: THREE.Event) => {
    e.stopPropagation()
    onSelect?.(body.location)
  }

  const handlePointerEnter = (e: THREE.Event) => {
    e.stopPropagation()
    onHover?.(body.location)
  }

  const handlePointerLeave = () => {
    onHover?.(null)
  }

  return (
    <>
      {/* Moon orbit path (small, around planet) */}
      <OrbitPath radius={body.orbitRadius} opacity={0.1} />

      {/* Moon group */}
      <group ref={groupRef}>
        {/* Subtle glow for recent moons - FIXED: always render, control visibility */}
        <mesh
          scale={body.radius * 1.5}
          visible={body.glowIntensity > 0.5}
          position={[0, 0, 0.005]} // Small z-offset to prevent z-fighting
        >
          <sphereGeometry args={[1, 8, 8]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={body.glowIntensity > 0.5 ? body.glowIntensity * 0.2 : 0}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>

        {/* Main moon sphere */}
        <mesh
          ref={meshRef}
          onClick={handleClick}
          onPointerEnter={handlePointerEnter}
          onPointerLeave={handlePointerLeave}
        >
          <sphereGeometry args={[body.radius, 16, 16]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={body.glowIntensity * 0.2}
            roughness={0.7}
            metalness={0.1}
          />
        </mesh>

        {/* Selection/hover indicator - FIXED: always render, control visibility */}
        <mesh
          scale={body.radius * 2}
          rotation={[Math.PI / 2, 0, 0]}
          visible={isSelected || isHovered}
        >
          <ringGeometry args={[0.8, 1, 32]} />
          <meshBasicMaterial
            color={isSelected ? '#fbbf24' : '#94a3b8'}
            transparent
            opacity={isSelected || isHovered ? 0.5 : 0}
            side={THREE.DoubleSide}
          />
        </mesh>
      </group>
    </>
  )
}

export default Moon
