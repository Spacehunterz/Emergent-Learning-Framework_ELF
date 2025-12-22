import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { usePowerupStore, Powerup } from '../systems/PowerupSystem'
import * as THREE from 'three'

const PowerupMesh = ({ data }: { data: Powerup }) => {
    const ref = useRef<THREE.Group>(null)

    useFrame((state, delta) => {
        if (!ref.current) return
        ref.current.rotation.y += delta * 2
        ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 3) * 0.2

        // Bobbing
        ref.current.position.y = data.position.y + Math.sin(state.clock.elapsedTime * 2) * 0.5
    })

    const color = useMemo(() => {
        if (data.type === 'shield') return '#38bdf8' // Cyan/Blue
        if (data.type === 'hull') return '#ef4444'   // Red
        if (data.type === 'rapid') return '#eab308'  // Yellow
        return '#ffffff'
    }, [data.type])

    return (
        <group ref={ref} position={data.position}>
            {/* Glow / Halo */}
            <mesh>
                <sphereGeometry args={[1.5, 16, 16]} />
                <meshBasicMaterial color={color} transparent opacity={0.3} wireframe />
            </mesh>
            <pointLight distance={10} intensity={2} color={color} />

            {/* Icon Geometry */}
            {data.type === 'shield' && (
                <group scale={0.6}>
                    <mesh rotation={[0, 0, 0]}>
                        <boxGeometry args={[1, 3, 0.5]} />
                        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
                    </mesh>
                    <mesh rotation={[0, 0, Math.PI / 2]}>
                        <boxGeometry args={[1, 3, 0.5]} />
                        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
                    </mesh>
                </group>
            )}

            {data.type === 'hull' && (
                <mesh scale={0.7} rotation={[Math.PI, 0, 0]}>
                    <octahedronGeometry args={[1.5, 0]} />
                    <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
                </mesh>
            )}

            {data.type === 'rapid' && (
                <group scale={0.6} rotation={[0, 0, Math.PI / 4]}>
                    <mesh position={[0.2, 0.5, 0]}>
                        <boxGeometry args={[0.5, 2.5, 0.5]} />
                        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
                    </mesh>
                    <mesh position={[-0.2, -0.5, 0]}>
                        <boxGeometry args={[0.5, 2.5, 0.5]} />
                        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
                    </mesh>
                </group>
            )}
        </group>
    )
}

export const PowerupRenderer = () => {
    const powerups = usePowerupStore(s => s.powerups)
    const expireOldPowerups = usePowerupStore(s => s.expireOldPowerups)

    useFrame(() => {
        // Run cleanup occasionally - or every frame is fine for small N
        expireOldPowerups()
    })

    return (
        <group>
            {powerups.map(p => (
                <PowerupMesh key={p.id} data={p} />
            ))}
        </group>
    )
}
