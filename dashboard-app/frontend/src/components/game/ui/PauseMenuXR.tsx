import { useEffect, useRef, useState } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
// Note: Interactive removed in @react-three/xr v6 - using mesh onPointerDown instead
import { useXR } from '@react-three/xr'
import { Text } from '@react-three/drei'
import * as THREE from 'three'
import { useGame } from '../../../context/GameContext'
import { useGameSettings } from '../systems/GameSettings'

const MENU_DISTANCE = 2.2
const PANEL_WIDTH = 2.4
const PANEL_HEIGHT = 1.7

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

const MenuButton = ({
    label,
    position,
    width = 1.6,
    height = 0.28,
    color = '#0ea5e9',
    textColor = '#0b1120',
    onClick
}: {
    label: string
    position: [number, number, number]
    width?: number
    height?: number
    color?: string
    textColor?: string
    onClick: () => void
}) => (
    <group position={position}>
        <mesh onPointerDown={onClick}>
            <boxGeometry args={[width, height, 0.04]} />
            <meshStandardMaterial color={color} />
        </mesh>
        <Text
            position={[0, 0, 0.03]}
            fontSize={0.12}
            color={textColor}
            anchorX="center"
            anchorY="middle"
        >
            {label}
        </Text>
    </group>
)

const MenuStepper = ({
    label,
    value,
    min,
    max,
    step,
    position,
    onChange
}: {
    label: string
    value: number
    min: number
    max: number
    step: number
    position: [number, number, number]
    onChange: (next: number) => void
}) => (
    <group position={position}>
        <Text position={[-0.9, 0.1, 0]} fontSize={0.1} color="#e2e8f0" anchorX="left" anchorY="middle">
            {label}
        </Text>
        <Text position={[0.9, 0.1, 0]} fontSize={0.1} color="#38bdf8" anchorX="right" anchorY="middle">
            {value.toFixed(2)}
        </Text>
        <MenuButton
            label="-"
            position={[-0.5, -0.18, 0]}
            width={0.4}
            height={0.22}
            color="#1f2937"
            textColor="#e2e8f0"
            onClick={() => onChange(clamp(value - step, min, max))}
        />
        <MenuButton
            label="+"
            position={[0.5, -0.18, 0]}
            width={0.4}
            height={0.22}
            color="#1f2937"
            textColor="#e2e8f0"
            onClick={() => onChange(clamp(value + step, min, max))}
        />
    </group>
)

export const PauseMenuXR = () => {
    const { isPresenting } = useXR()
    const { camera } = useThree()
    const menuRef = useRef<THREE.Group>(null)
    const forward = useRef(new THREE.Vector3(0, 0, -1))
    const { setGameEnabled } = useGame()
    const {
        sensitivityX,
        sensitivityY,
        smoothness,
        setSensitivityX,
        setSensitivityY,
        setSmoothness,
        isPaused,
        setPaused
    } = useGameSettings()
    const [exitHint, setExitHint] = useState(false)

    useEffect(() => {
        if (isPaused) {
            setExitHint(false)
        }
    }, [isPaused])

    useFrame(() => {
        if (!menuRef.current) return
        if (!isPaused) return
        forward.current.set(0, 0, -1).applyQuaternion(camera.quaternion)
        menuRef.current.position.copy(camera.position).add(forward.current.multiplyScalar(MENU_DISTANCE))
        menuRef.current.quaternion.copy(camera.quaternion)
    })

    if (!isPresenting || !isPaused) return null

    const handleResume = () => setPaused(false)
    const handleExitToDashboard = () => {
        setPaused(false)
        setGameEnabled(false)
    }
    const handleExitToDesktop = () => {
        setExitHint(false)
        window.close()
        setTimeout(() => {
            if (!window.closed) {
                setExitHint(true)
            }
        }, 200)
    }

    return (
        <group ref={menuRef}>
            {/* Background overlay - click to resume */}
            <mesh position={[0, 0, -0.06]} onPointerDown={handleResume}>
                <planeGeometry args={[6, 4]} />
                <meshBasicMaterial color="#000000" transparent opacity={0.25} />
            </mesh>

            <mesh>
                <planeGeometry args={[PANEL_WIDTH, PANEL_HEIGHT]} />
                <meshStandardMaterial color="#0b1220" transparent opacity={0.95} />
            </mesh>

            <Text position={[0, 0.7, 0.02]} fontSize={0.16} color="#38bdf8" anchorX="center" anchorY="middle">
                SYSTEM PAUSED
            </Text>

            <MenuStepper
                label="Horizontal Sens (X)"
                value={sensitivityX}
                min={0.1}
                max={5.0}
                step={0.1}
                position={[0, 0.35, 0.02]}
                onChange={setSensitivityX}
            />
            <MenuStepper
                label="Vertical Sens (Y)"
                value={sensitivityY}
                min={0.1}
                max={5.0}
                step={0.1}
                position={[0, 0.05, 0.02]}
                onChange={setSensitivityY}
            />
            <MenuStepper
                label="Smoothness"
                value={smoothness}
                min={0}
                max={0.5}
                step={0.02}
                position={[0, -0.25, 0.02]}
                onChange={setSmoothness}
            />

            <MenuButton
                label="RESUME"
                position={[0, -0.6, 0.02]}
                width={1.6}
                color="#0ea5e9"
                textColor="#0b1120"
                onClick={handleResume}
            />
            <MenuButton
                label="EXIT TO DATA PLANETS"
                position={[0, -0.92, 0.02]}
                width={1.6}
                color="#475569"
                textColor="#e2e8f0"
                onClick={handleExitToDashboard}
            />
            <MenuButton
                label="EXIT TO DESKTOP"
                position={[0, -1.22, 0.02]}
                width={1.6}
                color="#ef4444"
                textColor="#0b1120"
                onClick={handleExitToDesktop}
            />

            {exitHint && (
                <Text position={[0, -1.48, 0.02]} fontSize={0.08} color="#fbbf24" anchorX="center" anchorY="middle">
                    Close this tab to exit.
                </Text>
            )}
        </group>
    )
}
