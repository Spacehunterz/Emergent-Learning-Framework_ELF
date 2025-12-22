
import React, { useLayoutEffect, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { GameEngine } from '../core/GameEngine'

const TEMP_OBJ = new THREE.Object3D()
const TEMP_COLOR = new THREE.Color()

export const InstancedProjectileRenderer = ({ engine }: { engine: GameEngine }) => {
    const meshRef = useRef<THREE.InstancedMesh>(null)
    const lightRef = useRef<THREE.InstancedMesh>(null) // Optional: Glow effect mesh

    useLayoutEffect(() => {
        if (meshRef.current) {
            meshRef.current.count = 0
        }
    }, [])

    useFrame(() => {
        if (!meshRef.current) return

        const projectiles = engine.state.projectiles
        const count = projectiles.length

        // Resize if needed (rarely, since pool is large) or just cap it
        if (count > meshRef.current.instanceMatrix.count) {
            // Reallocate handled by Three.js if we were stricter, but for now we trust pool size limits
            // or max at instance count
        }

        meshRef.current.count = count

        for (let i = 0; i < count; i++) {
            const p = projectiles[i]

            TEMP_OBJ.position.copy(p.position)
            TEMP_OBJ.quaternion.copy(p.rotation)
            // TEMP_OBJ.rotateX(Math.PI / 2) // REVERTED: Player bullets define orientation correctly
            TEMP_OBJ.scale.set(1, 1, 4) // Elongated projectile
            TEMP_OBJ.updateMatrix()

            // Safety Check
            if (isNaN(TEMP_OBJ.matrix.elements[0])) {
                console.error('InstancedProjectileRenderer: NaN Matrix detected at index', i, p)
                continue
            }

            meshRef.current.setMatrixAt(i, TEMP_OBJ.matrix)
        }

        meshRef.current.instanceMatrix.needsUpdate = true
    })

    return (
        <instancedMesh
            ref={meshRef}
            args={[undefined, undefined, 1000]}
            frustumCulled={false}
        >
            <capsuleGeometry args={[0.08, 3, 4, 8]} />
            <meshBasicMaterial color="#00ffff" toneMapped={false} />
        </instancedMesh>
    )
}
