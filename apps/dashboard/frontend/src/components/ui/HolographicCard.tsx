import React, { useRef, useEffect } from 'react';
import { motion, useAnimation, useInView } from 'framer-motion';

interface HolographicCardProps {
    children: React.ReactNode;
    className?: string;
    title?: string;
    delay?: number;
    featured?: boolean;
}

export const HolographicCard: React.FC<HolographicCardProps> = ({
    children,
    className = '',
    title,
    delay = 0,
    featured = false
}) => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, margin: "0px 0px -50px 0px" });
    const controls = useAnimation();

    useEffect(() => {
        if (isInView) {
            controls.start("visible");
        }
    }, [isInView, controls]);

    return (
        <motion.div
            ref={ref}
            variants={{
                hidden: { opacity: 0, y: 20, scale: 0.95 },
                visible: {
                    opacity: 1,
                    y: 0,
                    scale: 1,
                    transition: {
                        duration: 0.5,
                        delay: delay,
                        ease: "easeOut"
                    }
                }
            }}
            initial="hidden"
            animate={controls}
            className={`
        relative group
        glass-panel 
        rounded-xl 
        ${featured ? 'border-cyan-500/30' : 'border-slate-700/50'}
        ${className}
      `}
        >
            {/* Holographic Border Gradient */}
            <div className={`absolute inset-0 rounded-xl bg-gradient-to-br from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none`} />

            {/* Corner Accents - Futuristic Look */}
            <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-cyan-400 opacity-50 rounded-tl-sm" />
            <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-cyan-400 opacity-50 rounded-tr-sm" />
            <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-cyan-400 opacity-50 rounded-bl-sm" />
            <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-cyan-400 opacity-50 rounded-br-sm" />

            {/* Title Header */}
            {title && (
                <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
                    <h3 className="text-sm font-semibold tracking-wider uppercase text-cyan-300/90 drop-shadow-[0_0_5px_rgba(6,182,212,0.5)]">
                        {title}
                    </h3>
                    <div className="flex gap-1">
                        <div className="w-1 h-1 rounded-full bg-cyan-500/50" />
                        <div className="w-1 h-1 rounded-full bg-cyan-500/30" />
                    </div>
                </div>
            )}

            {/* Content */}
            <div className={`${title ? 'p-5' : 'p-4'}`}>
                {children}
            </div>
        </motion.div>
    );
};
