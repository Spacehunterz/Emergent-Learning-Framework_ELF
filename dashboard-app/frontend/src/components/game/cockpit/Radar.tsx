
import { useRef, useMemo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { useEnemyStore } from '../systems/EnemySystem'
import * as THREE from 'three'

export const Radar = () => {
    const { enemies } = useEnemyStore()
    const { camera } = useThree()

    // FIXED: Pre-allocate temp objects for radar calculations
    const tempVec = useRef(new THREE.Vector3())
    const tempQuat = useRef(new THREE.Quaternion())

    return (
        // Tilted nicely for 2.5D isometric look
        <group position={[0, 0, 0]} rotation={[-Math.PI / 3, 0, 0]} scale={[0.5, 0.5, 0.5]}>
            {/* Screen Helper / Base */}
            <mesh>
                <circleGeometry args={[0.5, 32]} />
                <meshBasicMaterial color="#002200" opacity={0.6} transparent />
            </mesh>
            <mesh>
                <ringGeometry args={[0.48, 0.5, 32]} />
                <meshBasicMaterial color="#33ff33" />
            </mesh>
            <mesh position={[0, 0, -0.01]}>
                <ringGeometry args={[0.25, 0.26, 32]} />
                <meshBasicMaterial color="#33ff33" opacity={0.3} transparent />
            </mesh>

            {/* Player Marker */}
            <mesh position={[0, 0, 0.01]}>
                <circleGeometry args={[0.02, 16]} />
                <meshBasicMaterial color="white" />
            </mesh>

            {/* Grid Lines */}
            <group rotation={[0, 0, Math.PI / 4]}>
                <mesh>
                    <planeGeometry args={[1, 0.01]} />
                    <meshBasicMaterial color="#004400" />
                </mesh>
                <mesh rotation={[0, 0, Math.PI / 2]}>
                    <planeGeometry args={[1, 0.01]} />
                    <meshBasicMaterial color="#004400" />
                </mesh>
            </group>

            {/* Blips */}
            {enemies.map(e => {
                // Transform World Position -> Local Camera Space
                // This makes the radar rotate WITH the player
                // FIXED: Reuse pre-allocated vectors instead of clone()
                tempVec.current.copy(e.position).sub(camera.position)
                tempQuat.current.copy(camera.quaternion).invert()
                tempVec.current.applyQuaternion(tempQuat.current)
                const relativePos = tempVec.current

                // Map to Radar Plane (X, -Z)
                // Scaling: 100 units world = 0.5 units radar
                const scale = 0.005
                const x = relativePos.x * scale
                const y = -relativePos.z * scale // Forward (-Z) is Up (+Y) on radar

                // Clamp to edge if out of range (optional, keeps them on screen)
                const dist = Math.sqrt(x * x + y * y)
                // Fade out at edge
                const opacity = Math.max(0.2, 1 - (dist * 2))

                // Height indication? (Simple: Color shift if above/below?)
                const isAbove = relativePos.y > 5
                const isBelow = relativePos.y < -5
                const color = isAbove ? '#ffcc00' : isBelow ? '#cc5500' : 'red'

                return (
                    <group key={e.id} position={[x, y, 0.02 + (relativePos.y * 0.001)]}>
                        {/* Blip */}
                        <mesh>
                            <circleGeometry args={[0.03]} />
                            <meshBasicMaterial color={color} opacity={1} transparent depthTest={false} />
                        </mesh>
                        {/* Height Stick (Pseudo-3D) */}
                        {Math.abs(relativePos.y) > 2 && (
                            <mesh position={[0, -relativePos.y * 0.005, -0.01]}>
                                <planeGeometry args={[0.005, Math.abs(relativePos.y * 0.01)]} />
                                <meshBasicMaterial color={color} opacity={0.5} transparent />
                            </mesh>
                        )}
                    </group>
                )
            })}
        </group>
    )
}

