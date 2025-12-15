import React from 'react'

interface NeonTextProps {
    children: React.ReactNode
    color?: 'cyan' | 'purple' | 'pink' | 'white'
    size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
    className?: string
    flicker?: boolean
}

export default function NeonText({
    children,
    color = 'cyan',
    size = 'md',
    className = '',
    flicker = false
}: NeonTextProps) {

    const colors = {
        cyan: 'text-cosmic-cyan shadow-cosmic-cyan',
        purple: 'text-cosmic-purple shadow-cosmic-purple',
        pink: 'text-cosmic-pink shadow-cosmic-pink',
        white: 'text-white shadow-white'
    }

    const sizes = {
        sm: 'text-sm',
        md: 'text-base',
        lg: 'text-lg',
        xl: 'text-xl',
        '2xl': 'text-2xl'
    }

    const glowStyle = {
        textShadow: `0 0 5px currentColor, 0 0 10px currentColor, 0 0 20px currentColor`
    }

    return (
        <span
            className={`font-display tracking-wider ${colors[color]} ${sizes[size]} ${flicker ? 'animate-pulse' : ''} ${className}`}
            style={glowStyle}
        >
            {children}
        </span>
    )
}
