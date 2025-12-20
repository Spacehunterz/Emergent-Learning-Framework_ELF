export class ExplosionParticle {
    x: number
    y: number
    vx: number
    vy: number
    life: number = 1.0
    decay: number
    color: string
    size: number

    constructor(x: number, y: number, color: string) {
        this.x = x
        this.y = y
        const angle = Math.random() * Math.PI * 2
        const speed = Math.random() * 5 + 2
        this.vx = Math.cos(angle) * speed
        this.vy = Math.sin(angle) * speed
        this.decay = Math.random() * 0.02 + 0.01 // Slower fade
        this.color = color
        this.size = Math.random() * 6 + 4 // Bigger (4-10px)
    }

    update() {
        this.x += this.vx
        this.y += this.vy
        this.life -= this.decay
        this.size *= 0.98 // Slower shrink
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

export class Explosion {
    particles: ExplosionParticle[] = []
    isDead: boolean = false

    constructor(x: number, y: number, color: string = '#ef4444', count: number = 15) {
        for (let i = 0; i < count; i++) {
            this.particles.push(new ExplosionParticle(x, y, color))
        }
    }

    update() {
        this.particles.forEach(p => p.update())
        this.particles = this.particles.filter(p => p.life > 0)
        if (this.particles.length === 0) {
            this.isDead = true
        }
    }

    draw(ctx: CanvasRenderingContext2D) {
        this.particles.forEach(p => p.draw(ctx))
    }
}
