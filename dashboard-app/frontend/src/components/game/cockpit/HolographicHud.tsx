import { Text } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'

export interface HudData {
    stageLabel: string
    stageObjective: string
    bossHealth: number | null // 0-1
    energy: number // 0-100
    shields: number // 0-100
    integrity: number // 0-100
    overcharge: number // 0-100 - builds from kills, middle mouse to activate turbo
    score: number
    level: number
}

// Default initial data to prevent crashes
export const DEFAULT_HUD_DATA: HudData = {
    stageLabel: '',
    stageObjective: '',
    bossHealth: null,
    energy: 100,
    shields: 100,
    integrity: 100,
    overcharge: 0,
    score: 0,
    level: 1
}

export const HolographicHud = ({ hudRef }: { hudRef: React.MutableRefObject<HudData> }) => {
    // Refs for animated bars
    const shieldBarRef = useRef<THREE.Group>(null)
    const hullBarRef = useRef<THREE.Group>(null)
    const energyBarRef = useRef<THREE.Group>(null)
    const overchargeBarRef = useRef<THREE.Group>(null)
    const bossBarRef = useRef<THREE.Group>(null)

    // Refs for Text components (Troika-three-text instances)
    const scoreTextRef = useRef<any>(null)
    const levelTextRef = useRef<any>(null)
    const stageLabelRef = useRef<any>(null)
    const stageObjRef = useRef<any>(null)

    // Internal state for boss bar visibility toggling (rare update, safe for state)
    // Actually, let's just control opacity/scale in useFrame to avoid ANY re-renders
    const bossGroupRef = useRef<THREE.Group>(null)

    useFrame((_, delta) => {
        const data = hudRef.current

        // Smooth bar animation
        if (shieldBarRef.current) {
            const target = Math.max(0, data.shields / 100)
            shieldBarRef.current.scale.x = THREE.MathUtils.lerp(shieldBarRef.current.scale.x, target, delta * 5)
        }
        if (hullBarRef.current) {
            const target = Math.max(0, data.integrity / 100)
            hullBarRef.current.scale.x = THREE.MathUtils.lerp(hullBarRef.current.scale.x, target, delta * 5)
        }
        if (energyBarRef.current) {
            const target = Math.max(0, data.energy / 100)
            energyBarRef.current.scale.x = THREE.MathUtils.lerp(energyBarRef.current.scale.x, target, delta * 10)
        }
        if (overchargeBarRef.current) {
            const target = Math.max(0, data.overcharge / 100)
            overchargeBarRef.current.scale.x = THREE.MathUtils.lerp(overchargeBarRef.current.scale.x, target, delta * 8)
        }

        // Boss Bar Logic
        if (bossBarRef.current && bossGroupRef.current) {
            if (data.bossHealth !== null) {
                bossGroupRef.current.visible = true
                bossBarRef.current.scale.x = THREE.MathUtils.lerp(bossBarRef.current.scale.x, data.bossHealth, delta * 5)
            } else {
                bossGroupRef.current.visible = false
            }
        }

        // Text Updates - Check and update only if changed to minimize overhead (though assignment is cheap)
        if (scoreTextRef.current) {
            // Format score with commas
            const scoreStr = `SCORE: ${Math.floor(data.score).toLocaleString()}`
            if (scoreTextRef.current.text !== scoreStr) scoreTextRef.current.text = scoreStr
        }
        if (levelTextRef.current) {
            const levelStr = `LEVEL ${data.level}`
            if (levelTextRef.current.text !== levelStr) levelTextRef.current.text = levelStr
        }
        if (stageLabelRef.current) {
            const str = data.stageLabel.toUpperCase()
            if (stageLabelRef.current.text !== str) stageLabelRef.current.text = str
        }
        if (stageObjRef.current) {
            if (stageObjRef.current.text !== data.stageObjective) stageObjRef.current.text = data.stageObjective
        }
    })

    return (
        <group position={[0, 0, -1.8]} rotation={[0, 0, 0]}>
            {/* CENTER CROSSHAIR */}
            <group position={[0, 0, 0]}>
                {/* Outer ring */}
                <mesh>
                    <ringGeometry args={[0.025, 0.03, 32]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={0.8} toneMapped={false} />
                </mesh>
                {/* Inner dot */}
                <mesh>
                    <circleGeometry args={[0.006, 16]} />
                    <meshBasicMaterial color="#ffffff" toneMapped={false} />
                </mesh>
                {/* Crosshair lines */}
                <mesh position={[0, 0.05, 0]}>
                    <planeGeometry args={[0.003, 0.025]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={0.6} toneMapped={false} />
                </mesh>
                <mesh position={[0, -0.05, 0]}>
                    <planeGeometry args={[0.003, 0.025]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={0.6} toneMapped={false} />
                </mesh>
                <mesh position={[0.05, 0, 0]}>
                    <planeGeometry args={[0.025, 0.003]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={0.6} toneMapped={false} />
                </mesh>
                <mesh position={[-0.05, 0, 0]}>
                    <planeGeometry args={[0.025, 0.003]} />
                    <meshBasicMaterial color="#00ffff" transparent opacity={0.6} toneMapped={false} />
                </mesh>
            </group>

            {/* Left Panel: Status */}
            <group position={[-1.2, -0.6, 0]} rotation={[0, 0.2, 0]}>
                {/* Shield Bar (Cyan) */}
                <group position={[0, 0.15, 0]}>
                    <Text
                        position={[-0.6, 0, 0]}
                        fontSize={0.08}
                        color="#38bdf8"
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

                {/* Energy Bar (Yellow) */}
                <group position={[0, -0.15, 0]}>
                    <Text
                        position={[-0.6, 0, 0]}
                        fontSize={0.08}
                        color="#facc15"
                        anchorX="right"
                        anchorY="middle"
                    >
                        ENERGY
                    </Text>
                    <mesh position={[0, 0, 0]}>
                        <planeGeometry args={[1, 0.06]} />
                        <meshBasicMaterial color="#422006" transparent opacity={0.5} />
                    </mesh>
                    <group ref={energyBarRef} position={[-0.5, 0, 0.01]}>
                        <mesh position={[0.5, 0, 0]}>
                            <planeGeometry args={[1, 0.05]} />
                            <meshBasicMaterial color="#facc15" toneMapped={false} />
                        </mesh>
                    </group>
                </group>

                {/* Overcharge Bar (Magenta) - builds from kills, middle mouse to activate */}
                <group position={[0, -0.30, 0]}>
                    <Text
                        position={[-0.6, 0, 0]}
                        fontSize={0.08}
                        color="#e879f9"
                        anchorX="right"
                        anchorY="middle"
                    >
                        OVERCHARGE
                    </Text>
                    <mesh position={[0, 0, 0]}>
                        <planeGeometry args={[1, 0.06]} />
                        <meshBasicMaterial color="#4a044e" transparent opacity={0.5} />
                    </mesh>
                    <group ref={overchargeBarRef} position={[-0.5, 0, 0.01]} scale-x={0}>
                        <mesh position={[0.5, 0, 0]}>
                            <planeGeometry args={[1, 0.05]} />
                            <meshBasicMaterial color="#e879f9" toneMapped={false} />
                        </mesh>
                    </group>
                </group>
            </group>

            {/* Right Panel: Data */}
            <group position={[1.2, -0.6, 0]} rotation={[0, -0.2, 0]}>
                <Text
                    ref={scoreTextRef}
                    position={[0, 0.15, 0]}
                    fontSize={0.12}
                    color="#facc15"
                    anchorX="left"
                    anchorY="middle"
                >
                    SCORE: 0
                </Text>
                <Text
                    ref={levelTextRef}
                    position={[0, 0, 0]}
                    fontSize={0.09}
                    color="#ffffff"
                    anchorX="left"
                    anchorY="middle"
                    fillOpacity={0.8}
                >
                    LEVEL 1
                </Text>
            </group>

            {/* Center Top: Objectives */}
            <group position={[0, 0.9, 0]}>
                <group ref={bossGroupRef} position={[0, 0.2, 0]} visible={false}>
                    <Text
                        position={[0, 0.1, 0]}
                        fontSize={0.08}
                        color="#f97316"
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

                <Text
                    ref={stageLabelRef}
                    position={[0, 0, 0]}
                    fontSize={0.1}
                    color="#e2e8f0"
                    anchorX="center"
                    anchorY="middle"
                    fillOpacity={0.9}
                >
                    READY
                </Text>
                <Text
                    ref={stageObjRef}
                    position={[0, -0.12, 0]}
                    fontSize={0.06}
                    color="#94a3b8"
                    anchorX="center"
                    anchorY="middle"
                    maxWidth={2}
                    textAlign="center"
                >
                    Prepare for launch
                </Text>
            </group>

        </group>
    )
}
