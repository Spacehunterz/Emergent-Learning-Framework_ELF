import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 3: Organic themed - green/pink
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#00ff7f'; // SpringGreen
    if (healthPct > 0.25) return '#ffc0cb'; // Pink
    return '#ff69b4'; // HotPink
};

/**
 * Stage 3 Asteroid: Pulsing bio-mass with tendrils
 */
export const Stage3Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const tendrilRefs = useRef<(THREE.Mesh | null)[]>([]);

    const tendrils = useMemo(() => Array.from({ length: 8 }, (_, i) => ({
        angle: (i / 8) * Math.PI * 2,
        seed: Math.random() * 100,
        length: 1.5 + Math.random() * 1,
    })), []);

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

        ref.current.rotation.y += delta * 0.15;

        // Organic pulsing
        const pulse = 0.85 + Math.sin(t * 1.5 + data.seed) * 0.15;
        ref.current.scale.setScalar(ease * 30 * pulse); // 2x size

        if (mainMatRef.current) {
            // Color cycling/flashing
            const glitch = Math.random() > 0.92;
            if (glitch) {
                mainMatRef.current.color.set(['#00ff7f', '#ffc0cb', '#ff69b4'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            // Pulsing opacity
            mainMatRef.current.opacity = ease * (0.85 + Math.sin(t * 7) * 0.1);
        }

        // Animate tendrils
        tendrilRefs.current.forEach((tendril, i) => {
            if (!tendril) return;
            const wave = Math.sin(t * 2 + tendrils[i].seed) * 0.4;
            tendril.rotation.z = wave;
            tendril.scale.y = 0.8 + Math.sin(t * 3 + i) * 0.2;

            // Jittering tendrils
            if (Math.random() > 0.94) {
                tendril.position.x += (Math.random() - 0.5) * 0.2;
                tendril.position.y += (Math.random() - 0.5) * 0.2;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main bio-mass core */}
            <mesh>
                <sphereGeometry args={[1, 10, 8]} />
                <meshBasicMaterial ref={mainMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Inner nucleus */}
            <mesh scale={0.5}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#ff69b4" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Tendrils */}
            {tendrils.map((t, i) => (
                <mesh key={i} ref={el => tendrilRefs.current[i] = el}
                    position={[Math.cos(t.angle) * 0.8, Math.sin(t.angle) * 0.8, 0]}
                    rotation-z={t.angle - Math.PI / 2}
                    scale={[0.08, t.length, 0.08]}>
                    <cylinderGeometry args={[1, 0.3, 1, 6]} />
                    <meshBasicMaterial color="#ffc0cb" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 3 Drone: Jellyfish-like with trailing tentacles
 */
export const Stage3Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const tentacleRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailPositions = useRef<THREE.Vector3[]>([]);

    const tentacles = useMemo(() => Array.from({ length: 8 }, (_, i) => ({
        angle: (i / 8) * Math.PI * 2,
        length: 2 + Math.random() * 1.5,
        phase: Math.random() * Math.PI * 2,
    })), []);

    useMemo(() => {
        trailPositions.current = Array.from({ length: 4 }, () => new THREE.Vector3());
    }, []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.3;
        ref.current.scale.setScalar(ease * 18); // 2x size

        // Jerky discrete movement
        if (Math.random() > 0.96) {
            ref.current.position.x += (Math.random() - 0.5) * 2;
        }

        // Body pulse (jellyfish swimming motion)
        const bodyPulse = 0.85 + Math.sin(t * 2.5 + data.seed) * 0.15;
        ref.current.children[0].scale.set(bodyPulse, 1, bodyPulse);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Animate tentacles with wave motion
        tentacleRefs.current.forEach((tent, i) => {
            if (!tent) return;
            const wave = Math.sin(t * 3 + tentacles[i].phase) * 0.4;
            tent.rotation.x = wave;
            tent.rotation.z = Math.sin(t * 2 + i) * 0.2;
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
            {/* Dome body */}
            <mesh>
                <sphereGeometry args={[1, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} side={THREE.DoubleSide} />
            </mesh>
            {/* Glowing core */}
            <mesh position-y={0.3} scale={0.4}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.5} />
            </mesh>
            {/* Tentacles */}
            {tentacles.map((t, i) => (
                <mesh key={i} ref={el => tentacleRefs.current[i] = el}
                    position={[Math.cos(t.angle) * 0.6, -0.5, Math.sin(t.angle) * 0.6]}
                    scale={[0.05, t.length, 0.05]}>
                    <cylinderGeometry args={[1, 0.2, 1, 4]} />
                    <meshBasicMaterial color="#ff69b4" wireframe transparent opacity={0.6} />
                </mesh>
            ))}
            {/* Ghost trail */}
            {[0, 1, 2, 3].map(i => (
                <mesh
                    key={`trail-${i}`}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.3 - i * 0.05}
                >
                    <sphereGeometry args={[1, 8, 6]} />
                    <meshBasicMaterial color="#ffc0cb" transparent opacity={0} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 3 Fighter: Manta ray shape with undulating wings
 */
export const Stage3Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);

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

        // Undulating wing motion
        const wingWave = Math.sin(t * 3 + phase) * 0.4;
        if (wingLeftRef.current) wingLeftRef.current.rotation.z = -wingWave;
        if (wingRightRef.current) wingRightRef.current.rotation.z = wingWave;
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main body (elongated) */}
            <mesh rotation-x={Math.PI / 2} scale={[0.4, 1.5, 0.2]}>
                <capsuleGeometry args={[0.5, 1, 4, 8]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Left wing */}
            <mesh ref={wingLeftRef} position={[-0.3, 0, 0]} rotation-y={-Math.PI / 6}>
                <coneGeometry args={[1.5, 0.1, 4]} />
                <meshBasicMaterial color="#00ff7f" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Right wing */}
            <mesh ref={wingRightRef} position={[0.3, 0, 0]} rotation-y={Math.PI / 6}>
                <coneGeometry args={[1.5, 0.1, 4]} />
                <meshBasicMaterial color="#00ff7f" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Tail */}
            <mesh position-z={-1.2} scale={[0.1, 0.1, 1]}>
                <cylinderGeometry args={[1, 0.2, 1, 4]} />
                <meshBasicMaterial color="#ffc0cb" wireframe transparent opacity={0.6} />
            </mesh>
        </group>
    );
};

/**
 * Stage 3 Elite: Hive queen with orbiting swarm particles
 */
export const Stage3Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const swarmRefs = useRef<(THREE.Mesh | null)[]>([]);

    const swarmParticles = useMemo(() => Array.from({ length: 20 }, () => ({
        radius: 2 + Math.random() * 1.5,
        speed: 0.5 + Math.random() * 1,
        yOffset: (Math.random() - 0.5) * 2,
        phase: Math.random() * Math.PI * 2,
    })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.15;
        ref.current.scale.setScalar(ease * 36); // 2x size

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease;
        }

        // Animate swarm particles
        swarmRefs.current.forEach((particle, i) => {
            if (!particle) return;
            const p = swarmParticles[i];
            const angle = t * p.speed + p.phase;
            particle.position.set(
                Math.cos(angle) * p.radius,
                p.yOffset + Math.sin(t * p.speed * 2 + p.phase) * 0.5,
                Math.sin(angle) * p.radius
            );
            particle.scale.setScalar(0.1 + Math.sin(t * 4 + i) * 0.05);
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Queen body */}
            <mesh scale={[1, 1.5, 1]}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Crown */}
            <mesh position-y={1.3} scale={0.6}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#ff69b4" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Swarm particles */}
            {swarmParticles.map((_, i) => (
                <mesh key={i} ref={el => swarmRefs.current[i] = el} scale={0.1}>
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#ffc0cb" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 3 Boss: Leviathan with multiple segments
 */
export const Stage3Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const headMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const segmentRefs = useRef<(THREE.Group | null)[]>([]);

    const segmentCount = 8;

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        if (headMatRef.current) {
            headMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            headMatRef.current.opacity = ease;
        }

        // Animate segments in wave pattern
        segmentRefs.current.forEach((seg, i) => {
            if (!seg) return;
            const wave = Math.sin(t * 1.5 + i * 0.6 + data.seed) * 0.4;
            seg.position.y = wave;
            seg.rotation.z = Math.cos(t * 1.5 + i * 0.6 + data.seed) * 0.15;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Head */}
            <mesh scale={1.3}>
                <sphereGeometry args={[1, 10, 8]} />
                <meshBasicMaterial ref={headMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Eyes */}
            {[-0.4, 0.4].map((x, i) => (
                <mesh key={i} position={[x, 0.3, 0.8]} scale={0.25}>
                    <sphereGeometry args={[1, 6, 6]} />
                    <meshBasicMaterial color="#ff69b4" wireframe transparent opacity={0.9} />
                </mesh>
            ))}
            {/* Mouth */}
            <mesh position={[0, -0.3, 0.6]} rotation-x={Math.PI / 2} scale={0.5}>
                <torusGeometry args={[0.8, 0.15, 6, 8]} />
                <meshBasicMaterial color="#ffc0cb" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Body segments */}
            {Array.from({ length: segmentCount }).map((_, i) => {
                const scale = 1 - (i / segmentCount) * 0.6;
                return (
                    <group key={i} ref={el => segmentRefs.current[i] = el} position-z={-(i + 1) * 1.5}>
                        <mesh scale={scale}>
                            <sphereGeometry args={[1, 8, 6]} />
                            <meshBasicMaterial color="#00ff7f" wireframe transparent opacity={0.7} />
                        </mesh>
                        {/* Spines */}
                        {i % 2 === 0 && (
                            <>
                                <mesh position={[scale * 0.8, 0, 0]} rotation-z={-Math.PI / 4} scale={[0.1, scale * 0.6, 0.1]}>
                                    <coneGeometry args={[1, 1, 4]} />
                                    <meshBasicMaterial color="#ffc0cb" wireframe transparent opacity={0.6} />
                                </mesh>
                                <mesh position={[-scale * 0.8, 0, 0]} rotation-z={Math.PI / 4} scale={[0.1, scale * 0.6, 0.1]}>
                                    <coneGeometry args={[1, 1, 4]} />
                                    <meshBasicMaterial color="#ffc0cb" wireframe transparent opacity={0.6} />
                                </mesh>
                            </>
                        )}
                    </group>
                );
            })}
        </group>
    );
};
