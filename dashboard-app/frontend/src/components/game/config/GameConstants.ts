export const GAME_CONFIG = {
    // Player
    PLAYER: {
        SPEED: 2.5,
        SHIELD_REGEN_RATE: 2, // Per second
        MAX_SHIELDS: 100,
        MAX_HULL: 100,
        SHAKE_DECAY: 5,
        DAMAGE_FLASH_DECAY: 3,
        RECOIL_FORCE: 0.6,
        RECOIL_RECOVERY: 15,
        SMOOTHNESS_FACTOR: 3.5,
        BANK_SPEED: 4.0
    },
    // Weapons
    WEAPONS: {
        PLAYER_PLASMA: {
            SPEED: 200,
            DAMAGE: 15,
            LIFETIME: 2,
            OFFSET_X: 2.5,
            OFFSET_Y: -1.5,
            OFFSET_Z: -4,
            FIRE_RATE: 0.15
        },
        ENEMY_PLASMA: {
            SPEED: 15,
            DAMAGE_BOSS: 20,
            DAMAGE_NORMAL: 10,
            LIFETIME: 10
        }
    },
    // Enemies - MASSIVE MOTHERSHIP SCALE
    ENEMIES: {
        SIZES: {
            ASTEROID: 8,           // Small rocks for target practice
            BOSS: 150,             // AIRCRAFT CARRIER SIZE - massive mothership
            FIGHTER: 15,           // Corvette size
            DRONE: 8               // Small scout
        },
        // Model scales (multiplied by GLTF model size)
        MODEL_SCALES: {
            ASTEROID: 0.08,        // Small rocks
            BOSS: 1.5,             // MASSIVE - fills screen
            FIGHTER: 0.15,         // Medium ships
            DRONE: 0.06,           // Small ships
            SCOUT: 0.08
        },
        COLORS: {
            BOSS: '#ef4444',
            FIGHTER: '#f59e0b',
            ASTEROID: '#78716c',
            DRONE: '#10b981',
            EXPLOSION_DEFAULT: '#f97316',
            EXPLOSION_BOSS: '#ef4444'
        },
        TRAIL_COLORS: {
            BOSS: '#ef4444',
            FIGHTER: '#fbbf24',
            ASTEROID: '#57534e',
            DRONE: '#34d399'
        },
        FIRE_RATES: {
            BOSS: 0.8,
            FIGHTER: 1.5,
            DRONE: 3.0
        },
        HP: {
            BOSS: 1200,            // Harder boss (~80 shots at 15 dmg each)
            FIGHTER: 60,
            ASTEROID: 15,          // Slightly tougher
            DRONE: 30,
            ELITE: 200             // Mini-boss type
        },
        SPEEDS: {
            FIGHTER: 15,
            DRONE: 12,
            ASTEROID: 3,           // Slower for easier targeting
            BOSS: 1,               // VERY SLOW
            SWOOP_DIVE: 15,
            DRIFT: 4,
            STRAFE_ADVANCE_FIGHTER: 12,
            STRAFE_ADVANCE_DRONE: 10
        }
    },
    // Visuals
    VISUALS: {
        STAR_COUNT: 80,
        STAR_DEPTH: 60,
        STAR_FACTOR: 6
    },
    // Post Processing / Visuals
    POST_PROCESSING: {
        BLOOM_INTENSITY: 1.5,
        BLOOM_LUMINANCE_THRESHOLD: 0.2, // Lower to catch more glow
        BLOOM_LUMINANCE_SMOOTHING: 0.9,
        CHROMATIC_ABERRATION_OFFSET: 0.005
    },
    // Floating Text
    UI: {
        FLOATING_TEXT_LIFETIME: 1.5,
        base_FONT_SIZE: 16
    },
    // Wave / Spawn Logic
    WAVES: {
        SPAWN_DISTANCE_MIN: 180,
        SPAWN_DISTANCE_MAX: 250,
        RESPAWN_Z_THRESHOLD: 30,
        RESPAWN_X_THRESHOLD: 200,
        RESPAWN_Z_OFFSET: -200 // Further back respawn
    }
}


