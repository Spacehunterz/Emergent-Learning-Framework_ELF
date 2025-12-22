export class TrailParticle {
    x: number
    y: number
    size: number
    life: number = 1.0
    decay: number
    color: string
    vx: number
    vy: number

    constructor(x: number, y: number, color: string, size: number) {
        this.x = x
        this.y = y
        this.color = color
        this.size = size
        this.decay = Math.random() * 0.03 + 0.02
        // Slight spread
        this.vx = (Math.random() - 0.5) * 0.5
        this.vy = (Math.random() - 0.5) * 0.5
    }

    update() {
        this.x += this.vx
        this.y += this.vy
        this.life -= this.decay
        this.size *= 0.95
    }

    draw(ctx: CanvasRenderingContext2D) {
        ctx.globalAlpha = this.life
        ctx.fillStyle = this.color
        ctx.beginPath()
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
        ctx.fill()
        ctx.globalAlpha = 1.0
    }
}

export class TrailSystem {
    particles: TrailParticle[] = []

    addPoint(x: number, y: number, type: 'cyan' | 'star') {
        const count = type === 'star' ? 2 : 1 // More particles for star trail
        const color = type === 'cyan' ? '#22d3ee' : '#fbbf24'
        const baseSize = type === 'cyan' ? 2 : 3

        for (let i = 0; i < count; i++) {
            // Offset slightly
            const offsetX = (Math.random() - 0.5) * 4
            const offsetY = (Math.random() - 0.5) * 4
            this.particles.push(new TrailParticle(x + offsetX, y + offsetY, color, baseSize))
        }
    }

    updateAndDraw(ctx: CanvasRenderingContext2D) {
        // Filter dead
        this.particles = this.particles.filter(p => p.life > 0)

        // Stars need special drawing maybe? For now just dots.
        // Actually user asked for "cooler trails".
        // Let's make "cyan" a smooth line + particles, and "star" glittery.

        this.particles.forEach(p => {
            p.update()
            p.draw(ctx)
        })
    }
}
