import { create } from 'zustand'
import { Vector3, Quaternion, MathUtils } from 'three'

export type EnemyType = 'drone' | 'scout' | 'fighter' | 'boss' | 'asteroid' | 'elite'

export interface Enemy {
    id: string
    type: EnemyType
    stage: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20
    position: Vector3
    rotation: Quaternion
    hp: number
    maxHp: number
    velocity: Vector3
    isDead: boolean
    aiPattern: 'direct' | 'strafe' | 'circle' | 'swoop' | 'drift'
    seed: number
    createdAt: number
    wallAnchor: Vector3
    wallOffset: Vector3
    wallPhase: number
}

// Helper to get spawn ease for animations
export const getSpawnEase = (createdAt: number, duration = 500) => {
    const elapsed = Date.now() - createdAt
    return Math.min(1, elapsed / duration)
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
import { spawnHealthPickup, spawnShieldPickup, spawnWeaponPickup } from './PickupSystem'

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

            // Dispatch enemy-killed event for overcharge system
            window.dispatchEvent(new CustomEvent('enemy-killed', {
                detail: { type: enemy.type, stage: enemy.stage }
            }))

            // Random pickup drops from all enemies (stage 2+)
            if (enemy.stage > 1) {
                const roll = Math.random()
                // Drop chances: health 20%, shield 15%, weapon 5%
                if (roll < 0.20) {
                    spawnHealthPickup(enemy.position.clone(), 20) // 1/5 of max hull
                } else if (roll < 0.35) {
                    spawnShieldPickup(enemy.position.clone(), 20) // 1/5 of max shield
                } else if (roll < 0.40) {
                    spawnWeaponPickup(enemy.position.clone(), 30) // 30 second turbo
                }
            }

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

            if (!e.wallAnchor) {
                e.wallAnchor = e.position.clone()
                e.wallOffset = new Vector3()
                e.wallPhase = e.seed * Math.PI * 2
            }

            const anchor = e.wallAnchor
            const offset = e.wallOffset
            const phase = e.wallPhase

            let swayX = Math.sin(time * 0.9 + phase) * 2
            let swayY = Math.cos(time * 1.1 + phase) * 2
            let swayZ = Math.sin(time * 0.6 + phase) * 1.2

            if (e.aiPattern === 'strafe') {
                swayX += Math.sin(time * 2.1 + phase) * 8
                swayY += Math.cos(time * 1.6 + phase) * 3
            } else if (e.aiPattern === 'circle') {
                swayX += Math.cos(time * 1.0 + phase) * 6
                swayY += Math.sin(time * 1.0 + phase) * 6
            } else if (e.aiPattern === 'swoop') {
                swayY += Math.sin(time * 1.5 + phase) * 8
                swayZ += Math.sin(time * 1.2 + phase) * 2.5
            } else if (e.aiPattern === 'drift') {
                swayX += Math.sin(time * 0.5 + phase) * 5
                swayY += Math.cos(time * 0.7 + phase) * 4
                swayZ += Math.sin(time * 0.4 + phase) * 2
            } else {
                swayX += Math.cos(time * 1.3 + phase) * 3
                swayY += Math.sin(time * 1.2 + phase) * 3
            }

            if (e.type === 'asteroid') {
                swayX += Math.sin(time * 0.35 + phase) * 6
                swayY += Math.cos(time * 0.45 + phase) * 6
                swayZ += Math.sin(time * 0.3 + phase) * 2.5
            }

            const typeScale = e.type === 'elite' ? 1.4 : e.type === 'fighter' ? 1.2 : e.type === 'asteroid' ? 1.6 : 1
            const follow = e.type === 'asteroid' ? 1.6 : e.type === 'elite' ? 2.6 : 3

            const targetX = anchor.x + offset.x + (swayX * typeScale)
            const targetY = anchor.y + offset.y + (swayY * typeScale)
            const targetZ = Math.min(anchor.z + offset.z + (swayZ * typeScale), -8)

            x = MathUtils.lerp(x, targetX, delta * follow)
            y = MathUtils.lerp(y, targetY, delta * follow)
            z = MathUtils.lerp(z, targetZ, delta * follow)

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
