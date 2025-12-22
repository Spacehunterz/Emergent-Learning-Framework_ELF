export type WeaponType = 'pulse_laser' | 'star_blaster' | 'quantum_cannon'

export class Projectile {
    x: number
    y: number
    vx: number
    vy: number
    angle: number
    type: WeaponType
    createdAt: number
    isDead: boolean = false

    constructor(x: number, y: number, angle: number, type: WeaponType) {
        this.x = x
        this.y = y
        this.angle = angle
        this.type = type
        this.createdAt = performance.now()

        const rad = angle * Math.PI / 180
        const speed = type === 'pulse_laser' ? 15 : 10
        this.vx = Math.cos(rad) * speed
        this.vy = Math.sin(rad) * speed
    }

    update() {
        this.x += this.vx
        this.y += this.vy

        // Kill after 1 second (range limit)
        if (performance.now() - this.createdAt > 1000) {
            this.isDead = true
        }
    }

    draw(ctx: CanvasRenderingContext2D) {
        ctx.save()
        ctx.translate(this.x, this.y)
        ctx.rotate((this.angle + 90) * Math.PI / 180) // Rotate to face direction

        if (this.type === 'pulse_laser') {
            ctx.fillStyle = '#22d3ee'
            ctx.shadowBlur = 10
            ctx.shadowColor = '#22d3ee'
            ctx.beginPath()
            ctx.rect(-2, -8, 4, 16)
            ctx.fill()
        } else if (this.type === 'star_blaster') {
            // Star Emoji or Shape
            // Glow Effect
            ctx.shadowBlur = 20
            ctx.shadowColor = '#fbbf24' // Amber Glow

            // Draw
            ctx.font = '24px serif' // Larger
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'

            // Draw twice for bloom
            ctx.fillStyle = '#fff' // Core white
            ctx.fillText('⭐', 0, 0)

            ctx.globalAlpha = 0.5
            ctx.shadowBlur = 30
            ctx.fillText('⭐', 0, 0)
            ctx.globalAlpha = 1.0
        }

        ctx.restore()
    }
}
