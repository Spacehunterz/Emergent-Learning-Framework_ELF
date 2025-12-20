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

export const useProjectileStore = create<ProjectileState>((set) => ({
    projectiles: [],
    spawnProjectile: (p) => set((state) => {
        // Apply defaults if missing (though usually passed fully)
        // Hard to enforce defaults here without modifying P before call, but we can trust P is mostly correct 
        // OR we override here if we want to enforce constants strictly.
        // Let's rely on the CALLER (PlayerShip/Enemy) using the constants, but we can set safety defaults here?
        // Actually, best to just store what's passed. Callers are already refactored.
        return { projectiles: [...state.projectiles, p] }
    }),
    removeProjectile: (id) => set((state) => ({
        projectiles: state.projectiles.filter(p => p.id !== id)
    })),
    updateProjectiles: (delta) => set((state) => {
        // FIXED: Pre-allocate a single temp vector for velocity scaling
        // Position still needs clone() for React state change detection
        const tempVel = new Vector3()
        return {
            projectiles: state.projectiles
                .map(p => {
                    // IMPORTANT: We must create a NEW Vector3 instance so R3F detects the prop change!
                    // FIXED: Reuse tempVel instead of cloning velocity each time
                    tempVel.copy(p.velocity).multiplyScalar(delta)
                    const newPos = p.position.clone().add(tempVel)
                    return { ...p, position: newPos, lifetime: p.lifetime - delta }
                })
                .filter(p => p.lifetime > 0)
        }
    })
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
