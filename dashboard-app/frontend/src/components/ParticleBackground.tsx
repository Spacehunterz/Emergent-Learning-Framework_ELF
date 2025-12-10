import { useEffect, useRef } from 'react'
import { useTheme } from '../context/ThemeContext'

export const ParticleBackground = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const { particleCount, theme } = useTheme()

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        let animationFrameId: number
        let particles: Particle[] = []
        let width = window.innerWidth
        let height = window.innerHeight
        let time = 0

        // Mouse tracking for neural web effect
        const mouse = { x: -1000, y: -1000, radius: 150, isClicked: false }

        const handleMouseMove = (e: MouseEvent) => {
            mouse.x = e.clientX
            mouse.y = e.clientY
        }

        const handleMouseLeave = () => {
            mouse.x = -1000
            mouse.y = -1000
            mouse.isClicked = false
        }

        const handleMouseDown = () => {
            mouse.isClicked = true
        }

        const handleMouseUp = () => {
            mouse.isClicked = false
        }

        // Get particle color from CSS variable
        const getParticleColor = () => {
            const style = getComputedStyle(document.documentElement)
            return style.getPropertyValue('--theme-particle-color').trim() || '160, 200, 255'
        }

        const resize = () => {
            width = window.innerWidth
            height = window.innerHeight
            canvas.width = width
            canvas.height = height
            initParticles()
        }

        class Particle {
            x: number
            y: number
            vx: number
            vy: number
            size: number
            alpha: number
            targetAlpha: number
            baseVx: number
            baseVy: number

            constructor() {
                this.x = Math.random() * width
                this.y = Math.random() * height
                this.vx = (Math.random() - 0.5) * 0.3
                this.vy = (Math.random() - 0.5) * 0.3
                this.baseVx = this.vx
                this.baseVy = this.vy
                this.size = Math.random() * 2.5 + 0.5
                this.alpha = Math.random()
                this.targetAlpha = Math.random()
            }

            update() {
                // Attraction to cursor when clicked
                if (mouse.isClicked && mouse.x > 0) {
                    const dx = mouse.x - this.x
                    const dy = mouse.y - this.y
                    const dist = Math.sqrt(dx * dx + dy * dy)

                    if (dist < mouse.radius * 2) {
                        const force = (1 - dist / (mouse.radius * 2)) * 0.08
                        this.vx += (dx / dist) * force
                        this.vy += (dy / dist) * force
                    }
                }

                // Apply velocity with friction
                this.vx *= 0.98
                this.vy *= 0.98

                // Slowly return to base velocity when not attracted
                if (!mouse.isClicked) {
                    this.vx += (this.baseVx - this.vx) * 0.01
                    this.vy += (this.baseVy - this.vy) * 0.01
                }

                this.x += this.vx
                this.y += this.vy

                if (this.x < 0) this.x = width
                if (this.x > width) this.x = 0
                if (this.y < 0) this.y = height
                if (this.y > height) this.y = 0

                if (Math.abs(this.alpha - this.targetAlpha) < 0.01) {
                    this.targetAlpha = Math.random()
                } else {
                    this.alpha += (this.targetAlpha - this.alpha) * 0.02
                }
            }

            draw(particleColor: string) {
                if (!ctx) return
                ctx.fillStyle = 'rgba(' + particleColor + ', ' + (this.alpha * 0.6) + ')'
                ctx.beginPath()
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
                ctx.fill()
            }
        }

        const initParticles = () => {
            particles = []
            const count = Math.max(0, Math.min(particleCount, 300))
            for (let i = 0; i < count; i++) {
                particles.push(new Particle())
            }
        }

        // Draw neural web connections around cursor
        const drawConnections = (particleColor: string) => {
            const nearbyParticles: Particle[] = []

            // Pulse animation for connections
            const pulse = Math.sin(time * 0.03) * 0.3 + 0.7
            const clickPulse = mouse.isClicked ? Math.sin(time * 0.1) * 0.2 + 1.2 : 1

            // Find particles near the cursor
            for (const p of particles) {
                const dx = p.x - mouse.x
                const dy = p.y - mouse.y
                const dist = Math.sqrt(dx * dx + dy * dy)

                const effectiveRadius = mouse.radius * clickPulse

                if (dist < effectiveRadius) {
                    nearbyParticles.push(p)

                    const baseOpacity = (1 - dist / effectiveRadius) * 0.6
                    const opacity = baseOpacity * pulse
                    const lineWidth = mouse.isClicked ? 1.5 + Math.sin(time * 0.08 + dist * 0.01) * 0.5 : 1

                    ctx.strokeStyle = 'rgba(' + particleColor + ', ' + opacity + ')'
                    ctx.lineWidth = lineWidth
                    ctx.beginPath()
                    ctx.moveTo(mouse.x, mouse.y)
                    ctx.lineTo(p.x, p.y)
                    ctx.stroke()
                }
            }

            // Draw connections between nearby particles (the web effect)
            for (let i = 0; i < nearbyParticles.length; i++) {
                for (let j = i + 1; j < nearbyParticles.length; j++) {
                    const p1 = nearbyParticles[i]
                    const p2 = nearbyParticles[j]
                    const dx = p1.x - p2.x
                    const dy = p1.y - p2.y
                    const dist = Math.sqrt(dx * dx + dy * dy)

                    const maxDist = mouse.radius * 0.8 * clickPulse

                    if (dist < maxDist) {
                        const baseOpacity = (1 - dist / maxDist) * 0.3
                        const shimmer = Math.sin(time * 0.05 + i * 0.5 + j * 0.3) * 0.15 + 0.85
                        const opacity = baseOpacity * shimmer

                        ctx.strokeStyle = 'rgba(' + particleColor + ', ' + opacity + ')'
                        ctx.lineWidth = mouse.isClicked ? 0.8 : 0.5
                        ctx.beginPath()
                        ctx.moveTo(p1.x, p1.y)
                        ctx.lineTo(p2.x, p2.y)
                        ctx.stroke()
                    }
                }
            }

            // Draw a subtle glow at cursor position when near particles
            if (nearbyParticles.length > 0) {
                const glowSize = mouse.isClicked ? 30 + Math.sin(time * 0.1) * 10 : 20
                const glowOpacity = mouse.isClicked ? 0.5 : 0.3

                const gradient = ctx.createRadialGradient(
                    mouse.x, mouse.y, 0,
                    mouse.x, mouse.y, glowSize
                )
                gradient.addColorStop(0, 'rgba(' + particleColor + ', ' + (glowOpacity * pulse) + ')')
                gradient.addColorStop(1, 'rgba(' + particleColor + ', 0)')
                ctx.fillStyle = gradient
                ctx.beginPath()
                ctx.arc(mouse.x, mouse.y, glowSize, 0, Math.PI * 2)
                ctx.fill()
            }
        }

        const animate = () => {
            time++
            const particleColor = getParticleColor()
            ctx.clearRect(0, 0, width, height)

            drawConnections(particleColor)

            particles.forEach(p => {
                p.update()
                p.draw(particleColor)
            })

            animationFrameId = requestAnimationFrame(animate)
        }

        window.addEventListener('resize', resize)
        window.addEventListener('mousemove', handleMouseMove)
        window.addEventListener('mouseleave', handleMouseLeave)
        window.addEventListener('mousedown', handleMouseDown)
        window.addEventListener('mouseup', handleMouseUp)

        resize()
        animate()

        return () => {
            window.removeEventListener('resize', resize)
            window.removeEventListener('mousemove', handleMouseMove)
            window.removeEventListener('mouseleave', handleMouseLeave)
            window.removeEventListener('mousedown', handleMouseDown)
            window.removeEventListener('mouseup', handleMouseUp)
            cancelAnimationFrame(animationFrameId)
        }
    }, [particleCount, theme])

    return (
        <canvas
            id="particle-canvas"
            ref={canvasRef}
            className="fixed inset-0 w-full h-full pointer-events-none"
            style={{ zIndex: 0 }}
        />
    )
}
