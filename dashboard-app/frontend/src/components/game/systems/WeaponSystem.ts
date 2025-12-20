import { create } from 'zustand'
import { Vector3, Quaternion } from 'three'
import { GameItem } from './ItemDatabase'

export interface Projectile {
    id: string
    position: Vector3
    rotation: Quaternion
    velocity: Vector3
    damage: number
    owner: 'PLAYER' | 'ENEMY'
    type: 'PLASMA' | 'MINING'
    createdAt: number
    lifetime: number // seconds
}

interface ProjectileState {
    projectiles: Projectile[]
    spawnProjectile: (p: Projectile) => void
    removeProjectile: (id: string) => void
    updateProjectiles: (delta: number) => void
}

export const useProjectileStore = create<ProjectileState>((set, get) => ({
    projectiles: [],
    spawnProjectile: (p) => set((state) => {
        // Simple append - triggers React update, which is fine for spawns (staggered)
        return { projectiles: [...state.projectiles, p] }
    }),
    removeProjectile: (id) => set((state) => ({
        projectiles: state.projectiles.filter(p => p.id !== id)
    })),
    updateProjectiles: (delta) => {
        const state = get()
        const projectiles = state.projectiles
        const tempVel = new Vector3()
        const MAX_DISTANCE_SQ = 500 * 500



        // Mutate in place
        for (let i = 0; i < projectiles.length; i++) {
            const p = projectiles[i]

            // Move
            tempVel.copy(p.velocity).multiplyScalar(delta)
            p.position.add(tempVel)
            p.lifetime -= delta

            // Check bounds/lifetime
            if (p.lifetime <= 0 || p.position.lengthSq() > MAX_DISTANCE_SQ) {
                // Mark for removal?
                // Since we can't easily remove from the array in-place without affecting the store reference eventually
                // we will let the set() handle it below.
            }
        }

        // Filter out dead projectiles
        // We check if any NEED removal to avoid calling set() if nothing changed
        // This is O(N) but essential to avoid React renders when no one died.
        // Optimization: We could flag 'hasRemovals' inside the loop above?
        // Yes, let's do that to avoid the .some() check if possible, or just accept the filter cost.
        // Actually, mutation above doesn't tell us if we SHOULD remove.

        const activeProjectiles = projectiles.filter(p => p.lifetime > 0 && p.position.lengthSq() < MAX_DISTANCE_SQ)

        if (activeProjectiles.length !== projectiles.length) {
            set({ projectiles: activeProjectiles })
        }
    }
}))

// Hook for managing weapon state (Heat, Fire Rate)
import { useState, useRef } from 'react'

export const useWeaponLogic = (weapon: GameItem) => {
    const heat = useRef(0)
    const [overheated, setOverheated] = useState(false)
    const lastFireTime = useRef(0)

    // Stats
    const fireRate = weapon.stats.fireRate || 5
    const fireInterval = 1000 / fireRate
    const coolingRate = weapon.stats.coolingRate || 10
    const heatGen = weapon.stats.heatGeneration || 5
    const maxHeat = 100

    const canFire = () => {
        const now = Date.now()
        if (overheated) return false
        if (now - lastFireTime.current < fireInterval) return false
        return true
    }

    const fire = () => {
        if (!canFire()) return false

        lastFireTime.current = Date.now()
        heat.current = Math.min(heat.current + heatGen, maxHeat)

        if (heat.current >= maxHeat) {
            setOverheated(true)
        }
        return true
    }

    // Call this in useFrame
    // We do NOT use setHeat/setState in the loop unless a discrete event (overheat/recovery) occurs.
    const update = (delta: number) => {
        if (heat.current > 0) {
            heat.current = Math.max(0, heat.current - coolingRate * delta)

            if (overheated && heat.current < 50) {
                setOverheated(false)
            }
        }
    }

    // Expose heat.current. 
    // Note: Components relying on heat for UI (bars) might not update smoothly without state.
    // For now, we prefer performance/stability over the heat bar animating smoothly in the UI loop,
    // OR we should drive the UI bar via useFrame ref update too (which is best practice for HUDs).
    return { heat: heat.current, overheated, fire, update }
}
