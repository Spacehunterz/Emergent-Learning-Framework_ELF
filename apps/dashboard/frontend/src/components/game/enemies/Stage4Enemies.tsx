import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 4: Void themed - dark purple/white
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#ffffff'; // White
    if (healthPct > 0.25) return '#9370db'; // MediumPurple
    return '#4b0082'; // Indigo
};

/**
 * Stage 4 Asteroid: Reality-warping cube with impossible geometry
 */
export const Stage4Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const innerCubeRefs = useRef<(THREE.Mesh | null)[]>([]);

    const innerCubes = useMemo(() => Array.from({ length: 4 }, (_, i) => ({
        scale: 0.3 + i * 0.15,
        rotSpeed: 1.5 - i * 0.3,
        axis: new THREE.Vector3(
            Math.random() - 0.5,
            Math.random() - 0.5,
            Math.random() - 0.5
        ).normalize()
    })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Random position jitter (glitch effect)
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 4;
            ref.current.position.y += (Math.random() - 0.5) * 4;
        }

        ref.current.scale.setScalar(ease * 36); // 2x size

        // Reality warp effect - slight position oscillation
        const warp = Math.sin(t * 2 + data.seed) * 0.1;
        ref.current.position.x += warp;
        ref.current.position.z += Math.cos(t * 2.3 + data.seed) * 0.1;

        if (mainMatRef.current) {
            // Color cycling/flashing
            const glitch = Math.random() > 0.91;
            if (glitch) {
                mainMatRef.current.color.set(['#ffffff', '#9370db', '#4b0082'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            // Pulsing opacity
            mainMatRef.current.opacity = ease * (0.8 + Math.sin(t * 7) * 0.1);
        }

        // Inner cubes rotate on different axes
        innerCubeRefs.current.forEach((cube, i) => {
            if (!cube) return;
            const c = innerCubes[i];
            cube.rotateOnAxis(c.axis, delta * c.rotSpeed);
            // Phase through each other effect
            const phaseScale = 1 + Math.sin(t * 2 + i * Math.PI / 2) * 0.1;
            cube.scale.setScalar(c.scale * phaseScale);

            // Jittering cubes
            if (Math.random() > 0.92) {
                cube.position.x = (Math.random() - 0.5) * 0.3;
                cube.position.y = (Math.random() - 0.5) * 0.3;
                cube.position.z = (Math.random() - 0.5) * 0.3;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Outer impossible cube */}
            <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={mainMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Nested rotating cubes */}
            {innerCubes.map((c, i) => (
                <mesh key={i} ref={el => innerCubeRefs.current[i] = el} scale={c.scale}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color={i % 2 === 0 ? "#9370db" : "#ffffff"} wireframe transparent opacity={0.6} />
                </mesh>
            ))}
            {/* Void tendrils */}
            {[0, 1, 2, 3].map(i => (
                <mesh key={`tendril-${i}`}
                    position={[
                        (i % 2 === 0 ? 1 : -1) * 0.8,
                        (i < 2 ? 1 : -1) * 0.8,
                        0
                    ]}
                    scale={[0.05, 0.5, 0.05]}>
                    <cylinderGeometry args={[1, 0, 1, 4]} />
                    <meshBasicMaterial color="#4b0082" wireframe transparent opacity={0.5} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 4 Drone: Phase-shifting ghost with afterimages
 */
export const Stage4Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const afterimageRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailPositions = useRef<THREE.Vector3[]>([]);

    const afterimages = useMemo(() => Array.from({ length: 5 }, (_, i) => ({
        offset: (i + 1) * 0.3,
        opacity: 0.6 - i * 0.1,
    })), []);

    useMemo(() => {
        trailPositions.current = Array.from({ length: 4 }, () => new THREE.Vector3());
    }, []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 15); // 2x size

        // Jerky discrete movement
        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
        }

        // Phase shift flicker
        const flicker = Math.sin(t * 10 + phase) > 0.8 ? 0.3 : 1;
        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9 * flicker;
        }

        // Afterimages trail behind
        afterimageRefs.current.forEach((img, i) => {
            if (!img) return;
            const a = afterimages[i];
            img.position.z = -a.offset;
            img.scale.setScalar(1 - a.offset * 0.3);
            (img.material as THREE.MeshBasicMaterial).opacity = a.opacity * ease * flicker;
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
                trail.material.opacity = (0.3 - i * 0.07) * ease;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main ghost body */}
            <mesh>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Core */}
            <mesh scale={0.4}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Afterimages */}
            {afterimages.map((a, i) => (
                <mesh key={i} ref={el => afterimageRefs.current[i] = el} scale={1}>
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#9370db" wireframe transparent opacity={0} />
                </mesh>
            ))}
            {/* Ghost trail */}
            {[0, 1, 2, 3].map(i => (
                <mesh
                    key={`trail-${i}`}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.25 - i * 0.04}
                >
                    <tetrahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#4b0082" transparent opacity={0} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 4 Fighter: Dimensional rift with emerging claws
 */
export const Stage4Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const riftMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const clawRefs = useRef<(THREE.Group | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 21); // 2x size

        // Visibility flickering
        const visible = Math.sin(t * 16) > -0.85;
        ref.current.visible = visible;

        // Rift pulsing
        const riftPulse = 0.8 + Math.sin(t * 3 + phase) * 0.2;
        ref.current.children[0].scale.setScalar(riftPulse);

        if (riftMatRef.current) {
            riftMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            riftMatRef.current.opacity = ease * (Math.random() > 0.12 ? 0.85 : 0.3);
        }

        // Claws reaching out
        clawRefs.current.forEach((claw, i) => {
            if (!claw) return;
            const reachCycle = (Math.sin(t * 2 + i * Math.PI / 2 + phase) + 1) / 2;
            claw.scale.y = 0.5 + reachCycle * 0.8;
            claw.position.z = reachCycle * 0.5;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Dimensional rift (torus) */}
            <mesh rotation-x={Math.PI / 2}>
                <torusGeometry args={[1, 0.15, 8, 16]} />
                <meshBasicMaterial ref={riftMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Void core */}
            <mesh scale={0.5}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#4b0082" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Emerging claws */}
            {[0, 1, 2, 3, 4, 5].map(i => {
                const angle = (i / 6) * Math.PI * 2;
                return (
                    <group key={i} ref={el => clawRefs.current[i] = el}
                        position={[Math.cos(angle) * 0.7, Math.sin(angle) * 0.7, 0]}
                        rotation-z={angle + Math.PI / 2}>
                        <mesh scale={[0.1, 0.8, 0.05]}>
                            <coneGeometry args={[1, 1, 4]} />
                            <meshBasicMaterial color="#9370db" wireframe transparent opacity={0.8} />
                        </mesh>
                    </group>
                );
            })}
        </group>
    );
};

/**
 * Stage 4 Elite: Void sentinel with reality-bending aura
 */
export const Stage4Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const auraRefs = useRef<(THREE.Mesh | null)[]>([]);
    const orbRefs = useRef<(THREE.Mesh | null)[]>([]);

    const auraLayers = useMemo(() => [1.5, 2, 2.5], []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.1;
        ref.current.scale.setScalar(ease * 30); // 2x size

        // Random position jitter
        if (Math.random() > 0.97) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
            ref.current.position.y += (Math.random() - 0.5) * 3;
        }

        if (bodyMatRef.current) {
            // Color cycling
            const glitch = Math.random() > 0.92;
            if (glitch) {
                bodyMatRef.current.color.set(['#ffffff', '#9370db'][Math.floor(Math.random() * 2)]);
            } else {
                bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            bodyMatRef.current.opacity = ease * (0.9 + Math.sin(t * 6) * 0.1);
        }

        // Aura layers pulse outward
        auraRefs.current.forEach((aura, i) => {
            if (!aura) return;
            const pulseCycle = (Math.sin(t * 1.5 + i * Math.PI / 2) + 1) / 2;
            const scale = auraLayers[i] + pulseCycle * 0.3;
            aura.scale.setScalar(scale);
            (aura.material as THREE.MeshBasicMaterial).opacity = (0.15 - i * 0.03) * ease;
        });

        // Orbiting void orbs
        orbRefs.current.forEach((orb, i) => {
            if (!orb) return;
            const angle = t * 0.8 + (i * Math.PI / 2);
            const radius = 2;
            orb.position.set(
                Math.cos(angle) * radius,
                Math.sin(t * 2 + i) * 0.5,
                Math.sin(angle) * radius
            );
            orb.rotation.y += delta * 3;

            // Jittering orbs
            if (Math.random() > 0.93) {
                orb.position.x += (Math.random() - 0.5) * 0.4;
                orb.position.y += (Math.random() - 0.5) * 0.4;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Sentinel body */}
            <mesh>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Core eye */}
            <mesh scale={0.4}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.9} />
            </mesh>
            {/* Reality-bending aura layers */}
            {auraLayers.map((scale, i) => (
                <mesh key={i} ref={el => auraRefs.current[i] = el} scale={scale}>
                    <icosahedronGeometry args={[1, 1]} />
                    <meshBasicMaterial color="#9370db" wireframe transparent opacity={0} />
                </mesh>
            ))}
            {/* Void orbs */}
            {[0, 1, 2, 3].map(i => (
                <mesh key={`orb-${i}`} ref={el => orbRefs.current[i] = el} scale={0.3}>
                    <octahedronGeometry args={[1, 0]} />
                    <meshBasicMaterial color="#4b0082" wireframe transparent opacity={0.8} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 4 Boss: Eldritch horror - incomprehensible geometry with many eyes
 */
export const Stage4Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const coreMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const eyeRefs = useRef<(THREE.Group | null)[]>([]);
    const tentacleRefs = useRef<(THREE.Mesh | null)[]>([]);
    const ringRefs = useRef<(THREE.Mesh | null)[]>([]);

    const eyes = useMemo(() => Array.from({ length: 12 }, () => ({
        pos: new THREE.Vector3().randomDirection().multiplyScalar(2 + Math.random()),
        size: 0.2 + Math.random() * 0.3,
        blinkPhase: Math.random() * Math.PI * 2,
    })), []);

    const tentacles = useMemo(() => Array.from({ length: 8 }, (_, i) => ({
        angle: (i / 8) * Math.PI * 2,
        length: 2 + Math.random() * 1.5,
        phase: Math.random() * Math.PI * 2,
    })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Random teleport jitter
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 6;
            ref.current.position.y += (Math.random() - 0.5) * 6;
        }

        ref.current.rotation.y += delta * 0.05;
        ref.current.rotation.x = Math.sin(t * 0.3) * 0.1;
        ref.current.scale.setScalar(ease * 20);

        if (coreMatRef.current) {
            // Color glitching
            const glitch = Math.random() > 0.9;
            if (glitch) {
                coreMatRef.current.color.set(['#ffffff', '#9370db', '#4b0082'][Math.floor(Math.random() * 3)]);
            } else {
                coreMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            coreMatRef.current.opacity = ease * (0.85 + Math.sin(t * 5) * 0.15);
        }

        // Eyes look around and blink
        eyeRefs.current.forEach((eye, i) => {
            if (!eye) return;
            const e = eyes[i];
            const blink = Math.sin(t * 2 + e.blinkPhase) > 0.7 ? 0 : 1;
            eye.scale.setScalar(e.size * blink);
            eye.lookAt(0, 0, 0);
        });

        // Tentacles writhe
        tentacleRefs.current.forEach((tent, i) => {
            if (!tent) return;
            const te = tentacles[i];
            const wave = Math.sin(t * 2 + te.phase) * 0.5;
            tent.rotation.x = wave;
            tent.rotation.z = Math.cos(t * 1.5 + te.phase) * 0.3;
        });

        // Rings rotate
        ringRefs.current.forEach((ring, i) => {
            if (!ring) return;
            ring.rotation.x += delta * (0.3 + i * 0.2);
            ring.rotation.y += delta * (0.2 + i * 0.15);
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Central mass */}
            <mesh>
                <icosahedronGeometry args={[1.5, 2]} />
                <meshBasicMaterial ref={coreMatRef} wireframe transparent opacity={0} />
            </mesh>
            {/* Inner void */}
            <mesh scale={0.8}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#4b0082" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Orbiting rings of impossible geometry */}
            {[2, 2.5, 3].map((size, i) => (
                <mesh key={`ring-${i}`} ref={el => ringRefs.current[i] = el}>
                    <torusGeometry args={[size, 0.08, 6, 16]} />
                    <meshBasicMaterial color={i % 2 === 0 ? "#9370db" : "#ffffff"} wireframe transparent opacity={0.5} />
                </mesh>
            ))}
            {/* Many eyes */}
            {eyes.map((e, i) => (
                <group key={i} ref={el => eyeRefs.current[i] = el} position={e.pos}>
                    <mesh scale={e.size}>
                        <sphereGeometry args={[1, 8, 6]} />
                        <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.9} />
                    </mesh>
                    <mesh scale={e.size * 0.4}>
                        <sphereGeometry args={[1, 6, 4]} />
                        <meshBasicMaterial color="#4b0082" transparent opacity={0.9} />
                    </mesh>
                </group>
            ))}
            {/* Void tentacles */}
            {tentacles.map((te, i) => (
                <mesh key={`tent-${i}`} ref={el => tentacleRefs.current[i] = el}
                    position={[Math.cos(te.angle) * 1.5, -0.5, Math.sin(te.angle) * 1.5]}
                    rotation-z={te.angle}
                    scale={[0.15, te.length, 0.15]}>
                    <cylinderGeometry args={[1, 0.3, 1, 6]} />
                    <meshBasicMaterial color="#9370db" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};
