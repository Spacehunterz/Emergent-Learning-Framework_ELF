import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { SolarSystem } from './types'

interface UfoTrailsProps {
  systems: SolarSystem[]
}

const UFO_COUNT = 8 // Number of UFOs flying around
const UFO_SPEED = 0.3 // Speed of movement
const TRAIL_LENGTH = 15 // Number of trail points

interface Ufo {
  position: THREE.Vector3
  target: THREE.Vector3
  velocity: THREE.Vector3
  trail: THREE.Vector3[]
  systemIndex: number
  targetBodyIndex: number
  progress: number
}

export function UfoTrails({ systems }: UfoTrailsProps) {
  const groupRef = useRef<THREE.Group>(null)
  const ufosRef = useRef<Ufo[]>([])
  const trailGeometriesRef = useRef<THREE.BufferGeometry[]>([])

  // Get all body positions from systems
  const bodyPositions = useMemo(() => {
    const positions: { pos: THREE.Vector3; systemIdx: number }[] = []

    // Null check for empty systems
    if (!systems || systems.length === 0) {
      console.warn('[UfoTrails] No systems provided')
      return positions
    }

    systems.forEach((system, sysIdx) => {
      // Add system center (sun position)
      positions.push({
        pos: new THREE.Vector3(...system.position),
        systemIdx: sysIdx
      })

      // Add estimated planet positions (they orbit, so we use base position)
      system.planets?.forEach((planet) => {
        const planetPos = new THREE.Vector3(
          system.position[0] + planet.orbitRadius,
          system.position[1],
          system.position[2]
        )
        positions.push({ pos: planetPos, systemIdx: sysIdx })
      })
    })

    console.log(`[UfoTrails] Found ${positions.length} body positions`)
    return positions
  }, [systems])

  // Initialize UFOs when body positions are available
  useEffect(() => {
    // Clear existing UFOs and geometries on reset
    if (ufosRef.current.length > 0) {
      console.log('[UfoTrails] Clearing existing UFOs')
      ufosRef.current = []

      // Dispose old geometries to prevent memory leaks
      trailGeometriesRef.current.forEach((geom) => {
        geom.dispose()
      })
      trailGeometriesRef.current = []
    }

    // Need at least 2 positions to create meaningful paths
    if (bodyPositions.length < 2) {
      console.warn('[UfoTrails] Not enough body positions to create UFO paths')
      return
    }

    console.log('[UfoTrails] Initializing UFOs')
    const ufoCount = Math.min(UFO_COUNT, bodyPositions.length)

    for (let i = 0; i < ufoCount; i++) {
      const startIdx = i % bodyPositions.length
      const targetIdx = (i + 1) % bodyPositions.length

      const startPos = bodyPositions[startIdx].pos.clone()
      const targetPos = bodyPositions[targetIdx].pos.clone()

      ufosRef.current.push({
        position: startPos.clone(),
        target: targetPos.clone(),
        velocity: new THREE.Vector3(),
        trail: Array(TRAIL_LENGTH).fill(null).map(() => startPos.clone()),
        systemIndex: startIdx,
        targetBodyIndex: targetIdx,
        progress: 0,
      })

      // Create geometry for this UFO's trail
      const geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(TRAIL_LENGTH * 3)

      // Initialize with starting position
      for (let j = 0; j < TRAIL_LENGTH; j++) {
        positions[j * 3] = startPos.x
        positions[j * 3 + 1] = startPos.y
        positions[j * 3 + 2] = startPos.z
      }

      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      trailGeometriesRef.current.push(geometry)
    }

    console.log(`[UfoTrails] Initialized ${ufosRef.current.length} UFOs`)

    // Cleanup on unmount
    return () => {
      console.log('[UfoTrails] Cleaning up geometries')
      trailGeometriesRef.current.forEach((geom) => {
        geom.dispose()
      })
      trailGeometriesRef.current = []
    }
  }, [bodyPositions])

  // Animate UFOs
  useFrame((state, delta) => {
    if (bodyPositions.length < 2 || ufosRef.current.length === 0) return

    ufosRef.current.forEach((ufo, idx) => {
      // Move toward target
      const direction = ufo.target.clone().sub(ufo.position)
      const distance = direction.length()

      if (distance < 2) {
        // Reached target, pick new random target
        const newTargetIdx = Math.floor(Math.random() * bodyPositions.length)
        ufo.targetBodyIndex = newTargetIdx
        ufo.target = bodyPositions[newTargetIdx].pos.clone()

        // Add slight randomness to target
        ufo.target.x += (Math.random() - 0.5) * 5
        ufo.target.y += (Math.random() - 0.5) * 3
        ufo.target.z += (Math.random() - 0.5) * 5
      } else {
        // Move toward target with slight wobble
        direction.normalize()
        const wobble = Math.sin(state.clock.elapsedTime * 3 + ufo.progress * 10) * 0.1
        direction.y += wobble

        ufo.velocity.lerp(direction.multiplyScalar(UFO_SPEED), delta * 2)
        ufo.position.add(ufo.velocity.clone().multiplyScalar(delta * 60))
      }

      // Update trail
      ufo.trail.pop()
      ufo.trail.unshift(ufo.position.clone())

      ufo.progress += delta

      // Update trail geometry
      if (trailGeometriesRef.current[idx]) {
        const positions = new Float32Array(ufo.trail.length * 3)
        ufo.trail.forEach((point, i) => {
          positions[i * 3] = point.x
          positions[i * 3 + 1] = point.y
          positions[i * 3 + 2] = point.z
        })

        const positionAttribute = trailGeometriesRef.current[idx].getAttribute('position') as THREE.BufferAttribute
        positionAttribute.set(positions)
        positionAttribute.needsUpdate = true
      }
    })
  })

  // Early return if not enough data
  if (bodyPositions.length < 2 || ufosRef.current.length === 0) {
    return null
  }

  return (
    <group ref={groupRef}>
      {ufosRef.current.map((ufo, idx) => (
        <group key={idx}>
          {/* UFO body - small glowing sphere */}
          <mesh position={ufo.position}>
            <sphereGeometry args={[0.3, 8, 8]} />
            <meshBasicMaterial
              color="#22d3ee"
              transparent
              opacity={0.9}
            />
          </mesh>

          {/* UFO glow */}
          <mesh position={ufo.position}>
            <sphereGeometry args={[0.5, 8, 8]} />
            <meshBasicMaterial
              color="#22d3ee"
              transparent
              opacity={0.3}
              blending={THREE.AdditiveBlending}
            />
          </mesh>

          {/* Trail line - use LineSegments for better rendering */}
          <lineSegments geometry={trailGeometriesRef.current[idx]}>
            <lineBasicMaterial
              color="#22d3ee"
              transparent
              opacity={0.4}
              blending={THREE.AdditiveBlending}
            />
          </lineSegments>
        </group>
      ))}
    </group>
  )
}

export default UfoTrails
