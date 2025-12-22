
import { System } from './System'
import { GameEngine } from '../core/GameEngine'
import { GameState, EntityState } from '../core/GameState'
import { ObjectPool } from '../core/ObjectPool'
import { Vector3, Quaternion } from 'three'

export class EnemySystem implements System {
    private pool: ObjectPool<EntityState>
    private lastSpawnTime: number = 0
    private spawnInterval: number = 1.5 // 1.5s
    private projectiles: any // Reference to projectile system? Ideally decoupling via engine
    private engine!: GameEngine // Injected in init

    // Stage Management
    private currentStage: number = 1
    private isTransitioning: boolean = false
    private readonly POINTS_PER_STAGE = 500

    constructor() {
        this.pool = new ObjectPool<EntityState>(
            () => ({
                id: '',
                active: false,
                type: 'drone', // 'drone', 'fighter', 'asteroid', etc.
                position: new Vector3(),
                rotation: new Quaternion(),
                scale: new Vector3(1, 1, 1),
                velocity: new Vector3(),
                hp: 100,
                maxHp: 100,
                damage: 10,
                createdAt: 0,
                owner: 'ENEMY',
                seed: Math.random(),
                isDying: false,
                deathTimer: 0,
                lastHitTime: 0
            }),
            (e) => {
                e.active = false
                e.hp = 100
                e.isDying = false
                e.deathTimer = 0
                e.lastHitTime = 0
                e.scale.set(1, 1, 1)
            },
            100
        )
    }



    initialize(engine: GameEngine) {
        this.engine = engine
    }

    update(delta: number, state: GameState) {
        // No variable update for now
    }

    fixedUpdate(delta: number, state: GameState) {
        // Stage Progression Check
        if (!this.isTransitioning && state.score >= this.currentStage * this.POINTS_PER_STAGE) {
            this.currentStage++
            this.isTransitioning = true
            this.vaporizeAll(state)
        }

        // Spawning Logic
        // Only spawn if NOT transitioning (screen must be clear)
        const canSpawn = !this.isTransitioning && state.enemies.length < 15

        if (canSpawn && state.time.elapsed - this.lastSpawnTime > this.spawnInterval) {
            this.spawnRandomEnemy(state)
            this.lastSpawnTime = state.time.elapsed
        }

        // End Transition when screen is clear
        if (this.isTransitioning && state.enemies.length === 0) {
            this.isTransitioning = false
            // Optional: Pause briefly or show text?
        }

        // Update Enemies
        let writeIdx = 0
        for (let i = 0; i < state.enemies.length; i++) {
            const e = state.enemies[i]

            // Handle Death Animation
            if (e.isDying) {
                e.deathTimer = (e.deathTimer || 0) + delta

                // Spin faster while dying
                const tumbleSpeed = 5 * delta
                e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), tumbleSpeed))

                if (e.deathTimer > 0.8) { // 800ms disintegration
                    e.active = false
                }
            }

            if (e.active) {
                if (!e.isDying) {
                    this.updateAI(e, delta, state)
                }

                // Boundaries Check (Despawn)
                if (e.position.z > 50 || e.position.z < -1000) {
                    e.active = false
                    this.pool.release(e)
                } else {
                    state.enemies[writeIdx++] = e
                }
            } else {
                this.pool.release(e)
            }
        }
        state.enemies.length = writeIdx
    }

    private spawnRandomEnemy(state: GameState) {
        const e = this.pool.acquire()
        e.active = true
        e.id = `e-${Date.now()}-${Math.random()}`
        e.createdAt = state.time.elapsed
        e.owner = 'ENEMY'

        // Randomize based on Stage
        // Stage 1: Drones Only
        // Stage 2+: Scouts Only (for now)

        if (this.currentStage === 1) this.setupDrone(e)
        else if (this.currentStage === 2) this.setupScout(e)
        else if (this.currentStage === 3) this.setupHeavy(e)
        else if (this.currentStage === 4) this.setupSpeeder(e)
        else if (this.currentStage === 5) this.setupCharger(e)
        else if (this.currentStage === 6) this.setupSniper(e)
        else if (this.currentStage === 7) this.setupSwarmer(e)
        else if (this.currentStage === 8) this.setupOrbit(e)
        else this.setupTitan(e) // Stage 9+

        state.enemies.push(e)
    }

    private vaporizeAll(state: GameState) {
        // Vaporize all active enemies
        for (const e of state.enemies) {
            if (e.active && !e.isDying) {
                e.hp = 0
                e.isDying = true
                e.deathTimer = 0
                e.lastHitTime = state.time.elapsed
                // No score for vaporization? Or bonus? let's give 0 to avoid loop
            }
        }
    }

    private setupDrone(e: EntityState) {
        e.type = 'drone'
        e.hp = e.maxHp = 60 // Buffed slightly (4 shots)
        e.position.set(
            (Math.random() - 0.5) * 80,
            (Math.random() - 0.5) * 20 + 20,
            -300 - Math.random() * 100
        )
    }

    private setupScout(e: EntityState) {
        e.type = 'scout'
        e.hp = e.maxHp = 150
        e.position.set(
            (Math.random() - 0.5) * 120,
            (Math.random() - 0.5) * 40 + 20,
            -300 - Math.random() * 100
        )
    }

    private setupHeavy(e: EntityState) {
        e.type = 'heavy'
        e.hp = e.maxHp = 400
        e.position.set((Math.random() - 0.5) * 60, Math.random() * 30 + 10, -200) // Closer spawn
    }
    private setupSpeeder(e: EntityState) {
        e.type = 'speeder'
        e.hp = e.maxHp = 40
        e.position.set((Math.random() - 0.5) * 150, Math.random() * 50 + 10, -400)
    }
    private setupCharger(e: EntityState) {
        e.type = 'charger'
        e.hp = e.maxHp = 200
        e.position.set((Math.random() - 0.5) * 40, Math.random() * 20 + 20, -400)
    }
    private setupSniper(e: EntityState) {
        e.type = 'sniper'
        e.hp = e.maxHp = 100
        e.position.set((Math.random() - 0.5) * 100, Math.random() * 60 + 20, -500)
    }
    private setupSwarmer(e: EntityState) {
        e.type = 'swarmer'
        e.hp = e.maxHp = 30
        e.position.set((Math.random() - 0.5) * 80, Math.random() * 40 + 20, -300)
    }
    private setupOrbit(e: EntityState) {
        e.type = 'orbit'
        e.hp = e.maxHp = 250
        e.position.set((Math.random() - 0.5) * 150, Math.random() * 60, -250) // Closer
    }
    private setupTitan(e: EntityState) {
        e.type = 'titan'
        e.hp = e.maxHp = 2000
        e.position.set(0, 20, -400) // Closer
    }

    // Removed unused logic
    private setupFighter(e: EntityState) { }
    private setupAsteroid(e: EntityState) { }



    private updateAI(e: EntityState, delta: number, state: GameState) {
        const time = state.time.elapsed

        if (e.type === 'drone') {
            const z = e.position.z
            const x = e.position.x
            const y = e.position.y

            // SWARM LOGIC
            const STOP_DISTANCE = -50
            const RETREAT_DISTANCE = -40
            const STRAFE_SPEED = 40

            if (z < STOP_DISTANCE) {
                // Approach
                e.position.z += STRAFE_SPEED * delta
            } else {
                // Hover Zone
                e.position.z += Math.sin(time * 3 + e.seed) * 2 * delta

                // Keep them back
                if (z > RETREAT_DISTANCE) {
                    e.position.z -= STRAFE_SPEED * delta
                }

                // WALL CLAMP (X/Y)
                if (e.position.x > 60) e.position.x -= 20 * delta
                if (e.position.x < -60) e.position.x += 20 * delta
                if (e.position.y > 40) e.position.y -= 20 * delta
                if (e.position.y < 10) e.position.y += 20 * delta
            }

            // HARD CLAMP
            if (e.position.z > -35) e.position.z = -35

            // Strafe Animation
            e.position.x += Math.sin(time * 2 + e.seed) * 30 * delta
            e.position.y += Math.cos(time * 1.5 + e.seed) * 15 * delta

            // Idle Spin (Slow Tumble)
            e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), 1.5 * delta))
            e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), 0.5 * delta))
        }

        // --- STRICT WALL ENFORCEMENT ---
        // NO ONE PASSES THIS LINE
        const WALL_Z = -35
        if (e.position.z > WALL_Z) {
            e.position.z = WALL_Z
            // Optionally bounce them back slightly?
            // e.position.z -= 0.5 
        } else if (e.type === 'scout') {
            // Scout Logic: Fast, erratic
            const speed = 80
            e.position.z += speed * delta
            e.position.x += Math.cos(time * 4 + e.seed) * 25 * delta
            e.position.y += Math.sin(time * 3 + e.seed) * 15 * delta

            // FIXED: Incremental Rotation (No Glitch)
            e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), 2 * delta))
            e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), 1 * delta))
        } else if (e.type === 'heavy') {
            e.position.z += 20 * delta // Faster (was 10)
            e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), 0.5 * delta))
        } else if (e.type === 'speeder') {
            e.position.z += 120 * delta // Very Fast
            e.position.x += Math.sin(time * 5 + e.seed) * 40 * delta // Swoop
            e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), 5 * delta))
        } else if (e.type === 'charger') {
            const speed = e.position.z > -100 ? 150 : 30 // Rush when close? Or simple fast approach
            e.position.z += 60 * delta
            // Face player logic could go here
        } else if (e.type === 'sniper') {
            // Hover at range
            if (e.position.z < -200) e.position.z += 30 * delta
            e.position.y += Math.sin(time + e.seed) * 5 * delta
        } else if (e.type === 'swarmer') {
            // Erratic swarm
            e.position.z += 50 * delta
            e.position.x += Math.sin(time * 6 + e.seed) * 10 * delta
            e.position.y += Math.cos(time * 5 + e.seed) * 10 * delta
        } else if (e.type === 'orbit') {
            // Wide Circles
            e.position.z += 40 * delta // Faster (was 20)
            e.position.x = Math.sin(time * 0.5 + e.seed) * 100
            e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), 1 * delta))
        } else if (e.type === 'titan') {
            e.position.z += 15 * delta // Faster (was 5)
            e.rotation.multiply(new Quaternion().setFromAxisAngle(new Vector3(1, 1, 0), 0.2 * delta))
        }
    }
}
