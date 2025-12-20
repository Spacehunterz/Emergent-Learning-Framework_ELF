import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { CelestialBody, CelestialBodyProps } from './types'

export function Sun({
  body,
  onSelect,
  onHover,
  isSelected,
  isHovered,
}: CelestialBodyProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)

  // Sun colors based on severity/intensity
  const colors = useMemo(() => {
    const intensity = body.glowIntensity
    return {
      core: new THREE.Color().setHSL(0.08, 0.9, 0.5 + intensity * 0.2), // Orange-yellow
      glow: new THREE.Color().setHSL(0.06, 1.0, 0.4 + intensity * 0.3), // Deeper orange
      corona: new THREE.Color().setHSL(0.1, 0.8, 0.6), // Yellow
    }
  }, [body.glowIntensity])

  // Animate the sun's glow
  useFrame((state) => {
    if (!meshRef.current || !glowRef.current) return

    const time = state.clock.elapsedTime

    // Slow pulsing glow effect
    const pulse = 1 + Math.sin(time * 0.2) * 0.03
    glowRef.current.scale.setScalar(body.radius * 1.3 * pulse)

    // Very subtle rotation
    meshRef.current.rotation.y += 0.0005
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
    <group position={[0, 0, 0]}>
      {/* Inner glow layer */}
      <mesh ref={glowRef} scale={body.radius * 1.3}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial
          color={colors.glow}
          transparent
          opacity={0.3 + body.glowIntensity * 0.2}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Main sun sphere */}
      <mesh
        ref={meshRef}
        onClick={handleClick}
        onPointerEnter={handlePointerEnter}
        onPointerLeave={handlePointerLeave}
      >
        <sphereGeometry args={[body.radius, 64, 64]} />
        <meshStandardMaterial
          color={colors.core}
          emissive={colors.core}
          emissiveIntensity={0.8 + body.glowIntensity * 0.4}
          roughness={0.2}
          metalness={0.1}
        />
      </mesh>

      {/* Outer corona (very faint) */}
      <mesh scale={body.radius * 1.8}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial
          color={colors.corona}
          transparent
          opacity={0.1}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Point light emanating from sun */}
      <pointLight
        color={colors.core}
        intensity={body.glowIntensity * 2 + 1}
        distance={50}
        decay={2}
      />

      {/* Selection/hover indicator - FIXED: always render, control visibility */}
      <mesh
        scale={body.radius * 2.2}
        visible={isSelected || isHovered}
      >
        <ringGeometry args={[0.9, 1, 64]} />
        <meshBasicMaterial
          color={isSelected ? '#fbbf24' : '#94a3b8'}
          transparent
          opacity={isSelected || isHovered ? 0.6 : 0}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  )
}

export default Sun
