
import { Vector3, Quaternion, Euler } from 'three'

// --- CORE TYPES ---

export interface EntityState {
    id: string
    active: boolean
    type: string
    position: Vector3
    rotation: Quaternion
    scale: Vector3
    velocity: Vector3
    // Gameplay
    hp: number
    maxHp: number
    damage: number
    // Metadata
    createdAt: number
    owner: 'PLAYER' | 'ENEMY'
    seed: number // For visual variation

    // Visual States
    isDying?: boolean
    deathTimer?: number
    lastHitTime?: number
}

export interface PlayerState {
    position: Vector3
    velocity: Vector3
    rotation: Euler // YXZ order for FPS camera
    quaternion: Quaternion

    // Status
    hp: number
    maxHp: number
    shields: number
    maxShields: number
    energy: number
    maxEnergy: number

    // Movement Flags
    isBoosting: boolean
    isFiring: boolean

    // Camera
    tilt: number
}

// Global Game State (Mutable)
export interface GameState {
    // Systems
    player: PlayerState

    // Entities (Pooled)
    projectiles: EntityState[]
    enemies: EntityState[]

    // World
    score: number
    level: number
    isGameOver: boolean
    isPaused: boolean

    // Input Snapshot (Updated every frame before physics)
    input: {
        forward: number
        right: number
        up: number // Boost/Jump
        pitch: number
        yaw: number
        roll: number
        fire: boolean
        secondary: boolean
        use: boolean
        mouseX: number
        mouseY: number
    }

    // Time
    time: {
        now: number
        delta: number
        elapsed: number
    }
}

// Factory for initial state
export const createGameState = (): GameState => ({
    player: {
        position: new Vector3(0, 0, 0),
        velocity: new Vector3(),
        rotation: new Euler(0, 0, 0, 'YXZ'),
        quaternion: new Quaternion(),
        hp: 100,
        maxHp: 100,
        shields: 100,
        maxShields: 100,
        energy: 100,
        maxEnergy: 100,
        isBoosting: false,
        isFiring: false,
        tilt: 0
    },
    projectiles: [], // Will be filled by pool
    enemies: [],     // Will be filled by pool
    score: 0,
    level: 1,
    isGameOver: false,
    isPaused: false,
    input: {
        forward: 0,
        right: 0,
        up: 0,
        pitch: 0,
        yaw: 0,
        roll: 0,
        fire: false,
        secondary: false,
        use: false,
        mouseX: 0,
        mouseY: 0
    },
    time: {
        now: 0,
        delta: 0.016,
        elapsed: 0
    }
})
