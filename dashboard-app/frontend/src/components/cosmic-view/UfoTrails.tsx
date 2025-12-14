import { useRef, useMemo } from 'react'
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

  // Initialize UFOs
  const ufosRef = useRef<Ufo[]>([])

  // Get all body positions from systems
  const bodyPositions = useMemo(() => {
    const positions: { pos: THREE.Vector3; systemIdx: number }[] = []

    systems.forEach((system, sysIdx) => {
      // Add system center (sun position)
      positions.push({
        pos: new THREE.Vector3(...system.position),
        systemIdx: sysIdx
      })

      // Add estimated planet positions (they orbit, so we use base position)
      system.planets.forEach((planet) => {
        const planetPos = new THREE.Vector3(
          system.position[0] + planet.orbitRadius,
          system.position[1],
          system.position[2]
        )
        positions.push({ pos: planetPos, systemIdx: sysIdx })
      })
    })

    return positions
  }, [systems])

  // Initialize UFOs on first render
  if (ufosRef.current.length === 0 && bodyPositions.length > 1) {
    for (let i = 0; i < Math.min(UFO_COUNT, bodyPositions.length); i++) {
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
    }
  }

  // Animate UFOs
  useFrame((state, delta) => {
    if (bodyPositions.length < 2) return

    ufosRef.current.forEach((ufo) => {
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
    })
  })

  // Create geometry for trails
  const trailGeometries = useMemo(() => {
    return ufosRef.current.map(() => new THREE.BufferGeometry())
  }, [])

  // Update trail geometries each frame
  useFrame(() => {
    ufosRef.current.forEach((ufo, idx) => {
      const positions = new Float32Array(ufo.trail.length * 3)
      ufo.trail.forEach((point, i) => {
        positions[i * 3] = point.x
        positions[i * 3 + 1] = point.y
        positions[i * 3 + 2] = point.z
      })
      trailGeometries[idx].setAttribute(
        'position',
        new THREE.BufferAttribute(positions, 3)
      )
    })
  })

  if (bodyPositions.length < 2) return null

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

          {/* Trail line */}
          <line geometry={trailGeometries[idx]}>
            <lineBasicMaterial
              color="#22d3ee"
              transparent
              opacity={0.4}
              blending={THREE.AdditiveBlending}
            />
          </line>
        </group>
      ))}
    </group>
  )
}

export default UfoTrails
