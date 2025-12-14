import { useRef } from 'react'
import * as THREE from 'three'

export function CosmicLighting() {
  const ambientRef = useRef<THREE.AmbientLight>(null)
  const directionalRef = useRef<THREE.DirectionalLight>(null)

  return (
    <>
      {/* Ambient light for base visibility */}
      <ambientLight ref={ambientRef} intensity={0.15} color="#4a5568" />

      {/* Main directional light (simulates distant star) */}
      <directionalLight
        ref={directionalRef}
        position={[50, 50, 25]}
        intensity={0.6}
        color="#fef3c7"
        castShadow={false}
      />

      {/* Secondary fill light from opposite direction */}
      <directionalLight
        position={[-30, -20, -30]}
        intensity={0.2}
        color="#93c5fd"
      />

      {/* Subtle rim light for depth */}
      <pointLight position={[0, 100, 0]} intensity={0.1} color="#f472b6" />
    </>
  )
}

export default CosmicLighting
