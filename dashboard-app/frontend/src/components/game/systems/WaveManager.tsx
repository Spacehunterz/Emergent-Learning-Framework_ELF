import { useEffect, useRef, useState } from 'react'
import { GAME_CONFIG } from '../config/GameConstants'
import { useFrame } from '@react-three/fiber'
import { useSound } from './SoundManager'
import { Vector3, Quaternion } from 'three'
import { useEnemyStore } from './EnemySystem'
import { useGame } from '../../../context/GameContext'
import { useGLTF } from '@react-three/drei'

// Game phases for the Contra-style flow
type GamePhase = 'asteroid_intro' | 'boss_approaching' | 'boss_fight' | 'victory'

export const WaveManager = () => {
    const { levelUp, addScore } = useGame()
    const { spawnEnemy, clearEnemies } = useEnemyStore()
    const sound = useSound()

    // Phase state
    const [, setPhase] = useState<GamePhase>('asteroid_intro')
    const phaseRef = useRef<GamePhase>('asteroid_intro')

    // Timers
    const lastAsteroidSpawn = useRef(0)
    const asteroidCount = useRef(0)
    const bossSpawned = useRef(false)
    const introStartTime = useRef(0)



    // Reset on mount
    useEffect(() => {
        clearEnemies()
        setPhase('asteroid_intro')
        phaseRef.current = 'asteroid_intro'
        lastAsteroidSpawn.current = 0
        asteroidCount.current = 0
        bossSpawned.current = false
        introStartTime.current = Date.now()

        console.log('[WaveManager] Starting asteroid intro phase...')
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

    // Spawn a single asteroid for target practice
    const spawnAsteroid = () => {
        // Random position - wider spread
        const angle = (Math.random() - 0.5) * Math.PI * 1.5 // Wider angle
        const dist = 150 + Math.random() * 50 // Spawn distance
        const x = Math.sin(angle) * dist * 2.0 // Widen x
        const z = -dist // Coming toward player
        const y = (Math.random() - 0.5) * 140 + 80 // Raised HIGHER per request

        console.log(`[WaveManager] Spawning asteroid #${asteroidCount.current + 1} at (${x.toFixed(0)}, ${y.toFixed(0)}, ${z.toFixed(0)})`)

        spawnEnemy({
            id: `asteroid-${Date.now()}-${Math.random()}`,
            type: 'asteroid',
            position: new Vector3(x, y, z),
            rotation: new Quaternion(),
            hp: GAME_CONFIG.ENEMIES.HP.ASTEROID,
            maxHp: GAME_CONFIG.ENEMIES.HP.ASTEROID,
            velocity: new Vector3(0, 0, 0),
            isDead: false,
            aiPattern: 'direct',
            seed: Math.random(),
            createdAt: Date.now()
        })

        asteroidCount.current++
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

    // Main game loop
    useFrame(() => {
        const now = Date.now()
        const enemies = useEnemyStore.getState().enemies
        const introElapsed = now - introStartTime.current

        // PHASE: Asteroid Intro (target practice cutscene)
        if (phaseRef.current === 'asteroid_intro') {
            // Spawn asteroids (Increased rate for engagement)
            if (now - lastAsteroidSpawn.current > 1200) {
                lastAsteroidSpawn.current = now
                spawnAsteroid()
            }

            // After 45 seconds OR 25 asteroids destroyed, transition to boss
            const destroyedCount = asteroidCount.current - enemies.filter(e => e.type === 'asteroid').length
            if (introElapsed > 45000 || destroyedCount >= 25) {
                console.log('[WaveManager] Transitioning to boss approach...')
                setPhase('boss_approaching')
                phaseRef.current = 'boss_approaching'

                // Clear remaining asteroids
                clearEnemies()
            }
        }

        // PHASE: Boss Approaching (dramatic pause)
        if (phaseRef.current === 'boss_approaching') {
            // Give 2 seconds of empty space for dramatic effect
            if (introElapsed > 17000) {
                setPhase('boss_fight')
                phaseRef.current = 'boss_fight'
                spawnMothership()
            }
        }

        // PHASE: Boss Fight
        if (phaseRef.current === 'boss_fight') {
            const boss = enemies.find(e => e.type === 'boss')

            if (!boss && bossSpawned.current) {
                // Boss defeated!
                console.log('[WaveManager] BOSS DEFEATED!')
                setPhase('victory')
                phaseRef.current = 'victory'
                addScore(10000) // Big bonus
                sound.playLevelUp()
            }
        }

        // PHASE: Victory
        if (phaseRef.current === 'victory') {
            // Could restart or show victory screen
            // For now, respawn another boss after 5 seconds
            // TODO: Add proper victory flow
        }
    })

    return null // Logic-only controller
}
