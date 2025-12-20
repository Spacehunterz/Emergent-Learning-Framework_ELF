import { create } from 'zustand'
import { Vector3, Quaternion } from 'three'

export type EnemyType = 'drone' | 'scout' | 'fighter' | 'boss' | 'asteroid' | 'elite'

export interface Enemy {
    id: string
    type: EnemyType
    position: Vector3
    rotation: Quaternion
    hp: number
    maxHp: number
    velocity: Vector3
    isDead: boolean
    aiPattern: 'direct' | 'strafe' | 'circle' | 'swoop' | 'drift'
    seed: number
    createdAt: number
}

interface EnemyState {
    enemies: Enemy[]
    spawnEnemy: (enemy: Enemy) => void
    updateEnemy: (id: string, updates: Partial<Enemy>) => void
    removeEnemy: (id: string) => void
    damageEnemy: (id: string, amount: number) => boolean
    tick: (delta: number) => void
    clearEnemies: () => void
}

import { GAME_CONFIG } from '../config/GameConstants'

export const useEnemyStore = create<EnemyState>((set, get) => ({
    enemies: [],
    spawnEnemy: (enemy) => set((state) => ({ enemies: [...state.enemies, enemy] })),
    updateEnemy: (id, updates) => set((state) => ({
        enemies: state.enemies.map(e => e.id === id ? { ...e, ...updates } : e)
    })),
    removeEnemy: (id) => set((state) => ({
        enemies: state.enemies.filter(e => e.id !== id)
    })),
    damageEnemy: (id, amount) => {
        // PERF: Mutate in place, only trigger state update when enemy dies
        const enemies = get().enemies
        const enemy = enemies.find(e => e.id === id)
        if (!enemy) return false

        enemy.hp -= amount

        if (enemy.hp <= 0) {
            enemy.hp = 0
            enemy.isDead = true
            // Only set state when we need to remove the enemy
            set({ enemies: enemies.filter(e => e.hp > 0) })
            return true
        }
        return false
    },
    tick: (delta) => {
        const state = get()
        const enemies = state.enemies

        const time = Date.now() * 0.001

        const loopThreshold = GAME_CONFIG.WAVES.RESPAWN_Z_THRESHOLD
        const respawnXThreshold = GAME_CONFIG.WAVES.RESPAWN_X_THRESHOLD

        // Mutate positions in place to avoid React re-renders and GC pressure
        for (let i = 0; i < enemies.length; i++) {
            const e = enemies[i]
            let x = e.position.x
            let y = e.position.y
            let z = e.position.z

            // BOSS: Slow, imposing approach - no respawn loop
            if (e.type === 'boss') {
                const bossSpeed = GAME_CONFIG.ENEMIES.SPEEDS.BOSS || 2
                z += bossSpeed * delta
                // Slight menacing sway
                x += Math.sin(time * 0.3 + e.seed) * 2 * delta
                y += Math.cos(time * 0.2 + e.seed) * 1 * delta

                const minZ = -120
                e.position.set(x, y, Math.max(z, minZ))
                continue
            }

            if (e.aiPattern === 'strafe') {
                const strafeSpeed = e.type === 'fighter'
                    ? GAME_CONFIG.ENEMIES.SPEEDS.STRAFE_ADVANCE_FIGHTER
                    : GAME_CONFIG.ENEMIES.SPEEDS.STRAFE_ADVANCE_DRONE
                z += strafeSpeed * delta
                x += Math.sin(time * 2 + e.seed) * 30 * delta
                y += Math.cos(time * 1.5 + e.seed) * 15 * delta
            } else if (e.aiPattern === 'circle') {
                const angle = Math.atan2(x, z)
                const dist = Math.sqrt(x * x + z * z)
                const newDist = dist - (5 * delta)
                const newAngle = angle + (1 * delta)
                x = Math.sin(newAngle) * newDist
                z = Math.cos(newAngle) * newDist
                y += Math.sin(time + e.seed) * 10 * delta
            } else if (e.aiPattern === 'swoop') {
                const diveSpeed = GAME_CONFIG.ENEMIES.SPEEDS.SWOOP_DIVE * delta
                z += diveSpeed
                if (z < -20 && z > -60) {
                    y -= 20 * delta
                } else if (z > -10) {
                    y += 20 * delta
                }
            } else if (e.aiPattern === 'drift') {
                const driftSpeed = GAME_CONFIG.ENEMIES.SPEEDS.DRIFT * delta
                z += driftSpeed * 1.2
                x += Math.sin(time * 0.5 + e.seed) * 5 * delta
                y += Math.cos(time * 0.8 + e.seed) * 3 * delta
            } else if (e.type === 'asteroid') {
                const speed = GAME_CONFIG.ENEMIES.SPEEDS.ASTEROID * delta
                z += speed
            } else {
                const speed = e.type === 'fighter'
                    ? GAME_CONFIG.ENEMIES.SPEEDS.FIGHTER
                    : GAME_CONFIG.ENEMIES.SPEEDS.DRONE
                z += speed * delta
                x += Math.cos(time * 3 + e.seed) * 10 * delta
                y += Math.sin(time * 3 + e.seed) * 10 * delta
            }

            // Movement Constraint
            if (y < -10) y = -10

            // Apply mutation
            e.position.set(x, y, z)

            // Check for removal
            if (z > loopThreshold || Math.abs(x) > respawnXThreshold) {
                // Use a property-based flag or just mark for removal from the set
                // For now, we'll just use the shouldUpdate flag logic, 
                // but since we can't easily modify the array while iterating effectively without a new array
                // we will rely on a new array ONLY if needed.
                // Wait, simply filtering IS the way if we need to remove.
                // To minimize GC, we only filter if we find one.
            }
        }

        // Second pass for removals - only if needed
        // Actually, we can just check if any exceeded bounds
        const hasRemovals = enemies.some(e => e.position.z > loopThreshold || Math.abs(e.position.x) > respawnXThreshold)

        if (hasRemovals) {
            set((state) => ({
                enemies: state.enemies.filter(e =>
                    e.position.z <= loopThreshold && Math.abs(e.position.x) <= respawnXThreshold
                )
            }))
        }
    },
    clearEnemies: () => set({ enemies: [] })
}))
