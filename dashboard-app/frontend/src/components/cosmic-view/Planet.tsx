import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { CelestialBodyProps } from './types'
import { Moon } from './Moon'
import { OrbitPath } from './OrbitPath'
import { PlanetRings } from './PlanetRings'

export function Planet({
  body,
  onSelect,
  onHover,
  isSelected,
  isHovered,
  moons = [],
}: CelestialBodyProps & { moons?: typeof body[] }) {
  const groupRef = useRef<THREE.Group>(null)
  const meshRef = useRef<THREE.Mesh>(null)
  const angleRef = useRef(body.orbitPhase)

  // Planet color based on severity
  const color = useMemo(() => {
    switch (body.severity) {
      case 'blocker':
        return new THREE.Color('#ef4444') // Red
      case 'warning':
        return new THREE.Color('#f97316') // Orange
      case 'discovery':
        return new THREE.Color('#22c55e') // Green
      default:
        return new THREE.Color('#64748b') // Gray
    }
  }, [body.severity])

  // Glow color (slightly lighter)
  const glowColor = useMemo(() => {
    return color.clone().offsetHSL(0, -0.1, 0.2)
  }, [color])

  // Orbital animation - using refs to avoid React state updates
  useFrame((state, delta) => {
    if (!groupRef.current) return

    // Update orbital angle - Kepler speed already applied
    angleRef.current += body.orbitSpeed * delta

    // Calculate position on flat orbital plane
    const x = Math.cos(angleRef.current) * body.orbitRadius
    const z = Math.sin(angleRef.current) * body.orbitRadius

    groupRef.current.position.set(x, 0, z)

    // Slow axial rotation
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.1
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
      {/* Orbit path */}
      <OrbitPath radius={body.orbitRadius} opacity={0.15} />

      {/* Planet group (moves along orbit) */}
      <group ref={groupRef}>
        {/* Glow effect - FIXED: always render, control visibility to prevent remounts */}
        <mesh
          scale={body.radius * 1.4}
          visible={body.glowIntensity > 0.3}
          position={[0, 0, 0.01]} // FIXED: small z-offset to prevent z-fighting
        >
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial
            color={glowColor}
            transparent
            opacity={body.glowIntensity > 0.3 ? body.glowIntensity * 0.3 : 0}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>

        {/* Main planet sphere */}
        <mesh
          ref={meshRef}
          onClick={handleClick}
          onPointerEnter={handlePointerEnter}
          onPointerLeave={handlePointerLeave}
        >
          <sphereGeometry args={[body.radius, 32, 32]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={body.glowIntensity * 0.3}
            roughness={0.6}
            metalness={0.2}
          />
        </mesh>

        {/* Rings for heuristic categories */}
        {body.heuristicCategories.length > 0 && (
          <PlanetRings
            categories={body.heuristicCategories}
            planetRadius={body.radius}
          />
        )}

        {/* Selection/hover indicator - FIXED: always render, control visibility */}
        <mesh
          scale={body.radius * 1.8}
          rotation={[Math.PI / 2, 0, 0]}
          visible={isSelected || isHovered}
        >
          <ringGeometry args={[0.85, 1, 64]} />
          <meshBasicMaterial
            color={isSelected ? '#fbbf24' : '#94a3b8'}
            transparent
            opacity={isSelected || isHovered ? 0.6 : 0}
            side={THREE.DoubleSide}
          />
        </mesh>

        {/* Render moons orbiting this planet */}
        {moons.map((moon) => (
          <Moon
            key={moon.id}
            body={moon}
            onSelect={onSelect}
            onHover={onHover}
            isSelected={isSelected}
            isHovered={isHovered}
          />
        ))}
      </group>
    </>
  )
}

export default Planet
