import { useEffect, useRef, useState } from 'react'
import { GAME_CONFIG } from '../config/GameConstants'
import { useFrame } from '@react-three/fiber'
import { useSound } from './SoundManager'
import { Vector3, Quaternion } from 'three'
import { useEnemyStore } from './EnemySystem'
import { useGame } from '../../../context/GameContext'
import { useGLTF } from '@react-three/drei'
import { useGameSettings } from './GameSettings'

// Game phases - one enemy type at a time
type GamePhase = 'asteroid_intro' | 'asteroids' | 'drones' | 'fighters' | 'elite' | 'boss_approaching' | 'boss_fight' | 'victory'

const FORMATIONS = {
    asteroid: { total: 8, columns: 4, spacingX: 90, spacingY: 60, baseY: 60 },
    drone: { total: 6, columns: 3, spacingX: 80, spacingY: 50, baseY: 35 },
    fighter: { total: 4, columns: 2, spacingX: 110, spacingY: 70, baseY: 35 },
    elite: { total: 1, columns: 1, spacingX: 0, spacingY: 0, baseY: 45 }
}

const buildWallAnchor = (index: number, total: number, columns: number, spacingX: number, spacingY: number, baseY: number, z: number, seed: number) => {
    const rows = Math.ceil(total / columns)
    const row = Math.floor(index / columns)
    const col = index % columns
    const centerCol = (columns - 1) / 2
    const centerRow = (rows - 1) / 2

    const x = (col - centerCol) * spacingX
    const y = baseY + (row - centerRow) * spacingY

    const jitterX = Math.sin(seed * Math.PI * 2) * spacingX * 0.15
    const jitterY = Math.cos(seed * Math.PI * 2) * spacingY * 0.15

    return {
        anchor: new Vector3(x, y, z),
        offset: new Vector3(jitterX, jitterY, 0)
    }
}

export const WaveManager = () => {
    const { levelUp, addScore } = useGame()
    const { spawnEnemy, clearEnemies } = useEnemyStore()
    const sound = useSound()
    const { isPaused } = useGameSettings()

    // Phase state
    const [, setPhase] = useState<GamePhase>('asteroid_intro')
    const phaseRef = useRef<GamePhase>('asteroid_intro')

    // Stage tracking (1-10, cycles for endless mode)
    const stageRef = useRef<1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10>(1)

    // Timers
    const lastAsteroidSpawn = useRef(0)
    const asteroidCount = useRef(0)
    const bossSpawned = useRef(false)
    const elapsedMs = useRef(0)
    const phaseStartMs = useRef(0)



    // Track kills per phase
    const phaseKills = useRef(0)

    // Track if elite has been spawned (to prevent double-spawn)
    const eliteSpawned = useRef(false)

    // Reset on mount
    useEffect(() => {
        clearEnemies()
        setPhase('asteroids')
        phaseRef.current = 'asteroids'
        lastAsteroidSpawn.current = 0
        asteroidCount.current = 0
        bossSpawned.current = false
        elapsedMs.current = 0
        phaseStartMs.current = 0
        phaseKills.current = 0
        eliteSpawned.current = false

        // Debug log removed
    }, [clearEnemies])

    // Immediate Preload (Asteroids) + Delayed Preload (Ships) to prevent lag spike
    useEffect(() => {
        // Load Asteroids ASAP for Stage 1
        useGLTF.preload('/models/asteroids/asteroid1.glb')

        // Load Heavy Ships in background after game has started (3s delay)
        const timeout = setTimeout(() => {
            // Debug log removed
            useGLTF.preload('/models/enemies/ship1.glb')
            useGLTF.preload('/models/enemies/ship2.glb')
        }, 3000)

        return () => clearTimeout(timeout)
    }, [])

    // Spawn a single asteroid
    const spawnAsteroid = (formationIndex: number) => {
        const dist = 126 + Math.random() * 56 // 30% closer
        const z = -dist - Math.random() * 100
        const seed = Math.random()
        const { anchor, offset } = buildWallAnchor(
            formationIndex,
            FORMATIONS.asteroid.total,
            FORMATIONS.asteroid.columns,
            FORMATIONS.asteroid.spacingX,
            FORMATIONS.asteroid.spacingY,
            FORMATIONS.asteroid.baseY,
            z,
            seed
        )

        spawnEnemy({
            id: `asteroid-${Date.now()}-${Math.random()}`,
            type: 'asteroid',
            stage: stageRef.current,
            position: anchor.clone().add(offset),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.ASTEROID,
            maxHp: GAME_CONFIG.ENEMIES.HP.ASTEROID,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'drift',
            seed,
            createdAt: Date.now(),
            wallAnchor: anchor,
            wallOffset: offset,
            wallPhase: seed * Math.PI * 2
        })
        asteroidCount.current++
    }

    // Spawn a drone (small, fast)
    const spawnDrone = (formationIndex: number) => {
        const dist = 105 + Math.random() * 35 // 30% closer
        const z = -dist
        const seed = Math.random()
        const { anchor, offset } = buildWallAnchor(
            formationIndex,
            FORMATIONS.drone.total,
            FORMATIONS.drone.columns,
            FORMATIONS.drone.spacingX,
            FORMATIONS.drone.spacingY,
            FORMATIONS.drone.baseY,
            z,
            seed
        )

        spawnEnemy({
            id: `drone-${Date.now()}-${Math.random()}`,
            type: 'drone',
            stage: stageRef.current,
            position: anchor.clone().add(offset),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.DRONE,
            maxHp: GAME_CONFIG.ENEMIES.HP.DRONE,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'strafe',
            seed,
            createdAt: Date.now(),
            wallAnchor: anchor,
            wallOffset: offset,
            wallPhase: seed * Math.PI * 2
        })
    }

    // Spawn a fighter (medium, aggressive)
    const spawnFighter = (formationIndex: number) => {
        const dist = 140 + Math.random() * 56 // 30% closer
        const z = -dist
        const seed = Math.random()
        const { anchor, offset } = buildWallAnchor(
            formationIndex,
            FORMATIONS.fighter.total,
            FORMATIONS.fighter.columns,
            FORMATIONS.fighter.spacingX,
            FORMATIONS.fighter.spacingY,
            FORMATIONS.fighter.baseY,
            z,
            seed
        )

        spawnEnemy({
            id: `fighter-${Date.now()}-${Math.random()}`,
            type: 'fighter',
            stage: stageRef.current,
            position: anchor.clone().add(offset),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.FIGHTER,
            maxHp: GAME_CONFIG.ENEMIES.HP.FIGHTER,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'swoop',
            seed,
            createdAt: Date.now(),
            wallAnchor: anchor,
            wallOffset: offset,
            wallPhase: seed * Math.PI * 2
        })
    }

    // Spawn an elite (mini-boss)
    const spawnElite = () => {
        const z = -210 - Math.random() * 70 // 30% closer
        const seed = Math.random()
        const { anchor, offset } = buildWallAnchor(
            0,
            FORMATIONS.elite.total,
            FORMATIONS.elite.columns,
            FORMATIONS.elite.spacingX,
            FORMATIONS.elite.spacingY,
            FORMATIONS.elite.baseY,
            z,
            seed
        )

        spawnEnemy({
            id: `elite-${Date.now()}-${Math.random()}`,
            type: 'elite',
            stage: stageRef.current,
            position: anchor.clone().add(offset),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.ELITE,
            maxHp: GAME_CONFIG.ENEMIES.HP.ELITE,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'circle',
            seed,
            createdAt: Date.now(),
            wallAnchor: anchor,
            wallOffset: offset,
            wallPhase: seed * Math.PI * 2
        })
    }

    // Spawn the massive mothership boss
    const spawnMothership = () => {
        if (bossSpawned.current) return
        bossSpawned.current = true

        sound.playBossSpawn()
        // Debug log removed

        // Spawn CLOSE and in front - filling the screen
        // Position it so the player can see the full scale
        const x = 0
        const y = 10
        const z = -600 // Start WAY back for long approach
        const seed = Math.random()

        spawnEnemy({
            id: `boss-mothership-${Date.now()}`,
            type: 'boss',
            stage: stageRef.current,
            position: new Vector3(x, y, z),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.BOSS,
            maxHp: GAME_CONFIG.ENEMIES.HP.BOSS,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'direct', // Slow approach
            seed,
            createdAt: Date.now(),
            wallAnchor: new Vector3(x, y, z),
            wallOffset: new Vector3(0, 0, 0),
            wallPhase: seed * Math.PI * 2
        })

        levelUp()
    }

    const setPhaseState = (next: GamePhase) => {
        setPhase(next)
        phaseRef.current = next
        phaseStartMs.current = elapsedMs.current
    }

    // Spawn timers and tracking
    const lastSpawn = useRef(0)
    const totalSpawned = useRef(0)

    // Main game loop - ONE enemy type at a time
    useFrame((_, delta) => {
        if (isPaused) return
        elapsedMs.current += delta * 1000
        const now = elapsedMs.current
        const enemies = useEnemyStore.getState().enemies
        const phaseElapsed = now - phaseStartMs.current

        // Track kills by detecting enemy count decreases (excluding despawns which also reduce count)
        const currentEnemyCount = enemies.length

        // Helper: Get FRESH enemy count - MUST call this before phase transitions
        // to avoid race conditions where spawning within the same frame makes
        // the initial enemies snapshot stale
        const getFreshEnemyCount = () => useEnemyStore.getState().enemies.length

        // Use switch to ensure only ONE phase logic runs per frame
        switch (phaseRef.current) {
            case 'asteroids': {
                // PHASE 1: ASTEROIDS - Spawn 8, then clear to advance
                const currentCount = enemies.filter(e => e.type === 'asteroid').length

                // Only spawn more if we haven't spawned enough yet
                if (totalSpawned.current < 8 && now - lastSpawn.current > 1500 && currentCount < 4) {
                    const formationIndex = totalSpawned.current
                    lastSpawn.current = now
                    spawnAsteroid(formationIndex)
                    totalSpawned.current++
                }

                // After spawning 8 and clearing the field - use FRESH count to avoid stale data
                if (totalSpawned.current >= 8 && getFreshEnemyCount() === 0) {
                    // Debug log removed
                    clearEnemies()
                    totalSpawned.current = 0
                    setPhaseState('drones')
                }
                break
            }

            case 'drones': {
                // PHASE 2: DRONES - Spawn 6, then clear to advance
                const currentCount = enemies.filter(e => e.type === 'drone').length

                if (totalSpawned.current < 6 && now - lastSpawn.current > 2000 && currentCount < 3) {
                    const formationIndex = totalSpawned.current
                    lastSpawn.current = now
                    spawnDrone(formationIndex)
                    totalSpawned.current++
                }

                if (totalSpawned.current >= 6 && getFreshEnemyCount() === 0) {
                    // Debug log removed
                    clearEnemies()
                    totalSpawned.current = 0
                    setPhaseState('fighters')
                }
                break
            }

            case 'fighters': {
                // PHASE 3: FIGHTERS - Spawn 4, then clear to advance
                const currentCount = enemies.filter(e => e.type === 'fighter').length

                if (totalSpawned.current < 4 && now - lastSpawn.current > 3000 && currentCount < 2) {
                    const formationIndex = totalSpawned.current
                    lastSpawn.current = now
                    spawnFighter(formationIndex)
                    totalSpawned.current++
                }

                if (totalSpawned.current >= 4 && getFreshEnemyCount() === 0) {
                    // Debug log removed
                    totalSpawned.current = 0
                    eliteSpawned.current = false  // Reset for new elite phase
                    setPhaseState('elite')
                    // Elite spawn moved to 'elite' case with delay for stability
                }
                break
            }

            case 'elite': {
                // PHASE 4: ELITE - Spawn elite after a short delay, then kill to advance
                // Spawn elite with delay to ensure phase transition is complete
                if (!eliteSpawned.current && phaseElapsed > 500) {
                    // Debug log removed
                    spawnElite()
                    eliteSpawned.current = true
                }

                // Check if elite is defeated (only after spawn)
                if (eliteSpawned.current) {
                    const eliteCount = useEnemyStore.getState().enemies.filter(e => e.type === 'elite').length
                    if (eliteCount === 0 && phaseElapsed > 1000) {
                        // Only advance if elite is actually dead (not just spawned)
                        // Debug log removed
                        clearEnemies()
                        setPhaseState('boss_approaching')
                    }
                }
                break
            }

            case 'boss_approaching': {
                // PHASE 5: Boss Approaching (dramatic pause)
                if (phaseElapsed > 2500) {
                    clearEnemies()
                    setPhaseState('boss_fight')
                    spawnMothership()
                }
                break
            }

            case 'boss_fight': {
                // PHASE 6: Boss Fight
                const boss = enemies.find(e => e.type === 'boss')

                if (!boss && bossSpawned.current) {
                    // Debug log removed
                    setPhaseState('victory')
                    addScore(10000)
                    sound.playLevelUp()
                }
                break
            }

            case 'victory': {
                // PHASE 7: Victory - advance to next stage
                if (phaseElapsed > 3000) {
                    // Advance stage (1 → 2 → ... → 10 → 1 for endless mode)
                    const nextStage = stageRef.current === 10 ? 1 : (stageRef.current + 1) as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10
                    stageRef.current = nextStage

                    // Restart the cycle with new stage
                    clearEnemies()
                    bossSpawned.current = false
                    totalSpawned.current = 0
                    setPhaseState('asteroids')
                }
                break
            }
        }
    })

    return null // Logic-only controller
}
