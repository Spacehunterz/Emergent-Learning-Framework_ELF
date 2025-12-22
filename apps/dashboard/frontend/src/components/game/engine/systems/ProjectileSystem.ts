
import { System } from './System'
import { GameEngine } from '../core/GameEngine'
import { GameState, EntityState } from '../core/GameState'
import { ObjectPool } from '../core/ObjectPool'
import { Vector3, Quaternion } from 'three'

export class ProjectileSystem implements System {
    private pool: ObjectPool<EntityState>
    private lastFireTime: number = 0
    private readonly FIRE_RATE = 0.15 // 150ms

    constructor() {
        this.pool = new ObjectPool<EntityState>(
            () => ({
                id: '',
                active: false,
                type: 'plasma',
                position: new Vector3(),
                rotation: new Quaternion(),
                scale: new Vector3(1, 1, 1),
                velocity: new Vector3(),
                hp: 1,
                maxHp: 1,
                damage: 10,
                createdAt: 0,
                owner: 'PLAYER',
                seed: 0
            }),
            (p) => {
                p.active = false
                p.position.set(0, 0, 0)
                p.velocity.set(0, 0, 0)
            },
            500 // Initial pool size
        )
    }

    private engine!: GameEngine

    initialize(engine: GameEngine) {
        this.engine = engine
    }

    update(delta: number, state: GameState) {
        // Input handling for firing
        if (state.input.fire && state.time.elapsed - this.lastFireTime > this.FIRE_RATE) {
            this.firePlayerProjectile(state)
            this.lastFireTime = state.time.elapsed
            state.player.isFiring = true
        } else {
            state.player.isFiring = false
        }
    }

    fixedUpdate(delta: number, state: GameState) {
        // Sync active projectiles to state
        // For performance, we'll maintain the list effectively
        // Actually, let's clear the state list and rebuild it from our active pool members?
        // OR, we just use the state list AS the active list, and the pool manages instances.

        // Approach: State has the array. Pool just gives us objects to put in the array.
        // We iterate the array, update physics. passing bullets back to pool if dead.

        // Filter out dead projectiles from previous frame (mutating array in place is faster but trickier)
        let writeIdx = 0
        for (let i = 0; i < state.projectiles.length; i++) {
            const p = state.projectiles[i]
            if (p.active) {
                // Update Physics
                p.position.addScaledVector(p.velocity, delta)

                // Lifetime check (2.5s)
                if (state.time.elapsed - p.createdAt > 2.5) {
                    p.active = false
                    this.pool.release(p)
                } else {
                    // Keep it
                    state.projectiles[writeIdx++] = p
                }
            } else {
                this.pool.release(p)
            }
        }
        // Trim array
        state.projectiles.length = writeIdx
    }

    spawn(state: GameState, position: Vector3, velocity: Vector3, owner: 'PLAYER' | 'ENEMY', damage: number) {
        const p = this.pool.acquire()
        p.active = true
        p.id = `p-${Date.now()}-${Math.random()}`
        p.position.copy(position)
        p.velocity.copy(velocity)
        p.owner = owner
        p.damage = damage
        p.createdAt = state.time.elapsed

        // Orientation - capsule geometry is Y-axis aligned, so rotate from Y to velocity direction
        p.rotation.setFromUnitVectors(new Vector3(0, 1, 0), velocity.clone().normalize())

        state.projectiles.push(p)
    }

    private firePlayerProjectile(state: GameState) {
        // Dual guns logic
        const offsetLeft = new Vector3(-2.2, -1.2, -1.0).applyQuaternion(state.player.quaternion).add(state.player.position)
        const offsetRight = new Vector3(2.2, -1.2, -1.0).applyQuaternion(state.player.quaternion).add(state.player.position)

        const speed = 150
        const dir = new Vector3(0, 0, -1).applyEuler(state.player.rotation).normalize()
        const vel = dir.multiplyScalar(speed)

        this.spawn(state, offsetLeft, vel, 'PLAYER', 15)
        this.spawn(state, offsetRight, vel, 'PLAYER', 15)
        this.engine?.sound?.playLaser('player')
    }
}
