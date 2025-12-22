
import { System } from './System'
import { GameEngine } from '../core/GameEngine'
import { GameState, EntityState } from '../core/GameState'
import { Vector3 } from 'three'

export class PhysicsSystem implements System {
    private engine!: GameEngine

    initialize(engine: GameEngine) {
        this.engine = engine
    }

    update(delta: number, state: GameState) {
        // No variable update needed for physics
    }

    fixedUpdate(delta: number, state: GameState) {
        this.checkProjectileCollisions(state)
        this.checkPlayerCollisions(state)
    }

    private checkProjectileCollisions(state: GameState) {
        // Simple O(N*M) for now - can optimize with grid later if needed
        // Given < 1000 bullets and < 50 enemies, it's fine for JS

        for (const projectile of state.projectiles) {
            if (!projectile.active) continue

            // Player Bullet vs Enemies
            if (projectile.owner === 'PLAYER') {
                for (const enemy of state.enemies) {
                    if (!enemy.active) continue

                    const distSq = projectile.position.distanceToSquared(enemy.position)
                    const hitRadius = this.getEnemyRadius(enemy.type)

                    if (distSq < hitRadius * hitRadius) {
                        this.handleHit(projectile, enemy, state)
                        break // Bullet consumed
                    }
                }
            }

            // Enemy Bullet vs Player
            else if (projectile.owner === 'ENEMY') {
                const distSq = projectile.position.distanceToSquared(state.player.position)
                // Player radius approx 3
                if (distSq < 3 * 3) {
                    this.handlePlayerHit(projectile, state)
                }
            }
        }
    }

    private checkPlayerCollisions(state: GameState) {
        const playerPos = state.player.position

        for (const enemy of state.enemies) {
            if (!enemy.active) continue

            const dist = enemy.position.distanceTo(playerPos)
            const enemyRadius = this.getEnemyRadius(enemy.type)
            const minSpace = 8 + enemyRadius // 8 is player safety bubble

            if (dist < minSpace) {
                // Push enemy away
                const pushDir = enemy.position.clone().sub(playerPos).normalize()
                const pushDist = minSpace - dist
                enemy.position.add(pushDir.multiplyScalar(pushDist))
            }
        }
    }

    private handleHit(projectile: EntityState, enemy: EntityState, state: GameState) {
        projectile.active = false
        enemy.hp -= projectile.damage
        enemy.lastHitTime = state.time.elapsed

        if (enemy.hp <= 0 && !enemy.isDying) {
            enemy.isDying = true
            enemy.deathTimer = 0
            // Do not set active=false yet (Animation plays first)

            state.score += this.getScoreValue(enemy.type)
            this.engine?.sound?.playExplosion(enemy.type === 'boss' ? 'large' : 'small')
        } else if (!enemy.isDying) {
            this.engine?.sound?.playHit()
        }
    }

    private handlePlayerHit(projectile: EntityState, state: GameState) {
        projectile.active = false
        this.engine?.sound?.playShieldHit()

        if (state.player.shields > 0) {
            state.player.shields = Math.max(0, state.player.shields - projectile.damage)
        } else {
            state.player.hp = Math.max(0, state.player.hp - projectile.damage)
        }

        if (state.player.hp <= 0) {
            state.isGameOver = true
        }
    }

    private getEnemyRadius(type: string): number {
        switch (type) {
            case 'boss': return 50
            case 'elite': return 30
            case 'scout': return 20
            case 'heavy': return 25 // Box
            case 'speeder': return 12 // Small/Fast
            case 'charger': return 18
            case 'sniper': return 15
            case 'swarmer': return 8 // Tiny
            case 'orbit': return 25 // Torus
            case 'titan': return 60 // Huge
            case 'asteroid': return 15
            case 'fighter': return 15
            default: return 10
        }
    }

    private getScoreValue(type: string): number {
        switch (type) {
            case 'boss': return 5000
            case 'elite': return 1000
            case 'scout': return 300
            case 'heavy': return 400
            case 'speeder': return 200
            case 'charger': return 250
            case 'sniper': return 350
            case 'swarmer': return 100
            case 'orbit': return 500
            case 'titan': return 2000
            case 'fighter': return 200
            case 'drone': return 100
            case 'asteroid': return 50
            default: return 50 // Default score (was 0)
        }
    }
}
