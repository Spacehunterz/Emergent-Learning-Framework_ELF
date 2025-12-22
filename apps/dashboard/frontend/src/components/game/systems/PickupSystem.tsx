import React, { useRef } from 'react'
import { create } from 'zustand'
import { Vector3 } from 'three'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'

export type PickupType = 'health' | 'shield' | 'weapon'

export interface Pickup {
    id: string
    type: PickupType
    position: Vector3
    createdAt: number
    value: number // heal/shield amount or duration for weapon boost
}

interface PickupState {
    pickups: Pickup[]
    spawnPickup: (pickup: Pickup) => void
    removePickup: (id: string) => void
    clearPickups: () => void
}

export const usePickupStore = create<PickupState>((set) => ({
    pickups: [],
    spawnPickup: (pickup) => set((state) => ({ pickups: [...state.pickups, pickup] })),
    removePickup: (id) => set((state) => ({ pickups: state.pickups.filter(p => p.id !== id) })),
    clearPickups: () => set({ pickups: [] })
}))

// Spawn a health pickup at position (red plus)
export const spawnHealthPickup = (position: Vector3, healAmount: number = 20) => {
    const { spawnPickup } = usePickupStore.getState()
    spawnPickup({
        id: `health-${Date.now()}-${Math.random()}`,
        type: 'health',
        position: position.clone(),
        createdAt: Date.now(),
        value: healAmount
    })
}

// Spawn a shield pickup at position (blue plus)
export const spawnShieldPickup = (position: Vector3, shieldAmount: number = 20) => {
    const { spawnPickup } = usePickupStore.getState()
    spawnPickup({
        id: `shield-${Date.now()}-${Math.random()}`,
        type: 'shield',
        position: position.clone(),
        createdAt: Date.now(),
        value: shieldAmount
    })
}

// Spawn a weapon boost pickup (turbo shot for 30s)
export const spawnWeaponPickup = (position: Vector3, duration: number = 30) => {
    const { spawnPickup } = usePickupStore.getState()
    spawnPickup({
        id: `weapon-${Date.now()}-${Math.random()}`,
        type: 'weapon',
        position: position.clone(),
        createdAt: Date.now(),
        value: duration
    })
}

// Legacy alias
export const spawnHeartPickup = spawnHealthPickup

// Health pickup visual component - RED PLUS SIGN (2x size = scale 8)
const HealthMesh = ({ data, onCollect }: { data: Pickup, onCollect: (id: string, type: PickupType, value: number) => void }) => {
    const ref = useRef<THREE.Group>(null)
    const matRef = useRef<THREE.MeshBasicMaterial>(null)

    useFrame((state, delta) => {
        if (!ref.current) return
        const t = state.clock.getElapsedTime()

        // Float upward slowly and bob
        data.position.y += delta * 5
        data.position.z += delta * 20 // Move toward player

        ref.current.position.copy(data.position)
        ref.current.rotation.y += delta * 2

        // Pulse effect - 2x size (8 instead of 4)
        const pulse = 1 + Math.sin(t * 4) * 0.1
        ref.current.scale.setScalar(pulse * 8)

        // Glow
        if (matRef.current) {
            matRef.current.opacity = 0.8 + Math.sin(t * 6) * 0.2
        }

        // Check if close to player (at origin)
        const distToPlayer = data.position.length()
        if (distToPlayer < 20) {
            onCollect(data.id, 'health', data.value)
        }

        // Despawn if too old or past player
        if (data.position.z > 50 || Date.now() - data.createdAt > 10000) {
            usePickupStore.getState().removePickup(data.id)
        }
    })

    return (
        <group ref={ref}>
            {/* Red plus sign - vertical bar */}
            <mesh scale={[0.25, 1, 0.25]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={matRef} color="#ff2222" transparent opacity={0.9} />
            </mesh>
            {/* Red plus sign - horizontal bar */}
            <mesh scale={[1, 0.25, 0.25]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#ff2222" transparent opacity={0.9} />
            </mesh>
            {/* Glow ring */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={1.2}>
                <torusGeometry args={[1, 0.08, 8, 16]} />
                <meshBasicMaterial color="#ff6666" transparent opacity={0.4} />
            </mesh>
        </group>
    )
}

// Shield pickup visual component - BLUE PLUS SIGN (same size as health)
const ShieldMesh = ({ data, onCollect }: { data: Pickup, onCollect: (id: string, type: PickupType, value: number) => void }) => {
    const ref = useRef<THREE.Group>(null)
    const matRef = useRef<THREE.MeshBasicMaterial>(null)

    useFrame((state, delta) => {
        if (!ref.current) return
        const t = state.clock.getElapsedTime()

        data.position.y += delta * 5
        data.position.z += delta * 20

        ref.current.position.copy(data.position)
        ref.current.rotation.y += delta * 2.5

        // Pulse effect - same size as health
        const pulse = 1 + Math.sin(t * 4) * 0.15
        ref.current.scale.setScalar(pulse * 8)

        if (matRef.current) {
            matRef.current.opacity = 0.8 + Math.sin(t * 6) * 0.2
        }

        const distToPlayer = data.position.length()
        if (distToPlayer < 20) {
            onCollect(data.id, 'shield', data.value)
        }

        if (data.position.z > 50 || Date.now() - data.createdAt > 10000) {
            usePickupStore.getState().removePickup(data.id)
        }
    })

    return (
        <group ref={ref}>
            {/* Blue plus sign - vertical bar */}
            <mesh scale={[0.25, 1, 0.25]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={matRef} color="#2288ff" transparent opacity={0.9} />
            </mesh>
            {/* Blue plus sign - horizontal bar */}
            <mesh scale={[1, 0.25, 0.25]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#2288ff" transparent opacity={0.9} />
            </mesh>
            {/* Glow ring */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={1.2}>
                <torusGeometry args={[1, 0.08, 8, 16]} />
                <meshBasicMaterial color="#66aaff" transparent opacity={0.4} />
            </mesh>
            {/* Shield icon effect - outer ring */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={1.5}>
                <torusGeometry args={[1, 0.04, 8, 16]} />
                <meshBasicMaterial color="#44ccff" transparent opacity={0.3} />
            </mesh>
        </group>
    )
}

// Weapon boost pickup - DUAL BARRELS with explosion circle (orange/yellow)
const WeaponMesh = ({ data, onCollect }: { data: Pickup, onCollect: (id: string, type: PickupType, value: number) => void }) => {
    const ref = useRef<THREE.Group>(null)
    const matRef = useRef<THREE.MeshBasicMaterial>(null)
    const burstRefs = useRef<(THREE.Mesh | null)[]>([])

    useFrame((state, delta) => {
        if (!ref.current) return
        const t = state.clock.getElapsedTime()

        data.position.y += delta * 5
        data.position.z += delta * 20

        ref.current.position.copy(data.position)
        ref.current.rotation.y += delta * 3

        // Pulse effect - same size as others
        const pulse = 1 + Math.sin(t * 5) * 0.12
        ref.current.scale.setScalar(pulse * 8)

        if (matRef.current) {
            matRef.current.opacity = 0.85 + Math.sin(t * 8) * 0.15
        }

        // Animate explosion burst spikes
        burstRefs.current.forEach((spike, i) => {
            if (!spike) return
            const burstPulse = 1 + Math.sin(t * 6 + i * 0.5) * 0.2
            spike.scale.setScalar(burstPulse)
        })

        const distToPlayer = data.position.length()
        if (distToPlayer < 20) {
            onCollect(data.id, 'weapon', data.value)
        }

        if (data.position.z > 50 || Date.now() - data.createdAt > 10000) {
            usePickupStore.getState().removePickup(data.id)
        }
    })

    // Create explosion burst spikes around the pickup
    const burstCount = 8

    return (
        <group ref={ref}>
            {/* Dual barrels - pause symbol look */}
            <mesh position={[-0.3, 0, 0]} scale={[0.2, 0.8, 0.2]}>
                <cylinderGeometry args={[1, 1, 1, 8]} />
                <meshBasicMaterial ref={matRef} color="#ffaa00" transparent opacity={0.9} />
            </mesh>
            <mesh position={[0.3, 0, 0]} scale={[0.2, 0.8, 0.2]}>
                <cylinderGeometry args={[1, 1, 1, 8]} />
                <meshBasicMaterial color="#ffaa00" transparent opacity={0.9} />
            </mesh>
            {/* Explosion burst ring - crinkle circle */}
            {Array.from({ length: burstCount }).map((_, i) => {
                const angle = (i / burstCount) * Math.PI * 2
                const x = Math.cos(angle) * 1.2
                const y = Math.sin(angle) * 1.2
                return (
                    <mesh
                        key={i}
                        ref={el => burstRefs.current[i] = el}
                        position={[x, y, 0]}
                        rotation={[0, 0, angle + Math.PI / 2]}
                        scale={[0.15, 0.4, 0.15]}
                    >
                        <coneGeometry args={[1, 1, 4]} />
                        <meshBasicMaterial color="#ff6600" transparent opacity={0.7} />
                    </mesh>
                )
            })}
            {/* Inner glow ring */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={0.9}>
                <torusGeometry args={[1, 0.1, 8, 16]} />
                <meshBasicMaterial color="#ffdd00" transparent opacity={0.5} />
            </mesh>
        </group>
    )
}

// Pickup collision radius for shooting
export const PICKUP_HIT_RADIUS = 12

// Renderer component for all pickups
export const PickupRenderer = ({
    onHeal,
    onShield,
    onWeaponBoost
}: {
    onHeal: (amount: number) => void
    onShield?: (amount: number) => void
    onWeaponBoost?: (duration: number) => void
}) => {
    const pickups = usePickupStore(s => s.pickups)
    const { removePickup } = usePickupStore()

    const handleCollect = (id: string, type: PickupType, value: number) => {
        removePickup(id)
        if (type === 'health') {
            onHeal(value)
        } else if (type === 'shield' && onShield) {
            onShield(value)
        } else if (type === 'weapon' && onWeaponBoost) {
            onWeaponBoost(value)
        }
    }

    return (
        <>
            {pickups.map(pickup => {
                if (pickup.type === 'health') {
                    return <HealthMesh key={pickup.id} data={pickup} onCollect={handleCollect} />
                }
                if (pickup.type === 'shield') {
                    return <ShieldMesh key={pickup.id} data={pickup} onCollect={handleCollect} />
                }
                if (pickup.type === 'weapon') {
                    return <WeaponMesh key={pickup.id} data={pickup} onCollect={handleCollect} />
                }
                return null
            })}
        </>
    )
}
