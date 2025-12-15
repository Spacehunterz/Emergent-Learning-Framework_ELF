import { useEffect, useRef } from 'react'

interface Point {
    x: number
    y: number
    vx: number
    vy: number
    life: number
    color: string
    size: number
}

export const CosmicCursorTrail = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const mouse = useRef({ x: -100, y: -100 })
    const particles = useRef<Point[]>([])

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        let animationFrameId: number

        const getThemeColor = () => {
            const style = getComputedStyle(document.documentElement)
            // Default to a star-like cyan/white if var missing
            return style.getPropertyValue('--theme-accent').trim() || '#38bdf8'
        }

        const handleMouseMove = (e: MouseEvent) => {
            mouse.current = { x: e.clientX, y: e.clientY }

            // Spawn fewer particles for a cleaner look
            if (Math.random() > 0.5) { // 50% chance per move event
                spawnParticle(e.clientX, e.clientY)
            }
        }

        const spawnParticle = (x: number, y: number) => {
            const angle = Math.random() * Math.PI * 2
            // Slower, more drift-like speed
            const speed = Math.random() * 0.5 + 0.2
            const themeColor = getThemeColor()

            particles.current.push({
                x,
                y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: 1.0,
                color: themeColor,
                // Smaller, more stardust-like
                size: Math.random() * 2 + 0.5
            })
        }

        const animate = () => {
            // Faster fade out for shorter trails
            ctx.globalCompositeOperation = 'destination-out'
            ctx.fillStyle = 'rgba(0, 0, 0, 0.4)' // Stronger fade
            ctx.fillRect(0, 0, canvas.width, canvas.height)

            ctx.globalCompositeOperation = 'lighter'

            for (let i = particles.current.length - 1; i >= 0; i--) {
                const p = particles.current[i]

                // Update
                p.x += p.vx
                p.y += p.vy
                p.life -= 0.03 // Die faster
                p.size *= 0.96 // Shrink faster

                // Draw
                ctx.fillStyle = p.color
                ctx.globalAlpha = p.life * 0.6 // More transparent
                ctx.beginPath()
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
                ctx.fill()

                if (p.life <= 0) {
                    particles.current.splice(i, 1)
                }
            }

            ctx.globalAlpha = 1.0
            animationFrameId = requestAnimationFrame(animate)
        }

        const resize = () => {
            canvas.width = window.innerWidth
            canvas.height = window.innerHeight
        }

        window.addEventListener('resize', resize)
        window.addEventListener('mousemove', handleMouseMove)

        resize()
        animate()

        return () => {
            window.removeEventListener('resize', resize)
            window.removeEventListener('mousemove', handleMouseMove)
            cancelAnimationFrame(animationFrameId)
        }
    }, [])

    return (
        <canvas
            ref={canvasRef}
            className="fixed inset-0 pointer-events-none z-[9999]"
            style={{ mixBlendMode: 'screen' }}
        />
    )
}
