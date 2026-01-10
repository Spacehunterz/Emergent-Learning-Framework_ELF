import { useRef, ReactNode } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Enemy } from '../systems/EnemySystem'
import { computeEnemyVisuals, EnemyState, SizeClass, getStageMotion } from '../systems/useEnemyVisualController'

interface EnemyVisualBaseProps {
    data: Enemy
    state?: EnemyState
    sizeClass?: SizeClass
    coreContent: ReactNode
    energyContent?: ReactNode
    noiseContent?: ReactNode
    baseScale?: number
}

export const EnemyVisualBase = ({
    data,
    state = 'idle',
    sizeClass = 'medium',
    coreContent,
    energyContent,
    noiseContent,
    baseScale = 18,
}: EnemyVisualBaseProps) => {
    const rootRef = useRef<THREE.Group>(null)
    const coreRef = useRef<THREE.Group>(null)
    const energyRef = useRef<THREE.Group>(null)
    const noiseRef = useRef<THREE.Group>(null)
    const timeRef = useRef(0)
    const beatRef = useRef(0)
    const lastHpRef = useRef(data.hp)
    const damageFlashRef = useRef(0)

    const stageMotion = getStageMotion(data.stage)

    useFrame((frameState, delta) => {
        if (!rootRef.current) return

        timeRef.current += delta
        beatRef.current = (beatRef.current + delta * 0.5) % 1

        // Update damage flash tracking
        if (data.hp < lastHpRef.current) {
            damageFlashRef.current = 1
        }
        lastHpRef.current = data.hp
        damageFlashRef.current = Math.max(0, damageFlashRef.current - delta * 3)

        const controller = computeEnemyVisuals(
            {
                type: data.type,
                stage: data.stage,
                hp: data.hp,
                maxHp: data.maxHp,
                state,
                speed: data.velocity?.length() || 0,
                seed: data.seed,
                sizeClass,
                distance: data.position.length(),
                lastHp: lastHpRef.current,
                damageFlashValue: damageFlashRef.current,
            },
            timeRef.current,
            beatRef.current
        )

        rootRef.current.position.copy(data.position)

        const spawnEase = Math.min(1, (Date.now() - data.createdAt) / 500)
        rootRef.current.scale.setScalar(spawnEase * baseScale * controller.coreScale)

        if (controller.glitchAmount > 0) {
            rootRef.current.position.x += (Math.random() - 0.5) * controller.glitchAmount * 3
            rootRef.current.position.y += (Math.random() - 0.5) * controller.glitchAmount * 3
        }

        rootRef.current.position.x += controller.wobble.x * stageMotion.wobbleScale
        rootRef.current.position.y += controller.wobble.y * stageMotion.wobbleScale
        rootRef.current.position.z += controller.wobble.z * stageMotion.wobbleScale

        if (coreRef.current) {
            coreRef.current.rotation.y += delta * stageMotion.rotSpeed
            coreRef.current.rotation.x += delta * stageMotion.rotSpeed * 0.3
        }

        if (energyRef.current) {
            energyRef.current.rotation.y -= delta * stageMotion.rotSpeed * 0.7
            energyRef.current.rotation.z += delta * stageMotion.rotSpeed * 0.2
            energyRef.current.scale.setScalar(controller.energyScale / controller.coreScale)

            energyRef.current.children.forEach((child) => {
                if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshBasicMaterial) {
                    child.material.opacity = controller.energyOpacity * spawnEase
                }
            })
        }

        if (noiseRef.current) {
            noiseRef.current.children.forEach((child) => {
                if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshBasicMaterial) {
                    child.material.opacity = controller.noiseOpacity * spawnEase
                }
            })
        }
    })

    return (
        <group ref={rootRef} scale={0}>
            <group ref={coreRef} name="core">
                {coreContent}
            </group>
            {energyContent && (
                <group ref={energyRef} name="energy">
                    {energyContent}
                </group>
            )}
            {noiseContent && (
                <group ref={noiseRef} name="noise">
                    {noiseContent}
                </group>
            )}
        </group>
    )
}

interface CoreMeshProps {
    geometry: ReactNode
    color: string
    opacity?: number
    wireframe?: boolean
}

export const CoreMesh = ({ geometry, color, opacity = 0.9, wireframe = true }: CoreMeshProps) => (
    <mesh>
        {geometry}
        <meshBasicMaterial color={color} wireframe={wireframe} transparent opacity={opacity} />
    </mesh>
)

interface EnergyShellProps {
    geometry: ReactNode
    color: string
    scale?: number
    opacity?: number
}

export const EnergyShell = ({ geometry, color, scale = 1.3, opacity = 0.5 }: EnergyShellProps) => (
    <mesh scale={scale}>
        {geometry}
        <meshBasicMaterial color={color} wireframe transparent opacity={opacity} />
    </mesh>
)

interface OrbitSatelliteProps {
    count: number
    radius: number
    geometry: ReactNode
    color: string
    scale?: number
    opacity?: number
}

export const OrbitSatellites = ({ count, radius, geometry, color, scale = 0.3, opacity = 0.7 }: OrbitSatelliteProps) => {
    const groupRef = useRef<THREE.Group>(null)

    useFrame((state) => {
        if (!groupRef.current) return
        groupRef.current.rotation.y = state.clock.elapsedTime * 0.5
        groupRef.current.rotation.x = state.clock.elapsedTime * 0.2
    })

    return (
        <group ref={groupRef}>
            {Array.from({ length: count }).map((_, i) => {
                const angle = (i / count) * Math.PI * 2
                const x = Math.cos(angle) * radius
                const z = Math.sin(angle) * radius
                return (
                    <mesh key={i} position={[x, 0, z]} scale={scale}>
                        {geometry}
                        <meshBasicMaterial color={color} wireframe transparent opacity={opacity} />
                    </mesh>
                )
            })}
        </group>
    )
}

interface GhostTrailProps {
    positions: THREE.Vector3[]
    geometry: ReactNode
    color: string
    baseScale?: number
    baseOpacity?: number
}

export const GhostTrail = ({ positions, geometry, color, baseScale = 0.3, baseOpacity = 0.4 }: GhostTrailProps) => (
    <>
        {positions.map((pos, i) => (
            <mesh key={i} position={pos} scale={baseScale - i * 0.05}>
                {geometry}
                <meshBasicMaterial color={color} transparent opacity={baseOpacity - i * 0.08} />
            </mesh>
        ))}
    </>
)
