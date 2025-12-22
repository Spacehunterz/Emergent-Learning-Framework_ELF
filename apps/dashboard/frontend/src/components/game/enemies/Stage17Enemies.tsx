import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 17: Volcanic/Magma themed - #FF4500, #FF8C00, #000000
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#FF4500'; // OrangeRed
    if (healthPct > 0.25) return '#FF8C00'; // DarkOrange
    return '#FFD700'; // Gold (hot!)
};

/**
 * Stage 17 Asteroid: Jagged black lava rock with pulsing orange-red cracks and glitch effects
 */
export const Stage17Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const rockMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const crackMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const fragmentRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.04 + Math.random() * 0.05,
        y: 0.05 + Math.random() * 0.06,
        z: 0.03 + Math.random() * 0.04
    }), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;

        // Scale pulse with occasional spikes
        const glitchScale = Math.random() > 0.92 ? 1.15 : 1.0;
        ref.current.scale.setScalar(ease * 36 * glitchScale);

        // Occasional teleport jitter
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 5;
            ref.current.position.y += (Math.random() - 0.5) * 5;
        }

        if (rockMatRef.current) {
            const glitch = Math.random() > 0.9;
            if (glitch) {
                rockMatRef.current.color.set(['#FF4500', '#FF8C00', '#FFD700'][Math.floor(Math.random() * 3)]);
            } else {
                rockMatRef.current.color.set('#000000');
            }
            // Opacity flicker during glitch
            rockMatRef.current.opacity = ease * (glitch ? 0.6 : 0.95);
        }

        // Cracks pulse with inner heat and color cycling
        if (crackMatRef.current) {
            const glitch = Math.random() > 0.9;
            if (glitch) {
                crackMatRef.current.color.set(['#FF4500', '#FF8C00', '#FFD700'][Math.floor(Math.random() * 3)]);
            } else {
                crackMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            crackMatRef.current.opacity = 0.5 + Math.sin(t * 3) * 0.3;
        }

        // Fragment jitter
        fragmentRefs.current.forEach((frag) => {
            if (!frag) return;
            if (Math.random() > 0.9) {
                frag.position.x += (Math.random() - 0.5) * 0.3;
                frag.position.y += (Math.random() - 0.5) * 0.3;
                frag.position.z += (Math.random() - 0.5) * 0.3;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Black cooled lava rock */}
            <mesh>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={rockMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Glowing cracks underneath */}
            <mesh scale={0.95}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={crackMatRef} color="#FF4500" wireframe transparent opacity={0.5} />
            </mesh>
            {/* Orbiting lava fragments */}
            {[0, 1, 2].map(i => (
                <mesh
                    key={i}
                    ref={el => fragmentRefs.current[i] = el}
                    position={[
                        Math.cos(i * Math.PI * 2 / 3) * 1.2,
                        Math.sin(i * Math.PI * 2 / 3) * 0.4,
                        Math.sin(i * Math.PI * 2 / 3) * 1.2
                    ]}
                    scale={0.2}
                >
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color={['#FF4500', '#FF8C00', '#FFD700'][i]} transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 17 Drone: Churning lava sphere with orbiting obsidian chunks that jitter
 */
export const Stage17Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const lavaMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const chunkGroupRef = useRef<THREE.Group>(null);
    const chunkRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);

        // Scale pulse with glitch spikes
        const glitchScale = Math.random() > 0.92 ? 1.2 : 1.0;
        ref.current.scale.setScalar(ease * 18 * glitchScale);

        // Jerky discrete movement
        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
        }

        // Lava churns with color flashing
        if (lavaMatRef.current) {
            const glitch = Math.random() > 0.9;
            if (glitch) {
                lavaMatRef.current.color.set(['#FF4500', '#FF8C00', '#FFD700'][Math.floor(Math.random() * 3)]);
            } else {
                lavaMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            // Dramatic opacity pulse during glitch
            lavaMatRef.current.opacity = ease * (glitch ? 0.4 : (0.7 + Math.sin(t * 5) * 0.2));
        }

        // Obsidian chunks orbit slowly
        if (chunkGroupRef.current) {
            chunkGroupRef.current.rotation.y += delta * 0.8;
            chunkGroupRef.current.rotation.x += delta * 0.3;
        }

        // Chunk jitter during glitch
        chunkRefs.current.forEach((chunk) => {
            if (!chunk) return;
            if (Math.random() > 0.9) {
                chunk.position.x += (Math.random() - 0.5) * 0.2;
                chunk.position.y += (Math.random() - 0.5) * 0.2;
                chunk.position.z += (Math.random() - 0.5) * 0.2;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Churning lava core */}
            <mesh>
                <sphereGeometry args={[0.6, 12, 8]} />
                <meshBasicMaterial ref={lavaMatRef} color="#FF4500" transparent opacity={0} />
            </mesh>
            <mesh scale={0.5}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#FF8C00" transparent opacity={0.6} />
            </mesh>
            {/* Orbiting obsidian chunks */}
            <group ref={chunkGroupRef}>
                {[0, 1, 2, 3].map(i => (
                    <mesh
                        key={i}
                        ref={el => chunkRefs.current[i] = el}
                        position={[
                            Math.cos(i * Math.PI / 2) * 1,
                            Math.sin(i * Math.PI / 2) * 0.3,
                            Math.sin(i * Math.PI / 2) * 1
                        ]}
                        scale={0.15}
                    >
                        <boxGeometry args={[1, 1, 1]} />
                        <meshBasicMaterial color="#000000" transparent opacity={0.9} />
                    </mesh>
                ))}
            </group>
        </group>
    );
};

/**
 * Stage 17 Fighter: Sharp obsidian arrowhead with glowing orange engines and glitch displacement
 */
export const Stage17Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const partsRef = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const engineMatRefs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);

        // Scale pulse with glitch spikes
        const glitchScale = Math.random() > 0.92 ? 1.15 : 1.0;
        ref.current.scale.setScalar(ease * 24 * glitchScale);

        // Flicker in and out
        const visible = Math.sin(t * 20) > -0.8;
        ref.current.visible = visible;

        // Parts get displaced by glitch effect
        if (partsRef.current && Math.random() > 0.9) {
            partsRef.current.children.forEach((child) => {
                if (child instanceof THREE.Mesh) {
                    child.position.x = (Math.random() - 0.5) * 0.3;
                    child.position.y = (Math.random() - 0.5) * 0.3;
                }
            });
        }

        if (bodyMatRef.current) {
            const glitch = Math.random() > 0.9;
            bodyMatRef.current.opacity = ease * (glitch ? 0.5 : 0.95);
        }

        // Engines flare with heat distortion and color flashing
        engineMatRefs.current.forEach((mat, i) => {
            if (!mat) return;
            const glitch = Math.random() > 0.9;
            if (glitch) {
                mat.color.set(['#FF4500', '#FF8C00', '#FFD700'][Math.floor(Math.random() * 3)]);
            } else {
                mat.color.set(getHealthColor(data.hp, data.maxHp));
            }
            mat.opacity = glitch ? 0.3 : (0.6 + Math.sin(t * 8 + i) * 0.3);
        });
    });

    return (
        <group ref={ref} scale={0}>
            <group ref={partsRef}>
                {/* Sharp obsidian body */}
                <mesh rotation={[Math.PI, 0, 0]} scale={[0.5, 1.5, 0.2]}>
                    <coneGeometry args={[1, 2, 4]} />
                    <meshBasicMaterial ref={bodyMatRef} color="#000000" transparent opacity={0} />
                </mesh>
                {/* Glowing orange engines */}
                <mesh position={[-0.4, 0.8, 0]} scale={0.25}>
                    <coneGeometry args={[0.8, 1.5, 6]} />
                    <meshBasicMaterial ref={el => engineMatRefs.current[0] = el} color="#FF4500" transparent opacity={0.8} />
                </mesh>
                <mesh position={[0.4, 0.8, 0]} scale={0.25}>
                    <coneGeometry args={[0.8, 1.5, 6]} />
                    <meshBasicMaterial ref={el => engineMatRefs.current[1] = el} color="#FF4500" transparent opacity={0.8} />
                </mesh>
            </group>
        </group>
    );
};

/**
 * Stage 17 Elite: Black obsidian torus with suspended molten magma sphere and glitch effects
 */
export const Stage17Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const torusMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const magmaRef = useRef<THREE.Mesh>(null);
    const magmaMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const fragmentRefs = useRef<(THREE.Mesh | null)[]>([]);

    const fragments = useMemo(() =>
        Array.from({ length: 6 }, (_, i) => ({
            angle: (i / 6) * Math.PI * 2,
            dist: 1.8 + Math.random() * 0.4,
            frozen: Math.random() > 0.5
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.x += delta * 0.3;
        ref.current.rotation.y += delta * 0.5;

        // Scale pulse with glitch spikes
        const glitchScale = Math.random() > 0.92 ? 1.2 : 1.0;
        ref.current.scale.setScalar(ease * 36 * glitchScale);

        // Rapid color cycling during glitch
        if (torusMatRef.current) {
            const glitch = Math.random() > 0.9;
            if (glitch) {
                const phase = Math.floor(t * 8) % 3;
                torusMatRef.current.color.set(['#FF4500', '#FF8C00', '#FFD700'][phase]);
                torusMatRef.current.opacity = ease * 0.5;
            } else {
                torusMatRef.current.color.set('#000000');
                torusMatRef.current.opacity = ease * 0.9;
            }
        }

        // Magma churns and bubbles
        if (magmaRef.current) {
            magmaRef.current.scale.setScalar(0.8 + Math.sin(t * 4) * 0.1);
        }

        if (magmaMatRef.current) {
            const glitch = Math.random() > 0.9;
            if (glitch) {
                magmaMatRef.current.color.set(['#FF4500', '#FF8C00', '#FFD700'][Math.floor(Math.random() * 3)]);
            } else {
                magmaMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            magmaMatRef.current.opacity = 0.7 + Math.sin(t * 6) * 0.2;
        }

        // Fragment jitter (some frozen, some moving)
        fragmentRefs.current.forEach((frag, i) => {
            if (!frag) return;
            if (!fragments[i].frozen && Math.random() > 0.9) {
                frag.position.x += (Math.random() - 0.5) * 0.3;
                frag.position.y += (Math.random() - 0.5) * 0.3;
                frag.position.z += (Math.random() - 0.5) * 0.3;
            }
            if (frag.material instanceof THREE.MeshBasicMaterial) {
                frag.material.opacity = 0.5 + Math.sin(t * 5 + i) * 0.3;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Black obsidian torus */}
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1.5, 0.4, 8, 16]} />
                <meshBasicMaterial ref={torusMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Suspended molten magma */}
            <mesh ref={magmaRef}>
                <sphereGeometry args={[0.8, 12, 8]} />
                <meshBasicMaterial ref={magmaMatRef} color="#FF4500" transparent opacity={0.8} />
            </mesh>
            <mesh scale={0.6}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#FF8C00" transparent opacity={0.5} />
            </mesh>
            {/* Lava fragments */}
            {fragments.map((f, i) => (
                <mesh
                    key={i}
                    ref={el => fragmentRefs.current[i] = el}
                    position={[
                        Math.cos(f.angle) * f.dist,
                        Math.sin(f.angle) * 0.5,
                        Math.sin(f.angle) * f.dist
                    ]}
                    scale={0.2}
                >
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color={f.frozen ? '#000000' : '#FF8C00'} transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 17 Boss: Massive active volcano with bubbling crater, lava eruptions, and glitch effects
 */
export const Stage17Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const volcanoMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const lavaMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const eruptionRefs = useRef<(THREE.Mesh | null)[]>([]);
    const bodyPartRefs = useRef<(THREE.Mesh | null)[]>([]);

    const eruptions = useMemo(() =>
        Array.from({ length: 6 }, () => ({
            offset: Math.random() * Math.PI * 2,
            speed: 1 + Math.random() * 2,
            maxHeight: 2 + Math.random() * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Scale pulse with glitch spikes
        const glitchScale = Math.random() > 0.92 ? 1.15 : 1.0;
        ref.current.scale.setScalar(ease * 15 * glitchScale);

        // Fast-forward teleport effect
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 10;
        }

        // Volcano body glitches
        if (volcanoMatRef.current) {
            const glitch = Math.random() > 0.9;
            if (glitch) {
                volcanoMatRef.current.color.set(['#FF4500', '#FF8C00', '#FFD700'][Math.floor(Math.random() * 3)]);
            } else {
                volcanoMatRef.current.color.set('#000000');
            }
            volcanoMatRef.current.opacity = ease * (glitch ? 0.6 : 0.95);
        }

        // Crater lava bubbles with color flashing
        if (lavaMatRef.current) {
            const glitch = Math.random() > 0.9;
            if (glitch) {
                lavaMatRef.current.color.set(['#FF4500', '#FF8C00', '#FFD700'][Math.floor(Math.random() * 3)]);
            } else {
                lavaMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            lavaMatRef.current.opacity = glitch ? 0.4 : (0.7 + Math.sin(t * 5) * 0.2);
        }

        // Body parts glitch and reposition
        bodyPartRefs.current.forEach((part) => {
            if (!part) return;
            if (Math.random() > 0.95) {
                part.position.x += (Math.random() - 0.5) * 0.3;
                part.position.y += (Math.random() - 0.5) * 0.3;
            }
        });

        // Eruption particles shoot up and fall with glitch flicker
        eruptionRefs.current.forEach((particle, i) => {
            if (!particle) return;
            const e = eruptions[i];
            const cycle = ((t * e.speed + e.offset) % 4) / 4; // 0 to 1 cycle
            const height = cycle < 0.5 ? cycle * 2 * e.maxHeight : (1 - (cycle - 0.5) * 2) * e.maxHeight;
            particle.position.y = 1.5 + height;
            particle.position.x = Math.sin(e.offset) * cycle * 0.5;
            particle.position.z = Math.cos(e.offset) * cycle * 0.5;

            if (particle.material instanceof THREE.MeshBasicMaterial) {
                const glitch = Math.random() > 0.9;
                if (glitch) {
                    particle.material.color.set(['#FF4500', '#FF8C00', '#FFD700'][Math.floor(Math.random() * 3)]);
                } else {
                    particle.material.color.set('#FF8C00');
                }
                particle.material.opacity = cycle < 0.5 ? 0.9 : 0.9 - (cycle - 0.5) * 1.6;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Volcano cone */}
            <mesh ref={el => bodyPartRefs.current[0] = el} position={[0, -1, 0]}>
                <coneGeometry args={[3, 4, 12]} />
                <meshBasicMaterial ref={volcanoMatRef} color="#000000" transparent opacity={0} />
            </mesh>
            {/* Crater rim */}
            <mesh ref={el => bodyPartRefs.current[1] = el} position={[0, 1, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1.2, 0.3, 8, 16]} />
                <meshBasicMaterial color="#1a0a00" transparent opacity={0.9} />
            </mesh>
            {/* Bubbling lava pool */}
            <mesh position={[0, 0.8, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <circleGeometry args={[1, 16]} />
                <meshBasicMaterial ref={lavaMatRef} color="#FF4500" transparent opacity={0.8} side={THREE.DoubleSide} />
            </mesh>
            {/* Eruption particles */}
            {eruptions.map((_, i) => (
                <mesh
                    key={i}
                    ref={el => eruptionRefs.current[i] = el}
                    position={[0, 2, 0]}
                    scale={0.2}
                >
                    <sphereGeometry args={[1, 6, 4]} />
                    <meshBasicMaterial color="#FF8C00" transparent opacity={0.8} />
                </mesh>
            ))}
            {/* Smoke wisps */}
            {[0, 1, 2].map(i => (
                <mesh key={`smoke${i}`} position={[Math.sin(i) * 0.5, 2.5 + i * 0.5, Math.cos(i) * 0.5]} scale={0.4 + i * 0.2}>
                    <sphereGeometry args={[1, 6, 4]} />
                    <meshBasicMaterial color="#333333" transparent opacity={0.3} />
                </mesh>
            ))}
        </group>
    );
};
