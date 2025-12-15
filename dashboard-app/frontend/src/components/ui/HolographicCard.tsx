import React from 'react'

interface HolographicCardProps extends React.HTMLAttributes<HTMLDivElement> {
    children: React.ReactNode
    className?: string
    title?: string
}

export default function HolographicCard({ children, className = '', title, ...props }: HolographicCardProps) {
    return (
        <div
            className={`relative group ${className}`}
            {...props}
        >
            {/* Animated Border Gradient - uses theme accent */}
            <div className="absolute -inset-[1px] opacity-30 group-hover:opacity-60 transition-opacity duration-500 blur-sm rounded-xl animate-hologram"
                style={{ background: 'linear-gradient(to right, var(--theme-accent), var(--neon-purple), var(--theme-accent))' }}
            />

            {/* Main Glass Panel - uses theme variables */}
            <div className="relative h-full backdrop-blur-md rounded-xl border border-white/10 overflow-hidden transition-colors duration-300"
                style={{ backgroundColor: 'var(--theme-bg-card)' }}
            >
                {/* Scanline Effect */}
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/5 to-transparent h-[100%] w-full animate-pulse-slow pointer-events-none" style={{ backgroundSize: '100% 3px' }} />

                {/* Content */}
                <div className="relative z-10 p-6 h-full flex flex-col">
                    {title && (
                        <div className="mb-4 border-b border-white/10 pb-2">
                            <h3 className="font-display text-lg tracking-widest text-transparent bg-clip-text font-bold uppercase"
                                style={{ backgroundImage: 'linear-gradient(to right, var(--theme-accent), #fff)' }}
                            >
                                {title}
                            </h3>
                        </div>
                    )}
                    {children}
                </div>
            </div>
        </div>
    )
}
