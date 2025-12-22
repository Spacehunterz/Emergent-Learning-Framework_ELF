import { create } from 'zustand'
import { useFrame } from '@react-three/fiber'
import { useRef, useMemo } from 'react'
import { Vector3 } from 'three'
import * as THREE from 'three'
import { useGameSettings } from './GameSettings'
import { EnemyType } from './EnemySystem'

// Death effect types
export type DeathEffectType =
    | 'disintegrate'  // Particles scatter outward
    | 'shatter'       // Geometric shards fly apart
    | 'vaporize'      // Quick bright flash then fade
    | 'implode'       // Sucks inward then explodes
    | 'electric'      // Sparking electric death

interface DeathEffect {
    id: string
    position: Vector3
    effectType: DeathEffectType
    color: string
    scale: number
    createdAt: number
    enemyType: EnemyType
    stage: number
}

interface DeathEffectsStore {
    effects: DeathEffect[]
    spawnDeathEffect: (
        position: Vector3,
        enemyType: EnemyType,
        stage: number,
        color?: string,
        scale?: number
    ) => void
}

// Map enemy types to death effect types
const getDeathEffectType = (enemyType: EnemyType, stage: number): DeathEffectType => {
    // Stage-based variations
    if (stage >= 8) {
        // Later stages get more dramatic effects
        if (enemyType === 'boss') return 'implode'
        if (enemyType === 'elite') return 'electric'
    }

    switch (enemyType) {
        case 'asteroid': return 'shatter'
        case 'drone': return 'vaporize'
        case 'fighter': return 'disintegrate'
        case 'elite': return 'electric'
        case 'boss': return 'implode'
        default: return 'disintegrate'
    }
}

export const useDeathEffectsStore = create<DeathEffectsStore>((set) => ({
    effects: [],
    spawnDeathEffect: (position, enemyType, stage, color = '#ff6600', scale = 1) => set((state) => {
        const now = Date.now()
        // Clean up old effects
        const activeEffects = state.effects.filter(e => now - e.createdAt < 1500)

        return {
            effects: [...activeEffects, {
                id: `death-${now}-${Math.random()}`,
                position: position.clone(),
                effectType: getDeathEffectType(enemyType, stage),
                color,
                scale,
                createdAt: now,
                enemyType,
                stage
            }]
        }
    })
}))

// --- DISINTEGRATE EFFECT ---
// Particles scatter outward in all directions
const DisintegrateEffect = ({ data }: { data: DeathEffect }) => {
    const groupRef = useRef<THREE.Group>(null)
    const { isPaused } = useGameSettings()

    // Generate random particle directions
    const particles = useMemo(() => {
        const count = 20 + Math.floor(data.scale * 10)
        return Array.from({ length: count }, () => ({
            direction: new Vector3(
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2
            ).normalize(),
            speed: 30 + Math.random() * 50,
            size: 0.3 + Math.random() * 0.5,
            rotSpeed: (Math.random() - 0.5) * 10
        }))
    }, [data.scale])

    useFrame(() => {
        if (isPaused || !groupRef.current) return
        const age = (Date.now() - data.createdAt) / 1000
        const progress = Math.min(age / 1.0, 1)

        groupRef.current.children.forEach((child, i) => {
            if (child instanceof THREE.Mesh) {
                const p = particles[i]
                if (!p) return

                // Move outward
                child.position.copy(p.direction).multiplyScalar(progress * p.speed * data.scale)

                // Rotate
                child.rotation.x += p.rotSpeed * 0.016
                child.rotation.y += p.rotSpeed * 0.016

                // Fade and shrink
                const mat = child.material as THREE.MeshBasicMaterial
                mat.opacity = 1 - progress
                child.scale.setScalar(p.size * (1 - progress * 0.5) * data.scale)
            }
        })
    })

    return (
        <group ref={groupRef} position={data.position}>
            {particles.map((p, i) => (
                <mesh key={i}>
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial
                        color={data.color}
                        transparent
                        opacity={1}
                        blending={THREE.AdditiveBlending}
                        depthWrite={false}
                    />
                </mesh>
            ))}
        </group>
    )
}

// --- SHATTER EFFECT ---
// Geometric shards fly apart (good for asteroids)
const ShatterEffect = ({ data }: { data: DeathEffect }) => {
    const groupRef = useRef<THREE.Group>(null)
    const { isPaused } = useGameSettings()

    const shards = useMemo(() => {
        const count = 8 + Math.floor(data.scale * 5)
        return Array.from({ length: count }, () => ({
            direction: new Vector3(
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2
            ).normalize(),
            speed: 15 + Math.random() * 30,
            size: 1 + Math.random() * 2,
            rotSpeed: new Vector3(
                (Math.random() - 0.5) * 5,
                (Math.random() - 0.5) * 5,
                (Math.random() - 0.5) * 5
            ),
            geoType: Math.floor(Math.random() * 3)
        }))
    }, [data.scale])

    useFrame(() => {
        if (isPaused || !groupRef.current) return
        const age = (Date.now() - data.createdAt) / 1000
        const progress = Math.min(age / 1.2, 1)

        groupRef.current.children.forEach((child, i) => {
            if (child instanceof THREE.Mesh) {
                const s = shards[i]
                if (!s) return

                // Move outward with gravity
                const pos = s.direction.clone().multiplyScalar(progress * s.speed * data.scale)
                pos.y -= progress * progress * 10 // Gravity
                child.position.copy(pos)

                // Rotate
                child.rotation.x += s.rotSpeed.x * 0.016
                child.rotation.y += s.rotSpeed.y * 0.016
                child.rotation.z += s.rotSpeed.z * 0.016

                // Fade
                const mat = child.material as THREE.MeshBasicMaterial
                mat.opacity = 1 - progress
            }
        })
    })

    return (
        <group ref={groupRef} position={data.position}>
            {shards.map((s, i) => (
                <mesh key={i} scale={s.size * data.scale}>
                    {s.geoType === 0 && <octahedronGeometry args={[1, 0]} />}
                    {s.geoType === 1 && <tetrahedronGeometry args={[1, 0]} />}
                    {s.geoType === 2 && <dodecahedronGeometry args={[0.8, 0]} />}
                    <meshBasicMaterial
                        color={data.color}
                        wireframe
                        transparent
                        opacity={1}
                        blending={THREE.AdditiveBlending}
                        depthWrite={false}
                    />
                </mesh>
            ))}
        </group>
    )
}

// --- VAPORIZE EFFECT ---
// Quick bright flash then fade (good for drones)
const VaporizeEffect = ({ data }: { data: DeathEffect }) => {
    const meshRef = useRef<THREE.Mesh>(null)
    const ringRef = useRef<THREE.Mesh>(null)
    const { isPaused } = useGameSettings()

    useFrame(() => {
        if (isPaused || !meshRef.current) return
        const age = (Date.now() - data.createdAt) / 1000
        const progress = Math.min(age / 0.3, 1)

        // Quick expand
        const scale = data.scale * (1 + progress * 15)
        meshRef.current.scale.setScalar(scale)

        // Quick fade
        const mat = meshRef.current.material as THREE.MeshBasicMaterial
        mat.opacity = 1 - progress

        // Expanding ring
        if (ringRef.current) {
            ringRef.current.scale.setScalar(scale * 2)
            const ringMat = ringRef.current.material as THREE.MeshBasicMaterial
            ringMat.opacity = (1 - progress) * 0.5
        }
    })

    return (
        <group position={data.position}>
            {/* Core flash */}
            <mesh ref={meshRef}>
                <sphereGeometry args={[1, 12, 12]} />
                <meshBasicMaterial
                    color="#ffffff"
                    transparent
                    opacity={1}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
            {/* Expanding ring */}
            <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.8, 1, 16]} />
                <meshBasicMaterial
                    color={data.color}
                    transparent
                    opacity={0.5}
                    side={THREE.DoubleSide}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        </group>
    )
}

// --- IMPLODE EFFECT ---
// Sucks inward then explodes outward (good for bosses)
const ImplodeEffect = ({ data }: { data: DeathEffect }) => {
    const groupRef = useRef<THREE.Group>(null)
    const coreRef = useRef<THREE.Mesh>(null)
    const { isPaused } = useGameSettings()

    const particles = useMemo(() => {
        const count = 30
        return Array.from({ length: count }, () => ({
            startPos: new Vector3(
                (Math.random() - 0.5) * 60,
                (Math.random() - 0.5) * 60,
                (Math.random() - 0.5) * 60
            ),
            endDir: new Vector3(
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2
            ).normalize(),
            size: 0.5 + Math.random() * 1
        }))
    }, [])

    useFrame(() => {
        if (isPaused || !groupRef.current || !coreRef.current) return
        const age = (Date.now() - data.createdAt) / 1000
        const totalDuration = 1.5
        const implodeEnd = 0.4
        const progress = Math.min(age / totalDuration, 1)

        // Core pulsing and scaling
        if (age < implodeEnd) {
            // Implode phase - core shrinks and brightens
            const implodeProgress = age / implodeEnd
            coreRef.current.scale.setScalar(data.scale * 3 * (1 - implodeProgress * 0.8))
            const mat = coreRef.current.material as THREE.MeshBasicMaterial
            mat.opacity = 0.3 + implodeProgress * 0.7
        } else {
            // Explode phase
            const explodeProgress = (age - implodeEnd) / (totalDuration - implodeEnd)
            coreRef.current.scale.setScalar(data.scale * 3 * (0.2 + explodeProgress * 10))
            const mat = coreRef.current.material as THREE.MeshBasicMaterial
            mat.opacity = 1 - explodeProgress
        }

        // Particles
        groupRef.current.children.forEach((child, i) => {
            if (child instanceof THREE.Mesh && i < particles.length) {
                const p = particles[i]

                if (age < implodeEnd) {
                    // Move toward center
                    const implodeProgress = age / implodeEnd
                    child.position.copy(p.startPos).multiplyScalar(1 - implodeProgress)
                } else {
                    // Explode outward
                    const explodeProgress = (age - implodeEnd) / (totalDuration - implodeEnd)
                    child.position.copy(p.endDir).multiplyScalar(explodeProgress * 80 * data.scale)
                }

                const mat = child.material as THREE.MeshBasicMaterial
                mat.opacity = 1 - progress
            }
        })
    })

    return (
        <group position={data.position}>
            {/* Core */}
            <mesh ref={coreRef}>
                <sphereGeometry args={[1, 16, 16]} />
                <meshBasicMaterial
                    color={data.color}
                    transparent
                    opacity={0.3}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
            {/* Particles */}
            <group ref={groupRef}>
                {particles.map((p, i) => (
                    <mesh key={i} position={p.startPos} scale={p.size * data.scale}>
                        <octahedronGeometry args={[1, 0]} />
                        <meshBasicMaterial
                            color={data.color}
                            transparent
                            opacity={1}
                            blending={THREE.AdditiveBlending}
                            depthWrite={false}
                        />
                    </mesh>
                ))}
            </group>
        </group>
    )
}

// --- ELECTRIC EFFECT ---
// Sparking electric death (good for elites)
const ElectricEffect = ({ data }: { data: DeathEffect }) => {
    const groupRef = useRef<THREE.Group>(null)
    const { isPaused } = useGameSettings()
    const timeRef = useRef(0)

    const arcs = useMemo(() => {
        return Array.from({ length: 12 }, () => ({
            angle: Math.random() * Math.PI * 2,
            length: 5 + Math.random() * 15,
            thickness: 0.2 + Math.random() * 0.3,
            phaseOffset: Math.random() * Math.PI * 2
        }))
    }, [])

    useFrame((_, delta) => {
        if (isPaused || !groupRef.current) return
        timeRef.current += delta * 30
        const age = (Date.now() - data.createdAt) / 1000
        const progress = Math.min(age / 0.8, 1)

        groupRef.current.children.forEach((child, i) => {
            if (child instanceof THREE.Mesh) {
                const arc = arcs[i]
                if (!arc) return

                // Jitter position
                const jitter = Math.sin(timeRef.current + arc.phaseOffset) * 2
                const angle = arc.angle + jitter * 0.1
                child.position.set(
                    Math.cos(angle) * arc.length * data.scale * (0.5 + progress * 0.5),
                    Math.sin(angle) * arc.length * data.scale * (0.5 + progress * 0.5),
                    jitter
                )
                child.lookAt(data.position)

                // Flicker opacity
                const flicker = Math.abs(Math.sin(timeRef.current * 2 + i))
                const mat = child.material as THREE.MeshBasicMaterial
                mat.opacity = (1 - progress) * flicker

                // Scale based on progress
                child.scale.set(
                    arc.thickness * data.scale,
                    arc.thickness * data.scale,
                    arc.length * data.scale * (1 - progress * 0.5)
                )
            }
        })
    })

    return (
        <group position={data.position}>
            {/* Central spark */}
            <mesh>
                <sphereGeometry args={[data.scale * 2, 8, 8]} />
                <meshBasicMaterial
                    color="#ffffff"
                    transparent
                    opacity={0.8}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
            {/* Electric arcs */}
            <group ref={groupRef}>
                {arcs.map((_, i) => (
                    <mesh key={i}>
                        <boxGeometry args={[1, 1, 1]} />
                        <meshBasicMaterial
                            color={i % 2 === 0 ? '#88ccff' : '#ffffff'}
                            transparent
                            opacity={1}
                            blending={THREE.AdditiveBlending}
                            depthWrite={false}
                        />
                    </mesh>
                ))}
            </group>
        </group>
    )
}

// Effect type to component mapping
const EffectComponents: Record<DeathEffectType, React.FC<{ data: DeathEffect }>> = {
    disintegrate: DisintegrateEffect,
    shatter: ShatterEffect,
    vaporize: VaporizeEffect,
    implode: ImplodeEffect,
    electric: ElectricEffect
}

export const DeathEffectsRenderer = () => {
    const { effects } = useDeathEffectsStore()

    // Filter active effects
    const now = Date.now()
    const activeEffects = effects.filter(e => now - e.createdAt < 1500)

    return (
        <group>
            {activeEffects.map(e => {
                const Component = EffectComponents[e.effectType]
                return <Component key={e.id} data={e} />
            })}
        </group>
    )
}
