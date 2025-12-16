import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useCosmicSettings } from '../../context/CosmicSettingsContext';

// Ring buffer for trail points - increased size for smoother/longer trails
const MAX_TRAIL_POINTS = 600;

interface TrailPoint {
    x: number;
    y: number;
    timestamp: number;
}

export const UfoCursor: React.FC = () => {
    const { cursorMode, trailsEnabled } = useCosmicSettings();
    const [position, setPosition] = useState({ x: -100, y: -100 });
    const [isClicking, setIsClicking] = useState(false);

    // Ring buffer refs for trail - avoids React state updates
    const trailRef = useRef<TrailPoint[]>([]);
    const trailIndexRef = useRef(0);
    const svgPathRef = useRef<SVGPolylineElement>(null);
    const beamParticlesRef = useRef<HTMLDivElement>(null);
    const requestRef = useRef<number>();

    // Light animation state
    const [lightPhase, setLightPhase] = useState(0);

    // Toggle body cursor class
    useEffect(() => {
        if (cursorMode === 'ufo') {
            document.body.classList.add('cosmic-cursor-hidden');
        } else {
            document.body.classList.remove('cosmic-cursor-hidden');
        }
        return () => {
            document.body.classList.remove('cosmic-cursor-hidden');
        };
    }, [cursorMode]);

    // Add trail point to ring buffer
    const addTrailPoint = useCallback((x: number, y: number) => {
        // Respect toggles
        if (cursorMode !== 'ufo' || !trailsEnabled) return;

        const now = performance.now();
        const trail = trailRef.current;

        // Initialize array if empty
        if (trail.length < MAX_TRAIL_POINTS) {
            trail.push({ x, y, timestamp: now });
        } else {
            // Overwrite oldest point (ring buffer)
            trail[trailIndexRef.current] = { x, y, timestamp: now };
            trailIndexRef.current = (trailIndexRef.current + 1) % MAX_TRAIL_POINTS;
        }
    }, [cursorMode]);

    // Track movement
    useEffect(() => {
        const updatePosition = (e: MouseEvent) => {
            setPosition({ x: e.clientX, y: e.clientY });
            addTrailPoint(e.clientX, e.clientY);
        };

        const handleMouseDown = () => setIsClicking(true);
        const handleMouseUp = () => setIsClicking(false);

        window.addEventListener('mousemove', updatePosition);
        window.addEventListener('mousedown', handleMouseDown);
        window.addEventListener('mouseup', handleMouseUp);

        return () => {
            window.removeEventListener('mousemove', updatePosition);
            window.removeEventListener('mousedown', handleMouseDown);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [addTrailPoint]);

    // Animation loop - updates SVG path directly, no React state
    useEffect(() => {
        let lastTime = performance.now();

        const animate = (currentTime: number) => {
            const deltaTime = currentTime - lastTime;

            // Update light phase for chase effect (60fps throttle)
            if (deltaTime > 16) {
                setLightPhase(prev => (prev + deltaTime * 0.003) % 1);
                lastTime = currentTime;
            }

            // Update trail SVG path directly
            if (svgPathRef.current) {
                if (!trailsEnabled || trailRef.current.length === 0) {
                    svgPathRef.current.setAttribute('points', '');
                    return;
                }

                const now = currentTime;
                const trailLifetime = 400; // ms

                // Build points string from valid trail points
                const validPoints = trailRef.current
                    .filter(p => now - p.timestamp < trailLifetime)
                    .sort((a, b) => a.timestamp - b.timestamp);

                if (validPoints.length > 1) {
                    const pointsStr = validPoints.map(p => `${p.x},${p.y}`).join(' ');
                    svgPathRef.current.setAttribute('points', pointsStr);

                    // Fade based on age
                    const oldestAge = now - validPoints[0].timestamp;
                    const opacity = Math.max(0, 1 - oldestAge / trailLifetime);
                    svgPathRef.current.style.opacity = String(opacity * 1.0); // Increased from 0.6
                } else {
                    svgPathRef.current.setAttribute('points', '');
                }
            }

            requestRef.current = requestAnimationFrame(animate);
        };

        requestRef.current = requestAnimationFrame(animate);
        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [trailsEnabled, cursorMode]);

    if (cursorMode === 'default') return null;

    // Calculate light opacities for chase effect
    const getLightOpacity = (index: number) => {
        const offset = (lightPhase + index / 8) % 1;
        return 0.3 + 0.7 * Math.sin(offset * Math.PI * 2) ** 2;
    };

    return (
        <div className="pointer-events-none fixed inset-0 z-[9999999] overflow-visible">
            {/* Trail SVG - single element, updated directly */}
            <svg className="absolute inset-0 w-full h-full overflow-visible">
                <polyline
                    ref={svgPathRef}
                    fill="none"
                    stroke="#22d3ee"
                    strokeWidth="4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ opacity: 0.8 }}
                />
            </svg>

            {/* UFO Container */}
            <div
                className="absolute transition-transform duration-100 ease-out will-change-transform"
                style={{
                    left: position.x,
                    top: position.y,
                    transform: `translate(-50%, -50%) scale(${isClicking ? 0.9 : 1.2}) rotate(${isClicking ? -5 : 5}deg)`,
                }}
            >
                {/* INLINE SVG UFO with Alien */}
                <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="drop-shadow-[0_0_15px_rgba(34,211,238,0.8)]">

                    {/* 1. Saucer Hull (Back) - Brighter Metal */}
                    <ellipse cx="50" cy="50" rx="45" ry="12" fill="#475569" stroke="#94a3b8" strokeWidth="2" />

                    {/* 2. Engines / Undercarriage */}
                    <ellipse cx="50" cy="55" rx="15" ry="4" fill="rgba(34, 211, 238, 0.6)" className="animate-pulse" />


                    {/* 3. Tiny Green Alien - Moved UP significantly to be inside */}
                    <g className="animate-bounce-slight" style={{ transform: 'translateY(-5px)' }}>
                        {/* Body - Vivid Green */}
                        <ellipse cx="50" cy="40" rx="10" ry="12" fill="#22c55e" />
                        {/* Eyes */}
                        <ellipse cx="46" cy="38" rx="2.5" ry="3.5" fill="black" />
                        <ellipse cx="54" cy="38" rx="2.5" ry="3.5" fill="black" />
                        {/* Smile */}
                        <path d="M 48 44 Q 50 46 52 44" stroke="black" strokeWidth="1" strokeLinecap="round" opacity="0.5" />

                        {/* Waving Arm */}
                        <path
                            d="M 58 40 Q 68 35 70 25"
                            stroke="#22c55e"
                            strokeWidth="3"
                            strokeLinecap="round"
                            className="origin-[58px_40px] animate-wave"
                        />
                    </g>

                    {/* 4. Cockpit Glass - Semi-transparent, drawn OVER alien */}
                    <path d="M50 15 C 30 15, 20 40, 15 50 L 85 50 C 80 40, 70 15, 50 15 Z" fill="rgba(165, 243, 252, 0.4)" stroke="rgba(255,255,255,0.6)" strokeWidth="1" />
                    {/* Glass Reflection */}
                    <path d="M40 20 Q 30 25 35 35" stroke="rgba(255,255,255,0.4)" strokeWidth="2" fill="none" />

                    {/* 5. Saucer Rim (Front) - to cover bottom of glass */}
                    <path d="M 5 50 Q 50 62 95 50" stroke="#94a3b8" strokeWidth="2" fill="none" opacity="0.8" />


                    {/* 6. Lights - CHASE ANIMATION (opacity only, no transform) */}
                    {[0, 45, 90, 135, 180, 225, 270, 315].map((deg, i) => (
                        <circle
                            key={i}
                            cx={50 + 38 * Math.cos(deg * Math.PI / 180)}
                            cy={50 + 8 * Math.sin(deg * Math.PI / 180)}
                            r={isClicking ? 3 : 2}
                            fill={isClicking ? "#ef4444" : "#00fff2"}
                            style={{ opacity: getLightOpacity(i) }}
                        />
                    ))}


                    <defs>
                        <filter id="glow">
                            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                            <feMerge>
                                <feMergeNode in="coloredBlur" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>
                    </defs>
                </svg>

                {/* Hybrid Abduction Beam on Click */}
                {isClicking && (
                    <div
                        ref={beamParticlesRef}
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 translate-y-1"
                    >
                        {/* Main beam - gradient triangle */}
                        <svg width="80" height="120" viewBox="0 0 80 120" className="absolute -left-10 top-0">
                            <defs>
                                <linearGradient id="beamGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                    <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.6" />
                                    <stop offset="50%" stopColor="#06b6d4" stopOpacity="0.3" />
                                    <stop offset="100%" stopColor="#0891b2" stopOpacity="0.1" />
                                </linearGradient>
                            </defs>
                            <polygon
                                points="30,0 50,0 70,120 10,120"
                                fill="url(#beamGradient)"
                                style={{ filter: 'blur(2px)' }}
                            />
                            {/* Inner bright core */}
                            <polygon
                                points="35,0 45,0 55,120 25,120"
                                fill="rgba(165, 243, 252, 0.4)"
                                style={{ filter: 'blur(1px)' }}
                            />
                        </svg>

                        {/* Floating particles */}
                        {[0, 1, 2, 3, 4].map(i => (
                            <div
                                key={i}
                                className="absolute rounded-full bg-cyan-300"
                                style={{
                                    width: `${4 + Math.random() * 4}px`,
                                    height: `${4 + Math.random() * 4}px`,
                                    left: `${-10 + Math.random() * 20}px`,
                                    top: `${20 + i * 20}px`,
                                    opacity: 0.6 - i * 0.1,
                                    animation: `floatUp ${1 + i * 0.2}s ease-out infinite`,
                                    animationDelay: `${i * 0.15}s`,
                                    filter: 'blur(1px)',
                                }}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Keyframes for floating particles */}
            <style>{`
                @keyframes floatUp {
                    0% {
                        transform: translateY(0) scale(1);
                        opacity: 0.6;
                    }
                    50% {
                        opacity: 0.8;
                    }
                    100% {
                        transform: translateY(-30px) scale(0.5);
                        opacity: 0;
                    }
                }
            `}</style>
        </div>
    );
};
