import { useEffect, useRef } from 'react'
import { useTheme } from '../context/ThemeContext'
import { Particle, drawConnections, getParticleColor, DEFAULT_MOUSE_RADIUS, MAX_PARTICLE_COUNT } from './particle-background'
import type { Mouse } from './particle-background/types'

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
        const mouse: Mouse = { x: -1000, y: -1000, radius: DEFAULT_MOUSE_RADIUS, isClicked: false }

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

        const resize = () => {
            width = window.innerWidth
            height = window.innerHeight
            canvas.width = width
            canvas.height = height
            initParticles()
        }

        const initParticles = () => {
            particles = []
            const count = Math.max(0, Math.min(particleCount, MAX_PARTICLE_COUNT))
            for (let i = 0; i < count; i++) {
                particles.push(new Particle(width, height))
            }
        }

        const animate = () => {
            time++
            const particleColor = getParticleColor()
            ctx.clearRect(0, 0, width, height)

            drawConnections(ctx, particles, mouse, time, particleColor)

            particles.forEach(p => {
                p.update(mouse, width, height)
                p.draw(ctx, particleColor)
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
