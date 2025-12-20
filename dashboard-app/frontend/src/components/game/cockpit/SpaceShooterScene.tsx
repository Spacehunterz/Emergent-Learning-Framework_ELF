import React, { Suspense, useEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Stars } from '@react-three/drei'
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
import { useGameSettings } from '../systems/GameSettings'
import { PauseMenuXR } from '../ui/PauseMenuXR'
import { FloatingTextRenderer } from '../systems/FloatingTextManager'
import { useExplosionStore } from '../systems/ExplosionManager'

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
    pitchMin: -Math.PI / 12, // Allow looking down ~15 degrees
    pitchMax: Math.PI / 2.1
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
    new THREE.Vector3(-2.2, -1.2, -1.0), // Wider and lower
    new THREE.Vector3(2.2, -1.2, -1.0)
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

    const rotSpeed = useMemo(() => ({
        x: 0.3 + Math.random() * 0.4,
        y: 0.2 + Math.random() * 0.3,
        z: 0.1 + Math.random() * 0.2
    }), [])
    const baseScale = useMemo(() => 12 + Math.random() * 8, [])
    const geoType = useMemo(() => Math.floor(data.seed * 3), [data.seed])

    // Health-based color
    const healthPct = data.hp / data.maxHp
    const color = healthPct > 0.5 ? '#ff6600' : healthPct > 0.25 ? '#ffff00' : '#ff0044'

    useFrame((_, delta) => {
        if (!ref.current) return
        ref.current.position.copy(data.position)
        ref.current.rotation.x += rotSpeed.x * delta
        ref.current.rotation.y += rotSpeed.y * delta
        ref.current.rotation.z += rotSpeed.z * delta

        // Per-enemy spawn animation
        const ease = getSpawnEase(data.createdAt)
        ref.current.scale.setScalar(baseScale * ease)

        // Update material opacity
        if (mainMatRef.current) mainMatRef.current.opacity = 0.85 * ease
        if (innerMatRef.current) innerMatRef.current.opacity = 0.4 * ease
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
        </group>
    )
}

// Neon wireframe drone - small fast pyramid
const DroneMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const outerMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const innerMatRef = useRef<THREE.MeshBasicMaterial>(null)

    const healthPct = data.hp / data.maxHp
    const color = healthPct > 0.5 ? '#00ff88' : healthPct > 0.25 ? '#ffff00' : '#ff0044'

    useFrame((_, delta) => {
        if (!ref.current) return
        ref.current.position.copy(data.position)
        ref.current.lookAt(0, 0, 0)
        ref.current.rotation.z += delta * 3 // Spin while facing player

        // Per-enemy spawn animation
        const ease = getSpawnEase(data.createdAt)
        ref.current.scale.setScalar(ease)

        // Update material opacity
        if (outerMatRef.current) outerMatRef.current.opacity = 0.9 * ease
        if (innerMatRef.current) innerMatRef.current.opacity = 0.6 * ease
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
        </group>
    )
}

// Neon wireframe fighter - aggressive double-pyramid
const FighterMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const innerRef = useRef<THREE.Mesh>(null)
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const wingMat1Ref = useRef<THREE.MeshBasicMaterial>(null)
    const wingMat2Ref = useRef<THREE.MeshBasicMaterial>(null)
    const coreMatRef = useRef<THREE.MeshBasicMaterial>(null)

    const healthPct = data.hp / data.maxHp
    const color = healthPct > 0.5 ? '#ff00ff' : healthPct > 0.25 ? '#ffff00' : '#ff0044'

    useFrame((_, delta) => {
        if (!ref.current) return
        ref.current.position.copy(data.position)
        ref.current.lookAt(0, 0, 0)
        if (innerRef.current) {
            innerRef.current.rotation.y += delta * 4
        }

        // Per-enemy spawn animation
        const ease = getSpawnEase(data.createdAt)
        ref.current.scale.setScalar(ease)

        // Update material opacity
        if (bodyMatRef.current) bodyMatRef.current.opacity = 0.85 * ease
        if (wingMat1Ref.current) wingMat1Ref.current.opacity = 0.7 * ease
        if (wingMat2Ref.current) wingMat2Ref.current.opacity = 0.7 * ease
        if (coreMatRef.current) coreMatRef.current.opacity = 0.8 * ease
    })

    return (
        <group ref={ref} scale={0}>
            {/* Main body - elongated octahedron */}
            <mesh scale={[10, 10, 20]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color={color} wireframe transparent opacity={0} />
            </mesh>
            {/* Wings - two flat diamonds */}
            <mesh position={[12, 0, 0]} scale={[8, 2, 10]} rotation={[0, 0, Math.PI / 4]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={wingMat1Ref} color={color} wireframe transparent opacity={0} />
            </mesh>
            <mesh position={[-12, 0, 0]} scale={[8, 2, 10]} rotation={[0, 0, -Math.PI / 4]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={wingMat2Ref} color={color} wireframe transparent opacity={0} />
            </mesh>
            {/* Spinning core */}
            <mesh ref={innerRef} scale={5}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={coreMatRef} color="#00ffff" wireframe transparent opacity={0} />
            </mesh>
        </group>
    )
}

// Elite mini-boss - larger more complex structure
const EliteMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const ring1Ref = useRef<THREE.Mesh>(null)
    const ring2Ref = useRef<THREE.Mesh>(null)
    const centerMatRef = useRef<THREE.MeshBasicMaterial>(null)
    const ring1MatRef = useRef<THREE.MeshBasicMaterial>(null)
    const ring2MatRef = useRef<THREE.MeshBasicMaterial>(null)
    const innerMatRef = useRef<THREE.MeshBasicMaterial>(null)

    const healthPct = data.hp / data.maxHp
    const color = healthPct > 0.5 ? '#ffaa00' : healthPct > 0.25 ? '#ff6600' : '#ff0044'

    useFrame((_, delta) => {
        if (!ref.current) return
        ref.current.position.copy(data.position)
        ref.current.lookAt(0, 0, 0)
        if (ring1Ref.current) ring1Ref.current.rotation.x += delta * 2
        if (ring2Ref.current) ring2Ref.current.rotation.y += delta * 2.5

        // Per-enemy spawn animation
        const ease = getSpawnEase(data.createdAt)
        ref.current.scale.setScalar(ease)

        // Update material opacity
        if (centerMatRef.current) centerMatRef.current.opacity = 0.9 * ease
        if (ring1MatRef.current) ring1MatRef.current.opacity = 0.8 * ease
        if (ring2MatRef.current) ring2MatRef.current.opacity = 0.8 * ease
        if (innerMatRef.current) innerMatRef.current.opacity = 0.7 * ease
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
        </group>
    )
}

// Legacy ship mesh fallback (shouldn't be used now)


const BossMesh = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null)
    const innerRef = useRef<THREE.Group>(null)
    const time = useRef(0)

    useFrame((_, delta) => {
        if (!ref.current) return
        time.current += delta

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
        }

        // Rotate inner structure
        if (innerRef.current) {
            innerRef.current.rotation.x += delta * 0.3
            innerRef.current.rotation.y += delta * 0.5
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
        </group>
    )
}

const EntityRenderer = React.memo(({ data }: { data: Enemy }) => {
    if (data.type === 'asteroid') return <AsteroidMesh data={data} />
    if (data.type === 'boss') return <BossMesh data={data} />
    if (data.type === 'elite') return <EliteMesh data={data} />
    if (data.type === 'drone') return <DroneMesh data={data} />
    if (data.type === 'fighter') return <FighterMesh data={data} />
    return <FighterMesh data={data} /> // Default
}, (prev, next) => prev.data === next.data) // Equality check based on reference identity


const GunRig = ({ gunRef, recoilImpulse }: { gunRef: React.RefObject<THREE.Group>, recoilImpulse: React.MutableRefObject<number> }) => {
    const innerRef = useRef<THREE.Group>(null)

    useFrame((_, delta) => {
        if (!innerRef.current) return
        // Decay impulse
        recoilImpulse.current = THREE.MathUtils.lerp(recoilImpulse.current, 0, delta * 10)
        // Apply to local Z
        innerRef.current.position.z = recoilImpulse.current
    })

    return (
        <group ref={gunRef}>
            <group ref={innerRef} name="RecoilContainer">
                {/* Lit from behind/above to ensure visibility */}
                <pointLight position={[0, 1, 0.5]} intensity={0.5} distance={5} color="#ffffff" />
                <pointLight position={[0, 0.4, -6]} intensity={1.2} distance={140} color="#dbeafe" />
                <group position={GUN_OFFSETS[0].toArray()}>
                    <mesh rotation={[Math.PI / 2, 0, 0]}>
                        <cylinderGeometry args={[0.08, 0.16, 2.8]} />
                        <meshStandardMaterial color="#a1a1aa" metalness={0.2} roughness={0.8} />
                    </mesh>
                    <mesh position={[0, 0, -1.2]}>
                        <sphereGeometry args={[0.14, 12, 12]} />
                        <meshBasicMaterial color="#38bdf8" />
                    </mesh>
                </group>
                <group position={GUN_OFFSETS[1].toArray()}>
                    <mesh rotation={[Math.PI / 2, 0, 0]}>
                        <cylinderGeometry args={[0.08, 0.16, 2.8]} />
                        <meshStandardMaterial color="#a1a1aa" metalness={0.2} roughness={0.8} />
                    </mesh>
                    <mesh position={[0, 0, -1.2]}>
                        <sphereGeometry args={[0.14, 12, 12]} />
                        <meshBasicMaterial color="#38bdf8" />
                    </mesh>
                </group>
            </group>
        </group>
    )
}

export const SpaceShooterScene = () => {
    const { camera, gl } = useThree()
    const mode = useXR((state) => state.mode)
    const isPresenting = mode === 'immersive-vr'
    const { rechargeShields, damageShields, shields, level, score, viewMode, setGameOver, triggerPlayerHit } = useGame()
    const { isPaused } = useGameSettings()
    const isStaticView = viewMode === 'static'

    // SYSTEMS & STORES
    const enemies = useEnemyStore(s => s.enemies)
    const { spawnProjectile } = useProjectileStore()
    const { spawnExplosion } = useExplosionStore()
    const sound = useSound()

    // Local hull tracking for cockpit mode (shields come from GameContext)
    const hullRef = useRef(100)

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

    const weaponEnergy = useRef(100)
    const canFire = useRef(true)

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
        const handlePlayerHit = (event: CustomEvent<{ damage: number }>) => {
            const damage = event.detail.damage || 10
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
    }, [shields, damageShields, setGameOver, triggerPlayerHit, sound, spawnExplosion])

    // INPUT HANDLING
    useEffect(() => {
        const handlePointerDown = (event: PointerEvent) => {
            if (isPresenting || isPaused) return
            if (event.button !== 0) return
            firing.current = true
            if (!isStaticView && document.pointerLockElement !== gl.domElement) {
                // requestPointerLock returns a Promise - handle rejection gracefully
                gl.domElement.requestPointerLock()?.catch?.(() => {
                    // Pointer lock may fail in certain contexts (XR, iframe, etc.) - game still works without it
                })
            }
        }
        const handlePointerUp = () => {
            if (isPresenting || isPaused) return
            firing.current = false
        }
        const handleMouseMove = (event: MouseEvent) => {
            if (isPresenting || isPaused) return
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
            if (isPaused) return
            if (event.code === 'Space') firing.current = true
        }
        const handleKeyUp = (event: KeyboardEvent) => {
            if (isPaused) return
            if (event.code === 'Space') firing.current = false
        }
        const handlePointerLockChange = () => {
            pointerLocked.current = document.pointerLockElement === gl.domElement
            if (!pointerLocked.current && !isPresenting && !isStaticView) {
                targetAngles.current.yaw = aimAngles.current.yaw
                targetAngles.current.pitch = aimAngles.current.pitch
            }
        }

        window.addEventListener('pointerdown', handlePointerDown)
        window.addEventListener('pointerup', handlePointerUp)
        window.addEventListener('mousemove', handleMouseMove)
        window.addEventListener('keydown', handleKeyDown)
        window.addEventListener('keyup', handleKeyUp)
        document.addEventListener('pointerlockchange', handlePointerLockChange)

        return () => {
            window.removeEventListener('pointerdown', handlePointerDown)
            window.removeEventListener('pointerup', handlePointerUp)
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('keydown', handleKeyDown)
            window.removeEventListener('keyup', handleKeyUp)
            document.removeEventListener('pointerlockchange', handlePointerLockChange)
        }
    }, [gl, isPresenting, isPaused, isStaticView])

    useEffect(() => {
        if (isPaused && document.pointerLockElement === gl.domElement) {
            document.exitPointerLock()
        }
        if (isPaused) {
            firing.current = false
        }
    }, [gl, isPaused])

    useEffect(() => {
        if (isStaticView && document.pointerLockElement === gl.domElement) {
            document.exitPointerLock()
        }
    }, [gl, isStaticView])

    const recoilImpulse = useRef(0)

    useFrame((state, delta) => {
        if (isPaused) {
            firing.current = false
            return
        }
        const elapsed = state.clock.getElapsedTime()
        if (Math.round(elapsed * 60) % 120 === 0) console.log(`[SpaceShooterScene] Active Enemies: ${enemies.length}`)

        // Energy Regen
        if (!firing.current) {
            weaponEnergy.current = Math.min(100, weaponEnergy.current + LASER.regenRate * delta)
            if (weaponEnergy.current > 20) canFire.current = true // Re-enable if above threshold
        }

        // --- HUD UPDATES (Per Frame, mutable) ---
        hudRef.current.energy = weaponEnergy.current
        hudRef.current.shields = shields // Note: shields is state, but we read it here. 
        // Ideally shields would be a ref too for true zero-render, but it changes rarely compared to position/energy.
        // Actually shields IS state, so this whole component re-renders when shields change. 
        // That is acceptable for 'hit' events, but not for 'energy' or 'time'.
        // To fix shields re-rendering, we'd need to move shields to a store/ref.
        // For now, energy is the big one.

        hudRef.current.integrity = hullRef.current

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
        if (firing.current && elapsed - lastShot.current > LASER.cooldown) {
            if (!canFire.current || weaponEnergy.current < LASER.energyCost) {
                // Out of energy sound?
                firing.current = false // Stop trying to fire automatically
                canFire.current = false // Lockout until regen
                return
            }

            // Consume Energy
            weaponEnergy.current -= LASER.energyCost

            lastShot.current = elapsed
            sound.playLaser('player')

            // RECOIL
            recoilImpulse.current = 0.4

            // CAMERA SHAKE REMOVED

            tempVecC.copy(aimDir.current).multiplyScalar(LASER.speed)
            // Spawn dual bolts
            // CONVERGENT AIM: Calculate point 100m in front of camera
            const convergeDist = 100
            const targetPoint = tempVecA.clone().add(aimDir.current.clone().multiplyScalar(convergeDist))

            // Spawn dual bolts
            for (const offset of GUN_OFFSETS) {
                const rotation = camera.quaternion
                // Muzzle Position
                tempVecB.copy(offset).applyQuaternion(rotation).add(tempVecA)

                // Velocity Vector: (Target - Muzzle).normalize() * speed
                tempVecC.copy(targetPoint).sub(tempVecB).normalize().multiplyScalar(LASER.speed)

                // Align projectile: Visual points +Z, so align +Z to velocity dir
                const dir = tempVecC.clone().normalize()
                const projectileRot = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir)

                spawnProjectile({
                    id: `p-${Date.now()}-${Math.random()}`,
                    position: tempVecB.clone(),
                    rotation: projectileRot,
                    velocity: tempVecC.clone(),
                    damage: 15, // Increased from 1
                    owner: 'PLAYER',
                    type: 'PLASMA',
                    createdAt: Date.now(),
                    lifetime: LASER.lifetime
                })
            }
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
            <GunRig gunRef={gunRigRef} recoilImpulse={recoilImpulse} />

            {/* SYSTEMS MOUNTED HERE */}
            <CollisionManager />
            <WaveManager />
            <ExplosionRenderer />
            <FloatingTextRenderer />
            <ProjectileRenderer />

            {/* ENTITY RENDERING */}
            {enemies.map(enemy => (
                <EntityRenderer key={enemy.id} data={enemy} />
            ))}

            <PauseMenuXR />
        </group>
    )
}
