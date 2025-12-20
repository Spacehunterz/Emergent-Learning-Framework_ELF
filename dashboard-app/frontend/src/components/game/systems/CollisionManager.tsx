import { Vector3, Quaternion } from 'three'
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import { useGame } from '../../../context/GameContext'
import { useProjectileStore } from './WeaponSystem'
import { useEnemyStore, EnemyType } from './EnemySystem'
import { useExplosionStore } from './ExplosionManager'
// import { usePlayerState } from '../cockpit/PlayerShip' // Circular dep? Better to move store to separate file or use event.
import { useFloatingTextStore } from './FloatingTextManager'
import { useSound } from './SoundManager'
import { useGameSettings } from './GameSettings'
// For now, let's just assume we can get the player state or dispatch an event.
// Actually, let's simple export the store from a new PlayerSystem file if we could, but for speed:
// We will emit a custom event "player-hit" or just use a global store if possible.
// Let's use the window dispatch for now for loose coupling or just import the hook if it works.

// Enemy firing configuration
const ENEMY_FIRE_CONFIG: Record<EnemyType, { cooldown: number; speed: number; damage: number; range: number } | null> = {
    drone: { cooldown: 2.5, speed: 60, damage: 5, range: 150 },
    fighter: { cooldown: 1.8, speed: 80, damage: 8, range: 200 },
    elite: { cooldown: 1.2, speed: 100, damage: 12, range: 250 },
    boss: { cooldown: 0.8, speed: 70, damage: 15, range: 300 },
    asteroid: null, // Asteroids don't shoot
    scout: { cooldown: 3.0, speed: 50, damage: 4, range: 120 }
}

export const CollisionManager = () => {
    const { projectiles, removeProjectile, updateProjectiles, spawnProjectile } = useProjectileStore()
    const { enemies, damageEnemy, tick } = useEnemyStore()
    const { spawnExplosion } = useExplosionStore()
    const { spawnText } = useFloatingTextStore()
    const { addScore } = useGame()
    const sound = useSound()
    const { isPaused } = useGameSettings()

    // Track last fire time per enemy
    const enemyLastFire = useRef<Map<string, number>>(new Map())

    useFrame((_, delta) => {
        if (isPaused) return
        updateProjectiles(delta)
        tick(delta) // Update Enemy Positions (Centralized)


        // FIXED: Use squared distance to avoid expensive sqrt() calls
        const BULLET_RADIUS_SQ = 4 // 2^2

        // Pre-allocate temp vector for text position
        const tempTextPos = new Vector3()

        // Check Projectiles vs Enemies
        // PLAYER-ENEMY BODY COLLISION - Push enemies away when too close
        const PLAYER_COLLISION_RADIUS = 8 // Player's collision sphere
        const PUSH_FORCE = 50 // How fast to push enemies away

        enemies.forEach(enemy => {
            const distToPlayer = enemy.position.length()

            // Dynamic collision radius based on enemy type
            let enemyRadius = 10
            if (enemy.type === 'asteroid') enemyRadius = 15
            if (enemy.type === 'drone') enemyRadius = 10
            if (enemy.type === 'fighter') enemyRadius = 15
            if (enemy.type === 'elite') enemyRadius = 30
            if (enemy.type === 'boss') enemyRadius = 50

            const minDist = PLAYER_COLLISION_RADIUS + enemyRadius

            if (distToPlayer < minDist && distToPlayer > 0.1) {
                // Push enemy away from player (origin)
                const pushDir = enemy.position.clone().normalize()
                const pushAmount = (minDist - distToPlayer) * PUSH_FORCE * delta
                enemy.position.add(pushDir.multiplyScalar(pushAmount))

                // If enemy is VERY close, damage the player (ram damage)
                if (distToPlayer < minDist * 0.5) {
                    // Throttle ram damage to once per second
                    const now = Date.now()
                    const lastRamKey = `ram_${enemy.id}`
                    const lastRam = (window as any)[lastRamKey] || 0
                    if (now - lastRam > 1000) {
                        (window as any)[lastRamKey] = now
                        const ramDamage = enemy.type === 'boss' ? 20 : (enemy.type === 'asteroid' ? 5 : 10)
                        window.dispatchEvent(new CustomEvent('player-hit', { detail: { damage: ramDamage } }))
                        spawnExplosion(enemy.position.clone().normalize().multiplyScalar(5), 'orange', 1)
                        sound.playShieldHit()
                    }
                }
            }

            // --- ENEMY FIRING LOGIC ---
            const fireConfig = ENEMY_FIRE_CONFIG[enemy.type]
            if (fireConfig && distToPlayer < fireConfig.range) {
                const now = Date.now()
                const lastFire = enemyLastFire.current.get(enemy.id) || 0
                const cooldownMs = fireConfig.cooldown * 1000

                if (now - lastFire > cooldownMs) {
                    enemyLastFire.current.set(enemy.id, now)

                    // Fire at player (origin)
                    const direction = new Vector3(0, 0, 0).sub(enemy.position).normalize()
                    const velocity = direction.clone().multiplyScalar(fireConfig.speed)
                    const rotation = new Quaternion().setFromUnitVectors(new Vector3(0, 0, 1), direction)

                    spawnProjectile({
                        id: `enemy-${enemy.id}-${now}`,
                        position: enemy.position.clone(),
                        rotation: rotation,
                        velocity: velocity,
                        damage: fireConfig.damage,
                        owner: 'ENEMY',
                        type: 'PLASMA',
                        createdAt: now,
                        lifetime: 4
                    })

                    // Play enemy laser sound
                    sound.playLaser('enemy')
                }
            }
        })

        projectiles.forEach(p => {
            if (p.owner === 'PLAYER') {
                // Check vs Enemies - FIXED: use distanceToSquared
                for (const e of enemies) {
                    const distSq = p.position.distanceToSquared(e.position)

                    // Dynamic Hit Radius Calculation
                    let hitRadius = 15 // Default
                    if (e.type === 'asteroid') hitRadius = 20
                    if (e.type === 'drone') hitRadius = 12
                    if (e.type === 'fighter') hitRadius = 18
                    if (e.type === 'elite') hitRadius = 35
                    if (e.type === 'boss') hitRadius = 80

                    const hitRadiusSq = hitRadius * hitRadius

                    if (distSq < hitRadiusSq) { // Enemy Hit Radius squared
                        removeProjectile(p.id)
                        spawnExplosion(p.position, 'cyan', 0.5) // Small hit effect
                        sound.playHit()

                        // PERF: Removed per-hit damage text (expensive drei Text component)

                        const dead = damageEnemy(e.id, p.damage)
                        if (dead) {
                            spawnExplosion(e.position, e.type === 'boss' ? 'cyan' : 'orange', e.type === 'boss' ? 4 : 2)
                            // Small explosions for smaller enemies, large for bigger ones
                            const isLargeExplosion = e.type === 'boss' || e.type === 'elite' || e.type === 'fighter'
                            sound.playExplosion(isLargeExplosion ? 'large' : 'small')
                            // Score based on enemy type
                            const scores: Record<string, number> = {
                                asteroid: 50,
                                drone: 100,
                                fighter: 200,
                                elite: 1000,
                                boss: 5000
                            }
                            const score = scores[e.type] || 100
                            tempTextPos.copy(e.position).addScalar(2)
                            spawnText(tempTextPos, `+${score}`, '#fbbf24', 1.5)
                            addScore(score)
                        }
                        break
                    }
                }

                // Check vs Enemy Projectiles (INTERCEPTION) - FIXED: use distanceToSquared
                projectiles.forEach(otherP => {
                    if (otherP.owner !== 'PLAYER') {
                        const distSq = p.position.distanceToSquared(otherP.position)
                        if (distSq < BULLET_RADIUS_SQ) { // Bullet vs Bullet radius squared
                            removeProjectile(p.id)
                            removeProjectile(otherP.id)
                            spawnExplosion(p.position, 'white', 0.3) // Tiny spark
                            sound.playExplosion('small') // Small pop for bullet interception
                            // PERF: Removed "BLOCK" text (expensive drei Text component)
                        }
                    }
                })

            } else {
                // ENEMY PROJECTILE vs PLAYER
                // Player is at 0,0,0
                if (p.position.length() < 3) { // Player Hit Radius
                    removeProjectile(p.id)
                    spawnExplosion(p.position, 'blue', 1) // Shield hit effect
                    sound.playShieldHit()

                    // Dispatch Shield Damage Event
                    window.dispatchEvent(new CustomEvent('player-hit', { detail: { damage: p.damage } }))
                }
            }
        })
    })

    return null
}
