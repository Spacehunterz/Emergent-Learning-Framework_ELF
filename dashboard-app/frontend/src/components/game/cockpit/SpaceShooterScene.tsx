import { Suspense, useEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Stars, useGLTF, Sparkles } from '@react-three/drei'
import { useXR } from '@react-three/xr'
import * as THREE from 'three'
import { useGame } from '../../../context/GameContext'
import type { HudState } from './Hud'
import { HolographicHud } from './HolographicHud'
import { ProjectileRenderer } from './ProjectileRenderer'
import { CollisionManager } from '../systems/CollisionManager'
import { useEnemyStore, Enemy } from '../systems/EnemySystem'
import { useProjectileStore } from '../systems/WeaponSystem'
import { useSound } from '../systems/SoundManager'
import { WaveManager } from '../systems/WaveManager'
import { ExplosionRenderer } from '../systems/ExplosionManager'
import { FloatingTextRenderer } from '../systems/FloatingTextManager'

// --- CONSTANTS ---
const INPUT = {
    yawSpeed: 0.003,
    pitchSpeed: 0.0028,
    damp: 40
}

const LIMITS = {
    yaw: Math.PI / 2,
    pitchMin: 0,
    pitchMax: Math.PI / 2.1
}

const LASER = {
    speed: 120,
    lifetime: 1.6,
    cooldown: 0.12,
    radius: 0.35
}

const GUN_OFFSETS = [
    new THREE.Vector3(-2.2, -1.2, -1.0), // Wider and lower
    new THREE.Vector3(2.2, -1.2, -1.0)
]

// --- VISUAL COMPONENTS ---

const AsteroidMesh = ({ data }: { data: Enemy }) => {
    const { scene } = useGLTF('/models/asteroids/asteroid1.glb')
    const ref = useRef<THREE.Group>(null)
    // Clone scene to allow multiple instances
    const clone = useMemo(() => scene.clone(), [scene])

    const scale = useMemo(() => 20.0 + Math.random() * 5, [])

    useFrame((_, delta) => {
        if (!ref.current) return
        ref.current.position.copy(data.position)
        // Smooth rotation using delta
        ref.current.rotation.x += 0.5 * delta
        ref.current.rotation.y += 0.2 * delta
    })

    return <primitive object={clone} ref={ref} scale={scale} />
}

const ShipMesh = ({ data }: { data: Enemy }) => {
    const isFighter = data.type === 'fighter'
    const url = isFighter ? '/models/enemies/ship2.glb' : '/models/enemies/ship1.glb'
    const { scene } = useGLTF(url)
    const ref = useRef<THREE.Group>(null)
    const clone = useMemo(() => scene.clone(), [scene])

    useFrame(() => {
        if (!ref.current) return
        ref.current.position.copy(data.position)
        // Ships should look at the player roughly or fly forward
        // The System sets rotation based on velocity!
        // But we need to apply that rotation here.
        // data.rotation is a Quaternion.
        // HOWEVER: The system updates data.rotation?
        // EnemySystem.ts doesn't explicitly store rotation updates in the state for all types?
        // Actually, SpaceShooterScene previously did: enemy.rotation.setFromRotationMatrix...
        // Let's re-add that logic in a "VisualSystem" hook or just do it here.
        // For now, let's just LookAt(0,0,0) + 180 deg (since models usually face +Z)
        ref.current.lookAt(0, 0, 0)
        ref.current.rotateY(Math.PI) // Face player
    })

    return <primitive object={clone} ref={ref} scale={isFighter ? 15.0 : 20.0} />
}

const BossMesh = ({ data }: { data: Enemy }) => {
    // Mothership - using ship1 but HUGE
    const { scene } = useGLTF('/models/enemies/ship1.glb')
    const ref = useRef<THREE.Group>(null)
    const clone = useMemo(() => scene.clone(), [scene])

    useFrame(() => {
        if (!ref.current) return

        // WARP IN EFFECT
        const age = Date.now() - (data.createdAt || 0)
        const warpDuration = 1800 // ms

        if (age < warpDuration) {
            // Percent complete (0 to 1)
            // Use easeOutExpo for dramatic arrive
            const p = age / warpDuration
            const ease = 1 - Math.pow(2, -10 * p) // easeOutExpo

            // Start WAY back, arrive at destination
            const startZ = -4000
            const currentZ = THREE.MathUtils.lerp(startZ, data.position.z, ease)

            ref.current.position.set(data.position.x, data.position.y, currentZ)

            // Stretch Effect: Long at start, normal at end
            const stretch = THREE.MathUtils.lerp(30, 1, ease)
            ref.current.scale.set(150.0, 150.0, 150.0 * stretch)

            ref.current.lookAt(0, 0, 0)
            ref.current.rotateY(Math.PI)
        } else {
            // Normal behavior
            ref.current.position.copy(data.position)
            ref.current.scale.set(150.0, 150.0, 150.0) // Normal massive scale
            ref.current.lookAt(0, 0, 0)
            ref.current.rotateY(Math.PI)
        }
    })

    const EngineExhaust = () => {
        // Twin Ion Engines
        return (
            <group position={[0, 0, 3.5]}> {/* Positioned at rear of ship1 model */}
                {/* Left Engine */}
                <mesh position={[-0.8, 0, 0]}>
                    <sphereGeometry args={[0.4, 16, 16]} />
                    <meshBasicMaterial color="#00ffff" />
                </mesh>
                <pointLight position={[-0.8, 0, 1]} distance={5} intensity={5} color="#00ffff" />

                {/* Right Engine */}
                <mesh position={[0.8, 0, 0]}>
                    <sphereGeometry args={[0.4, 16, 16]} />
                    <meshBasicMaterial color="#00ffff" />
                </mesh>
                <pointLight position={[0.8, 0, 1]} distance={5} intensity={5} color="#00ffff" />

                {/* Particle Trail - Twin Streams */}
                <group position={[-0.8, 0, 0]}>
                    <Sparkles count={50} scale={[1, 1, 10]} size={10} speed={4} opacity={0.5} color="#00ffff" position={[0, 0, 5]} />
                </group>
                <group position={[0.8, 0, 0]}>
                    <Sparkles count={50} scale={[1, 1, 10]} size={10} speed={4} opacity={0.5} color="#00ffff" position={[0, 0, 5]} />
                </group>
            </group>
        )
    }

    // ... inside BossMesh ...
    return (
        <group ref={ref}>
            <primitive object={clone} />
            <EngineExhaust />
        </group>
    )
}

const EntityRenderer = ({ data }: { data: Enemy }) => {
    if (data.type === 'asteroid') return <AsteroidMesh data={data} />
    if (data.type === 'boss') return <BossMesh data={data} />
    // Fighter / Interceptor
    return <ShipMesh data={data} />
}

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
                <pointLight position={[0, 0.4, -6]} intensity={1.2} distance={140} color="#dbeafe" />
                <group position={GUN_OFFSETS[0].toArray()}>
                    <mesh rotation={[Math.PI / 2, 0, 0]}>
                        <cylinderGeometry args={[0.08, 0.16, 2.8]} />
                        <meshStandardMaterial color="#334155" metalness={0.8} roughness={0.2} />
                    </mesh>
                    <mesh position={[0, 0, -1.2]}>
                        <sphereGeometry args={[0.14, 12, 12]} />
                        <meshBasicMaterial color="#38bdf8" />
                    </mesh>
                </group>
                <group position={GUN_OFFSETS[1].toArray()}>
                    <mesh rotation={[Math.PI / 2, 0, 0]}>
                        <cylinderGeometry args={[0.08, 0.16, 2.8]} />
                        <meshStandardMaterial color="#334155" metalness={0.8} roughness={0.2} />
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

export const SpaceShooterScene = ({ onHudUpdate }: { onHudUpdate: (state: HudState) => void, resetKey: number }) => {
    const { camera, gl } = useThree()
    const mode = useXR((state) => state.mode)
    const isPresenting = mode === 'immersive-vr'
    const { rechargeShields, level } = useGame()

    // SYSTEMS & STORES
    const enemies = useEnemyStore(s => s.enemies)
    const { spawnProjectile } = useProjectileStore()
    const sound = useSound()

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

    const tempVecA = useMemo(() => new THREE.Vector3(), [])
    const tempVecB = useMemo(() => new THREE.Vector3(), [])
    const tempVecC = useMemo(() => new THREE.Vector3(), [])

    // HUD Sync (minimal now, as Systems drive logic)
    useEffect(() => {
        onHudUpdate({
            stageLabel: `Sector ${level}`,
            stageObjective: 'Defend the station',
            stageIndex: level,
            stageStatus: enemies.some(e => e.type === 'boss') ? 'BOSS DETECTED' : 'ENGAGE',
            bossHealth: enemies.find(e => e.type === 'boss') ? (enemies.find(e => e.type === 'boss')!.hp / enemies.find(e => e.type === 'boss')!.maxHp) : null,
            bossSegments: null
        })
    }, [enemies, level, onHudUpdate])


    // INPUT HANDLING
    useEffect(() => {
        const handlePointerDown = (event: PointerEvent) => {
            if (isPresenting) return
            if (event.button !== 0) return
            firing.current = true
            if (document.pointerLockElement !== gl.domElement) {
                gl.domElement.requestPointerLock()
            }
        }
        const handlePointerUp = () => {
            if (isPresenting) return
            firing.current = false
        }
        const handleMouseMove = (event: MouseEvent) => {
            if (isPresenting) return
            if (!pointerLocked.current) return
            targetAngles.current.yaw -= event.movementX * INPUT.yawSpeed
            targetAngles.current.pitch -= event.movementY * INPUT.pitchSpeed
            targetAngles.current.pitch = THREE.MathUtils.clamp(targetAngles.current.pitch, LIMITS.pitchMin, LIMITS.pitchMax)
        }
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.code === 'Space') firing.current = true
        }
        const handleKeyUp = (event: KeyboardEvent) => {
            if (event.code === 'Space') firing.current = false
        }
        const handlePointerLockChange = () => {
            pointerLocked.current = document.pointerLockElement === gl.domElement
            if (!pointerLocked.current && !isPresenting) {
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
    }, [gl, isPresenting])

    const recoilImpulse = useRef(0)

    useFrame((state, delta) => {
        const elapsed = state.clock.getElapsedTime()
        if (Math.round(elapsed * 60) % 120 === 0) console.log(`[SpaceShooterScene] Active Enemies: ${enemies.length}`)
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
            const targetYaw = pointerLocked.current ? targetAngles.current.yaw : 0
            const targetPitch = pointerLocked.current ? targetAngles.current.pitch : 0

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
            console.log('[SpaceShooterScene] Firing!', aimDir.current)
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
                    damage: 1,
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
            {/* ENVIRONMENT */}
            <color attach="background" args={['#040714']} />
            <Stars radius={220} depth={90} count={7000} factor={1.35} saturation={0} fade={false} speed={0} />
            <ambientLight intensity={0.4} />
            <directionalLight position={[20, 30, 10]} intensity={1.1} color="#e2e8f0" />
            <pointLight position={[-30, 8, -40]} intensity={0.8} color="#38bdf8" />

            {/* UI & HUD - Mounted inside Camera Rig Group or synced manually */}
            <group position={[0, 0, -1.5]} ref={cockpitRef}>
                <Suspense fallback={null}>
                    <HolographicHud
                        stageLabel={`Sector ${level}`}
                        stageObjective={enemies.some(e => e.type === 'boss') ? "DESTROY MOTHERSHIP" : "CLEAR SECTOR"}
                        bossHealth={enemies.find(e => e.type === 'boss') ? enemies.find(e => e.type === 'boss')!.hp : null}
                    />
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

        </group>
    )
}
