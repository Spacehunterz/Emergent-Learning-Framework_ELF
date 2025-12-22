import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 5: Solar/Fire themed - #FF6A00, #FFD200, #FF2D55
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#FF6A00'; // Orange
    if (healthPct > 0.25) return '#FFD200'; // Gold
    return '#FF2D55'; // Red-pink
};

/**
 * Stage 5 Asteroid: Jagged poly boulder with ember streaks and hollow core
 */
export const Stage5Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const coreRef = useRef<THREE.Mesh>(null);

    const rotSpeed = useMemo(() => ({
        x: 0.2 + Math.random() * 0.3,
        y: 0.15 + Math.random() * 0.2,
        z: 0.1 + Math.random() * 0.15
    }), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Random position jitter (glitch effect)
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
            ref.current.position.y += (Math.random() - 0.5) * 3;
        }

        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;
        ref.current.scale.setScalar(ease * 36);

        if (mainMatRef.current) {
            // Color cycling/flashing
            const glitch = Math.random() > 0.92;
            if (glitch) {
                mainMatRef.current.color.set(['#FF6A00', '#FFD200', '#FF2D55'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            // Pulsing opacity
            mainMatRef.current.opacity = ease * (0.85 + Math.sin(t * 7) * 0.1);
        }

        // Core pulses on 2-beat cycle
        if (coreRef.current) {
            const pulse = 0.6 + Math.sin(t * 4 + data.seed) * 0.4;
            coreRef.current.scale.setScalar(pulse);

            // Jittering core
            if (Math.random() > 0.94) {
                coreRef.current.position.x = (Math.random() - 0.5) * 0.2;
                coreRef.current.position.y = (Math.random() - 0.5) * 0.2;
            }
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main jagged boulder */}
            <mesh>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={mainMatRef} color="#FF6A00" wireframe transparent opacity={0} />
            </mesh>
            {/* Ember streaks - inner structure */}
            <mesh rotation={[0.5, 0.3, 0]} scale={0.8}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#FFD200" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Hollow core cavity */}
            <mesh ref={coreRef} scale={0.4}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#FF2D55" wireframe transparent opacity={0.8} />
            </mesh>
        </group>
    );
};

/**
 * Stage 5 Drone: Tight pyramid with heat-ripple fins
 */
export const Stage5Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const finRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailPositions = useRef<THREE.Vector3[]>([]);

    useMemo(() => {
        trailPositions.current = Array.from({ length: 4 }, () => new THREE.Vector3());
    }, []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.rotation.z += delta * 8; // Rapid spin
        ref.current.scale.setScalar(ease * 18);

        // Jerky discrete movement
        if (Math.random() > 0.96) {
            ref.current.position.x += (Math.random() - 0.5) * 2;
        }

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Fins flicker
        finRefs.current.forEach((fin, i) => {
            if (!fin) return;
            const flicker = 0.8 + Math.sin(t * 12 + i * 2) * 0.2;
            fin.scale.setScalar(flicker);
        });

        // Update ghost trail
        for (let i = trailPositions.current.length - 1; i > 0; i--) {
            trailPositions.current[i].copy(trailPositions.current[i - 1]);
        }
        trailPositions.current[0].copy(data.position);

        trailRefs.current.forEach((trail, i) => {
            if (!trail) return;
            trail.position.copy(trailPositions.current[i]);
            if (trail.material instanceof THREE.MeshBasicMaterial) {
                trail.material.opacity = (0.4 - i * 0.1) * ease;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main pyramid body */}
            <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[1, 2, 4]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FF6A00" wireframe transparent opacity={0} />
            </mesh>
            {/* Heat-ripple fins */}
            {[0, 1, 2, 3].map(i => (
                <mesh
                    key={i}
                    ref={el => finRefs.current[i] = el}
                    position={[Math.cos(i * Math.PI / 2) * 0.8, 0, Math.sin(i * Math.PI / 2) * 0.8]}
                    rotation={[0, i * Math.PI / 2, Math.PI / 4]}
                    scale={[0.3, 0.8, 0.05]}
                >
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color="#FFD200" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
            {/* Ghost trail */}
            {[0, 1, 2, 3].map(i => (
                <mesh
                    key={`trail-${i}`}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.3 - i * 0.05}
                >
                    <coneGeometry args={[1, 2, 4]} />
                    <meshBasicMaterial color="#FF2D55" transparent opacity={0} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 5 Fighter: Double-pyramid with swept wings and tail spike
 */
export const Stage5Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);
    const noseMatRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        // Visibility flickering
        const visible = Math.sin(t * 18) > -0.85;
        ref.current.visible = visible;

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * (Math.random() > 0.15 ? 0.9 : 0.4);
        }

        // Wings oscillate
        const wingWave = Math.sin(t * 3 + phase) * 0.15;
        if (wingLeftRef.current) wingLeftRef.current.rotation.z = -0.3 + wingWave;
        if (wingRightRef.current) wingRightRef.current.rotation.z = 0.3 - wingWave;

        // Nose glow pulses
        if (noseMatRef.current) {
            noseMatRef.current.opacity = 0.6 + Math.sin(t * 5 + phase) * 0.3;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Double-pyramid fuselage */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={[0.5, 1.5, 0.5]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FF6A00" wireframe transparent opacity={0} />
            </mesh>
            {/* Swept wings */}
            <mesh ref={wingLeftRef} position={[-0.8, 0, 0.3]} rotation={[0, 0.5, -0.3]} scale={[1.2, 0.1, 0.6]}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#FFD200" wireframe transparent opacity={0.7} />
            </mesh>
            <mesh ref={wingRightRef} position={[0.8, 0, 0.3]} rotation={[0, -0.5, 0.3]} scale={[1.2, 0.1, 0.6]}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#FFD200" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Tail spike */}
            <mesh position={[0, 0, 1]} rotation={[Math.PI / 2, 0, 0]} scale={[0.15, 0.8, 0.15]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial color="#FF2D55" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Nose glow */}
            <mesh position={[0, 0, -1.2]} scale={0.3}>
                <sphereGeometry args={[1, 8, 8]} />
                <meshBasicMaterial ref={noseMatRef} color="#FFD200" transparent opacity={0.6} />
            </mesh>
        </group>
    );
};

/**
 * Stage 5 Elite: Spiked poly-sphere with orbiting flame-ring hexagons
 */
export const Stage5Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ring1Ref = useRef<THREE.Mesh>(null);
    const ring2Ref = useRef<THREE.Mesh>(null);
    const spikesRef = useRef<THREE.Group>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Random position jitter
        if (Math.random() > 0.97) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
            ref.current.position.y += (Math.random() - 0.5) * 3;
        }

        ref.current.rotation.y += delta * 0.3;
        ref.current.scale.setScalar(ease * 36);

        if (bodyMatRef.current) {
            // Color cycling
            const glitch = Math.random() > 0.92;
            if (glitch) {
                bodyMatRef.current.color.set(['#FF6A00', '#FFD200'][Math.floor(Math.random() * 2)]);
            } else {
                bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            bodyMatRef.current.opacity = ease * (0.9 + Math.sin(t * 6) * 0.1);
        }

        // Rings counter-rotate
        if (ring1Ref.current) ring1Ref.current.rotation.z += delta * 2;
        if (ring2Ref.current) ring2Ref.current.rotation.z -= delta * 1.5;

        // Spikes pulse outward
        if (spikesRef.current) {
            const pulse = 1 + Math.sin(t * 3 + data.seed) * 0.15;
            spikesRef.current.scale.setScalar(pulse);

            // Jitter spikes
            if (Math.random() > 0.94) {
                spikesRef.current.rotation.z += (Math.random() - 0.5) * 0.3;
            }
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Central spiked sphere */}
            <mesh>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FF6A00" wireframe transparent opacity={0} />
            </mesh>
            {/* Spike cluster */}
            <group ref={spikesRef}>
                {[0, 1, 2, 3, 4, 5].map(i => {
                    const theta = (i / 6) * Math.PI * 2;
                    return (
                        <mesh
                            key={i}
                            position={[Math.cos(theta) * 0.8, Math.sin(theta) * 0.8, 0]}
                            rotation={[0, 0, theta]}
                            scale={[0.15, 0.5, 0.15]}
                        >
                            <coneGeometry args={[1, 1, 4]} />
                            <meshBasicMaterial color="#FF2D55" wireframe transparent opacity={0.8} />
                        </mesh>
                    );
                })}
            </group>
            {/* Orbiting flame-ring hexagons */}
            <mesh ref={ring1Ref} position={[1.8, 0, 0]} rotation={[Math.PI / 2, 0, 0]} scale={0.5}>
                <torusGeometry args={[1, 0.15, 6, 6]} />
                <meshBasicMaterial color="#FFD200" transparent opacity={0.7} />
            </mesh>
            <mesh ref={ring2Ref} position={[-1.8, 0, 0]} rotation={[Math.PI / 2, 0, 0]} scale={0.5}>
                <torusGeometry args={[1, 0.15, 6, 6]} />
                <meshBasicMaterial color="#FFD200" transparent opacity={0.7} />
            </mesh>
        </group>
    );
};

/**
 * Stage 5 Boss: Massive sun-core cage with radial spokes and crown of spikes
 */
export const Stage5Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const coreMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const crownRef = useRef<THREE.Group>(null);
    const spokesRef = useRef<THREE.Group>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Random teleport jitter
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 5;
            ref.current.position.y += (Math.random() - 0.5) * 5;
        }

        ref.current.scale.setScalar(ease * 15);

        if (coreMatRef.current) {
            // Color glitching
            const glitch = Math.random() > 0.91;
            if (glitch) {
                coreMatRef.current.color.set(['#FF6A00', '#FFD200', '#FF2D55'][Math.floor(Math.random() * 3)]);
            } else {
                coreMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            // Core throbs
            coreMatRef.current.opacity = 0.7 + Math.sin(t * 2) * 0.2;
        }

        // Crown precesses
        if (crownRef.current) {
            crownRef.current.rotation.y += delta * 0.3;
            crownRef.current.rotation.x = Math.sin(t * 0.5) * 0.1;
        }

        // Spokes rotate in slow fan
        if (spokesRef.current) {
            spokesRef.current.rotation.z += delta * 0.5;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Sun-core cage */}
            <mesh scale={2}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={coreMatRef} color="#FF6A00" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Inner core */}
            <mesh scale={1.2}>
                <sphereGeometry args={[1, 12, 12]} />
                <meshBasicMaterial color="#FFD200" transparent opacity={0.5} />
            </mesh>
            {/* Radial spokes */}
            <group ref={spokesRef}>
                {Array.from({ length: 8 }).map((_, i) => {
                    const angle = (i / 8) * Math.PI * 2;
                    return (
                        <mesh
                            key={i}
                            position={[Math.cos(angle) * 2.5, 0, Math.sin(angle) * 2.5]}
                            rotation={[0, -angle, 0]}
                            scale={[0.1, 0.1, 1.5]}
                        >
                            <boxGeometry args={[1, 1, 1]} />
                            <meshBasicMaterial color="#FFD200" wireframe transparent opacity={0.6} />
                        </mesh>
                    );
                })}
            </group>
            {/* Crown of spikes */}
            <group ref={crownRef} position={[0, 2.5, 0]}>
                {Array.from({ length: 12 }).map((_, i) => {
                    const angle = (i / 12) * Math.PI * 2;
                    return (
                        <mesh
                            key={i}
                            position={[Math.cos(angle) * 1.5, 0, Math.sin(angle) * 1.5]}
                            rotation={[0, 0, -Math.PI / 6]}
                            scale={[0.2, 1, 0.2]}
                        >
                            <coneGeometry args={[1, 1, 4]} />
                            <meshBasicMaterial color="#FF2D55" wireframe transparent opacity={0.8} />
                        </mesh>
                    );
                })}
                <mesh rotation={[Math.PI / 2, 0, 0]} scale={1.8}>
                    <torusGeometry args={[1, 0.08, 8, 12]} />
                    <meshBasicMaterial color="#FF6A00" transparent opacity={0.6} />
                </mesh>
            </group>
        </group>
    );
};
