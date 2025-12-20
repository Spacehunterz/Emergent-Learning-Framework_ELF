import { Vector3 } from 'three'
import { useFrame } from '@react-three/fiber'
import { useGame } from '../../../context/GameContext'
import { useProjectileStore } from './WeaponSystem'
import { useEnemyStore } from './EnemySystem'
import { useExplosionStore } from './ExplosionManager'
// import { usePlayerState } from '../cockpit/PlayerShip' // Circular dep? Better to move store to separate file or use event.
import { useFloatingTextStore } from './FloatingTextManager'
import { useSound } from './SoundManager'
// For now, let's just assume we can get the player state or dispatch an event.
// Actually, let's simple export the store from a new PlayerSystem file if we could, but for speed:
// We will emit a custom event "player-hit" or just use a global store if possible.
// Let's use the window dispatch for now for loose coupling or just import the hook if it works.

export const CollisionManager = () => {
    const { projectiles, removeProjectile, updateProjectiles } = useProjectileStore()
    const { enemies, damageEnemy, tick } = useEnemyStore()
    const { spawnExplosion } = useExplosionStore()
    const { spawnText } = useFloatingTextStore()
    const { addScore } = useGame()
    const sound = useSound()

    useFrame((_, delta) => {
        if (performance.now() % 60 < 1) console.log('[CollisionManager] Tick', delta)
        updateProjectiles(delta)
        tick(delta) // Update Enemy Positions (Centralized)


        // FIXED: Use squared distance to avoid expensive sqrt() calls
        const HIT_RADIUS_SQ = 16 // 4^2
        const BULLET_RADIUS_SQ = 4 // 2^2

        // Pre-allocate temp vector for text position
        const tempTextPos = new Vector3()

        // Check Projectiles vs Enemies
        projectiles.forEach(p => {
            if (p.owner === 'PLAYER') {
                // Check vs Enemies - FIXED: use distanceToSquared
                for (const e of enemies) {
                    const distSq = p.position.distanceToSquared(e.position)

                    // Dynamic Hit Radius Calculation
                    let hitRadius = 15 // Default (Fighters)
                    if (e.type === 'asteroid') hitRadius = 25
                    if (e.type === 'boss') hitRadius = 250 // Massive hitbox for massive ship

                    const hitRadiusSq = hitRadius * hitRadius

                    if (distSq < hitRadiusSq) { // Enemy Hit Radius squared
                        removeProjectile(p.id)
                        spawnExplosion(p.position, 'cyan', 0.5) // Small hit effect
                        sound.playHit()

                        // DAMAGE TEXT - FIXED: reuse temp vector instead of clone
                        tempTextPos.copy(e.position).addScalar((Math.random() - 0.5) * 2)
                        spawnText(tempTextPos, p.damage.toString(), '#22d3ee', 1.0) // Cyan Text

                        const dead = damageEnemy(e.id, p.damage)
                        if (dead) {
                            spawnExplosion(e.position, 'orange', 2) // Big boom
                            sound.playExplosion('large')
                            // SCORE POPUP - FIXED: reuse temp vector
                            tempTextPos.copy(e.position).addScalar(2)
                            spawnText(tempTextPos, '+100', '#fbbf24', 1.5) // Gold Text
                            addScore(100)
                        }
                        break // FIXED: use break instead of return (return in forEach only exits callback)
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
                            spawnText(p.position, 'BLOCK', '#a1a1aa', 0.8)
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
