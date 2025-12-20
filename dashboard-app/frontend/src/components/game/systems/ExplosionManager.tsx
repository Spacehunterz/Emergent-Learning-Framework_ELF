import { create } from 'zustand'
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import { Vector3 } from 'three'
import * as THREE from 'three'
import { useGameSettings } from './GameSettings'

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
}

// Simple store - no removeExplosion needed, we'll filter in render
export const useExplosionStore = create<ExplosionStore>((set) => ({
    explosions: [],
    spawnExplosion: (position, color = 'orange', scale = 1) => set((state) => {
        // Also clean up old explosions when spawning new ones (avoid separate cleanup loop)
        const now = Date.now()
        const activeExplosions = state.explosions.filter(e => now - e.createdAt < 800)
        return {
            explosions: [...activeExplosions, {
                id: `exp-${now}-${Math.random()}`,
                position: position.clone(), // Clone to avoid mutation issues
                color,
                scale,
                createdAt: now
            }]
        }
    })
}))

// Simple explosion - just an expanding/fading sphere
const SimpleExplosion = ({ data }: { data: Explosion }) => {
    const ref = useRef<THREE.Mesh>(null)
    const { isPaused } = useGameSettings()
    const startScale = data.scale * 2

    useFrame(() => {
        if (isPaused || !ref.current) return
        const age = (Date.now() - data.createdAt) / 1000 // seconds
        const progress = Math.min(age / 0.5, 1) // 0.5 second duration

        // Expand and fade
        const currentScale = startScale + progress * data.scale * 8
        ref.current.scale.setScalar(currentScale)

        // Fade out
        const mat = ref.current.material as THREE.MeshBasicMaterial
        mat.opacity = 1 - progress
    })

    return (
        <mesh ref={ref} position={data.position}>
            <sphereGeometry args={[1, 8, 8]} />
            <meshBasicMaterial
                color={data.color}
                transparent
                opacity={1}
                blending={THREE.AdditiveBlending}
                depthWrite={false}
            />
        </mesh>
    )
}

export const ExplosionRenderer = () => {
    const { explosions } = useExplosionStore()

    // Filter active explosions in render (no state updates needed)
    const now = Date.now()
    const activeExplosions = explosions.filter(e => now - e.createdAt < 800)

    return (
        <group>
            {activeExplosions.map(e => (
                <SimpleExplosion key={e.id} data={e} />
            ))}
        </group>
    )
}
