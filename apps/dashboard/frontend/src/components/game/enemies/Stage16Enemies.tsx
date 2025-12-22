import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 16: Abyssal/Deep Sea themed - #00008B, #00FFFF, #4682B4
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#00008B'; // DarkBlue
    if (healthPct > 0.25) return '#00FFFF'; // Aqua
    return '#4682B4'; // SteelBlue
};

/**
 * Stage 16 Asteroid: Porous deep-blue rock with flickering bioluminescent spots
 */
export const Stage16Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const spotRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.02 + Math.random() * 0.03,
        y: 0.03 + Math.random() * 0.04,
        z: 0.015 + Math.random() * 0.025
    }), []);

    const spots = useMemo(() =>
        Array.from({ length: 10 }, () => ({
            pos: new THREE.Vector3(
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2,
                (Math.random() - 0.5) * 2
            ).normalize().multiplyScalar(0.95),
            flickerSpeed: 2 + Math.random() * 4,
            phase: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;
        ref.current.scale.setScalar(ease * 36);

        // Occasional teleport jitter
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 5;
            ref.current.position.y += (Math.random() - 0.5) * 5;
        }

        if (mainMatRef.current) {
            mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            mainMatRef.current.opacity = ease * 0.85;
        }

        // Bioluminescent spots flicker randomly
        spotRefs.current.forEach((spot, i) => {
            if (!spot || !(spot.material instanceof THREE.MeshBasicMaterial)) return;
            const flicker = Math.random() > 0.95 ? 0.3 : 1;
            spot.material.opacity = (0.4 + Math.sin(t * spots[i].flickerSpeed + spots[i].phase) * 0.4) * flicker;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Porous dark rock */}
            <mesh>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={mainMatRef} color="#00008B" transparent opacity={0} />
            </mesh>
            {/* Bioluminescent spots */}
            {spots.map((s, i) => (
                <mesh
                    key={i}
                    ref={el => spotRefs.current[i] = el}
                    position={s.pos.toArray()}
                    scale={0.08}
                >
                    <sphereGeometry args={[1, 4, 4]} />
                    <meshBasicMaterial color="#00FFFF" transparent opacity={0.6} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 16 Drone: Jellyfish with pulsing translucent bell and undulating tentacles
 */
export const Stage16Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bellRef = useRef<THREE.Mesh>(null);
    const bellMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const tentacleRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 18);

        // Jerky discrete movement
        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
        }

        // Bell pulses in size
        if (bellRef.current) {
            const pulse = 1 + Math.sin(t * 3) * 0.15;
            bellRef.current.scale.set(pulse, 0.6 + Math.sin(t * 3) * 0.1, pulse);
        }

        if (bellMatRef.current) {
            bellMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bellMatRef.current.opacity = ease * 0.6;
        }

        // Tentacles undulate
        tentacleRefs.current.forEach((tent, i) => {
            if (!tent) return;
            tent.rotation.x = Math.sin(t * 2 + i * 0.5) * 0.3;
            tent.rotation.z = Math.cos(t * 1.5 + i * 0.5) * 0.2;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Translucent bell */}
            <mesh ref={bellRef}>
                <sphereGeometry args={[0.8, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshBasicMaterial ref={bellMatRef} color="#4682B4" transparent opacity={0} side={THREE.DoubleSide} />
            </mesh>
            {/* Aqua tentacles */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh
                    key={i}
                    ref={el => tentacleRefs.current[i] = el}
                    position={[Math.cos(i * Math.PI * 0.4) * 0.3, -0.3, Math.sin(i * Math.PI * 0.4) * 0.3]}
                    scale={[0.05, 1.2, 0.05]}
                >
                    <cylinderGeometry args={[1, 0.3, 1, 6]} />
                    <meshBasicMaterial color="#00FFFF" transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 16 Fighter: Anglerfish with swaying lure and glowing aqua tip
 */
export const Stage16Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const lureRef = useRef<THREE.Group>(null);
    const lureMatRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        // Flicker in and out
        const visible = Math.sin(t * 20) > -0.8;
        ref.current.visible = visible;

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Lure sways hypnotically
        if (lureRef.current) {
            lureRef.current.rotation.z = Math.sin(t * 2) * 0.4;
            lureRef.current.rotation.x = Math.cos(t * 1.5) * 0.2;
        }

        // Lure tip glows
        if (lureMatRef.current) {
            lureMatRef.current.opacity = 0.6 + Math.sin(t * 5) * 0.4;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Rounded anglerfish body */}
            <mesh scale={[1, 0.7, 0.6]}>
                <sphereGeometry args={[0.8, 10, 8]} />
                <meshBasicMaterial ref={bodyMatRef} color="#00008B" transparent opacity={0} />
            </mesh>
            {/* Mouth */}
            <mesh position={[0.5, -0.1, 0]} scale={0.4}>
                <coneGeometry args={[0.8, 0.5, 8]} />
                <meshBasicMaterial color="#000033" transparent opacity={0.8} />
            </mesh>
            {/* Lure stalk and light */}
            <group ref={lureRef} position={[0, 0.5, 0]}>
                <mesh scale={[0.03, 1, 0.03]}>
                    <cylinderGeometry args={[1, 1, 1, 6]} />
                    <meshBasicMaterial color="#4682B4" transparent opacity={0.6} />
                </mesh>
                <mesh position={[0, 0.6, 0]} scale={0.2}>
                    <sphereGeometry args={[1, 8, 6]} />
                    <meshBasicMaterial ref={lureMatRef} color="#00FFFF" transparent opacity={0.8} />
                </mesh>
            </group>
        </group>
    );
};

/**
 * Stage 16 Elite: Nautilus spiral shell with waving glowing tentacles
 */
export const Stage16Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const shellRef = useRef<THREE.Mesh>(null);
    const shellMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const tentacleRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 36);

        // Shell rotates slowly
        if (shellRef.current) {
            shellRef.current.rotation.z += delta * 0.3;
        }

        if (shellMatRef.current) {
            // Rapid color cycling
            const phase = Math.floor(t * 8) % 3;
            shellMatRef.current.color.set(['#00008B', '#00FFFF', '#4682B4'][phase]);
            shellMatRef.current.opacity = ease * 0.8 * (Math.random() > 0.1 ? 1 : 0.3);
        }

        // Tentacles wave slowly
        tentacleRefs.current.forEach((tent, i) => {
            if (!tent) return;
            tent.rotation.x = Math.sin(t * 1.5 + i * 0.3) * 0.4;
            tent.rotation.z = Math.cos(t + i * 0.3) * 0.2;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Spiral shell (approximated with torus) */}
            <mesh ref={shellRef} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[1, 0.5, 8, 16, Math.PI * 1.5]} />
                <meshBasicMaterial ref={shellMatRef} color="#4682B4" transparent opacity={0} />
            </mesh>
            {/* Shell details */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={0.7}>
                <torusGeometry args={[0.7, 0.3, 6, 12, Math.PI * 1.5]} />
                <meshBasicMaterial color="#00008B" transparent opacity={0.6} />
            </mesh>
            {/* Glowing tentacles */}
            {[0, 1, 2, 3, 4, 5].map(i => (
                <mesh
                    key={i}
                    ref={el => tentacleRefs.current[i] = el}
                    position={[-1.2 + i * 0.15, -0.3 - i * 0.1, 0]}
                    scale={[0.06, 0.8 - i * 0.1, 0.06]}
                >
                    <cylinderGeometry args={[1, 0.5, 1, 6]} />
                    <meshBasicMaterial color="#00FFFF" transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 16 Boss: Kraken with massive body, glowing eyes, and writhing tentacles
 */
export const Stage16Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const eyeMatRefs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);
    const tentacleGroupRefs = useRef<(THREE.Group | null)[]>([]);

    const tentacles = useMemo(() =>
        Array.from({ length: 8 }, (_, i) => ({
            angle: (i / 8) * Math.PI * 2,
            length: 4,
            segments: 5,
            phase: Math.random() * Math.PI * 2
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        // Fast-forward teleport effect
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 10;
        }

        // Fast-forward teleport effect
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 10;
        }

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Eyes glow menacingly
        eyeMatRefs.current.forEach((eye) => {
            if (!eye) return;
            eye.opacity = 0.7 + Math.sin(t * 3) * 0.3;
        });

        // Tentacles writhe
        tentacleGroupRefs.current.forEach((group, i) => {
            if (!group) return;
            group.rotation.x = Math.sin(t * 1.5 + tentacles[i].phase) * 0.3;
            group.rotation.z = Math.cos(t + tentacles[i].phase) * 0.2;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Massive body */}
            <mesh scale={[2.5, 2, 2]}>
                <icosahedronGeometry args={[1, 1]} />
                <meshBasicMaterial ref={bodyMatRef} color="#00008B" transparent opacity={0} />
            </mesh>
            {/* Glowing eyes */}
            <mesh position={[-0.8, 0.5, 1.5]} scale={0.4}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial ref={el => eyeMatRefs.current[0] = el} color="#00FFFF" transparent opacity={0.8} />
            </mesh>
            <mesh position={[0.8, 0.5, 1.5]} scale={0.4}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial ref={el => eyeMatRefs.current[1] = el} color="#00FFFF" transparent opacity={0.8} />
            </mesh>
            {/* Writhing tentacles */}
            {tentacles.map((tent, i) => (
                <group
                    key={i}
                    ref={el => tentacleGroupRefs.current[i] = el}
                    position={[
                        Math.cos(tent.angle) * 1.5,
                        -1.5,
                        Math.sin(tent.angle) * 1.5
                    ]}
                    rotation={[0.5, tent.angle, 0]}
                >
                    {Array.from({ length: tent.segments }).map((_, j) => (
                        <mesh
                            key={j}
                            position={[0, -j * 0.8, 0]}
                            scale={[0.3 - j * 0.04, 0.8, 0.3 - j * 0.04]}
                        >
                            <capsuleGeometry args={[1, 0.5, 4, 8]} />
                            <meshBasicMaterial color="#4682B4" transparent opacity={0.7 - j * 0.08} />
                        </mesh>
                    ))}
                    {/* Glowing suckers */}
                    {Array.from({ length: 3 }).map((_, j) => (
                        <mesh key={`s${j}`} position={[0.2, -j * 1.2, 0]} scale={0.1}>
                            <sphereGeometry args={[1, 4, 4]} />
                            <meshBasicMaterial color="#00FFFF" transparent opacity={0.6} />
                        </mesh>
                    ))}
                </group>
            ))}
        </group>
    );
};
