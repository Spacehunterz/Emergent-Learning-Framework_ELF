import { create } from 'zustand'
import { useFrame } from '@react-three/fiber'
import { useRef, useState } from 'react'
import { Vector3 } from 'three'
import * as THREE from 'three'
import { GAME_CONFIG } from '../config/GameConstants'

interface Explosion {
    id: string
    position: Vector3
    color: string
    scale: number
    createdAt: number
}

interface ExplosionStore {
    explosions: Explosion[]
    spawnExplosion: (position: Vector3, color?: string, scale?: number) => void
    removeExplosion: (id: string) => void
}

export const useExplosionStore = create<ExplosionStore>((set) => ({
    explosions: [],
    spawnExplosion: (position, color = 'orange', scale = 1) => set((state) => ({
        explosions: [...state.explosions, {
            id: Math.random().toString(),
            position,
            color: color || GAME_CONFIG.ENEMIES.COLORS.EXPLOSION_DEFAULT, // Use constant default
            scale,
            createdAt: Date.now()
        }]
    })),
    removeExplosion: (id) => set((state) => ({
        explosions: state.explosions.filter(e => e.id !== id)
    }))
}))

const ExplosionParticle = ({ position, color }: { position: Vector3, color: string }) => {
    const ref = useRef<any>()
    const [velocity] = useState(() => new Vector3(
        (Math.random() - 0.5) * 10,
        (Math.random() - 0.5) * 10,
        (Math.random() - 0.5) * 10
    ))

    // Pre-allocate temp vector to avoid clone() every frame
    const tempVelocity = useRef(new Vector3())

    useFrame((state, delta) => {
        if (ref.current) {
            tempVelocity.current.copy(velocity).multiplyScalar(delta)
            ref.current.position.add(tempVelocity.current)
            ref.current.scale.multiplyScalar(0.95) // Shrink
            ref.current.material.opacity -= delta * 2
        }
    })

    return (
        <mesh ref={ref} position={position}>
            <sphereGeometry args={[0.2, 8, 8]} />
            <meshBasicMaterial color={color} transparent opacity={1} />
        </mesh>
    )
}

const ExplosionEffect = ({ data }: { data: Explosion }) => {
    return (
        <group position={data.position}>
            {/* Particles */}
            {Array.from({ length: 12 }).map((_, i) => (
                <ExplosionParticle key={i} position={new Vector3(0, 0, 0)} color={data.color} />
            ))}

            {/* Shockwave Ring */}
            <Shockwave color={data.color} />

            {/* Flash */}
            <pointLight intensity={3} distance={15} decay={2} color={data.color} />
        </group>
    )
}

const Shockwave = ({ color }: { color: string }) => {
    const ref = useRef<any>()

    useFrame((state, delta) => {
        if (ref.current) {
            ref.current.scale.addScalar(delta * 20) // Fast expansion
            ref.current.material.opacity -= delta * 2 // Fade out
            // Rotate slightly
            ref.current.rotation.z -= delta * 0.5
        }
    })

    return (
        <group>
            <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.5, 0.8, 32]} />
                <meshBasicMaterial color={color} transparent opacity={0.8} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} />
            </mesh>
            {/* Secondary Ripple */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} scale={[0.7, 0.7, 0.7]}>
                <ringGeometry args={[0.4, 0.5, 32]} />
                <meshBasicMaterial color="white" transparent opacity={0.5} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} />
            </mesh>
        </group>
    )
}

export const ExplosionRenderer = () => {
    const { explosions, removeExplosion } = useExplosionStore()

    // Cleanup old explosions - FIXED: Date.now() inside useFrame to avoid stale closure
    useFrame(() => {
        const now = Date.now()
        explosions.forEach(e => {
            if (now - e.createdAt > 1000) {
                removeExplosion(e.id)
            }
        })
    })

    return (
        <group>
            {explosions.map(e => (
                <ExplosionEffect key={e.id} data={e} />
            ))}
        </group>
    )
}
