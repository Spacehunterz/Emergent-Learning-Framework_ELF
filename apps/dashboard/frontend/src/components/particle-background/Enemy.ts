

export class Enemy {
    x: number
    y: number
    vx: number
    vy: number
    size: number
    type: 'bug' | 'leak'
    hp: number
    maxHp: number

    // Animation
    wobbleOffset: number = Math.random() * 100

    constructor(width: number, height: number, type: 'bug' | 'leak' = 'bug') {
        this.type = type
        this.size = Math.random() * 5 + 5 // Reduced from 10-20 to 5-10 (Tiny!)
        this.hp = type === 'bug' ? 1 : 5
        this.maxHp = this.hp

        // Spawn at edges
        if (Math.random() > 0.5) {
            this.x = Math.random() > 0.5 ? 0 : width
            this.y = Math.random() * height
        } else {
            this.x = Math.random() * width
            this.y = Math.random() > 0.5 ? 0 : height
        }

        // Target center
        const dx = (width / 2) - this.x
        const dy = (height / 2) - this.y
        const angle = Math.atan2(dy, dx)

        const speed = type === 'bug' ? 4 : 1
        this.vx = Math.cos(angle) * speed
        this.vy = Math.sin(angle) * speed
    }

    update(mouse: unknown, width: number, height: number) {
        this.wobbleOffset += 0.2

        // Bug: Jittery movement
        if (this.type === 'bug') {
            this.x += this.vx + Math.sin(this.wobbleOffset * 10) * 2
            this.y += this.vy + Math.cos(this.wobbleOffset * 10) * 2

            // Randomly change direction slightly
            if (Math.random() < 0.05) {
                const angleVar = (Math.random() - 0.5) * 1
                const speed = 4
                const currentAngle = Math.atan2(this.vy, this.vx)
                this.vx = Math.cos(currentAngle + angleVar) * speed
                this.vy = Math.sin(currentAngle + angleVar) * speed
            }
        }
        // Leak: Slow direct movement
        else {
            this.x += this.vx
            this.y += this.vy
        }

        // Wrap around or bounce? For now, wrap to keep them on screen until killed
        if (this.x < -50) this.x = width + 50
        if (this.x > width + 50) this.x = -50
        if (this.y < -50) this.y = height + 50
        if (this.y > height + 50) this.y = -50
    }

    draw(ctx: CanvasRenderingContext2D) {
        if (this.type === 'bug') {
            ctx.save()
            ctx.translate(this.x, this.y)

            // Jitter effect for "glitch" look
            const jitterX = (Math.random() - 0.5) * 2
            const jitterY = (Math.random() - 0.5) * 2
            ctx.translate(jitterX, jitterY)

            // Rotate towards movement for "crawling" feel
            // We can just use a constant wobble or face center
            // Let's face the velocity
            const angle = Math.atan2(this.vy, this.vx) + Math.PI / 2
            ctx.rotate(angle)

            ctx.strokeStyle = '#ef4444'
            ctx.shadowColor = '#ef4444'
            ctx.shadowBlur = 5
            ctx.lineWidth = 2

            // BUG BODY (Retro Arcade Style)
            // Main Segment
            ctx.fillStyle = '#7f1d1d' // Dark Red
            ctx.beginPath()
            ctx.ellipse(0, 0, this.size, this.size * 1.5, 0, 0, Math.PI * 2)
            ctx.fill()
            ctx.stroke()

            // Head
            ctx.fillStyle = '#ef4444' // Bright Red
            ctx.beginPath()
            ctx.arc(0, -this.size, this.size * 0.6, 0, Math.PI * 2)
            ctx.fill()

            // Eyes (Glowing)
            ctx.fillStyle = '#fbbf24' // Yellow
            ctx.beginPath()
            ctx.arc(-3, -this.size - 2, 2, 0, Math.PI * 2)
            ctx.arc(3, -this.size - 2, 2, 0, Math.PI * 2)
            ctx.fill()

            // LEGS (Animated Scuttling)
            const time = Date.now() / 50
            const legOffset = Math.sin(time) * 5

            ctx.beginPath()
            // Right Legs
            ctx.moveTo(5, -5); ctx.lineTo(15 + legOffset, -10)
            ctx.moveTo(5, 0); ctx.lineTo(18 - legOffset, 0)
            ctx.moveTo(5, 5); ctx.lineTo(15 + legOffset, 10)
            // Left Legs
            ctx.moveTo(-5, -5); ctx.lineTo(-15 - legOffset, -10)
            ctx.moveTo(-5, 0); ctx.lineTo(-18 + legOffset, 0)
            ctx.moveTo(-5, 5); ctx.lineTo(-15 - legOffset, 10)
            ctx.stroke()

            // Mandibles
            ctx.beginPath()
            ctx.moveTo(-2, -this.size - 5); ctx.lineTo(-4, -this.size - 12)
            ctx.moveTo(2, -this.size - 5); ctx.lineTo(4, -this.size - 12)
            ctx.stroke()

            ctx.restore()
        } else {
            // Warning Yellow Slime
            ctx.fillStyle = '#eab308' // yellow-500
            ctx.beginPath()
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
            ctx.fill()
        }
    }
}
