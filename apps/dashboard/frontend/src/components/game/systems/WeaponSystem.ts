import { create } from 'zustand'
import { Vector3, Quaternion } from 'three'
import { GameItem } from './ItemDatabase'

// Projectile types matching WeaponTypes.ts projectileType values
export type ProjectileType =
    | 'standard'           // Basic plasma bolt
    | 'expanding_wave'     // Ripple cannon - expands outward
    | 'chain'              // Chain lightning - bounces between targets
    | 'piercing'           // Ballistic railgun - goes through enemies
    | 'spread'             // Plasma scatter - shotgun pellets
    | 'gravity'            // Gravitas anchor - gravity well
    | 'grid'               // Photon lattice - laser grid
    | 'delayed_burst'      // Nova spike - sticks then explodes
    | 'spiral'             // Phase winder - spiraling double-hit
    | 'enemy_plasma'       // Enemy default projectile

export interface Projectile {
    id: string
    position: Vector3
    rotation: Quaternion
    velocity: Vector3
    damage: number
    owner: 'PLAYER' | 'ENEMY'
    type: ProjectileType
    createdAt: number
    lifetime: number // seconds
    colors?: string[] // Weapon colors for rendering
    // Special properties for advanced projectiles
    special?: {
        // Expanding wave
        currentRadius?: number
        maxRadius?: number
        expandRate?: number
        // Chain lightning
        bounceCount?: number
        maxBounces?: number
        bounceRange?: number
        hitEnemies?: string[]
        // Piercing
        pierceCount?: number
        // Gravity well
        isDeployed?: boolean
        pullRadius?: number
        pullStrength?: number
        // Grid
        gridSize?: number
        lineCount?: number
        // Delayed burst
        stuckToEnemy?: string
        stickTimer?: number
        explosionRadius?: number
        explosionDamage?: number
        // Spiral
        spiralPhase?: number
        spiralRadius?: number
        spiralSpeed?: number
        hitsRemaining?: number
        // Colors for rendering
        colors?: string[]
    }
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
        if (projectiles.length === 0) return // Skip if no projectiles

        const tempVel = new Vector3()
        const MAX_DISTANCE_SQ = 500 * 500
        let hasExpired = false

        // Mutate in place and track if any expired
        for (let i = 0; i < projectiles.length; i++) {
            const p = projectiles[i]
            tempVel.copy(p.velocity).multiplyScalar(delta)
            p.position.add(tempVel)
            p.lifetime -= delta

            if (p.lifetime <= 0 || p.position.lengthSq() > MAX_DISTANCE_SQ) {
                hasExpired = true
            }
        }

        // Only filter and update state if something actually expired
        if (hasExpired) {
            const activeProjectiles = projectiles.filter(p => p.lifetime > 0 && p.position.lengthSq() < MAX_DISTANCE_SQ)
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
