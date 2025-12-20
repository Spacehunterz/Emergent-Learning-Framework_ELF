import { Text } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'
import { useGame } from '../../../context/GameContext'
import { usePlayerState } from './PlayerShip'

interface HudProps {
    stageLabel: string
    stageObjective: string
    bossHealth: number | null
}

export const HolographicHud = ({ stageLabel, stageObjective, bossHealth }: HudProps) => {
    const { score, level } = useGame()
    const { hull, maxHull, shields, maxShields } = usePlayerState()

    // Alias hull to health for consistency with existing ref logic
    const health = hull
    const maxHealth = maxHull

    // Refs for animated bars
    const shieldBarRef = useRef<THREE.Group>(null)
    const hullBarRef = useRef<THREE.Group>(null)
    const bossBarRef = useRef<THREE.Group>(null)

    useFrame((_, delta) => {
        // Smooth bar animation
        if (shieldBarRef.current) {
            const target = Math.max(0, shields / maxShields)
            shieldBarRef.current.scale.x = THREE.MathUtils.lerp(shieldBarRef.current.scale.x, target, delta * 5)
        }
        if (hullBarRef.current) {
            const target = Math.max(0, health / maxHealth)
            hullBarRef.current.scale.x = THREE.MathUtils.lerp(hullBarRef.current.scale.x, target, delta * 5)
        }
        if (bossBarRef.current && bossHealth !== null) {
            bossBarRef.current.scale.x = THREE.MathUtils.lerp(bossBarRef.current.scale.x, bossHealth, delta * 5)
        }
    })

    const fontUrl = 'https://fonts.gstatic.com/s/teko/v15/LYjCdG7kmE0gdQhfr-IF.woff'

    return (
        <group position={[0, 0, -1.8]} rotation={[0, 0, 0]}>
            {/* Left Panel: Status */}
            <group position={[-1.2, -0.6, 0]} rotation={[0, 0.2, 0]}>
                {/* Shield Bar (Cyan) */}
                <group position={[0, 0.15, 0]}>
                    <Text
                        position={[-0.6, 0, 0]}
                        fontSize={0.08}
                        color="#38bdf8"
                        font={fontUrl}
                        anchorX="right"
                        anchorY="middle"
                    >
                        SHIELDS
                    </Text>
                    {/* Bar Background */}
                    <mesh position={[0, 0, 0]}>
                        <planeGeometry args={[1, 0.06]} />
                        <meshBasicMaterial color="#0c4a6e" transparent opacity={0.5} />
                    </mesh>
                    {/* Bar Fill */}
                    <group ref={shieldBarRef} position={[-0.5, 0, 0.01]}>
                        <mesh position={[0.5, 0, 0]}>
                            <planeGeometry args={[1, 0.05]} />
                            <meshBasicMaterial color="#38bdf8" toneMapped={false} />
                        </mesh>
                    </group>
                </group>

                {/* Hull Bar (Red) */}
                <group position={[0, 0, 0]}>
                    <Text
                        position={[-0.6, 0, 0]}
                        fontSize={0.08}
                        color="#f43f5e"
                        font={fontUrl}
                        anchorX="right"
                        anchorY="middle"
                    >
                        INTEGRITY
                    </Text>
                    <mesh position={[0, 0, 0]}>
                        <planeGeometry args={[1, 0.06]} />
                        <meshBasicMaterial color="#881337" transparent opacity={0.5} />
                    </mesh>
                    <group ref={hullBarRef} position={[-0.5, 0, 0.01]}>
                        <mesh position={[0.5, 0, 0]}>
                            <planeGeometry args={[1, 0.05]} />
                            <meshBasicMaterial color="#f43f5e" toneMapped={false} />
                        </mesh>
                    </group>
                </group>
            </group>

            {/* Right Panel: Data */}
            <group position={[1.2, -0.6, 0]} rotation={[0, -0.2, 0]}>
                <Text
                    position={[0, 0.15, 0]}
                    fontSize={0.12}
                    color="#facc15"
                    font={fontUrl}
                    anchorX="left"
                    anchorY="middle"
                >
                    {`SCORE: ${score.toLocaleString()}`}
                </Text>
                <Text
                    position={[0, 0, 0]}
                    fontSize={0.09}
                    color="#ffffff"
                    font={fontUrl}
                    anchorX="left"
                    anchorY="middle"
                    fillOpacity={0.8}
                >
                    {`LEVEL ${level}`}
                </Text>
            </group>

            {/* Center Top: Objectives */}
            <group position={[0, 0.9, 0]}>
                {bossHealth !== null && (
                    <group position={[0, 0.2, 0]}>
                        <Text
                            position={[0, 0.1, 0]}
                            fontSize={0.08}
                            color="#f97316"
                            font={fontUrl}
                            anchorX="center"
                        >
                            DREADNOUGHT CLASS DETECTED
                        </Text>
                        <mesh position={[0, 0, 0]}>
                            <planeGeometry args={[2, 0.04]} />
                            <meshBasicMaterial color="#431407" transparent opacity={0.6} />
                        </mesh>
                        <group ref={bossBarRef} position={[-1, 0, 0.01]}>
                            <mesh position={[1, 0, 0]}>
                                <planeGeometry args={[2, 0.03]} />
                                <meshBasicMaterial color="#f97316" toneMapped={false} />
                            </mesh>
                        </group>
                    </group>
                )}

                <Text
                    position={[0, 0, 0]}
                    fontSize={0.1}
                    color="#e2e8f0"
                    font={fontUrl}
                    anchorX="center"
                    anchorY="middle"
                    fillOpacity={0.9}
                >
                    {stageLabel.toUpperCase()}
                </Text>
                <Text
                    position={[0, -0.12, 0]}
                    fontSize={0.06}
                    color="#94a3b8"
                    font={fontUrl}
                    anchorX="center"
                    anchorY="middle"
                    maxWidth={2}
                    textAlign="center"
                >
                    {stageObjective}
                </Text>
            </group>

        </group>
    )
}
