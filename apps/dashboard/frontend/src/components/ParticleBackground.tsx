import { useEffect, useRef } from 'react'
import { useTheme } from '../context/ThemeContext'
import { useGame } from '../context/GameContext'
import { Particle, drawConnections, getParticleColor, DEFAULT_MOUSE_RADIUS, MAX_PARTICLE_COUNT } from './particle-background'
import { Enemy } from './particle-background/Enemy'
import { Projectile } from './particle-background/Projectile'
import { Explosion } from './particle-background/Explosion'
import { TrailSystem } from './particle-background/TrailSystem'
import type { Mouse } from './particle-background/types'

export const ParticleBackground = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const { particleCount, theme } = useTheme()
    const { addScore, isGameEnabled, activeShip, activeTrail, damageShields, shields, rechargeShields, levelUp, level } = useGame() // Get methods

    // Refs
    const addScoreRef = useRef(addScore)

    const isGameEnabledRef = useRef(isGameEnabled)
    const activeShipRef = useRef(activeShip)
    const activeTrailRef = useRef(activeTrail)
    const damageShieldsRef = useRef(damageShields)
    const shieldsRef = useRef(shields)
    const rechargeShieldsRef = useRef(rechargeShields)
    const levelUpRef = useRef(levelUp)
    const levelRef = useRef(level)

    useEffect(() => { addScoreRef.current = addScore }, [addScore])

    useEffect(() => { isGameEnabledRef.current = isGameEnabled }, [isGameEnabled])
    useEffect(() => { activeShipRef.current = activeShip }, [activeShip])
    useEffect(() => { activeTrailRef.current = activeTrail }, [activeTrail])
    useEffect(() => { damageShieldsRef.current = damageShields }, [damageShields])
    useEffect(() => { shieldsRef.current = shields }, [shields])
    useEffect(() => { rechargeShieldsRef.current = rechargeShields }, [rechargeShields])
    useEffect(() => { levelUpRef.current = levelUp }, [levelUp])
    useEffect(() => { levelRef.current = level }, [level])

    // Rotation Logic (to match UFO)
    const lastPosRef = useRef({ x: 0, y: 0 })
    const rotationRef = useRef(-90) // Default Up

    // Wave Management State (Local to effect)
    const waveState = useRef({
        enemiesToSpawn: 0,
        spawnTimer: 0,
        waveDelay: 0,
        isWaveActive: false
    })

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        let animationFrameId: number
        let particles: Particle[] = []
        let enemies: Enemy[] = []
        let projectiles: Projectile[] = []
        let explosions: Explosion[] = []
        const trailSystem = new TrailSystem()

        let width = window.innerWidth
        let height = window.innerHeight
        let time = 0

        // Mouse tracking
        const mouse: Mouse = {
            x: -1000,
            y: -1000,
            radius: DEFAULT_MOUSE_RADIUS,
            isClicked: false,
            isRightClicked: false
        }

        const handleMouseMove = (e: MouseEvent) => {
            const dx = e.clientX - lastPosRef.current.x
            const dy = e.clientY - lastPosRef.current.y
            if (activeShipRef.current !== 'default' && (Math.abs(dx) > 2.0 || Math.abs(dy) > 2.0)) {
                const angle = Math.atan2(dy, dx) * 180 / Math.PI
                rotationRef.current = angle
                if (activeTrailRef.current !== 'none') {
                    trailSystem.addPoint(e.clientX, e.clientY, activeTrailRef.current as 'cyan' | 'star')
                }
            }
            lastPosRef.current = { x: e.clientX, y: e.clientY }
            mouse.x = e.clientX
            mouse.y = e.clientY
        }

        const handleMouseLeave = () => {
            mouse.x = -1000
            mouse.y = -1000
            mouse.isClicked = false
            mouse.isRightClicked = false
        }

        const handleMouseDown = (e: MouseEvent) => {
            if (e.button === 0) mouse.isClicked = true
            if (e.button === 2) {
                mouse.isRightClicked = true
                // Recharge Shield Mechanic (Right Click)
                if (isGameEnabledRef.current && activeShipRef.current !== 'default') {
                    rechargeShieldsRef.current(5) // Heal 5 per click? Or hold?
                    // Let's add an effect
                    explosions.push(new Explosion(mouse.x, mouse.y, '#22d3ee'))
                }
            }

            // FIRE WEAPON (Left Click)
            if (e.button === 0) {
                if (isGameEnabledRef.current && activeShipRef.current !== 'default') {
                    const angle = rotationRef.current
                    const weapon = 'pulse_laser'
                    projectiles.push(new Projectile(mouse.x, mouse.y, angle, weapon))
                }
            }
        }

        const handleMouseUp = (e: MouseEvent) => {
            if (e.button === 0) mouse.isClicked = false
            if (e.button === 2) mouse.isRightClicked = false
        }

        const resize = () => {
            width = window.innerWidth
            height = window.innerHeight
            canvas.width = width
            canvas.height = height
            initParticles()
        }

        const initParticles = () => {
            particles = [] // Reset
            // Do not reset enemies here, managed by Wave Logic
            const count = Math.max(0, Math.min(particleCount, MAX_PARTICLE_COUNT))
            for (let i = 0; i < count; i++) {
                particles.push(new Particle(width, height))
            }
        }

        const animate = () => {
            time++
            const particleColor = getParticleColor()
            ctx.clearRect(0, 0, width, height)

            // 1. Draw Background Grid
            drawConnections(ctx, particles, mouse, time, particleColor)

            // 1b. Draw Trails
            trailSystem.updateAndDraw(ctx)

            // 1c. Draw Shields
            if (activeShipRef.current !== 'default' && shieldsRef.current > 0 && isGameEnabledRef.current) {
                const s = shieldsRef.current
                ctx.beginPath()
                ctx.arc(mouse.x, mouse.y, 25, 0, Math.PI * 2)
                ctx.strokeStyle = `rgba(34, 211, 238, ${s / 100})`
                ctx.lineWidth = 2
                ctx.stroke()
            }

            // 2. Update/Draw Particles (Data Nodes)
            // STRICT INTERACTION LOCK: 
            // If Game is Enabled, we NEVER pass click state to particles.
            // We pass a dummy mouse object that is far away so they don't even hover.
            const interactionLocked = isGameEnabledRef.current
            const particleMouse = interactionLocked
                ? { x: -99999, y: -99999, radius: 0, isClicked: false, isRightClicked: false }
                : mouse

            let collectedCount = 0
            particles.forEach(p => {
                const collected = p.update(particleMouse, width, height)
                p.draw(ctx, particleColor) // Draw normally
                if (collected) collectedCount++
            })
            if (collectedCount > 0) {
                addScoreRef.current(collectedCount * 10)
            }

            // 3. Game Logic (Waves)
            if (!isGameEnabledRef.current) {
                enemies = []
                projectiles = []
                waveState.current.isWaveActive = false
                waveState.current.enemiesToSpawn = 0
            } else {
                // Wave Logic
                const currentLevel = levelRef.current

                if (!waveState.current.isWaveActive) {
                    // Start new wave?
                    if (enemies.length === 0 && waveState.current.enemiesToSpawn === 0) {
                        // Wave Complete or Start
                        if (waveState.current.waveDelay > 0) {
                            waveState.current.waveDelay--
                        } else {
                            // START WAVE
                            // Formula: Base 3 + Level * 2
                            waveState.current.enemiesToSpawn = 3 + (currentLevel * 2)
                            waveState.current.isWaveActive = true
                            // console.log("Starting Wave for Level", currentLevel)
                        }
                    }
                } else {
                    // Spawning Phase
                    if (waveState.current.enemiesToSpawn > 0) {
                        if (time % 60 === 0) { // Spawn every 60 frames (1 sec)
                            enemies.push(new Enemy(width, height, 'bug'))
                            waveState.current.enemiesToSpawn--
                        }
                    } else if (enemies.length === 0) {
                        // Wave Wiped Out!
                        levelUpRef.current()
                        waveState.current.isWaveActive = false
                        waveState.current.waveDelay = 180 // 3 seconds break
                        addScoreRef.current(500) // Level Clear Bonus
                    }
                }
            }

            // 4. Projectiles
            projectiles = projectiles.filter(p => !p.isDead)
            projectiles.forEach(p => {
                p.update()
                p.draw(ctx)
            })

            // 5. Explosions
            explosions = explosions.filter(e => !e.isDead)
            explosions.forEach(e => {
                e.update()
                e.draw(ctx)
            })

            // 6. Enemies
            enemies = enemies.filter(enemy => {
                enemy.update(mouse, width, height)
                enemy.draw(ctx)

                // Hit by Bullet
                let hit = false
                projectiles.forEach(p => {
                    if (p.isDead) return
                    const dx = p.x - enemy.x
                    const dy = p.y - enemy.y
                    const dist = Math.sqrt(dx * dx + dy * dy)
                    if (dist < enemy.size + 10) {
                        hit = true
                        p.isDead = true
                    }
                })

                // Hit Player
                if (!hit && activeShipRef.current !== 'default') {
                    const pdx = mouse.x - enemy.x
                    const pdy = mouse.y - enemy.y
                    const pDist = Math.sqrt(pdx * pdx + pdy * pdy)
                    if (pDist < enemy.size + 20) {
                        damageShieldsRef.current(10) // Reduced collision damage (tiny bugs)
                        explosions.push(new Explosion(enemy.x, enemy.y, '#22d3ee'))
                        return false
                    }
                }

                if (hit) {
                    enemy.hp--
                    if (enemy.hp <= 0) {
                        addScoreRef.current(50)
                        explosions.push(new Explosion(enemy.x, enemy.y, '#ef4444'))
                        return false
                    }
                }
                return true
            })

            animationFrameId = requestAnimationFrame(animate)
        }

        window.addEventListener('resize', resize)
        window.addEventListener('mousemove', handleMouseMove)
        window.addEventListener('mouseleave', handleMouseLeave)
        window.addEventListener('mousedown', handleMouseDown)
        window.addEventListener('mouseup', handleMouseUp)

        resize()
        initParticles()
        animate()

        return () => {
            window.removeEventListener('resize', resize)
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('mouseleave', handleMouseLeave)
            window.removeEventListener('mousedown', handleMouseDown)
            window.removeEventListener('mouseup', handleMouseUp)
            cancelAnimationFrame(animationFrameId)
        }
    }, [particleCount, theme]) // Deps

    return (
        <canvas
            id="particle-canvas"
            ref={canvasRef}
            className="fixed inset-0 w-full h-full pointer-events-none"
            style={{ zIndex: 0 }}
        />
    )
}
