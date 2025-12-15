import React from 'react'

interface CosmicButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger'
    glow?: boolean
}

export default function CosmicButton({
    children,
    variant = 'primary',
    glow = true,
    className = '',
    ...props
}: CosmicButtonProps) {

    const baseStyles = "relative px-6 py-2 font-display uppercase tracking-widest text-sm transition-all duration-300 transform hover:-translate-y-1 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed group clip-path-skew"

    const variants = {
        primary: "bg-cosmic-cyan/10 text-cosmic-cyan border border-cosmic-cyan/50 hover:bg-cosmic-cyan/20 hover:border-cosmic-cyan",
        secondary: "bg-cosmic-purple/10 text-cosmic-purple border border-cosmic-purple/50 hover:bg-cosmic-purple/20 hover:border-cosmic-purple",
        danger: "bg-cosmic-pink/10 text-cosmic-pink border border-cosmic-pink/50 hover:bg-cosmic-pink/20 hover:border-cosmic-pink"
    }

    const glowStyles = glow ? "hover:shadow-[0_0_20px_rgba(var(--neon-color),0.5)]" : ""

    return (
        <button
            className={`${baseStyles} ${variants[variant]} ${glowStyles} ${className}`}
            {...props}
            style={{
                clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)',
                '--neon-color': variant === 'primary' ? '0, 243, 255' : variant === 'secondary' ? '188, 19, 254' : '255, 0, 85'
            } as React.CSSProperties}
        >
            {/* Glitch Overlay */}
            <span className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-100 mix-blend-overlay" />

            {/* Content */}
            <span className="relative z-10 flex items-center gap-2">
                {children}
            </span>

            {/* Corner Accents */}
            <span className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-current opacity-50" />
            <span className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-current opacity-50" />
        </button>
    )
}
