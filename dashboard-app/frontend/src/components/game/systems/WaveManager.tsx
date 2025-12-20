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

export const WaveManager = () => {
    const { levelUp, addScore } = useGame()
    const { spawnEnemy, clearEnemies } = useEnemyStore()
    const sound = useSound()
    const { isPaused } = useGameSettings()

    // Phase state
    const [, setPhase] = useState<GamePhase>('asteroid_intro')
    const phaseRef = useRef<GamePhase>('asteroid_intro')

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

        console.log('[WaveManager] Starting asteroids phase...')
    }, [clearEnemies])

    // Immediate Preload (Asteroids) + Delayed Preload (Ships) to prevent lag spike
    useEffect(() => {
        // Load Asteroids ASAP for Stage 1
        useGLTF.preload('/models/asteroids/asteroid1.glb')

        // Load Heavy Ships in background after game has started (3s delay)
        const timeout = setTimeout(() => {
            console.log('[WaveManager] Background loading heavy assets...')
            useGLTF.preload('/models/enemies/ship1.glb')
            useGLTF.preload('/models/enemies/ship2.glb')
        }, 3000)

        return () => clearTimeout(timeout)
    }, [])

    // Spawn a single asteroid
    const spawnAsteroid = () => {
        const angle = (Math.random() - 0.5) * Math.PI * 2.0
        const dist = 180 + Math.random() * 80
        const x = Math.sin(angle) * dist * 2.5
        const z = -dist - Math.random() * 100
        const y = (Math.random() - 0.5) * 180 + 60

        spawnEnemy({
            id: `asteroid-${Date.now()}-${Math.random()}`,
            type: 'asteroid',
            position: new Vector3(x, y, z),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.ASTEROID,
            maxHp: GAME_CONFIG.ENEMIES.HP.ASTEROID,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'drift',
            seed: Math.random(),
            createdAt: Date.now()
        })
        asteroidCount.current++
    }

    // Spawn a drone (small, fast)
    const spawnDrone = () => {
        const angle = (Math.random() - 0.5) * Math.PI * 1.5
        const dist = 150 + Math.random() * 50
        const x = Math.sin(angle) * dist * 1.5
        const z = -dist
        const y = (Math.random() - 0.5) * 100 + 30

        spawnEnemy({
            id: `drone-${Date.now()}-${Math.random()}`,
            type: 'drone',
            position: new Vector3(x, y, z),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.DRONE,
            maxHp: GAME_CONFIG.ENEMIES.HP.DRONE,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'strafe',
            seed: Math.random(),
            createdAt: Date.now()
        })
    }

    // Spawn a fighter (medium, aggressive)
    const spawnFighter = () => {
        const angle = (Math.random() - 0.5) * Math.PI
        const dist = 200 + Math.random() * 80
        const x = Math.sin(angle) * dist * 2
        const z = -dist
        const y = (Math.random() - 0.5) * 80 + 20

        spawnEnemy({
            id: `fighter-${Date.now()}-${Math.random()}`,
            type: 'fighter',
            position: new Vector3(x, y, z),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.FIGHTER,
            maxHp: GAME_CONFIG.ENEMIES.HP.FIGHTER,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'swoop',
            seed: Math.random(),
            createdAt: Date.now()
        })
    }

    // Spawn an elite (mini-boss)
    const spawnElite = () => {
        const x = (Math.random() - 0.5) * 200
        const z = -300 - Math.random() * 100
        const y = Math.random() * 60 + 20

        spawnEnemy({
            id: `elite-${Date.now()}-${Math.random()}`,
            type: 'elite',
            position: new Vector3(x, y, z),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.ELITE,
            maxHp: GAME_CONFIG.ENEMIES.HP.ELITE,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'circle',
            seed: Math.random(),
            createdAt: Date.now()
        })
    }

    // Spawn the massive mothership boss
    const spawnMothership = () => {
        if (bossSpawned.current) return
        bossSpawned.current = true

        sound.playBossSpawn()
        console.log('[WaveManager] SPAWNING MOTHERSHIP BOSS!')

        // Spawn CLOSE and in front - filling the screen
        // Position it so the player can see the full scale
        const x = 0
        const y = 10
        const z = -600 // Start WAY back for long approach

        spawnEnemy({
            id: `boss-mothership-${Date.now()}`,
            type: 'boss',
            position: new Vector3(x, y, z),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.BOSS,
            maxHp: GAME_CONFIG.ENEMIES.HP.BOSS,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'direct', // Slow approach
            seed: Math.random(),
            createdAt: Date.now()
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
                    lastSpawn.current = now
                    spawnAsteroid()
                    totalSpawned.current++
                    console.log(`[WaveManager] Spawned asteroid ${totalSpawned.current}/8`)
                }

                // After spawning 8 and clearing the field - use FRESH count to avoid stale data
                if (totalSpawned.current >= 8 && getFreshEnemyCount() === 0) {
                    console.log('[WaveManager] ASTEROIDS CLEARED! Moving to drones...')
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
                    lastSpawn.current = now
                    spawnDrone()
                    totalSpawned.current++
                    console.log(`[WaveManager] Spawned drone ${totalSpawned.current}/6`)
                }

                if (totalSpawned.current >= 6 && getFreshEnemyCount() === 0) {
                    console.log('[WaveManager] DRONES CLEARED! Moving to fighters...')
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
                    lastSpawn.current = now
                    spawnFighter()
                    totalSpawned.current++
                    console.log(`[WaveManager] Spawned fighter ${totalSpawned.current}/4`)
                }

                if (totalSpawned.current >= 4 && getFreshEnemyCount() === 0) {
                    console.log('[WaveManager] FIGHTERS CLEARED! Transitioning to elite phase...')
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
                    console.log('[WaveManager] Spawning ELITE...')
                    spawnElite()
                    eliteSpawned.current = true
                }

                // Check if elite is defeated (only after spawn)
                if (eliteSpawned.current) {
                    const eliteCount = useEnemyStore.getState().enemies.filter(e => e.type === 'elite').length
                    if (eliteCount === 0 && phaseElapsed > 1000) {
                        // Only advance if elite is actually dead (not just spawned)
                        console.log('[WaveManager] ELITE DESTROYED! Boss approaching...')
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
                    console.log('[WaveManager] BOSS DEFEATED!')
                    setPhaseState('victory')
                    addScore(10000)
                    sound.playLevelUp()
                }
                break
            }

            case 'victory': {
                // PHASE 7: Victory
                if (phaseElapsed > 3000) {
                    // Restart the cycle for endless mode
                    console.log('[WaveManager] Restarting cycle...')
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
