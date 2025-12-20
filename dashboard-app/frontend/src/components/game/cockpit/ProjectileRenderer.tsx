import { useProjectileStore } from '../systems/WeaponSystem'
import * as THREE from 'three'
import React, { useRef } from 'react'
import { useFrame } from '@react-three/fiber'

const ProjectileMesh = React.memo(({ data }: { data: { id: string, position: THREE.Vector3, rotation: THREE.Quaternion, owner: string, type: string } }) => {
    const groupRef = useRef<THREE.Group>(null)

    useFrame(() => {
        if (groupRef.current) {
            // Direct position update from mutable data source (WeaponSystem)
            groupRef.current.position.copy(data.position)
        }
    })

    const isEnemy = data.owner === 'ENEMY'
    const color = isEnemy ? '#ff2200' : '#00ffff'
    const coreColor = isEnemy ? '#ffaa00' : '#ffffff'

    return (
        <group ref={groupRef} quaternion={data.rotation}>
            {/* Simple laser bolt - no Trail, just oriented geometry */}
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                {isEnemy ? (
                    <capsuleGeometry args={[0.4, 1.5, 4, 8]} />
                ) : (
                    // Player: Long thin laser beam pointing forward
                    <cylinderGeometry args={[0.15, 0.15, 8, 6]} />
                )}
                <meshBasicMaterial color={coreColor} toneMapped={false} />
            </mesh>

            {/* Outer glow */}
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                {isEnemy ? (
                    <sphereGeometry args={[0.8, 12, 12]} />
                ) : (
                    <cylinderGeometry args={[0.3, 0.2, 9, 6]} />
                )}
                <meshBasicMaterial
                    color={color}
                    transparent
                    opacity={0.6}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>

        </group>
    )
}, (prev, next) => prev.data.id === next.data.id) // Only re-render if ID changes (which shouldn't happen for same index usually, but data ref is stable)


export const ProjectileRenderer = React.memo(() => {
    const { projectiles } = useProjectileStore()

    return (
        <group>
            {projectiles.map(p => (
                <ProjectileMesh key={p.id} data={p} />
            ))}
        </group>
    )
})
