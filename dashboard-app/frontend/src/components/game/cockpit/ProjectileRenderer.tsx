import { useProjectileStore, Projectile, ProjectileType } from '../systems/WeaponSystem'
import * as THREE from 'three'
import React, { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'

// Standard plasma bolt (default weapon + enemy)
const StandardProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)

    useFrame(() => {
        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
        }
    })

    const isEnemy = data.owner === 'ENEMY'
    // Use weapon colors if available, otherwise defaults
    const colors = data.colors || ['#00ffff', '#ffffff']
    const color = isEnemy ? '#ff2200' : colors[0]
    const coreColor = isEnemy ? '#ffaa00' : (colors[1] || '#ffffff')

    return (
        <group ref={groupRef} quaternion={data.rotation}>
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                {isEnemy ? (
                    <capsuleGeometry args={[0.4, 1.5, 4, 8]} />
                ) : (
                    <cylinderGeometry args={[0.15, 0.15, 8, 6]} />
                )}
                <meshBasicMaterial color={coreColor} toneMapped={false} />
            </mesh>
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
})

// Expanding wave projectile (Ripple Cannon) - vertical wave that expands outward
const ExpandingWaveProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)
    const ringRef = useRef<THREE.Mesh>(null)

    useFrame(() => {
        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
        }
        // Animate ring expansion
        if (ringRef.current && data.special?.currentRadius !== undefined) {
            const scale = Math.max(0.1, data.special.currentRadius / 10)
            ringRef.current.scale.set(scale, scale, 1)
        }
    })

    const colors = data.colors || ['#00ffff', '#67e8f9', '#ffffff']

    return (
        <group ref={groupRef}>
            {/* Expanding ring - vertical orientation (faces forward, expands in Y/X plane) */}
            <mesh ref={ringRef}>
                <ringGeometry args={[8, 10, 32]} />
                <meshBasicMaterial
                    color={colors[0]}
                    transparent
                    opacity={0.8}
                    side={THREE.DoubleSide}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
            {/* Inner glow - vertical orientation */}
            <mesh>
                <ringGeometry args={[0, 8, 32]} />
                <meshBasicMaterial
                    color={colors[1]}
                    transparent
                    opacity={0.3}
                    side={THREE.DoubleSide}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        </group>
    )
})

// Chain lightning projectile
const ChainLightningProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)
    const timeRef = useRef(Math.random() * 100)

    useFrame((_, delta) => {
        timeRef.current += delta * 20
        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
            // Jitter effect for lightning
            groupRef.current.position.x += Math.sin(timeRef.current * 3) * 0.3
            groupRef.current.position.y += Math.cos(timeRef.current * 4) * 0.3
        }
    })

    const colors = data.colors || ['#818cf8', '#a78bfa', '#ffffff']

    return (
        <group ref={groupRef} quaternion={data.rotation}>
            {/* Electric core */}
            <mesh>
                <sphereGeometry args={[0.8, 8, 8]} />
                <meshBasicMaterial color={colors[2]} toneMapped={false} />
            </mesh>
            {/* Electric arcs - multiple small cylinders at angles */}
            {[0, 60, 120, 180, 240, 300].map((angle, i) => (
                <mesh
                    key={i}
                    position={[
                        Math.cos((angle * Math.PI) / 180) * 1.5,
                        Math.sin((angle * Math.PI) / 180) * 1.5,
                        0
                    ]}
                    rotation={[0, 0, (angle * Math.PI) / 180]}
                >
                    <boxGeometry args={[0.2, 2, 0.2]} />
                    <meshBasicMaterial
                        color={colors[i % 2 === 0 ? 0 : 1]}
                        transparent
                        opacity={0.8}
                        blending={THREE.AdditiveBlending}
                        depthWrite={false}
                    />
                </mesh>
            ))}
            {/* Outer glow */}
            <mesh>
                <sphereGeometry args={[2, 12, 12]} />
                <meshBasicMaterial
                    color={colors[0]}
                    transparent
                    opacity={0.3}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        </group>
    )
})

// Piercing railgun projectile
const PiercingProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)

    useFrame(() => {
        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
        }
    })

    const colors = data.colors || ['#f472b6', '#ffffff', '#ef4444']

    return (
        <group ref={groupRef} quaternion={data.rotation}>
            {/* Long piercing beam */}
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                <cylinderGeometry args={[0.1, 0.3, 20, 6]} />
                <meshBasicMaterial color={colors[1]} toneMapped={false} />
            </mesh>
            {/* Trail effect - positioned behind the main beam */}
            <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 12]}>
                <cylinderGeometry args={[0.03, 0.08, 24, 6]} />
                <meshBasicMaterial
                    color={colors[0]}
                    transparent
                    opacity={0.4}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
            {/* Tip glow */}
            <mesh position={[0, 0, -10]}>
                <sphereGeometry args={[0.5, 8, 8]} />
                <meshBasicMaterial
                    color={colors[2]}
                    transparent
                    opacity={0.8}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        </group>
    )
})

// Spread shotgun pellet
const SpreadProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)

    useFrame(() => {
        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
        }
    })

    const colors = data.colors || ['#a3e635', '#facc15', '#ffffff']

    return (
        <group ref={groupRef} quaternion={data.rotation}>
            {/* Pellet core */}
            <mesh>
                <sphereGeometry args={[0.5, 6, 6]} />
                <meshBasicMaterial color={colors[2]} toneMapped={false} />
            </mesh>
            {/* Glow */}
            <mesh>
                <sphereGeometry args={[0.8, 8, 8]} />
                <meshBasicMaterial
                    color={colors[0]}
                    transparent
                    opacity={0.6}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        </group>
    )
})

// Gravity well projectile
const GravityProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)
    const rotationRef = useRef(0)

    useFrame((_, delta) => {
        rotationRef.current += delta * 3
        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
            groupRef.current.rotation.z = rotationRef.current
        }
    })

    const colors = data.colors || ['#6366f1', '#2dd4bf', '#ffffff']
    const isDeployed = data.special?.isDeployed
    const pullRadius = data.special?.pullRadius || 80

    return (
        <group ref={groupRef}>
            {/* Central anchor */}
            <mesh>
                <octahedronGeometry args={[isDeployed ? 2 : 1, 0]} />
                <meshBasicMaterial color={colors[2]} toneMapped={false} />
            </mesh>
            {/* Swirling rings */}
            {isDeployed && (
                <>
                    <mesh rotation={[Math.PI / 2, 0, 0]}>
                        <ringGeometry args={[pullRadius * 0.3, pullRadius * 0.35, 32]} />
                        <meshBasicMaterial
                            color={colors[0]}
                            transparent
                            opacity={0.4}
                            side={THREE.DoubleSide}
                            blending={THREE.AdditiveBlending}
                            depthWrite={false}
                        />
                    </mesh>
                    <mesh rotation={[Math.PI / 2, Math.PI / 4, 0]}>
                        <ringGeometry args={[pullRadius * 0.6, pullRadius * 0.65, 32]} />
                        <meshBasicMaterial
                            color={colors[1]}
                            transparent
                            opacity={0.3}
                            side={THREE.DoubleSide}
                            blending={THREE.AdditiveBlending}
                            depthWrite={false}
                        />
                    </mesh>
                    <mesh rotation={[Math.PI / 2, Math.PI / 2, 0]}>
                        <ringGeometry args={[pullRadius * 0.9, pullRadius * 0.95, 32]} />
                        <meshBasicMaterial
                            color={colors[0]}
                            transparent
                            opacity={0.2}
                            side={THREE.DoubleSide}
                            blending={THREE.AdditiveBlending}
                            depthWrite={false}
                        />
                    </mesh>
                </>
            )}
            {/* Outer glow */}
            <mesh>
                <sphereGeometry args={[isDeployed ? 4 : 1.5, 12, 12]} />
                <meshBasicMaterial
                    color={colors[0]}
                    transparent
                    opacity={0.3}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        </group>
    )
})

// Grid/lattice projectile
const GridProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)
    const rotationRef = useRef(0)

    useFrame((_, delta) => {
        rotationRef.current += delta * 2
        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
            groupRef.current.rotation.z = rotationRef.current
        }
    })

    const colors = data.colors || ['#fbbf24', '#ffffff', '#f59e0b']
    const gridSize = data.special?.gridSize || 60
    const lineCount = data.special?.lineCount || 6

    // Generate grid lines
    const lines = useMemo(() => {
        const result = []
        const spacing = gridSize / lineCount
        for (let i = 0; i < lineCount; i++) {
            const offset = (i - lineCount / 2 + 0.5) * spacing
            // Horizontal lines
            result.push({ pos: [0, offset, 0], rot: [0, 0, 0], key: `h${i}` })
            // Vertical lines
            result.push({ pos: [offset, 0, 0], rot: [0, 0, Math.PI / 2], key: `v${i}` })
        }
        return result
    }, [gridSize, lineCount])

    return (
        <group ref={groupRef}>
            {/* Grid lines */}
            {lines.map(({ pos, rot, key }) => (
                <mesh
                    key={key}
                    position={pos as [number, number, number]}
                    rotation={rot as [number, number, number]}
                >
                    <boxGeometry args={[gridSize, 0.3, 0.3]} />
                    <meshBasicMaterial
                        color={colors[0]}
                        transparent
                        opacity={0.7}
                        blending={THREE.AdditiveBlending}
                        depthWrite={false}
                    />
                </mesh>
            ))}
            {/* Center node */}
            <mesh>
                <octahedronGeometry args={[2, 0]} />
                <meshBasicMaterial color={colors[1]} toneMapped={false} />
            </mesh>
        </group>
    )
})

// Delayed burst projectile (Nova Spike)
const DelayedBurstProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)
    const pulseRef = useRef(0)

    useFrame((_, delta) => {
        pulseRef.current += delta * 10
        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
            // Pulse when stuck
            if (data.special?.stuckToEnemy) {
                const pulse = 1 + Math.sin(pulseRef.current) * 0.2
                groupRef.current.scale.setScalar(pulse)
            }
        }
    })

    const colors = data.colors || ['#fb923c', '#ffffff', '#dc2626']
    const isStuck = !!data.special?.stuckToEnemy

    return (
        <group ref={groupRef} quaternion={data.rotation}>
            {/* Spike body */}
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                <coneGeometry args={[0.5, 4, 6]} />
                <meshBasicMaterial color={colors[1]} toneMapped={false} />
            </mesh>
            {/* Warning glow when stuck */}
            {isStuck && (
                <mesh>
                    <sphereGeometry args={[3, 12, 12]} />
                    <meshBasicMaterial
                        color={colors[2]}
                        transparent
                        opacity={0.4}
                        blending={THREE.AdditiveBlending}
                        depthWrite={false}
                    />
                </mesh>
            )}
            {/* Outer glow */}
            <mesh>
                <sphereGeometry args={[1.5, 8, 8]} />
                <meshBasicMaterial
                    color={colors[0]}
                    transparent
                    opacity={0.5}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        </group>
    )
})

// Spiral projectile (Phase Winder) - ENHANCED: larger, more distinctive visual
const SpiralProjectile = React.memo(({ data }: { data: Projectile }) => {
    const groupRef = useRef<THREE.Group>(null)
    const bridgeRef = useRef<THREE.Mesh>(null)
    const core1Ref = useRef<THREE.Mesh>(null)
    const core2Ref = useRef<THREE.Mesh>(null)
    const halo1Ref = useRef<THREE.Mesh>(null)
    const halo2Ref = useRef<THREE.Mesh>(null)
    const phaseRef = useRef(data.special?.spiralPhase || 0)
    const pulseRef = useRef(0)

    useFrame((_, delta) => {
        const spiralSpeed = data.special?.spiralSpeed || 15
        phaseRef.current += delta * spiralSpeed
        pulseRef.current += delta * 20 // Pulse animation

        if (groupRef.current) {
            groupRef.current.position.copy(data.position)
            // Add spiral offset
            const spiralRadius = data.special?.spiralRadius || 8
            groupRef.current.position.x += Math.cos(phaseRef.current) * spiralRadius
            groupRef.current.position.y += Math.sin(phaseRef.current) * spiralRadius
        }

        // Animate pulse scale
        const pulseScale = 1 + Math.sin(pulseRef.current) * 0.15
        if (core1Ref.current) core1Ref.current.scale.setScalar(pulseScale)
        if (core2Ref.current) core2Ref.current.scale.setScalar(pulseScale)
        if (halo1Ref.current) halo1Ref.current.scale.setScalar(pulseScale * 1.3)
        if (halo2Ref.current) halo2Ref.current.scale.setScalar(pulseScale * 1.3)

        // Spin the energy bridge
        if (bridgeRef.current) {
            bridgeRef.current.rotation.z = phaseRef.current * 0.5
        }
    })

    const colors = data.colors || ['#e879f9', '#22d3ee', '#ffffff']

    return (
        <group ref={groupRef} quaternion={data.rotation}>
            {/* PRIMARY CORES - Large glowing orbs */}
            <mesh ref={core1Ref} position={[2.5, 0, 0]}>
                <sphereGeometry args={[1.2, 12, 12]} />
                <meshBasicMaterial color={colors[0]} toneMapped={false} />
            </mesh>
            <mesh ref={core2Ref} position={[-2.5, 0, 0]}>
                <sphereGeometry args={[1.2, 12, 12]} />
                <meshBasicMaterial color={colors[1]} toneMapped={false} />
            </mesh>

            {/* OUTER GLOW HALOS around cores */}
            <mesh ref={halo1Ref} position={[2.5, 0, 0]}>
                <sphereGeometry args={[1.8, 8, 8]} />
                <meshBasicMaterial
                    color={colors[0]}
                    transparent
                    opacity={0.4}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
            <mesh ref={halo2Ref} position={[-2.5, 0, 0]}>
                <sphereGeometry args={[1.8, 8, 8]} />
                <meshBasicMaterial
                    color={colors[1]}
                    transparent
                    opacity={0.4}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>

            {/* ENERGY BRIDGE connecting cores - rotating */}
            <mesh ref={bridgeRef}>
                <cylinderGeometry args={[0.4, 0.4, 5, 8]} />
                <meshBasicMaterial
                    color={colors[2]}
                    transparent
                    opacity={0.9}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>

            {/* SPIRAL TRAILS - long plasma tails */}
            <mesh rotation={[Math.PI / 2, 0, 0]} position={[1.5, 0, 0]}>
                <coneGeometry args={[0.8, 8, 6]} />
                <meshBasicMaterial
                    color={colors[0]}
                    transparent
                    opacity={0.5}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
            <mesh rotation={[Math.PI / 2, 0, 0]} position={[-1.5, 0, 0]}>
                <coneGeometry args={[0.8, 8, 6]} />
                <meshBasicMaterial
                    color={colors[1]}
                    transparent
                    opacity={0.5}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>

            {/* CENTER GLOW */}
            <mesh>
                <sphereGeometry args={[0.8, 8, 8]} />
                <meshBasicMaterial
                    color={colors[2]}
                    transparent
                    opacity={0.7}
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </mesh>
        </group>
    )
})

// Projectile type to component mapping
const ProjectileComponents: Record<ProjectileType, React.FC<{ data: Projectile }>> = {
    standard: StandardProjectile,
    enemy_plasma: StandardProjectile,
    expanding_wave: ExpandingWaveProjectile,
    chain: ChainLightningProjectile,
    piercing: PiercingProjectile,
    spread: SpreadProjectile,
    gravity: GravityProjectile,
    grid: GridProjectile,
    delayed_burst: DelayedBurstProjectile,
    spiral: SpiralProjectile
}

const ProjectileMesh = React.memo(({ data }: { data: Projectile }) => {
    const Component = ProjectileComponents[data.type] || StandardProjectile
    return <Component data={data} />
}, (prev, next) => prev.data.id === next.data.id)

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
