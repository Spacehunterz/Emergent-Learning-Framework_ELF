import React, { Suspense, useEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Stars, Html } from '@react-three/drei'
import { useXR } from '@react-three/xr'
import * as THREE from 'three'
import { useGame } from '../../../context/GameContext'
import type { HudData } from './HolographicHud'
import { HolographicHud, DEFAULT_HUD_DATA } from './HolographicHud'
import { ProjectileRenderer } from './ProjectileRenderer'
import { CollisionManager } from '../systems/CollisionManager'
import { useEnemyStore, Enemy } from '../systems/EnemySystem'
import { useProjectileStore } from '../systems/WeaponSystem'
import { useSound } from '../systems/SoundManager'
import { WaveManager } from '../systems/WaveManager'
import { ExplosionRenderer } from '../systems/ExplosionManager'
import { DeathEffectsRenderer } from '../systems/DeathEffectsManager'
import { useGameSettings } from '../systems/GameSettings'
import { PauseMenuXR } from '../ui/PauseMenuXR'
import { GameOverScreen } from '../ui/GameOverScreen'
import { FloatingTextRenderer } from '../systems/FloatingTextManager'
import { useExplosionStore } from '../systems/ExplosionManager'
import { PickupRenderer, usePickupStore } from '../systems/PickupSystem'
import { usePlayerWeaponStore } from '../systems/PlayerWeaponStore'
import { WEAPON_TYPES } from '../systems/WeaponTypes'

// Stage-specific enemy meshes
import {
    Stage2Asteroid, Stage2Drone, Stage2Fighter, Stage2Elite, Stage2Boss
} from '../enemies/Stage2Enemies'
import {
    Stage3Asteroid, Stage3Drone, Stage3Fighter, Stage3Elite, Stage3Boss
} from '../enemies/Stage3Enemies'
import {
    Stage4Asteroid, Stage4Drone, Stage4Fighter, Stage4Elite, Stage4Boss
} from '../enemies/Stage4Enemies'
import {
    Stage5Asteroid, Stage5Drone, Stage5Fighter, Stage5Elite, Stage5Boss
} from '../enemies/Stage5Enemies'
import {
    Stage6Asteroid, Stage6Drone, Stage6Fighter, Stage6Elite, Stage6Boss
} from '../enemies/Stage6Enemies'
import {
    Stage7Asteroid, Stage7Drone, Stage7Fighter, Stage7Elite, Stage7Boss
} from '../enemies/Stage7Enemies'
import {
    Stage8Asteroid, Stage8Drone, Stage8Fighter, Stage8Elite, Stage8Boss
} from '../enemies/Stage8Enemies'
import {
    Stage9Asteroid, Stage9Drone, Stage9Fighter, Stage9Elite, Stage9Boss
} from '../enemies/Stage9Enemies'
import {
    Stage10Asteroid, Stage10Drone, Stage10Fighter, Stage10Elite, Stage10Boss
} from '../enemies/Stage10Enemies'
import {
    Stage11Asteroid, Stage11Drone, Stage11Fighter, Stage11Elite, Stage11Boss
} from '../enemies/Stage11Enemies'
import {
    Stage12Asteroid, Stage12Drone, Stage12Fighter, Stage12Elite, Stage12Boss
} from '../enemies/Stage12Enemies'
import {
    Stage13Asteroid, Stage13Drone, Stage13Fighter, Stage13Elite, Stage13Boss
} from '../enemies/Stage13Enemies'
import {
    Stage14Asteroid, Stage14Drone, Stage14Fighter, Stage14Elite, Stage14Boss
} from '../enemies/Stage14Enemies'
import {
    Stage15Asteroid, Stage15Drone, Stage15Fighter, Stage15Elite, Stage15Boss
} from '../enemies/Stage15Enemies'
import {
    Stage16Asteroid, Stage16Drone, Stage16Fighter, Stage16Elite, Stage16Boss
} from '../enemies/Stage16Enemies'
import {
    Stage17Asteroid, Stage17Drone, Stage17Fighter, Stage17Elite, Stage17Boss
} from '../enemies/Stage17Enemies'
import {
    Stage18Asteroid, Stage18Drone, Stage18Fighter, Stage18Elite, Stage18Boss
} from '../enemies/Stage18Enemies'
import {
    Stage19Asteroid, Stage19Drone, Stage19Fighter, Stage19Elite, Stage19Boss
} from '../enemies/Stage19Enemies'
import {
    Stage20Asteroid, Stage20Drone, Stage20Fighter, Stage20Elite, Stage20Boss
} from '../enemies/Stage20Enemies'

// --- AMBIENCE CONTROLLER ---
// Manages background ambience sound based on game state
const AmbienceController = () => {
    const sound = useSound()
    const { isGameOver } = useGame()
    const { isPaused } = useGameSettings()

    useEffect(() => {
        // Start ambience when component mounts (game starts)
        sound.startAmbience()

        // Cleanup: stop ambience when component unmounts (game ends)
        return () => {
            sound.stopAmbience()
        }
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    // Stop ambience on game over or pause, restart when resumed
    useEffect(() => {
        if (isGameOver || isPaused) {
            sound.stopAmbience()
        } else {
            sound.startAmbience()
        }
    }, [isGameOver, isPaused, sound])

    return null
}

// --- CONSTANTS ---
const INPUT = {
    yawSpeed: 0.003,
    pitchSpeed: 0.0028,
    damp: 40
}

const LIMITS = {
    yaw: Math.PI / 2,
    pitchMin: -Math.PI / 6, // Allow looking down ~30 degrees
    pitchMax: Math.PI / 3   // Allow looking up ~60 degrees (was ~85, too extreme)
}

const LASER = {
    speed: 150,
    lifetime: 2.5,
    cooldown: 0.5, // 2 shots per second max
    radius: 0.35,
    energyCost: 5,
    regenRate: 25
}

const GUN_OFFSETS = [
    new THREE.Vector3(-3.2, -2.0, -3.5), // Lowered to mount height
    new THREE.Vector3(3.2, -2.0, -3.5)
]

// --- WIREFRAME VISUAL COMPONENTS ---

// Spawn animation duration in ms
const SPAWN_DURATION = 600

// Helper: calculate spawn easing (0->1 over SPAWN_DURATION)
const getSpawnEase = (createdAt: number) => {
    const age = Date.now() - createdAt
    const t = Math.min(1, age / SPAWN_DURATION)
    return 1 - Math.pow(1 - t, 3) // Ease out cubic
}

// Neon wireframe asteroid - tumbling geometric crystal
const AsteroidMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const innerMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const ringRef = useRef<THREE.Mesh>(null)
    const ringMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const shardRef = useRef<THREE.Mesh>(null)
    const shardMatRef = useRef<THREE.MeshBasicMaterial>(null)

    const rotSpeed = useMemo(() => ({
        x: 0.3 + Math.random() * 0.4,
        y: 0.2 + Math.random() * 0.3,
        z: 0.1 + Math.random() * 0.2
    }), [])
    const baseScale = useMemo(() => 36 + Math.random() * 24, []) // 2x size
    const geoType = useMemo(() => Math.floor(data.seed * 3), [data.seed])

    // Health-based color
    const healthPct = data.hp / data.maxHp
    const color = healthPct > 0.5 ? '#ff6600' : healthPct > 0.25 ? '#ffff00' : '#ff0044'

    useFrame((state, delta) => {
        if (!ref.current) return
        const t = state.clock.getElapsedTime()
        const phase = data.seed * Math.PI * 2
        ref.current.position.copy(data.position)
        ref.current.rotation.x += rotSpeed.x * delta
        ref.current.rotation.y += rotSpeed.y * delta
        ref.current.rotation.z += rotSpeed.z * delta

        // Random position jitter (occasional teleport-like movement)
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 4
            ref.current.position.y += (Math.random() - 0.5) * 4
        }

        // Per-enemy spawn animation
        const ease = getSpawnEase(data.createdAt)
        ref.current.scale.setScalar(baseScale * ease)

        // Update material opacity with pulsing effect
        const pulse = 0.85 + Math.sin(t * 6 + phase) * 0.15
        if (mainMatRef.current) {
            // Color cycling/flashing
            const glitch = Math.random() > 0.92
            if (glitch) {
                mainMatRef.current.color.set(['#ff6600', '#ffff00', '#ff0044'][Math.floor(Math.random() * 3)])
            } else {
                mainMatRef.current.color.set(color)
            }
            mainMatRef.current.opacity = pulse * ease
        }
        if (innerMatRef.current) innerMatRef.current.opacity = 0.4 * ease
        if (ringMatRef.current) ringMatRef.current.opacity = (0.5 + Math.sin(t * 8) * 0.2) * ease
        if (shardMatRef.current) shardMatRef.current.opacity = 0.6 * ease

        if (ringRef.current) {
            ringRef.current.rotation.x += delta * 0.4
            ringRef.current.rotation.y += delta * 0.6
            const ringPulse = 0.9 + Math.sin(t * 2.3 + phase) * 0.08
            ringRef.current.scale.setScalar(ringPulse)
        }

        if (shardRef.current) {
            shardRef.current.position.set(
                Math.cos(t * 1.6 + phase) * 2.4,
                Math.sin(t * 1.8 + phase) * 2.2,
                Math.sin(t * 1.3 + phase) * 1.6
            )
            shardRef.current.rotation.x += delta * 2
            shardRef.current.rotation.y += delta * 1.4
            // Jitter shard fragments
            if (Math.random() > 0.95) {
                shardRef.current.position.x += (Math.random() - 0.5) * 0.5
                shardRef.current.position.y += (Math.random() - 0.5) * 0.5
            }
        }
    })

    return (
        <group ref={ref} scale={0}>
            {/* Main crystal shape */}
            <mesh scale={1}>
                {geoType === 0 && <dodecahedronGeometry args={[1, 0]} />}
                {geoType === 1 && <icosahedronGeometry args={[1, 0]} />}
                {geoType === 2 && <octahedronGeometry args={[1, 0]} />}
                <meshBasicMaterial ref={mainMatRef} color={color} wireframe transparent opacity={0} />
            </mesh>
            {/* Inner glow */}
            <mesh scale={0.5}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={innerMatRef} color="#ffffff" wireframe transparent opacity={0} />
            </mesh>
            {/* Orbit ring */}
            <mesh ref={ringRef} scale={1.4} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1.3, 0.05, 6, 10]} />
                <meshBasicMaterial ref={ringMatRef} color="#00ffff" transparent opacity={0} />
            </mesh>
            {/* Orbiting shard */}
            <mesh ref={shardRef} scale={0.5}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={shardMatRef} color="#ffffff" wireframe transparent opacity={0} />
            </mesh>
        </group>
    )
}

// Neon wireframe drone - small fast pyramid
const DroneMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const outerMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const innerMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const haloRef = useRef<THREE.Mesh>(null)
    const haloMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const finLeftRef = useRef<THREE.Mesh>(null)
    const finRightRef = useRef<THREE.Mesh>(null)

    const healthPct = data.hp / data.maxHp
    const color = healthPct > 0.5 ? '#00ff88' : healthPct > 0.25 ? '#ffff00' : '#ff0044'

    useFrame((state, delta) => {
        if (!ref.current) return
        const t = state.clock.getElapsedTime()
        const phase = data.seed * Math.PI * 2
        ref.current.position.copy(data.position)
        ref.current.lookAt(0, 0, 0)
        ref.current.rotation.z += delta * 3 // Spin while facing player

        // Random position jitter (jerky discrete movement like Stage 18)
        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 3
            ref.current.position.y += (Math.random() - 0.5) * 2
        }

        // Per-enemy spawn animation
        const ease = getSpawnEase(data.createdAt)
        ref.current.scale.setScalar(ease * 3) // 2x size

        // Update material opacity with color cycling
        if (outerMatRef.current) {
            const glitch = Math.random() > 0.9
            if (glitch) {
                outerMatRef.current.color.set(['#00ff88', '#ffff00', '#00ffff'][Math.floor(Math.random() * 3)])
            } else {
                outerMatRef.current.color.set(color)
            }
            outerMatRef.current.opacity = (0.9 + Math.sin(t * 8) * 0.1) * ease
        }
        if (innerMatRef.current) innerMatRef.current.opacity = (0.6 + Math.sin(t * 6 + phase) * 0.2) * ease
        if (haloMatRef.current) {
            const haloPulse = 0.85 + Math.sin(t * 3 + phase) * 0.12
            haloMatRef.current.opacity = 0.5 * ease * (0.6 + haloPulse * 0.4)
            if (haloRef.current) {
                haloRef.current.rotation.z += delta * 1.4
                haloRef.current.scale.setScalar(haloPulse)
            }
        }

        const finPulse = 1 + Math.sin(t * 4 + phase) * 0.2
        if (finLeftRef.current) {
            finLeftRef.current.scale.y = finPulse
            // Jitter fins
            if (Math.random() > 0.9) finLeftRef.current.position.x = -6.5 + (Math.random() - 0.5) * 0.5
        }
        if (finRightRef.current) {
            finRightRef.current.scale.y = finPulse
            if (Math.random() > 0.9) finRightRef.current.position.x = 6.5 + (Math.random() - 0.5) * 0.5
        }
    })

    return (
        <group ref={ref} scale={0}>
            {/* Outer pyramid */}
            <mesh scale={8} rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[1, 2, 4]} />
                <meshBasicMaterial ref={outerMatRef} color={color} wireframe transparent opacity={0} />
            </mesh>
            {/* Inner core */}
            <mesh scale={4}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={innerMatRef} color="#ffffff" wireframe transparent opacity={0} />
            </mesh>
            {/* Halo ring */}
            <mesh ref={haloRef} scale={11} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1, 0.06, 6, 12]} />
                <meshBasicMaterial ref={haloMatRef} color="#66fff0" transparent opacity={0} />
            </mesh>
            {/* Energy fins */}
            <mesh ref={finLeftRef} position={[-6.5, 0, 0]} scale={[0.6, 5, 1]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color={color} wireframe transparent opacity={0.5} />
            </mesh>
            <mesh ref={finRightRef} position={[6.5, 0, 0]} scale={[0.6, 5, 1]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color={color} wireframe transparent opacity={0.5} />
            </mesh>
        </group>
    )
}

// Neon wireframe fighter - aggressive double-pyramid
const FighterMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const innerRef = useRef<THREE.Mesh>(null)
    const wingLeftRef = useRef<THREE.Mesh>(null)
    const wingRightRef = useRef<THREE.Mesh>(null)
    const spineRef = useRef<THREE.Mesh>(null)
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const wingMat1Ref = useRef<THREE.MeshBasicMaterial>(null)
    const wingMat2Ref = useRef<THREE.MeshBasicMaterial>(null)
    const coreMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const spineMatRef = useRef<THREE.MeshBasicMaterial>(null)

    const healthPct = data.hp / data.maxHp
    const color = healthPct > 0.5 ? '#ff00ff' : healthPct > 0.25 ? '#ffff00' : '#ff0044'

    useFrame((state, delta) => {
        if (!ref.current) return
        const t = state.clock.getElapsedTime()
        const phase = data.seed * Math.PI * 2
        ref.current.position.copy(data.position)
        ref.current.lookAt(0, 0, 0)

        // Visibility flickering (like Stage 18 fighter)
        const visible = Math.sin(t * 20 + phase) > -0.8
        ref.current.visible = visible

        // Random position jitter
        if (Math.random() > 0.97) {
            ref.current.position.x += (Math.random() - 0.5) * 4
            ref.current.position.y += (Math.random() - 0.5) * 3
        }

        if (innerRef.current) {
            innerRef.current.rotation.y += delta * 4
        }
        const wingWobble = Math.sin(t * 1.6 + phase) * 0.12
        if (wingLeftRef.current) {
            wingLeftRef.current.rotation.z = Math.PI / 4 + wingWobble
            // Wing jitter
            if (Math.random() > 0.92) {
                wingLeftRef.current.position.x = 12 + (Math.random() - 0.5) * 0.5
            }
        }
        if (wingRightRef.current) {
            wingRightRef.current.rotation.z = -Math.PI / 4 - wingWobble
            if (Math.random() > 0.92) {
                wingRightRef.current.position.x = -12 + (Math.random() - 0.5) * 0.5
            }
        }

        // Per-enemy spawn animation
        const ease = getSpawnEase(data.createdAt)
        ref.current.scale.setScalar(ease * 3) // 2x size

        // Update material opacity with color cycling
        if (bodyMatRef.current) {
            const glitch = Math.random() > 0.88
            if (glitch) {
                bodyMatRef.current.color.set(['#ff00ff', '#00ffff', '#ffff00'][Math.floor(Math.random() * 3)])
            } else {
                bodyMatRef.current.color.set(color)
            }
            bodyMatRef.current.opacity = (0.85 + Math.sin(t * 10) * 0.15) * ease
        }
        if (wingMat1Ref.current) wingMat1Ref.current.opacity = (0.7 + Math.sin(t * 8 + phase) * 0.2) * ease
        if (wingMat2Ref.current) wingMat2Ref.current.opacity = (0.7 + Math.sin(t * 8 + phase) * 0.2) * ease
        if (coreMatRef.current) coreMatRef.current.opacity = (0.8 + Math.sin(t * 12) * 0.2) * ease
        if (spineMatRef.current) {
            const spinePulse = 0.9 + Math.sin(t * 3 + phase) * 0.12
            spineMatRef.current.opacity = 0.6 * ease * spinePulse
            if (spineRef.current) spineRef.current.scale.setScalar(spinePulse)
        }
    })

    return (
        <group ref={ref} scale={0}>
            {/* Main body - elongated octahedron */}
            <mesh scale={[10, 10, 20]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color={color} wireframe transparent opacity={0} />
            </mesh>
            {/* Wings - two flat diamonds */}
            <mesh ref={wingLeftRef} position={[12, 0, 0]} scale={[8, 2, 10]} rotation={[0, 0, Math.PI / 4]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={wingMat1Ref} color={color} wireframe transparent opacity={0} />
            </mesh>
            <mesh ref={wingRightRef} position={[-12, 0, 0]} scale={[8, 2, 10]} rotation={[0, 0, -Math.PI / 4]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={wingMat2Ref} color={color} wireframe transparent opacity={0} />
            </mesh>
            {/* Spinning core */}
            <mesh ref={innerRef} scale={5}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={coreMatRef} color="#00ffff" wireframe transparent opacity={0} />
            </mesh>
            {/* Energy spine */}
            <mesh ref={spineRef} scale={9} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1, 0.08, 8, 16]} />
                <meshBasicMaterial ref={spineMatRef} color="#00ffff" transparent opacity={0} />
            </mesh>
        </group>
    )
}

// Elite mini-boss - larger more complex structure
const EliteMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const ring1Ref = useRef<THREE.Mesh>(null)
    const ring2Ref = useRef<THREE.Mesh>(null)
    const satellitesRef = useRef<THREE.Group>(null)
    const pulseRef = useRef<THREE.Mesh>(null)
    const centerMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const ring1MatRef = useRef<THREE.MeshBasicMaterial>(null)
    const ring2MatRef = useRef<THREE.MeshBasicMaterial>(null)
    const innerMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const pulseMatRef = useRef<THREE.MeshBasicMaterial>(null)

    const healthPct = data.hp / data.maxHp
    const color = healthPct > 0.5 ? '#ffaa00' : healthPct > 0.25 ? '#ff6600' : '#ff0044'

    useFrame((state, delta) => {
        if (!ref.current) return
        const t = state.clock.getElapsedTime()
        const phase = data.seed * Math.PI * 2
        ref.current.position.copy(data.position)
        ref.current.lookAt(0, 0, 0)

        // Random position jitter (glitch effect)
        if (Math.random() > 0.97) {
            ref.current.position.x += (Math.random() - 0.5) * 5
            ref.current.position.y += (Math.random() - 0.5) * 5
        }

        if (ring1Ref.current) ring1Ref.current.rotation.x += delta * 2
        if (ring2Ref.current) ring2Ref.current.rotation.y += delta * 2.5
        if (satellitesRef.current) satellitesRef.current.rotation.y += delta * 1.2

        // Per-enemy spawn animation
        const ease = getSpawnEase(data.createdAt)
        ref.current.scale.setScalar(ease * 3) // 2x size

        // Color cycling/flashing
        const glitch = Math.random() > 0.92
        if (centerMatRef.current) {
            if (glitch) {
                centerMatRef.current.color.set(['#ffaa00', '#ff00ff', '#00ffff'][Math.floor(Math.random() * 3)])
            }
            centerMatRef.current.opacity = ease * (glitch ? 0.5 : 0.9)
        }
        if (ring1MatRef.current) ring1MatRef.current.opacity = ease * (0.7 + Math.sin(t * 8) * 0.1)
        if (ring2MatRef.current) ring2MatRef.current.opacity = ease * (0.7 + Math.sin(t * 8 + 1) * 0.1)
        if (innerMatRef.current) innerMatRef.current.opacity = ease * (0.6 + Math.sin(t * 6) * 0.1)
        if (pulseMatRef.current) {
            const pulse = 0.9 + Math.sin(t * 2 + phase) * 0.08
            pulseMatRef.current.opacity = 0.5 * ease
            if (pulseRef.current) pulseRef.current.scale.setScalar(pulse)
        }
    })

    return (
        <group ref={ref} scale={0}>
            {/* Central dodecahedron */}
            <mesh scale={25}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={centerMatRef} color={color} wireframe transparent opacity={0} />
            </mesh>
            {/* Orbiting ring 1 */}
            <mesh ref={ring1Ref} scale={35}>
                <torusGeometry args={[1, 0.05, 8, 6]} />
                <meshBasicMaterial ref={ring1MatRef} color="#00ffff" wireframe={false} transparent opacity={0} />
            </mesh>
            {/* Orbiting ring 2 */}
            <mesh ref={ring2Ref} scale={35} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1, 0.05, 8, 6]} />
                <meshBasicMaterial ref={ring2MatRef} color="#ff00ff" wireframe={false} transparent opacity={0} />
            </mesh>
            {/* Inner icosahedron */}
            <mesh scale={12}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={innerMatRef} color="#ffffff" wireframe transparent opacity={0} />
            </mesh>
            {/* Pulse shell */}
            <mesh ref={pulseRef} scale={18}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={pulseMatRef} color="#00ffff" wireframe transparent opacity={0} />
            </mesh>
            {/* Orbiting satellites */}
            <group ref={satellitesRef}>
                <mesh position={[38, 0, 0]} scale={3}>
                    <sphereGeometry args={[1, 6, 6]} />
                    <meshBasicMaterial color="#ffffff" transparent opacity={0.6} />
                </mesh>
                <mesh position={[-38, 0, 0]} scale={3}>
                    <sphereGeometry args={[1, 6, 6]} />
                    <meshBasicMaterial color="#ffffff" transparent opacity={0.6} />
                </mesh>
                <mesh position={[0, 0, 38]} scale={3}>
                    <sphereGeometry args={[1, 6, 6]} />
                    <meshBasicMaterial color="#ffffff" transparent opacity={0.6} />
                </mesh>
            </group>
        </group>
    )
}

// Legacy ship mesh fallback (shouldn't be used now)


const BossMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const innerRef = useRef<THREE.Group>(null)
    const shieldRef = useRef<THREE.Mesh>(null)
    const shieldMatRef = useRef<THREE.MeshBasicMaterial>(null)

    useFrame((state, delta) => {
        if (!ref.current) return
        const t = state.clock.getElapsedTime()

        // WARP IN EFFECT
        const age = Date.now() - (data.createdAt || 0)
        const warpDuration = 1800

        if (age < warpDuration) {
            const p = age / warpDuration
            const ease = 1 - Math.pow(2, -10 * p)
            const startZ = -4000
            const currentZ = THREE.MathUtils.lerp(startZ, data.position.z, ease)
            ref.current.position.set(data.position.x, data.position.y, currentZ)
            const stretch = THREE.MathUtils.lerp(5, 1, ease)
            ref.current.scale.set(1, 1, stretch)
        } else {
            ref.current.position.copy(data.position)
            ref.current.scale.set(1, 1, 1)

            // Random teleport jitter (menacing glitch effect)
            if (Math.random() > 0.98) {
                ref.current.position.x += (Math.random() - 0.5) * 8
                ref.current.position.y += (Math.random() - 0.5) * 8
            }
        }

        // Rotate inner structure with variable speed
        if (innerRef.current) {
            const rotSpeed = Math.random() > 0.95 ? 2 : 1
            innerRef.current.rotation.x += delta * 0.3 * rotSpeed
            innerRef.current.rotation.y += delta * 0.5 * rotSpeed
        }

        if (shieldRef.current) {
            shieldRef.current.scale.setScalar(1 + Math.sin(t * 0.8) * 0.03)
            // Occasional shield flicker
            shieldRef.current.visible = Math.random() > 0.02
        }
        if (shieldMatRef.current) {
            // Pulsing opacity with color cycling
            const glitch = Math.random() > 0.92
            if (glitch) {
                shieldMatRef.current.color.set(['#00ffff', '#ff00ff', '#ffff00'][Math.floor(Math.random() * 3)])
            }
            shieldMatRef.current.opacity = (0.25 + Math.sin(t * 1.1) * 0.08) * (glitch ? 1.5 : 1)
        }
    })

    // Health-based color (green -> yellow -> red)
    const healthPct = data.hp / data.maxHp
    const baseColor = healthPct > 0.5 ? '#00ffff' : healthPct > 0.25 ? '#ffff00' : '#ff0044'

    return (
        <group ref={ref}>
            {/* Outer Octahedron Frame */}
            <mesh scale={50}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color={baseColor} wireframe transparent opacity={0.9} />
            </mesh>

            {/* Inner rotating icosahedron */}
            <group ref={innerRef}>
                <mesh scale={30}>
                    <icosahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#ff00ff" wireframe transparent opacity={0.7} />
                </mesh>

                {/* Core tetrahedron */}
                <mesh scale={15}>
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.8} />
                </mesh>
            </group>

            {/* Glowing core */}
            <mesh scale={8}>
                <sphereGeometry args={[1, 8, 8]} />
                <meshBasicMaterial color={baseColor} transparent opacity={0.6} />
            </mesh>

            {/* Energy shield */}
            <mesh ref={shieldRef} scale={65}>
                <sphereGeometry args={[1, 12, 12]} />
                <meshBasicMaterial ref={shieldMatRef} color={baseColor} wireframe transparent opacity={0.25} />
            </mesh>
        </group>
    )
}

const EntityRenderer = React.memo(({ data }: { data: Enemy }) => {
    const stage = data.stage || 1

    // Stage 1: Original meshes
    if (stage === 1) {
        if (data.type === 'asteroid') return <AsteroidMesh data={data} />
        if (data.type === 'boss') return <BossMesh data={data} />
        if (data.type === 'elite') return <EliteMesh data={data} />
        if (data.type === 'drone') return <DroneMesh data={data} />
        if (data.type === 'fighter') return <FighterMesh data={data} />
        return <FighterMesh data={data} />
    }

    // Stage 2: Cyber themed (blue/purple)
    if (stage === 2) {
        if (data.type === 'asteroid') return <Stage2Asteroid data={data} />
        if (data.type === 'boss') return <Stage2Boss data={data} />
        if (data.type === 'elite') return <Stage2Elite data={data} />
        if (data.type === 'drone') return <Stage2Drone data={data} />
        if (data.type === 'fighter') return <Stage2Fighter data={data} />
        return <Stage2Fighter data={data} />
    }

    // Stage 3: Organic themed (green/pink)
    if (stage === 3) {
        if (data.type === 'asteroid') return <Stage3Asteroid data={data} />
        if (data.type === 'boss') return <Stage3Boss data={data} />
        if (data.type === 'elite') return <Stage3Elite data={data} />
        if (data.type === 'drone') return <Stage3Drone data={data} />
        if (data.type === 'fighter') return <Stage3Fighter data={data} />
        return <Stage3Fighter data={data} />
    }

    // Stage 4: Void themed (purple/white)
    if (stage === 4) {
        if (data.type === 'asteroid') return <Stage4Asteroid data={data} />
        if (data.type === 'boss') return <Stage4Boss data={data} />
        if (data.type === 'elite') return <Stage4Elite data={data} />
        if (data.type === 'drone') return <Stage4Drone data={data} />
        if (data.type === 'fighter') return <Stage4Fighter data={data} />
        return <Stage4Fighter data={data} />
    }

    // Stage 5: Solar/Fire themed (orange/yellow/red)
    if (stage === 5) {
        if (data.type === 'asteroid') return <Stage5Asteroid data={data} />
        if (data.type === 'boss') return <Stage5Boss data={data} />
        if (data.type === 'elite') return <Stage5Elite data={data} />
        if (data.type === 'drone') return <Stage5Drone data={data} />
        if (data.type === 'fighter') return <Stage5Fighter data={data} />
        return <Stage5Fighter data={data} />
    }

    // Stage 6: Ice/Crystal themed (blue/cyan/purple)
    if (stage === 6) {
        if (data.type === 'asteroid') return <Stage6Asteroid data={data} />
        if (data.type === 'boss') return <Stage6Boss data={data} />
        if (data.type === 'elite') return <Stage6Elite data={data} />
        if (data.type === 'drone') return <Stage6Drone data={data} />
        if (data.type === 'fighter') return <Stage6Fighter data={data} />
        return <Stage6Fighter data={data} />
    }

    // Stage 7: Ancient/Relic themed (tan/bronze/gold)
    if (stage === 7) {
        if (data.type === 'asteroid') return <Stage7Asteroid data={data} />
        if (data.type === 'boss') return <Stage7Boss data={data} />
        if (data.type === 'elite') return <Stage7Elite data={data} />
        if (data.type === 'drone') return <Stage7Drone data={data} />
        if (data.type === 'fighter') return <Stage7Fighter data={data} />
        return <Stage7Fighter data={data} />
    }

    // Stage 8: Swarm/Insect themed (green/yellow)
    if (stage === 8) {
        if (data.type === 'asteroid') return <Stage8Asteroid data={data} />
        if (data.type === 'boss') return <Stage8Boss data={data} />
        if (data.type === 'elite') return <Stage8Elite data={data} />
        if (data.type === 'drone') return <Stage8Drone data={data} />
        if (data.type === 'fighter') return <Stage8Fighter data={data} />
        return <Stage8Fighter data={data} />
    }

    // Stage 9: Mechanical/Steampunk themed (copper/brass/bronze)
    if (stage === 9) {
        if (data.type === 'asteroid') return <Stage9Asteroid data={data} />
        if (data.type === 'boss') return <Stage9Boss data={data} />
        if (data.type === 'elite') return <Stage9Elite data={data} />
        if (data.type === 'drone') return <Stage9Drone data={data} />
        if (data.type === 'fighter') return <Stage9Fighter data={data} />
        return <Stage9Fighter data={data} />
    }

    // Stage 10: Cosmic/Nebula themed (purple/pink/cyan)
    if (stage === 10) {
        if (data.type === 'asteroid') return <Stage10Asteroid data={data} />
        if (data.type === 'boss') return <Stage10Boss data={data} />
        if (data.type === 'elite') return <Stage10Elite data={data} />
        if (data.type === 'drone') return <Stage10Drone data={data} />
        if (data.type === 'fighter') return <Stage10Fighter data={data} />
        return <Stage10Fighter data={data} />
    }

    // Stage 11: Toxic/Radiation themed (green/yellow)
    if (stage === 11) {
        if (data.type === 'asteroid') return <Stage11Asteroid data={data} />
        if (data.type === 'boss') return <Stage11Boss data={data} />
        if (data.type === 'elite') return <Stage11Elite data={data} />
        if (data.type === 'drone') return <Stage11Drone data={data} />
        if (data.type === 'fighter') return <Stage11Fighter data={data} />
        return <Stage11Fighter data={data} />
    }

    // Stage 12: Electric/Plasma themed (blue/white)
    if (stage === 12) {
        if (data.type === 'asteroid') return <Stage12Asteroid data={data} />
        if (data.type === 'boss') return <Stage12Boss data={data} />
        if (data.type === 'elite') return <Stage12Elite data={data} />
        if (data.type === 'drone') return <Stage12Drone data={data} />
        if (data.type === 'fighter') return <Stage12Fighter data={data} />
        return <Stage12Fighter data={data} />
    }

    // Stage 13: Shadow/Dark Matter themed (black/purple)
    if (stage === 13) {
        if (data.type === 'asteroid') return <Stage13Asteroid data={data} />
        if (data.type === 'boss') return <Stage13Boss data={data} />
        if (data.type === 'elite') return <Stage13Elite data={data} />
        if (data.type === 'drone') return <Stage13Drone data={data} />
        if (data.type === 'fighter') return <Stage13Fighter data={data} />
        return <Stage13Fighter data={data} />
    }

    // Stage 14: Mineral/Geode themed (magenta/cyan/yellow)
    if (stage === 14) {
        if (data.type === 'asteroid') return <Stage14Asteroid data={data} />
        if (data.type === 'boss') return <Stage14Boss data={data} />
        if (data.type === 'elite') return <Stage14Elite data={data} />
        if (data.type === 'drone') return <Stage14Drone data={data} />
        if (data.type === 'fighter') return <Stage14Fighter data={data} />
        return <Stage14Fighter data={data} />
    }

    // Stage 15: Fungal/Spore themed (brown/coral)
    if (stage === 15) {
        if (data.type === 'asteroid') return <Stage15Asteroid data={data} />
        if (data.type === 'boss') return <Stage15Boss data={data} />
        if (data.type === 'elite') return <Stage15Elite data={data} />
        if (data.type === 'drone') return <Stage15Drone data={data} />
        if (data.type === 'fighter') return <Stage15Fighter data={data} />
        return <Stage15Fighter data={data} />
    }

    // Stage 16: Abyssal/Deep Sea themed (dark blue/aqua)
    if (stage === 16) {
        if (data.type === 'asteroid') return <Stage16Asteroid data={data} />
        if (data.type === 'boss') return <Stage16Boss data={data} />
        if (data.type === 'elite') return <Stage16Elite data={data} />
        if (data.type === 'drone') return <Stage16Drone data={data} />
        if (data.type === 'fighter') return <Stage16Fighter data={data} />
        return <Stage16Fighter data={data} />
    }

    // Stage 17: Volcanic/Magma themed (red/orange/black)
    if (stage === 17) {
        if (data.type === 'asteroid') return <Stage17Asteroid data={data} />
        if (data.type === 'boss') return <Stage17Boss data={data} />
        if (data.type === 'elite') return <Stage17Elite data={data} />
        if (data.type === 'drone') return <Stage17Drone data={data} />
        if (data.type === 'fighter') return <Stage17Fighter data={data} />
        return <Stage17Fighter data={data} />
    }

    // Stage 18: Temporal/Glitch themed (cyan/magenta/white)
    if (stage === 18) {
        if (data.type === 'asteroid') return <Stage18Asteroid data={data} />
        if (data.type === 'boss') return <Stage18Boss data={data} />
        if (data.type === 'elite') return <Stage18Elite data={data} />
        if (data.type === 'drone') return <Stage18Drone data={data} />
        if (data.type === 'fighter') return <Stage18Fighter data={data} />
        return <Stage18Fighter data={data} />
    }

    // Stage 19: Holy/Angelic themed (white/gold)
    if (stage === 19) {
        if (data.type === 'asteroid') return <Stage19Asteroid data={data} />
        if (data.type === 'boss') return <Stage19Boss data={data} />
        if (data.type === 'elite') return <Stage19Elite data={data} />
        if (data.type === 'drone') return <Stage19Drone data={data} />
        if (data.type === 'fighter') return <Stage19Fighter data={data} />
        return <Stage19Fighter data={data} />
    }

    // Stage 20: Demonic/Hellfire themed (red/black/orange) - also default fallback
    if (data.type === 'asteroid') return <Stage20Asteroid data={data} />
    if (data.type === 'boss') return <Stage20Boss data={data} />
    if (data.type === 'elite') return <Stage20Elite data={data} />
    if (data.type === 'drone') return <Stage20Drone data={data} />
    if (data.type === 'fighter') return <Stage20Fighter data={data} />
    return <Stage20Fighter data={data} />
}, (prev, next) => prev.data.id === next.data.id && prev.data.hp === next.data.hp && prev.data.stage === next.data.stage)


// Shield bubble visual - activates on right click
const ShieldBubble = ({ active, flash }: {
    active: React.MutableRefObject<boolean>,
    flash: React.MutableRefObject<number>
}) => {
    const shieldRef = useRef<THREE.Mesh>(null)
    const matRef = useRef<THREE.MeshBasicMaterial>(null)

    useFrame((_, delta) => {
        if (!shieldRef.current || !matRef.current) return

        const targetOpacity = active.current ? 0.25 + flash.current * 0.5 : 0
        matRef.current.opacity = THREE.MathUtils.lerp(matRef.current.opacity, targetOpacity, delta * 10)

        // Pulse effect when active
        if (active.current) {
            const pulse = 1 + Math.sin(Date.now() * 0.01) * 0.02
            shieldRef.current.scale.setScalar(pulse)
        }

        // Flash color: normal = blue, hit = white
        if (flash.current > 0.1) {
            matRef.current.color.setHex(0xffffff)
        } else {
            matRef.current.color.setHex(0x4488ff)
        }
    })

    return (
        <mesh ref={shieldRef} position={[0, 0, -3]} scale={1}>
            <sphereGeometry args={[4, 24, 16]} />
            <meshBasicMaterial
                ref={matRef}
                color="#4488ff"
                transparent
                opacity={0}
                side={THREE.BackSide}
                depthWrite={false}
            />
        </mesh>
    )
}

const GunRig = ({ gunRef, recoilImpulse, weaponEnergy }: {
    gunRef: React.RefObject<THREE.Group>,
    recoilImpulse: React.MutableRefObject<number>,
    weaponEnergy: React.MutableRefObject<number>
}) => {
    const innerRef = useRef<THREE.Group>(null)
    const tipMat1Ref = useRef<THREE.MeshBasicMaterial>(null)
    const tipMat2Ref = useRef<THREE.MeshBasicMaterial>(null)
    const smoke1Ref = useRef<THREE.Group>(null)
    const smoke2Ref = useRef<THREE.Group>(null)

    // Smoke particle positions (reused each frame)
    const smokeParticles = useMemo(() =>
        Array.from({ length: 6 }, () => ({
            offset: new THREE.Vector3(),
            life: Math.random()
        })), [])

    useFrame((state, delta) => {
        if (!innerRef.current) return
        const t = state.clock.getElapsedTime()

        // Decay impulse
        recoilImpulse.current = THREE.MathUtils.lerp(recoilImpulse.current, 0, delta * 10)
        innerRef.current.position.z = recoilImpulse.current

        // Heat level (0 = cool, 1 = overheated)
        const heat = 1 - (weaponEnergy.current / 100)
        const isOverheated = weaponEnergy.current < 20

        // Barrel tip color: blue (cool) → orange → red (hot)
        const tipColor = new THREE.Color()
        if (heat < 0.3) {
            tipColor.setHex(0x38bdf8) // Blue
        } else if (heat < 0.6) {
            tipColor.lerpColors(new THREE.Color(0x38bdf8), new THREE.Color(0xffa500), (heat - 0.3) / 0.3)
        } else {
            tipColor.lerpColors(new THREE.Color(0xffa500), new THREE.Color(0xff2200), (heat - 0.6) / 0.4)
        }

        if (tipMat1Ref.current) tipMat1Ref.current.color.copy(tipColor)
        if (tipMat2Ref.current) tipMat2Ref.current.color.copy(tipColor)

        // Smoke effect when overheated
        const smokeOpacity = isOverheated ? 0.4 : 0
            ;[smoke1Ref, smoke2Ref].forEach((smokeRef, gunIdx) => {
                if (!smokeRef.current) return
                smokeRef.current.children.forEach((child, i) => {
                    if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshBasicMaterial) {
                        // Animate smoke rising
                        const particle = smokeParticles[i]
                        particle.life += delta * 2
                        if (particle.life > 1) {
                            particle.life = 0
                            particle.offset.set(
                                (Math.random() - 0.5) * 0.15,
                                0,
                                (Math.random() - 0.5) * 0.15
                            )
                        }
                        child.position.y = particle.life * 0.5
                        child.position.x = particle.offset.x + Math.sin(t * 3 + i) * 0.03
                        child.position.z = particle.offset.z
                        const scale = 0.1 + particle.life * 0.2 // 2x size
                        child.scale.setScalar(scale)
                        child.material.opacity = smokeOpacity * (1 - particle.life)
                    }
                })
            })
    })

    return (
        <group ref={gunRef}>
            {/* --- HIGH TECH DASHBOARD V2 --- */}
            {/* Main Console Slab - Lowered slightly */}
            {/* Main Console Slab - HALF HEIGHT to reveal guns */}
            <mesh position={[0, -2.25, -2.5]}>
                <boxGeometry args={[14, 0.7, 2]} />
                <meshStandardMaterial color="#0f172a" metalness={0.8} roughness={0.3} />
            </mesh>

            {/* HUD Frame - Cyan Neon Box - Frames the HUD panels */}
            <group position={[0, -1.05, -1.75]}>
                {/* Top Bar */}
                <mesh position={[0, 0.2, 0]}>
                    <boxGeometry args={[2.62, 0.02, 0.05]} />
                    <meshBasicMaterial color="#0ea5e9" toneMapped={false} />
                </mesh>
                {/* Bottom Bar */}
                <mesh position={[0, -0.25, -.1]}>
                    <boxGeometry args={[2.8, 0.02, 0.05]} />
                    <meshBasicMaterial color="#0ea5e9" toneMapped={false} />
                </mesh>
                {/* Left Bar */}
                <mesh position={[-1.3, 0, 0]}>
                    <boxGeometry args={[0.02, 0.4, 0.05]} />
                    <meshBasicMaterial color="#0ea5e9" toneMapped={false} />
                </mesh>
                {/* Right Bar */}
                <mesh position={[1.3, 0, 0]}>
                    <boxGeometry args={[0.02, 0.4, 0.05]} />
                    <meshBasicMaterial color="#0ea5e9" toneMapped={false} />
                </mesh>
            </group>

            {/* HUD Glass Backing Plate (Center) */}
            <mesh position={[0, -1.15, -.85]} rotation={[-0.1, 0, 0]}>
                <planeGeometry args={[10, 1.5]} />
                <meshBasicMaterial color="#000000" transparent opacity={0.4} />
            </mesh>

            {/* Gun Mounts - Widened to x=3.2 */}
            <mesh position={[-3.2, -2.0, -2.8]}>
                <boxGeometry args={[1, 0.6, 3]} />
                <meshStandardMaterial color="#1e293b" metalness={0.6} roughness={0.4} />
            </mesh>
            <mesh position={[3.2, -2.0, -2.8]}>
                <boxGeometry args={[1, 0.6, 3]} />
                <meshStandardMaterial color="#1e293b" metalness={0.6} roughness={0.4} />
            </mesh>

            {/* Side Pillars - Angled - Widened to frame view */}
            <mesh position={[-6.5, 0, -2.5]} rotation={[0, 0, -0.15]}>
                <boxGeometry args={[1.5, 7, 2]} />
                <meshStandardMaterial color="#020617" metalness={0.5} roughness={0.2} />
            </mesh>
            <mesh position={[6.5, 0, -2.5]} rotation={[0, 0, 0.15]}>
                <boxGeometry args={[1.5, 7, 2]} />
                <meshStandardMaterial color="#020617" metalness={0.5} roughness={0.2} />
            </mesh>

            <group ref={innerRef} name="RecoilContainer">
                {/* Lit from behind/above to ensure visibility */}
                <pointLight position={[0, 1, 0.5]} intensity={0.5} distance={5} color="#ffffff" />
                <pointLight position={[0, 0.4, -6]} intensity={1.2} distance={140} color="#dbeafe" />

                {/* Left Gun */}
                <group position={GUN_OFFSETS[0].toArray()}>
                    <mesh rotation={[Math.PI / 2, 0, 0]}>
                        <cylinderGeometry args={[0.08, 0.16, 3.2]} />
                        <meshStandardMaterial color="#94a3b8" metalness={0.4} roughness={0.6} />
                    </mesh>
                    <mesh position={[0, 0, -1.2]}>
                        <sphereGeometry args={[0.14, 12, 12]} />
                        <meshBasicMaterial ref={tipMat1Ref} color="#38bdf8" />
                    </mesh>
                    {/* Smoke particles */}
                    <group ref={smoke1Ref} position={[0, 0, -1.2]}>
                        {[0, 1, 2].map(i => (
                            <mesh key={i}>
                                <sphereGeometry args={[1, 6, 6]} />
                                <meshBasicMaterial color="#cccccc" transparent opacity={0} />
                            </mesh>
                        ))}
                    </group>
                </group>

                {/* Right Gun */}
                <group position={GUN_OFFSETS[1].toArray()}>
                    <mesh rotation={[Math.PI / 2, 0, 0]}>
                        <cylinderGeometry args={[0.08, 0.16, 3.2]} />
                        <meshStandardMaterial color="#94a3b8" metalness={0.4} roughness={0.6} />
                    </mesh>
                    <mesh position={[0, 0, -1.2]}>
                        <sphereGeometry args={[0.14, 12, 12]} />
                        <meshBasicMaterial ref={tipMat2Ref} color="#38bdf8" />
                    </mesh>
                    {/* Smoke particles */}
                    <group ref={smoke2Ref} position={[0, 0, -1.2]}>
                        {[0, 1, 2].map(i => (
                            <mesh key={i}>
                                <sphereGeometry args={[1, 6, 6]} />
                                <meshBasicMaterial color="#cccccc" transparent opacity={0} />
                            </mesh>
                        ))}
                    </group>
                </group>
            </group>
        </group>
    )
}

export const SpaceShooterScene = () => {
    const { camera, gl } = useThree()
    const mode = useXR((state) => state.mode)
    const isPresenting = mode === 'immersive-vr'
    const { rechargeShields, damageShields, shields, level, score, viewMode, setGameOver, triggerPlayerHit, isGameOver } = useGame()
    const { isPaused, showMainMenu } = useGameSettings()
    const isGamePaused = isPaused || showMainMenu // Combine pause states
    const isStaticView = viewMode === 'static'

    // SYSTEMS & STORES
    const enemies = useEnemyStore(s => s.enemies)
    const { spawnProjectile } = useProjectileStore()
    const { spawnExplosion } = useExplosionStore()
    const sound = useSound()

    // Player weapon system
    const equippedWeaponId = usePlayerWeaponStore(s => s.equippedWeaponId)
    const getEffectiveStats = usePlayerWeaponStore(s => s.getEffectiveStats)
    const shipUpgrades = usePlayerWeaponStore(s => s.shipUpgrades)
    const equippedWeapon = WEAPON_TYPES[equippedWeaponId] || WEAPON_TYPES.plasma_bolt

    // GAME STATS - Scaled by Upgrades
    const maxHull = 100 + (shipUpgrades?.hull || 0) * 25
    const maxShields = 100 + (shipUpgrades?.shield || 0) * 25
    const maxEnergy = 100 + (shipUpgrades?.energy || 0) * 20
    const powerDuration = 30 + (shipUpgrades?.power || 0) * 10 // Base 30s + 10s per level

    // Local hull tracking for cockpit mode (shields come from GameContext)
    // Fixed HUD scaling issue by normalizing values
    const hullRef = useRef(maxHull)

    // REFS
    const aimQuat = useRef(new THREE.Quaternion())
    const aimDir = useRef(new THREE.Vector3(0, 0, -1))
    const aimAngles = useRef({ yaw: 0, pitch: 0 })
    const targetAngles = useRef({ yaw: 0, pitch: 0 })
    const cockpitRef = useRef<THREE.Group>(null)
    const gunRigRef = useRef<THREE.Group>(null)
    const firing = useRef(false)
    const lastShot = useRef(0)
    const pointerLocked = useRef(false)
    const isVrRef = useRef(false)

    // HUD REF - Zero render updates
    const hudRef = useRef<HudData>(DEFAULT_HUD_DATA)

    const weaponEnergy = useRef(maxEnergy)
    const canFire = useRef(true)

    // Weapon boost state - turbo shot mode
    const weaponBoostEnd = useRef(0) // Timestamp when boost ends
    const isWeaponBoosted = () => Date.now() < weaponBoostEnd.current

    // Overcharge system - builds from kills, middle mouse to activate turbo burst
    const overchargeRef = useRef(0) // 0-100, full = 30s turbo (scaled by powerDuration)

    // Shield system - right click to activate
    const shieldActive = useRef(false)
    const shieldFlash = useRef(0) // Flash intensity on hit

    const tempVecA = useMemo(() => new THREE.Vector3(), [])
    const tempVecB = useMemo(() => new THREE.Vector3(), [])
    const tempVecC = useMemo(() => new THREE.Vector3(), [])



    // Synced Refs for HUD (No Layout Thrashing)
    useEffect(() => {
        hudRef.current.level = level
        hudRef.current.score = score
        // onHudUpdate is removed/ignored to prevent parent re-renders
    }, [level, score])

    // PLAYER DAMAGE HANDLER - Listens for player-hit events from CollisionManager
    // This handles damage in cockpit mode where PlayerShip component isn't mounted
    useEffect(() => {
        const handlePlayerHit = (event: CustomEvent<{
            damage: number,
            projectileId?: string,
            projectilePosition?: THREE.Vector3,
            projectileVelocity?: THREE.Vector3
        }>) => {
            const damage = event.detail.damage || 10

            // If shield is active, block damage and flash
            if (shieldActive.current && shields > 0) {
                shieldFlash.current = 1 // Trigger flash effect
                damageShields(damage * 0.5) // Shield takes reduced damage
                sound.playShieldHit()

                // REFLECT the projectile back at enemies!
                if (event.detail.projectilePosition && event.detail.projectileVelocity) {
                    const reflectedVelocity = event.detail.projectileVelocity.clone().negate().multiplyScalar(1.5) // Faster return
                    const reflectedDir = reflectedVelocity.clone().normalize()
                    const reflectedRot = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), reflectedDir)

                    spawnProjectile({
                        id: `reflect-${Date.now()}-${Math.random()}`,
                        position: event.detail.projectilePosition.clone(),
                        rotation: reflectedRot,
                        velocity: reflectedVelocity,
                        damage: damage * 2, // Reflected shots do double damage
                        owner: 'PLAYER', // Now owned by player so it can hit enemies
                        type: 'standard',
                        createdAt: Date.now(),
                        lifetime: 3
                    })
                }

                return // Block the hit
            }

            triggerPlayerHit() // Update lastHitTime for visual feedback

            // Check shields first
            if (shields > 0) {
                damageShields(damage)
                sound.playShieldHit()
            } else {
                // Shields depleted - damage hull
                hullRef.current = Math.max(0, hullRef.current - damage)
                sound.playHit()

                // Camera shake on hull damage
                spawnExplosion(new THREE.Vector3(0, 0, -2), 'red', 0.3)

                if (hullRef.current <= 0) {
                    // Game Over
                    setGameOver(true)
                    sound.playExplosion('large')
                }
            }
        }

        window.addEventListener('player-hit', handlePlayerHit as EventListener)
        return () => window.removeEventListener('player-hit', handlePlayerHit as EventListener)
    }, [shields, damageShields, setGameOver, triggerPlayerHit, sound, spawnExplosion, spawnProjectile])

    // PICKUP COLLECTED HANDLER - for shoot-to-collect pickups
    useEffect(() => {
        const { removePickup } = usePickupStore.getState()

        const handlePickupCollected = (event: CustomEvent<{ type: string, value: number, id: string }>) => {
            const { type, value, id } = event.detail
            removePickup(id) // Remove the pickup from store

            if (type === 'health') {
                hullRef.current = Math.min(maxHull, hullRef.current + value)
            } else if (type === 'shield') {
                rechargeShields(value)
            } else if (type === 'weapon') {
                // Activate weapon boost for value seconds
                weaponBoostEnd.current = Date.now() + value * 1000
            }
        }

        window.addEventListener('pickup-collected', handlePickupCollected as EventListener)
        return () => window.removeEventListener('pickup-collected', handlePickupCollected as EventListener)
    }, [rechargeShields])

    // ENEMY KILLED HANDLER - builds overcharge from kills
    useEffect(() => {
        const handleEnemyKilled = (event: CustomEvent<{ type: string, stage: number }>) => {
            const { type } = event.detail
            // Different enemy types give different overcharge amounts
            let chargeGain = 0
            switch (type) {
                case 'asteroid': chargeGain = 3; break
                case 'drone': chargeGain = 5; break
                case 'fighter': chargeGain = 8; break
                case 'elite': chargeGain = 15; break
                case 'boss': chargeGain = 30; break
                default: chargeGain = 5
            }
            overchargeRef.current = Math.min(100, overchargeRef.current + chargeGain)
        }

        window.addEventListener('enemy-killed', handleEnemyKilled as EventListener)
        return () => window.removeEventListener('enemy-killed', handleEnemyKilled as EventListener)
    }, [])

    // INPUT HANDLING
    useEffect(() => {
        const handlePointerDown = (event: PointerEvent) => {
            if (isPresenting || isGamePaused) return
            // Left click = fire
            if (event.button === 0) {
                firing.current = true
                if (!isStaticView && document.pointerLockElement !== gl.domElement) {
                    // requestPointerLock returns a Promise - handle rejection gracefully
                    gl.domElement.requestPointerLock()?.catch?.(() => {
                        // Pointer lock may fail in certain contexts (XR, iframe, etc.) - game still works without it
                    })
                }
            }
            // Middle click = activate overcharge turbo burst
            if (event.button === 1) {
                if (overchargeRef.current > 0) {
                    // Duration scales with charge: 100% = powerDuration (30s+), 50% = half, etc.
                    const durationSeconds = (overchargeRef.current / 100) * powerDuration
                    weaponBoostEnd.current = Date.now() + durationSeconds * 1000
                    overchargeRef.current = 0 // Consume all charge
                    sound.playLevelUp() // Satisfying activation sound
                }
            }
            // Right click = shield
            if (event.button === 2) {
                shieldActive.current = true
            }
        }
        const handlePointerUp = (event: PointerEvent) => {
            if (isPresenting || isGamePaused) return
            if (event.button === 0) firing.current = false
            if (event.button === 2) shieldActive.current = false
        }
        const handleContextMenu = (event: Event) => {
            event.preventDefault() // Prevent right-click menu
        }
        const handleMouseMove = (event: MouseEvent) => {
            if (isPresenting || isGamePaused) return
            if (isStaticView) {
                const normX = (event.clientX / window.innerWidth) * 2 - 1
                const normY = (event.clientY / window.innerHeight) * 2 - 1
                targetAngles.current.yaw = -normX * LIMITS.yaw * 0.35
                targetAngles.current.pitch = THREE.MathUtils.clamp(normY * LIMITS.pitchMax * 0.45, LIMITS.pitchMin, LIMITS.pitchMax)
                return
            }
            if (!pointerLocked.current) return
            targetAngles.current.yaw -= event.movementX * INPUT.yawSpeed
            targetAngles.current.yaw = THREE.MathUtils.clamp(targetAngles.current.yaw, -LIMITS.yaw, LIMITS.yaw) // Clamp yaw to prevent spinning
            targetAngles.current.pitch -= event.movementY * INPUT.pitchSpeed // Standard: up=up, down=down
            targetAngles.current.pitch = THREE.MathUtils.clamp(targetAngles.current.pitch, LIMITS.pitchMin, LIMITS.pitchMax)
        }
        const handleKeyDown = (event: KeyboardEvent) => {
            if (isGamePaused) return
            if (event.code === 'Space') firing.current = true
        }
        const handleKeyUp = (event: KeyboardEvent) => {
            if (isGamePaused) return
            if (event.code === 'Space') firing.current = false
        }
        const handlePointerLockChange = () => {
            const wasLocked = pointerLocked.current
            pointerLocked.current = document.pointerLockElement === gl.domElement

            // Sync targetAngles to aimAngles on ANY pointer lock change
            // This prevents the camera from snapping back to old positions
            if (!isPresenting && !isStaticView) {
                targetAngles.current.yaw = aimAngles.current.yaw
                targetAngles.current.pitch = aimAngles.current.pitch
            }
        }

        window.addEventListener('pointerdown', handlePointerDown)
        window.addEventListener('pointerup', handlePointerUp)
        window.addEventListener('mousemove', handleMouseMove)
        window.addEventListener('keydown', handleKeyDown)
        window.addEventListener('keyup', handleKeyUp)
        window.addEventListener('contextmenu', handleContextMenu)
        document.addEventListener('pointerlockchange', handlePointerLockChange)

        return () => {
            window.removeEventListener('pointerdown', handlePointerDown)
            window.removeEventListener('pointerup', handlePointerUp)
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('keydown', handleKeyDown)
            window.removeEventListener('keyup', handleKeyUp)
            window.removeEventListener('contextmenu', handleContextMenu)
            document.removeEventListener('pointerlockchange', handlePointerLockChange)
        }
    }, [gl, isPresenting, isGamePaused, isStaticView])

    useEffect(() => {
        if (isGamePaused && document.pointerLockElement === gl.domElement) {
            document.exitPointerLock()
        }
        if (isGamePaused) {
            firing.current = false
        }
    }, [gl, isGamePaused])

    useEffect(() => {
        if (isStaticView && document.pointerLockElement === gl.domElement) {
            document.exitPointerLock()
        }
    }, [gl, isStaticView])

    const recoilImpulse = useRef(0)

    useFrame((state, delta) => {
        if (isGamePaused) {
            firing.current = false
            return
        }
        const elapsed = state.clock.getElapsedTime()

        // Energy Regen
        if (!firing.current) {
            weaponEnergy.current = Math.min(maxEnergy, weaponEnergy.current + LASER.regenRate * delta)
            if (weaponEnergy.current > 20) canFire.current = true // Re-enable if above threshold
        }

        // --- HUD UPDATES (Per Frame, mutable) ---
        // Normalize to 0-100 scale for UI bars
        hudRef.current.energy = (weaponEnergy.current / maxEnergy) * 100
        hudRef.current.shields = (shields / maxShields) * 100
        hudRef.current.integrity = (hullRef.current / maxHull) * 100
        hudRef.current.overcharge = overchargeRef.current

        const boss = enemies.find(e => e.type === 'boss')
        if (boss) {
            hudRef.current.bossHealth = boss.hp / boss.maxHp
            hudRef.current.stageObjective = 'DESTROY MOTHERSHIP'
        } else {
            hudRef.current.bossHealth = null
            hudRef.current.stageObjective = 'CLEAR SECTOR'
        }
        hudRef.current.stageLabel = `SECTOR ${level}`



        rechargeShields(delta * 3)

        // Shield drain when active
        if (shieldActive.current && shields > 0) {
            damageShields(delta * 15) // Drains shields while held
            if (shields <= 0) {
                shieldActive.current = false // Auto-deactivate when depleted
            }
        }

        // Shield flash decay
        if (shieldFlash.current > 0) {
            shieldFlash.current = Math.max(0, shieldFlash.current - delta * 5)
        }

        const isVr = isPresenting
        isVrRef.current = isVr

        // --- PLAYER FLOAT (Zero-G Drift) ---
        // Gentle compound sine waves for organic drift
        const floatY = Math.sin(elapsed * 0.5) * 0.5 + Math.sin(elapsed * 0.3) * 0.2
        const floatX = Math.cos(elapsed * 0.4) * 0.3

        // Apply to camera (only if not VR, as VR tracks head)
        if (!isVr) {
            camera.position.y = THREE.MathUtils.lerp(camera.position.y, floatY, delta)
            camera.position.x = THREE.MathUtils.lerp(camera.position.x, floatX, delta)
        }

        // --- CAMERA / COCKPIT MOVEMENT ---
        if (isVr) {
            const session = state.gl.xr.getSession()
            if (session) {
                let isTriggerPressed = false
                for (const source of session.inputSources) {
                    if (!source.gamepad) continue
                    if (source.gamepad.buttons?.[0]?.pressed) isTriggerPressed = true
                }
                firing.current = isTriggerPressed
            }
            // VR: Just sync aim vars for shooting
            tempVecA.copy(camera.position)
            aimQuat.current.copy(camera.quaternion)
            camera.getWorldDirection(aimDir.current)
        } else {
            // DESKTOP: Smooth look
            const allowAim = pointerLocked.current || isStaticView
            const targetYaw = allowAim ? targetAngles.current.yaw : 0
            const targetPitch = allowAim ? targetAngles.current.pitch : 0

            aimAngles.current.yaw = THREE.MathUtils.damp(aimAngles.current.yaw, targetYaw, INPUT.damp, delta)
            aimAngles.current.pitch = THREE.MathUtils.damp(aimAngles.current.pitch, targetPitch, INPUT.damp, delta)

            camera.rotation.set(aimAngles.current.pitch, aimAngles.current.yaw, 0, 'YXZ')
            camera.updateMatrixWorld()
            aimQuat.current.copy(camera.quaternion)
            camera.getWorldDirection(aimDir.current)
            tempVecA.copy(camera.position)
        }

        // Sync Cockpit/GunRig to Camera
        if (cockpitRef.current) {
            cockpitRef.current.position.copy(tempVecA)
            cockpitRef.current.quaternion.copy(camera.quaternion)
        }
        if (gunRigRef.current) {
            gunRigRef.current.position.copy(tempVecA)
            gunRigRef.current.quaternion.copy(camera.quaternion)
        }

        // --- FIRING LOGIC ---
        // Get equipped weapon's effective stats (with upgrades applied)
        const weaponStats = getEffectiveStats(equippedWeaponId)
        const baseFireCooldown = 1 / equippedWeapon.fireRate // Convert shots/sec to seconds

        // Turbo mode: faster fire rate (0.15s cooldown), no energy cost, more damage
        const boosted = isWeaponBoosted()
        const fireCooldown = boosted ? 0.15 : baseFireCooldown
        const fireDamage = boosted ? weaponStats.damage * 2 : weaponStats.damage
        const fireEnergyCost = boosted ? 0 : weaponStats.energyCost

        if (firing.current && elapsed - lastShot.current > fireCooldown) {
            if (!boosted && (!canFire.current || weaponEnergy.current < fireEnergyCost)) {
                // Out of energy sound?
                firing.current = false // Stop trying to fire automatically
                canFire.current = false // Lockout until regen
                return
            }

            // Consume Energy (none if boosted)
            weaponEnergy.current -= fireEnergyCost

            lastShot.current = elapsed
            sound.playLaser('player')

            // RECOIL
            recoilImpulse.current = boosted ? 0.2 : 0.4

            // CAMERA SHAKE REMOVED

            const weaponSpeed = equippedWeapon.speed
            tempVecC.copy(aimDir.current).multiplyScalar(weaponSpeed)
            // Spawn dual bolts
            // CONVERGENT AIM: Calculate point 100m in front of camera
            const convergeDist = 100
            const targetPoint = tempVecA.clone().add(aimDir.current.clone().multiplyScalar(convergeDist))

            // Spawn dual bolts - one from each barrel
            GUN_OFFSETS.forEach((offset, barrelIndex) => {
                const rotation = camera.quaternion
                // Muzzle Position
                tempVecB.copy(offset).applyQuaternion(rotation).add(tempVecA)

                // Velocity Vector: (Target - Muzzle).normalize() * speed
                tempVecC.copy(targetPoint).sub(tempVecB).normalize().multiplyScalar(weaponSpeed)

                // Align projectile: Visual points +Z, so align +Z to velocity dir
                const dir = tempVecC.clone().normalize()
                const projectileRot = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir)

                // Clone special properties and add barrel-specific offsets
                // For spiral weapons, offset phase by PI so they're 180 degrees apart
                const specialProps = equippedWeapon.special ? {
                    ...equippedWeapon.special,
                    spiralPhase: (equippedWeapon.special.spiralPhase || 0) + (barrelIndex * Math.PI)
                } : undefined

                spawnProjectile({
                    id: `p-${Date.now()}-${Math.random()}`,
                    position: tempVecB.clone(),
                    rotation: projectileRot,
                    velocity: tempVecC.clone(),
                    damage: fireDamage,
                    owner: 'PLAYER',
                    type: equippedWeapon.projectileType,
                    createdAt: Date.now(),
                    lifetime: LASER.lifetime,
                    colors: equippedWeapon.colors,
                    special: specialProps
                })
            })
        }
    })

    return (
        <group>
            {/* AMBIENCE SOUND CONTROLLER */}
            <AmbienceController />

            {/* ENVIRONMENT */}
            <color attach="background" args={['#040714']} />
            <Stars radius={220} depth={90} count={7000} factor={1.35} saturation={0} fade={false} speed={0} />
            <ambientLight intensity={0.4} />
            <directionalLight position={[20, 30, 10]} intensity={1.1} color="#e2e8f0" />
            <pointLight position={[-30, 8, -40]} intensity={0.8} color="#38bdf8" />

            {/* UI & HUD - Mounted inside Camera Rig Group or synced manually */}
            <group position={[0, 0, -1.5]} ref={cockpitRef}>
                <Suspense fallback={null}>
                    <HolographicHud hudRef={hudRef} />
                </Suspense>
            </group>

            {/* COCKPIT and GUNS */}
            <GunRig gunRef={gunRigRef} recoilImpulse={recoilImpulse} weaponEnergy={weaponEnergy} />
            <ShieldBubble active={shieldActive} flash={shieldFlash} />

            {/* SYSTEMS MOUNTED HERE */}
            <CollisionManager />
            <WaveManager />
            <ExplosionRenderer />
            <DeathEffectsRenderer />
            <FloatingTextRenderer />
            <ProjectileRenderer />
            <PickupRenderer
                onHeal={(amount) => { hullRef.current = Math.min(100, hullRef.current + amount) }}
                onShield={(amount) => { rechargeShields(amount) }}
                onWeaponBoost={(duration) => { weaponBoostEnd.current = Date.now() + duration * 1000 }}
            />

            {/* ENTITY RENDERING */}
            {enemies.map(enemy => (
                <EntityRenderer key={enemy.id} data={enemy} />
            ))}

            <PauseMenuXR />

            {/* Game Over Screen - HTML overlay */}
            {isGameOver && (
                <Html fullscreen>
                    <GameOverScreen />
                </Html>
            )}
        </group>
    )
}
