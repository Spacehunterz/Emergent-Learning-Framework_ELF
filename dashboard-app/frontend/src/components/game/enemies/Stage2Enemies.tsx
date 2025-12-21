import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 2: Cyber themed - blue/purple
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#00ffff'; // Cyan
    if (healthPct > 0.25) return '#8a2be2'; // BlueViolet
    return '#ff00ff'; // Magenta
};

/**
 * Stage 2 Asteroid: Hexagonal crystal cluster with spinning fragments
 */
export const Stage2Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const fragmentRefs = useRef<(THREE.Mesh | null)[]>([]);

    const fragments = useMemo(() => {
        return Array.from({ length: 6 }, (_, i) => ({
            position: new THREE.Vector3(
                Math.cos(i * Math.PI / 3) * 1.8,
                (Math.random() - 0.5) * 1.2,
                Math.sin(i * Math.PI / 3) * 1.8
            ),
            scale: 0.3 + Math.random() * 0.25,
            rotSpeed: 1.5 + Math.random() * 1.5,
        }));
    }, []);

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

        ref.current.rotation.y += delta * 0.3;
        ref.current.rotation.x += delta * 0.15;
        ref.current.scale.setScalar(ease * 36); // 2x size

        if (mainMatRef.current) {
            // Color cycling/flashing
            const glitch = Math.random() > 0.92;
            if (glitch) {
                mainMatRef.current.color.set(['#00ffff', '#8a2be2', '#ff00ff'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            // Pulsing opacity
            mainMatRef.current.opacity = ease * (0.85 + Math.sin(t * 8) * 0.1);
        }

        fragmentRefs.current.forEach((frag, i) => {
            if (!frag) return;
            frag.rotation.y += delta * fragments[i].rotSpeed;
            frag.rotation.z += delta * fragments[i].rotSpeed * 0.7;
            const pulse = 1 + Math.sin(t * 3 + i) * 0.15;
            frag.scale.setScalar(fragments[i].scale * pulse);

            // Orbiting/jittering fragments
            if (Math.random() > 0.93) {
                frag.position.x += (Math.random() - 0.5) * 0.3;
                frag.position.y += (Math.random() - 0.5) * 0.3;
                frag.position.z += (Math.random() - 0.5) * 0.3;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main hexagonal core */}
            <mesh>
                <cylinderGeometry args={[1, 1, 2.5, 6]} />
                <meshBasicMaterial ref={mainMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Inner glow */}
            <mesh scale={0.6}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.4} />
            </mesh>
            {/* Orbiting crystal fragments */}
            {fragments.map((frag, i) => (
                <mesh key={i} position={frag.position} scale={frag.scale} ref={el => fragmentRefs.current[i] = el}>
                    <cylinderGeometry args={[0.8, 0.8, 2, 6]} />
                    <meshBasicMaterial color="#8a2be2" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 2 Drone: Quad-rotor style with energy beams between rotors
 */
export const Stage2Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const rotorRefs = useRef<(THREE.Mesh | null)[]>([]);
    const beamMatRefs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);
    const trailRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailPositions = useRef<THREE.Vector3[]>([]);

    const rotorPositions = useMemo(() => [
        [1.8, 0, 1.8], [1.8, 0, -1.8], [-1.8, 0, -1.8], [-1.8, 0, 1.8]
    ] as [number, number, number][], []);

    useMemo(() => {
        trailPositions.current = Array.from({ length: 4 }, () => new THREE.Vector3());
    }, []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 18); // 2x size

        // Jerky discrete movement
        if (Math.random() > 0.96) {
            ref.current.position.x += (Math.random() - 0.5) * 2;
        }

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.95;
        }

        rotorRefs.current.forEach((rotor, i) => {
            if (rotor) rotor.rotation.y += delta * 15;
        });

        beamMatRefs.current.forEach((mat, i) => {
            if (mat) {
                const pulse = 0.4 + Math.sin(t * 8 + i * Math.PI / 2) * 0.4;
                mat.opacity = pulse * ease;
            }
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
            {/* Central body */}
            <mesh>
                <icosahedronGeometry args={[0.8, 0]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Rotors */}
            {rotorPositions.map((pos, i) => (
                <group key={i} position={pos}>
                    <mesh ref={el => rotorRefs.current[i] = el} rotation-x={Math.PI / 2}>
                        <torusGeometry args={[0.6, 0.08, 4, 8]} />
                        <meshBasicMaterial color="#00ffff" wireframe transparent opacity={0.8} />
                    </mesh>
                    {/* Arm */}
                    <mesh position={[-pos[0] * 0.4, 0, -pos[2] * 0.4]} scale={[0.8, 0.15, 0.15]}>
                        <boxGeometry args={[1, 1, 1]} />
                        <meshBasicMaterial color="#8a2be2" wireframe transparent opacity={0.6} />
                    </mesh>
                </group>
            ))}
            {/* Energy beams between rotors */}
            {rotorPositions.map((pos, i) => {
                const next = rotorPositions[(i + 1) % 4];
                return (
                    <mesh key={`beam-${i}`}
                        position={[(pos[0] + next[0]) / 2, 0, (pos[2] + next[2]) / 2]}
                        scale={[2.5, 0.06, 0.06]}
                        rotation-y={i % 2 === 0 ? Math.PI / 4 : -Math.PI / 4}
                    >
                        <boxGeometry args={[1, 1, 1]} />
                        <meshBasicMaterial ref={el => beamMatRefs.current[i] = el} color="#ff00ff" transparent opacity={0} />
                    </mesh>
                );
            })}
            {/* Ghost trail */}
            {[0, 1, 2, 3].map(i => (
                <mesh
                    key={`trail-${i}`}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.3 - i * 0.05}
                >
                    <icosahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#8a2be2" transparent opacity={0} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 2 Fighter: Sleek arrowhead with trailing energy ribbons
 */
export const Stage2Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ribbonRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24); // 2x size

        // Visibility flickering
        const visible = Math.sin(t * 18) > -0.85;
        ref.current.visible = visible;

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * (Math.random() > 0.15 ? 0.9 : 0.4);
        }

        // Animate ribbon waves
        ribbonRefs.current.forEach((ribbon, i) => {
            if (!ribbon) return;
            ribbon.rotation.x = Math.sin(t * 4 + phase + i) * 0.3;
            ribbon.scale.y = 0.8 + Math.sin(t * 3 + i * 2) * 0.2;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main arrowhead body */}
            <mesh rotation-x={Math.PI / 2}>
                <coneGeometry args={[0.7, 2.5, 4]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Inner core */}
            <mesh scale={0.4}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Energy ribbons */}
            {[-0.5, 0.5].map((x, i) => (
                <mesh key={i} ref={el => ribbonRefs.current[i] = el}
                    position={[x, 0, -1.5]} scale={[0.1, 2, 0.02]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color={i === 0 ? "#00ffff" : "#ff00ff"} wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 2 Elite: Floating fortress with shield generators
 */
export const Stage2Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const shieldMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const generatorRefs = useRef<(THREE.Group | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.2;
        ref.current.scale.setScalar(ease * 30); // 2x size

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease;
        }

        if (shieldMatRef.current) {
            const shieldPulse = 0.15 + Math.sin(t * 2 + phase) * 0.1;
            shieldMatRef.current.opacity = shieldPulse * ease;
        }

        generatorRefs.current.forEach((gen, i) => {
            if (!gen) return;
            const angle = t * 0.5 + (i * Math.PI / 2);
            gen.position.set(Math.cos(angle) * 2.5, Math.sin(t + i) * 0.5, Math.sin(angle) * 2.5);
            gen.rotation.y += delta * 2;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main fortress body */}
            <mesh>
                <dodecahedronGeometry args={[1.5, 0]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Shield bubble */}
            <mesh scale={2.8}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={shieldMatRef} color="#00ffff" wireframe transparent opacity={0} />
            </mesh>
            {/* Shield generators */}
            {[0, 1, 2, 3].map(i => (
                <group key={i} ref={el => generatorRefs.current[i] = el}>
                    <mesh>
                        <octahedronGeometry args={[0.4, 0]} />
                        <meshBasicMaterial color="#ff00ff" wireframe transparent opacity={0.8} />
                    </mesh>
                </group>
            ))}
        </group>
    );
};

/**
 * Stage 2 Boss: Massive spider-like construct with 8 articulated legs
 */
export const Stage2Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const legRefs = useRef<(THREE.Group | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 18);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease;
        }

        // Animate legs
        legRefs.current.forEach((leg, i) => {
            if (!leg) return;
            const phase = i * 0.4 + (i < 4 ? 0 : Math.PI);
            const wave = Math.sin(t * 2 + phase);
            leg.rotation.z = wave * 0.15;
            leg.children[0].rotation.z = -wave * 0.25;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main body sphere */}
            <mesh>
                <sphereGeometry args={[1.2, 12, 10]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Eye cluster */}
            <mesh position={[0, 0.3, 0.8]} scale={0.4}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#ff00ff" wireframe transparent opacity={0.9} />
            </mesh>
            {/* 8 Legs */}
            {Array.from({ length: 8 }).map((_, i) => {
                const angle = (i / 8) * Math.PI * 2;
                const side = i < 4 ? 1 : -1;
                return (
                    <group key={i} ref={el => legRefs.current[i] = el}
                        rotation-y={angle} position-y={-0.2}>
                        {/* Upper leg */}
                        <group position={[1.2, 0, 0]} rotation-z={-0.5}>
                            <mesh scale={[1.2, 0.15, 0.15]}>
                                <boxGeometry args={[1, 1, 1]} />
                                <meshBasicMaterial color="#00ffff" wireframe transparent opacity={0.8} />
                            </mesh>
                            {/* Lower leg */}
                            <group position={[1.2, 0, 0]} rotation-z={-0.8}>
                                <mesh scale={[1.5, 0.1, 0.1]}>
                                    <boxGeometry args={[1, 1, 1]} />
                                    <meshBasicMaterial color="#8a2be2" wireframe transparent opacity={0.7} />
                                </mesh>
                            </group>
                        </group>
                    </group>
                );
            })}
        </group>
    );
};
