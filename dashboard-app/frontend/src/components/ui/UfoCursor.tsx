import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useGame } from '../../context/GameContext';

export const UfoCursor: React.FC = () => {
    const { activeShip, isGameEnabled, activeTrail, isMenuOpen } = useGame(); // Hook into Game System

    const [position, setPosition] = useState({ x: -100, y: -100 });
    const [isBeamActive, setIsBeamActive] = useState(false); // Right Click

    // Trail particles
    interface TrailParticle {
        id: number;
        x: number;
        y: number;
        life: number;
        color: string;
        size: number;
        vx: number;
        vy: number;
    }
    const [particles, setParticles] = useState<TrailParticle[]>([]);

    // Light animation state
    const [lightPhase, setLightPhase] = useState(0);
    const requestRef = useRef<number>();

    // Toggle cursors
    useEffect(() => {
        // Only hide cursor if we have a ship active AND menu is NOT open
        // When menu is open, show cursor so user can click menu items
        if (activeShip !== 'default' && !isMenuOpen) {
            document.body.classList.add('cosmic-cursor-hidden');
        } else {
            document.body.classList.remove('cosmic-cursor-hidden');
        }
        return () => window.removeEventListener('contextmenu', preventMenu);
    }, [activeShip, isMenuOpen]);

    // Prevent Context Menu on Right Click if in UFO mode
    const preventMenu = useCallback((e: MouseEvent) => {
        if (activeShip !== 'default') {
            e.preventDefault();
        }
    }, [activeShip]);

    useEffect(() => {
        if (activeShip !== 'default') {
            window.addEventListener('contextmenu', preventMenu);
        }
        return () => window.removeEventListener('contextmenu', preventMenu);
    }, [activeShip, preventMenu]);

    // Mouse Listeners
    useEffect(() => {
        const updatePosition = (e: MouseEvent) => {
            setPosition({ x: e.clientX, y: e.clientY });

            // Emit particles based on active trail
            if (activeTrail !== 'none') {
                const count = activeTrail === 'plasma' ? 2 : activeTrail === 'fire' ? 3 : 1;

                const newParticles: TrailParticle[] = [];
                for (let i = 0; i < count; i++) {
                    let color = 'white';
                    let size = 2;
                    let life = 1.0;

                    if (activeTrail === 'plasma') {
                        color = Math.random() > 0.5 ? '#f43f5e' : '#fb7185'; // rose-500/400
                        size = 2 + Math.random() * 3;
                        life = 0.8;
                    } else if (activeTrail === 'fire') {
                        color = Math.random() > 0.5 ? '#f97316' : '#fbbf24'; // orange/amber
                        size = 3 + Math.random() * 4;
                        life = 0.6;
                    } else if (activeTrail === 'cyan') {
                        color = '#06b6d4';
                        life = 0.5;
                    } else if (activeTrail === 'star') {
                        color = '#fbbf24';
                        life = 0.7;
                    }

                    newParticles.push({
                        id: Math.random(),
                        x: e.clientX + (Math.random() - 0.5) * 10,
                        y: e.clientY + (Math.random() - 0.5) * 10,
                        life,
                        color,
                        size,
                        vx: (Math.random() - 0.5) * 2,
                        vy: (Math.random() - 0.5) * 2
                    });
                }

                setParticles(prev => [...prev, ...newParticles].slice(-50)); // Limit total particles
            }
        };

        const handleMouseDown = (e: MouseEvent) => {
            if (activeShip === 'default') return;
            if (!isGameEnabled) return;

            if (e.button === 2) { // Right Click
                setIsBeamActive(true);
            }
        };

        const handleMouseUp = (e: MouseEvent) => {
            if (e.button === 2) {
                setIsBeamActive(false);
            }
        };

        window.addEventListener('mousemove', updatePosition);
        window.addEventListener('mousedown', handleMouseDown);
        window.addEventListener('mouseup', handleMouseUp);

        return () => {
            window.removeEventListener('mousemove', updatePosition);
            window.removeEventListener('mousedown', handleMouseDown);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [activeShip, isGameEnabled]);

    // Animation Loop (Lights & Particles)
    useEffect(() => {
        let lastTime = performance.now();

        const animate = (currentTime: number) => {
            const deltaTime = currentTime - lastTime;

            // Lights
            if (deltaTime > 16) {
                setLightPhase(prev => (prev + deltaTime * 0.003) % 1);

                // Update Particles
                setParticles(prev => prev
                    .map(p => ({
                        ...p,
                        x: p.x + p.vx,
                        y: p.y + p.vy,
                        life: p.life - 0.02
                    }))
                    .filter(p => p.life > 0)
                );

                lastTime = currentTime;
            }

            requestRef.current = requestAnimationFrame(animate);
        };

        requestRef.current = requestAnimationFrame(animate);
        return () => {
            if (requestRef.current) {
                cancelAnimationFrame(requestRef.current);
            }
        };
    }, []);

    if (activeShip === 'default') return null;

    const getLightOpacity = (index: number) => {
        const offset = (lightPhase + index / 8) % 1;
        return 0.3 + 0.7 * Math.sin(offset * Math.PI * 2) ** 2;
    };

    return (
        <div className="pointer-events-none fixed inset-0 z-[9999999] overflow-visible">
            {/* Particles */}
            {particles.map(p => (
                <div
                    key={p.id}
                    className="absolute rounded-full pointer-events-none"
                    style={{
                        left: p.x,
                        top: p.y,
                        width: p.size,
                        height: p.size,
                        backgroundColor: p.color,
                        opacity: p.life,
                        boxShadow: `0 0 ${p.size * 2}px ${p.color}`,
                        transform: 'translate(-50%, -50%)'
                    }}
                />
            ))}

            {/* Ship Container */}
            <div
                className="absolute transition-transform duration-100 ease-out will-change-transform"
                style={{
                    left: position.x,
                    top: position.y,
                    transform: 'translate(-50%, -50%)' // No scaling/rotation here, separate from ship internals
                }}
            >
                {activeShip === 'ufo' ? (
                    // Classic UFO
                    <div className="relative w-8 h-8">
                        {/* Beam (Visual Only) */}
                        <div
                            className={`absolute top-1/2 left-1/2 -translate-x-1/2 w-0.5 bg-cyan-400/50 blur-[2px] transition-all duration-200 ${isBeamActive ? 'h-[500px] opacity-100' : 'h-0 opacity-0'
                                }`}
                            style={{ transformOrigin: 'top' }}
                        />

                        {/* Saucer */}
                        <div className="absolute inset-0 bg-slate-900 rounded-full border border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.5)] overflow-hidden">
                            {/* Rotating Lights */}
                            {[...Array(8)].map((_, i) => (
                                <div
                                    key={i}
                                    className="absolute w-1 h-1 bg-cyan-400 rounded-full"
                                    style={{
                                        top: '50%',
                                        left: '50%',
                                        transform: `rotate(${i * 45}deg) translate(0, -12px)`,
                                        opacity: getLightOpacity(i)
                                    }}
                                />
                            ))}
                            {/* Cockpit */}
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-cyan-900/50 rounded-full border border-cyan-400/30" />
                        </div>
                    </div>
                ) : activeShip === 'drone' ? (
                    // Drone
                    <div className="relative w-8 h-8 animate-[spin_4s_linear_infinite]">
                        <div className="absolute inset-0 border-2 border-emerald-500/50 rounded-full" />
                        <div className="absolute inset-1 border border-emerald-400/30 rounded-full border-dashed" />
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 bg-emerald-400 rounded-full shadow-[0_0_10px_rgba(52,211,153,0.8)]" />
                        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-2 w-1 h-3 bg-emerald-500/50" />
                        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-2 w-1 h-3 bg-emerald-500/50" />
                        <div className="absolute left-0 top-1/2 -translate-x-2 -translate-y-1/2 w-3 h-1 bg-emerald-500/50" />
                        <div className="absolute right-0 top-1/2 translate-x-2 -translate-y-1/2 w-3 h-1 bg-emerald-500/50" />
                    </div>
                ) : activeShip === 'glitch' ? (
                    // Glitch
                    <div className="relative w-8 h-8">
                        <div className="absolute inset-0 bg-fuchsia-600/20 clip-path-polygon animate-pulse" style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }} />
                        <div className="absolute inset-0 border-2 border-fuchsia-500 clip-path-polygon" style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }} />
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[10px] font-mono font-bold text-fuchsia-200">ERR</div>
                        {/* Glitch artifacts */}
                        <div className="absolute -left-2 top-0 w-2 h-1 bg-fuchsia-400/50 animate-[ping_0.5s_ease-in-out_infinite]" />
                        <div className="absolute -right-2 bottom-2 w-2 h-1 bg-white/50 animate-[ping_0.7s_ease-in-out_infinite]" />
                    </div>
                ) : (
                    // Star Ship (Rocket/Fighter)
                    <div className="relative w-10 h-10">
                        {/* Engine Glow */}
                        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-6 bg-amber-500/50 blur-md" />

                        {/* Ship Body */}
                        <svg viewBox="0 0 24 24" fill="none" className="w-full h-full text-slate-900 drop-shadow-[0_0_10px_rgba(251,191,36,0.5)]">
                            <path
                                d="M12 2L2 22L12 18L22 22L12 2Z"
                                fill="#0f172a"
                                stroke="#fbbf24"
                                strokeWidth="1.5"
                                strokeLinejoin="round"
                            />
                            <path d="M12 12V18" stroke="#fbbf24" strokeWidth="1" />
                        </svg>
                    </div>
                )}
            </div>
        </div>
    );
};
