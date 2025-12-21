import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 10: Cosmic/Nebula themed - #7A5CFF, #FF5FBE, #48D1FF
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#7A5CFF'; // Purple
    if (healthPct > 0.25) return '#FF5FBE'; // Pink
    return '#48D1FF'; // Cyan
};

/**
 * Stage 10 Asteroid: Floating void rock with starfield speckle lines
 */
export const Stage10Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const speckleRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.08 + Math.random() * 0.1,
        y: 0.1 + Math.random() * 0.12,
        z: 0.06 + Math.random() * 0.08
    }), []);

    const speckles = useMemo(() =>
        Array.from({ length: 12 }, () => ({
            pos: new THREE.Vector3(
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2
            ).normalize().multiplyScalar(0.8 + Math.random() * 0.3),
            phase: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Occasional teleport jitter
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 4;
            ref.current.position.y += (Math.random() - 0.5) * 4;
        }

        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;
        ref.current.scale.setScalar(ease * 36);

        if (mainMatRef.current) {
            // Random color flashing between stage colors
            const glitch = Math.random() > 0.92;
            if (glitch) {
                mainMatRef.current.color.set(['#7A5CFF', '#FF5FBE', '#48D1FF'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            mainMatRef.current.opacity = ease * (glitch ? 0.5 : 0.85);
        }

        // Speckle glow drifts and jitters
        speckleRefs.current.forEach((speckle, i) => {
            if (!speckle || !(speckle.material instanceof THREE.MeshBasicMaterial)) return;
            const drift = Math.sin(t * 0.5 + speckles[i].phase) * 0.5 + 0.5;
            speckle.material.opacity = 0.3 + drift * 0.6;
            // Random jitter
            if (Math.random() > 0.95) {
                speckle.position.x = speckles[i].pos.x + (Math.random() - 0.5) * 0.2;
                speckle.position.y = speckles[i].pos.y + (Math.random() - 0.5) * 0.2;
                speckle.position.z = speckles[i].pos.z + (Math.random() - 0.5) * 0.2;
            } else {
                speckle.position.copy(speckles[i].pos);
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main void rock */}
            <mesh>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={mainMatRef} color="#7A5CFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Hollow center */}
            <mesh scale={0.5}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#48D1FF" wireframe transparent opacity={0.4} />
            </mesh>
            {/* Starfield speckles */}
            {speckles.map((s, i) => (
                <mesh
                    key={i}
                    ref={el => speckleRefs.current[i] = el}
                    position={s.pos.toArray()}
                    scale={0.08}
                >
                    <sphereGeometry args={[1, 4, 4]} />
                    <meshBasicMaterial color="#ffffff" transparent opacity={0.3} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 10 Drone: Sleek pyramid with halo ring and trailing spikes
 */
export const Stage10Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const haloRef = useRef<THREE.Mesh>(null);
    const spikeRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailRefs = useRef<(THREE.Mesh | null)[]>([]);
    const trailPositions = useRef<THREE.Vector3[]>([]);

    useMemo(() => {
        trailPositions.current = Array.from({ length: 5 }, () => new THREE.Vector3());
    }, []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);

        // Jerky discrete movement
        if (Math.random() > 0.96) {
            ref.current.position.x += (Math.random() - 0.5) * 2;
        }

        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 18);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Halo spins
        if (haloRef.current) {
            haloRef.current.rotation.z += delta * 4;
        }

        // Spikes pulse in comet-like sequence
        spikeRefs.current.forEach((spike, i) => {
            if (!spike || !(spike.material instanceof THREE.MeshBasicMaterial)) return;
            const pulse = Math.sin(t * 6 - i * 0.8) * 0.4 + 0.6;
            spike.material.opacity = pulse;
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
                trail.material.opacity = 0.4 - i * 0.08;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Sleek pyramid */}
            <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[0.8, 2.5, 4]} />
                <meshBasicMaterial ref={bodyMatRef} color="#7A5CFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Thin halo ring */}
            <mesh ref={haloRef} rotation={[Math.PI / 2, 0, 0]} scale={1.2}>
                <torusGeometry args={[1, 0.04, 8, 16]} />
                <meshBasicMaterial color="#FF5FBE" transparent opacity={0.7} />
            </mesh>
            {/* Trailing vertex spikes */}
            {[0, 1, 2].map(i => (
                <mesh
                    key={i}
                    ref={el => spikeRefs.current[i] = el}
                    position={[0, 0.8 + i * 0.4, 0]}
                    scale={[0.1, 0.3, 0.1]}
                >
                    <coneGeometry args={[1, 1, 4]} />
                    <meshBasicMaterial color="#48D1FF" transparent opacity={0.6} />
                </mesh>
            ))}
            {/* Ghost trail */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh
                    key={`trail-${i}`}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.3 - i * 0.04}
                    rotation={[Math.PI, 0, 0]}
                >
                    <coneGeometry args={[0.8, 2.5, 4]} />
                    <meshBasicMaterial color="#FF5FBE" transparent opacity={0.3} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 10 Fighter: Double-pyramid with crescent wings and prismatic tail
 */
export const Stage10Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);
    const tailMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const colorPhase = useRef(0);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        // Flicker in and out
        const visible = Math.sin(t * 18) > -0.8;
        ref.current.visible = visible;

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * (Math.random() > 0.1 ? 1 : 0.4);
        }

        // Wings sweep back
        const wingSweep = Math.sin(t * 2 + phase) * 0.1;
        if (wingLeftRef.current) wingLeftRef.current.rotation.y = 0.3 + wingSweep;
        if (wingRightRef.current) wingRightRef.current.rotation.y = -0.3 - wingSweep;

        // Tail fin cycles through palette hues
        if (tailMatRef.current) {
            colorPhase.current += delta * 2;
            const hue = (Math.sin(colorPhase.current) + 1) / 2;
            if (hue < 0.33) tailMatRef.current.color.set('#7A5CFF');
            else if (hue < 0.66) tailMatRef.current.color.set('#FF5FBE');
            else tailMatRef.current.color.set('#48D1FF');
            tailMatRef.current.opacity = 0.7 + Math.sin(t * 3) * 0.2;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Double-pyramid body */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={[0.5, 1.5, 0.5]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#7A5CFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Crescent wings */}
            <mesh ref={wingLeftRef} position={[-0.8, 0, 0]} rotation={[0, 0.3, 0]} scale={[1.2, 0.1, 0.8]}>
                <torusGeometry args={[1, 0.3, 4, 8, Math.PI]} />
                <meshBasicMaterial color="#FF5FBE" wireframe transparent opacity={0.7} side={THREE.DoubleSide} />
            </mesh>
            <mesh ref={wingRightRef} position={[0.8, 0, 0]} rotation={[0, -0.3, Math.PI]} scale={[1.2, 0.1, 0.8]}>
                <torusGeometry args={[1, 0.3, 4, 8, Math.PI]} />
                <meshBasicMaterial color="#FF5FBE" wireframe transparent opacity={0.7} side={THREE.DoubleSide} />
            </mesh>
            {/* Prismatic tail fin */}
            <mesh position={[0, 0, 1]} rotation={[0, 0, 0]} scale={[0.4, 0.6, 0.1]}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={tailMatRef} color="#48D1FF" wireframe transparent opacity={0.7} />
            </mesh>
        </group>
    );
};

/**
 * Stage 10 Elite: Orb core with three tilted orbiting rings
 */
export const Stage10Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ringRefs = useRef<(THREE.Mesh | null)[]>([]);

    const ringData = useMemo(() => [
        { tiltX: 0.3, tiltZ: 0, speed: 1 },
        { tiltX: -0.5, tiltZ: 0.4, speed: 0.7 },
        { tiltX: 0.1, tiltZ: -0.6, speed: 1.3 }
    ], []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 36);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            // Core brightens in slow swell
            bodyMatRef.current.opacity = 0.5 + Math.sin(t * 1.5 + data.seed) * 0.3;
        }

        // Rings orbit at different speeds
        ringRefs.current.forEach((ring, i) => {
            if (!ring) return;
            ring.rotation.z += delta * ringData[i].speed;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Orb core */}
            <mesh>
                <sphereGeometry args={[1, 16, 12]} />
                <meshBasicMaterial ref={bodyMatRef} color="#7A5CFF" wireframe transparent opacity={0.5} />
            </mesh>
            <mesh scale={0.6}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#FF5FBE" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Three tilted orbiting rings */}
            {ringData.map((rd, i) => (
                <mesh
                    key={i}
                    ref={el => ringRefs.current[i] = el}
                    rotation={[rd.tiltX, 0, rd.tiltZ]}
                    scale={1.8 + i * 0.3}
                >
                    <torusGeometry args={[1, 0.05, 8, 24]} />
                    <meshBasicMaterial color={['#7A5CFF', '#FF5FBE', '#48D1FF'][i]} transparent opacity={0.6} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 10 Boss: Towering nebula lattice with layered poly-spheres and star cage
 */
export const Stage10Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const latticeMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const layerRefs = useRef<(THREE.Mesh | null)[]>([]);
    const starCageMatRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        if (latticeMatRef.current) {
            latticeMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            latticeMatRef.current.opacity = ease * 0.7;
        }

        // Layers rotate in opposing directions
        layerRefs.current.forEach((layer, i) => {
            if (!layer) return;
            layer.rotation.x += delta * (i % 2 === 0 ? 0.3 : -0.2);
            layer.rotation.y += delta * (i % 2 === 0 ? -0.2 : 0.4);
        });

        // Star cage pulses and flickers like heartbeat
        if (starCageMatRef.current) {
            const heartbeat = Math.sin(t * 4) > 0.7 ? 1 : 0.5 + Math.sin(t * 2) * 0.3;
            starCageMatRef.current.opacity = heartbeat;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Nebula lattice outer */}
            <mesh scale={3.5}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={latticeMatRef} color="#7A5CFF" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Layered poly-spheres */}
            <mesh ref={el => layerRefs.current[0] = el} scale={2.5}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#FF5FBE" wireframe transparent opacity={0.5} />
            </mesh>
            <mesh ref={el => layerRefs.current[1] = el} scale={1.8}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#48D1FF" wireframe transparent opacity={0.6} />
            </mesh>
            <mesh ref={el => layerRefs.current[2] = el} scale={1.2}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#FF5FBE" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Central star cage */}
            <mesh scale={0.7}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={starCageMatRef} color="#ffffff" wireframe transparent opacity={0.5} />
            </mesh>
            {/* Outer star points */}
            {Array.from({ length: 8 }).map((_, i) => {
                const phi = Math.acos(-1 + (2 * i) / 8);
                const theta = Math.sqrt(8 * Math.PI) * phi;
                return (
                    <mesh
                        key={i}
                        position={[
                            Math.cos(theta) * Math.sin(phi) * 3,
                            Math.sin(theta) * Math.sin(phi) * 3,
                            Math.cos(phi) * 3
                        ]}
                        scale={0.3}
                    >
                        <octahedronGeometry args={[1, 0]} />
                        <meshBasicMaterial color="#48D1FF" wireframe transparent opacity={0.6} />
                    </mesh>
                );
            })}
        </group>
    );
};
