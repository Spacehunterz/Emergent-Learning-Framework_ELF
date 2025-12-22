import { useRef, useState, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Vector3, Quaternion, Euler } from 'three'
import { useWeaponLogic, useProjectileStore } from '../systems/WeaponSystem'
import { ITEM_DATABASE } from '../systems/ItemDatabase'
import { useGame } from '../../../context/GameContext'
import * as THREE from 'three'
import { create } from 'zustand'
// import { useSound } from '../systems/SoundManager' // Unused
import { Radar } from './Radar'
import { useShipControls } from '../hooks/useShipControls'
import { GAME_CONFIG } from '../config/GameConstants'

// --- PLAYER STATE ---
export const usePlayerState = create<{
    shields: number
    maxShields: number
    hull: number
    maxHull: number
    damageShields: (amount: number) => void
    rechargeShields: (amount: number) => void
}>((set) => ({
    shields: 100,
    maxShields: 100,
    hull: 100,
    maxHull: 100,
    damageShields: (amount) => set(s => {
        let newShields = s.shields - amount
        let newHull = s.hull
        if (newShields < 0) {
            newHull += newShields // Subtract overflow from hull
            newShields = 0
        }
        return { shields: newShields, hull: Math.max(0, newHull) }
    }),
    rechargeShields: (amount) => set(s => ({ shields: Math.min(s.maxShields, s.shields + amount) }))
}))

// --- VISUALS ---

const Cannon = ({ position, recoil }: { position: [number, number, number], recoil: number }) => {
    return (
        <group position={position}>
            {/* Barrel */}
            <mesh position={[0, 0, recoil]}> {/* Recoil moves positive Z (backwards) */}
                <cylinderGeometry args={[0.1, 0.15, 3]} />
                <meshStandardMaterial color="#333" roughness={0.3} metalness={0.8} />
            </mesh>
            {/* Muzzle Glow */}
            <mesh position={[0, 0, -1.5 + recoil]} rotation={[Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.05, 0.1, 8]} />
                <meshBasicMaterial color="cyan" transparent opacity={0.5} />
            </mesh>
            {/* Base/Mount */}
            <mesh position={[0, -0.2, 1]}>
                <boxGeometry args={[0.5, 0.5, 2]} />
                <meshStandardMaterial color="#222" />
            </mesh>
        </group>
    )
}

import { Html } from '@react-three/drei'
// Removed CockpitHUD import - using 3D gauges
// import { CockpitHUD } from '../ui/CockpitHUD'

const TurretCockpit = ({ lastShotTime }: { lastShotTime: number }) => {
    // FIXED: Use refs for animation state to avoid React reconciliation every frame
    const recoilRef = useRef(0)
    const [displayRecoil, setDisplayRecoil] = useState(0) // Only for visual updates when significant

    // Recoil Impulse Logic
    useEffect(() => {
        if (lastShotTime > 0) {
            // New shot fired -> Set immediate recoil kick
            recoilRef.current = 0.6
        }
    }, [lastShotTime]) // Trigger whenever timestamp changes

    useFrame((_state, delta) => {
        // Recovery (Spring back) - FIXED: update ref, not state
        recoilRef.current = THREE.MathUtils.lerp(recoilRef.current, 0, delta * 15)
        // Only update React state when change is significant (reduces reconciliation)
        if (Math.abs(recoilRef.current - displayRecoil) > 0.05) {
            setDisplayRecoil(recoilRef.current)
        }
    })

    // Use ref value for animations, displayRecoil for React rendering
    const recoil = recoilRef.current

    return (
        <group>
            {/* PHYSICAL COCKPIT STRUCTURE (3D Geometry) */}

            {/* Side Struts (Pillars) - Moved out to frame the view */}
            <mesh position={[-3.5, 0, -2]} rotation={[0, 0, 0.1]}>
                <cylinderGeometry args={[0.2, 0.3, 4]} />
                <meshStandardMaterial color="#222" roughness={0.7} metalness={0.8} />
            </mesh>
            <mesh position={[3.5, 0, -2]} rotation={[0, 0, -0.1]}>
                <cylinderGeometry args={[0.2, 0.3, 4]} />
                <meshStandardMaterial color="#222" roughness={0.7} metalness={0.8} />
            </mesh>

            {/* Dashboard Console (Bottom Slab) 
                Matching the sketch: A dark grey area at the bottom.
                Positioned lower to give a clear view.
            */}
            <group position={[0, -2.2, -3]} rotation={[-0.1, 0, 0]}>
                <mesh>
                    <boxGeometry args={[12, 1.5, 3]} />
                    <meshBasicMaterial color="#333" />
                </mesh>
                {/* Thin trim line */}
                <mesh position={[0, 0.76, 0.5]}>
                    <boxGeometry args={[12, 0.05, 0.1]} />
                    <meshStandardMaterial color="#444" roughness={0.5} metalness={0.5} />
                </mesh>
            </group>

            {/* Cannons 
                Positioned so they look like they are mounted on/near the dashboard but not clipping.
                Moved slightly wider and up to clear the console surface (y=-1.45).
            */}
            <Cannon position={[-2.2, -1.2, -3.5]} recoil={recoil} />
            <Cannon position={[2.2, -1.2, -3.5]} recoil={recoil} />
        </group>
    )
}

import { useGameSettings } from '../systems/GameSettings'
import { PauseMenu } from '../ui/PauseMenu'
import { GameOverScreen } from '../ui/GameOverScreen'

export const PlayerShip = () => {
    const { camera } = useThree()
    const shipRef = useRef<any>(null)
    const [lastShotTime, setLastShotTime] = useState(0)

    // Settings & State
    const { sensitivityX, sensitivityY, smoothness, isPaused, setPaused } = useGameSettings()

    // Systems
    const weaponLogic = useWeaponLogic(ITEM_DATABASE['weapon_pulse_mk1'])
    const { spawnProjectile } = useProjectileStore()
    const { rechargeShields } = usePlayerState()
    const { damageShields } = usePlayerState()
    const { setGameOver, isGameOver, shields, triggerPlayerHit } = useGame()

    // Physics State (Stationary Turret)
    const targetRotation = useRef(new Euler(0, 0, 0, 'YXZ'))
    const actualRotation = useRef(new Euler(0, 0, 0, 'YXZ'))

    // Impact State
    const shakeIntensity = useRef(0)

    // FIXED: Pre-allocate reusable objects to avoid GC pressure
    const tempQuaternion = useRef(new Quaternion())
    const tempEuler = useRef(new Euler(0, 0, 0, 'YXZ'))
    const tempVector1 = useRef(new Vector3())
    const tempVector2 = useRef(new Vector3())
    const leftOffset = useRef(new Vector3(-GAME_CONFIG.WEAPONS.PLAYER_PLASMA.OFFSET_X, GAME_CONFIG.WEAPONS.PLAYER_PLASMA.OFFSET_Y, GAME_CONFIG.WEAPONS.PLAYER_PLASMA.OFFSET_Z))
    const rightOffset = useRef(new Vector3(GAME_CONFIG.WEAPONS.PLAYER_PLASMA.OFFSET_X, GAME_CONFIG.WEAPONS.PLAYER_PLASMA.OFFSET_Y, GAME_CONFIG.WEAPONS.PLAYER_PLASMA.OFFSET_Z))

    // Inputs
    const moveState = useShipControls(isPaused, setPaused)

    // Cursor Management
    useEffect(() => {
        if (!isPaused) {
            document.body.classList.add('cursor-hidden-important')
        } else {
            document.body.classList.remove('cursor-hidden-important')
        }
        return () => document.body.classList.remove('cursor-hidden-important') // Cleanup
    }, [isPaused])

    // Listen for Shield Damage Events
    useEffect(() => {
        const handleDamage = (e: any) => {
            if (e.detail && e.detail.damage) {
                // Apply Damage
                if (shields > 0) {
                    damageShields(e.detail.damage)
                } else {
                    // Hull Damage
                    usePlayerState.getState().damageShields(e.detail.damage) // Reusing the reducer logic which handles spillover
                }

                const currentHull = usePlayerState.getState().hull
                if (currentHull <= 0) {
                    setGameOver(true)
                }

                // Add Large Shake on Hit
                shakeIntensity.current = 1.0
                // Trigger Red Flash via Context (Handled by 2D HUD)
                triggerPlayerHit()
            }
        }
        window.addEventListener('player-hit', handleDamage)
        return () => window.removeEventListener('player-hit', handleDamage)
    }, [damageShields, setGameOver, shields, triggerPlayerHit])

    useFrame((_state, delta) => {
        if (isPaused || isGameOver) return // Freeze game loop if paused or dead

        // Shield Regen
        rechargeShields(GAME_CONFIG.PLAYER.SHIELD_REGEN_RATE * delta)

        // --- ROTATION (Turret Movement) ---
        const baseSpeed = GAME_CONFIG.PLAYER.SPEED * delta
        const speedX = baseSpeed * sensitivityX
        const speedY = baseSpeed * sensitivityY

        // Update Target (Raw Input)
        targetRotation.current.y -= moveState.current.mouseX * speedX
        targetRotation.current.x += moveState.current.mouseY * speedY

        // Clamp Pitch (Up/Down)
        targetRotation.current.x = Math.max(-Math.PI / 2.2, Math.min(Math.PI / 2.2, targetRotation.current.x))
        targetRotation.current.z = 0

        // Apply Smoothing (Lerp)
        // Apply Smoothing (Lerp)
        // Map smoothness (0-1) to logic (High smoothness = Low lerp alpha)
        // 0 (Raw) -> 0.3 (Snappy)
        // 1 (Smooth) -> 0.03 (Floaty)
        const lerpAlpha = THREE.MathUtils.mapLinear(smoothness, 0, 1, 0.3, 0.03)
        const effectiveLerp = 1 - Math.pow(1 - lerpAlpha, delta * 60) // Frame-rate independent lerp adjustment

        actualRotation.current.x = THREE.MathUtils.lerp(actualRotation.current.x, targetRotation.current.x, effectiveLerp)
        actualRotation.current.y = THREE.MathUtils.lerp(actualRotation.current.y, targetRotation.current.y, effectiveLerp)
        actualRotation.current.z = 0

        // --- CAMERA SHAKE ---
        // Decay shake intensity
        shakeIntensity.current = THREE.MathUtils.lerp(shakeIntensity.current, 0, delta * GAME_CONFIG.PLAYER.SHAKE_DECAY)
        const shakeX = (Math.random() - 0.5) * shakeIntensity.current * 0.2
        const shakeY = (Math.random() - 0.5) * shakeIntensity.current * 0.2

        // Apply shake to quaternion - FIXED: reuse pre-allocated objects
        tempEuler.current.set(
            actualRotation.current.x + shakeY,
            actualRotation.current.y + shakeX,
            0
        )
        tempQuaternion.current.setFromEuler(tempEuler.current)

        // Sync Camera
        camera.quaternion.copy(tempQuaternion.current)
        camera.position.set(0, 0, 0) // Fixed position

        if (shipRef.current) {
            shipRef.current.position.copy(camera.position)
            shipRef.current.quaternion.copy(camera.quaternion)
        }

        // --- WEAPONS (Dual Fire) ---
        weaponLogic.update(delta)
        if (moveState.current.firing) {
            if (weaponLogic.fire()) {
                setLastShotTime(Date.now()) // Trigger React update for Recoil

                // Add Small Shake on Fire
                shakeIntensity.current += 0.05

                // FIXED: Reuse pre-allocated offset vectors, only clone for projectile spawn
                const offsets = [leftOffset.current, rightOffset.current]
                offsets.forEach(offset => {
                    // Clone only what needs to be stored in projectile state
                    tempVector1.current.copy(offset).applyQuaternion(tempQuaternion.current).add(camera.position)
                    tempVector2.current.set(0, 0, -1).applyQuaternion(tempQuaternion.current)

                    spawnProjectile({
                        id: Math.random().toString(),
                        position: tempVector1.current.clone(), // Clone for projectile storage
                        rotation: tempQuaternion.current.clone(),
                        velocity: tempVector2.current.clone().multiplyScalar(GAME_CONFIG.WEAPONS.PLAYER_PLASMA.SPEED),
                        damage: GAME_CONFIG.WEAPONS.PLAYER_PLASMA.DAMAGE,
                        owner: 'PLAYER',
                        type: 'standard',
                        createdAt: Date.now(),
                        lifetime: GAME_CONFIG.WEAPONS.PLAYER_PLASMA.LIFETIME
                    })
                })
            }
        }
    })

    return (
        <group ref={shipRef}>
            <Html fullscreen style={{ pointerEvents: 'none' }}>
                <PauseMenu />
                {isGameOver && <GameOverScreen />}
                {/* Damage Flash Removed - moved to 2D HUD */}
            </Html>

            <TurretCockpit lastShotTime={lastShotTime} />

            {/* RADAR - Bottom Right Corner */}
            <group position={[3.5, -1.8, -3]} rotation={[0.4, -0.2, 0]} scale={[2, 2, 2]}> {/* Moved Up (-2.5 -> -1.8) */}
                <Radar />
            </group>

            {/* RETICLE */}
            <group position={[0, 0, -5]} >
                <mesh>
                    <ringGeometry args={[0.02, 0.05, 32]} />
                    <meshBasicMaterial color="lime" opacity={0.6} transparent />
                </mesh>
                <mesh>
                    <ringGeometry args={[0.15, 0.16, 32]} />
                    <meshBasicMaterial color="lime" opacity={0.3} transparent />
                </mesh>
            </group>

            {moveState.current.firing && (
                <pointLight position={[0, -1, -3]} intensity={5} color="cyan" distance={20} decay={2} />
            )}
        </group>
    )
}
