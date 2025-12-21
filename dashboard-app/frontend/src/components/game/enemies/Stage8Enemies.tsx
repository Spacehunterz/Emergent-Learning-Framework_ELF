import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 8: Swarm/Insect themed - #9DFF57, #2E8F5A, #F4FF8A
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#9DFF57'; // Bright green
    if (healthPct > 0.25) return '#F4FF8A'; // Yellow-green
    return '#2E8F5A'; // Dark green
};

/**
 * Stage 8 Asteroid: Gnawed hive-rock with honeycomb cuts
 */
export const Stage8Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const honeycombRef = useRef<THREE.Group>(null);

    const rotSpeed = useMemo(() => ({
        x: 0.1 + Math.random() * 0.15,
        y: 0.12 + Math.random() * 0.1,
        z: 0.08 + Math.random() * 0.1
    }), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.x += rotSpeed.x * delta;
        ref.current.rotation.y += rotSpeed.y * delta;
        ref.current.rotation.z += rotSpeed.z * delta;
        ref.current.scale.setScalar(ease * 36);

        if (mainMatRef.current) {
            mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            mainMatRef.current.opacity = ease * 0.9;
        }

        // Honeycomb pulses like breathing
        if (honeycombRef.current) {
            const breathe = 1 + Math.sin(t * 2 + data.seed) * 0.1;
            honeycombRef.current.scale.setScalar(breathe);
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main hive-rock */}
            <mesh>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={mainMatRef} color="#9DFF57" wireframe transparent opacity={0} />
            </mesh>
            {/* Honeycomb structure */}
            <group ref={honeycombRef}>
                {Array.from({ length: 7 }).map((_, i) => {
                    const angle = (i / 7) * Math.PI * 2;
                    return (
                        <mesh key={i} position={[Math.cos(angle) * 0.6, Math.sin(angle) * 0.6, 0]} scale={0.25}>
                            <cylinderGeometry args={[1, 1, 0.3, 6]} />
                            <meshBasicMaterial color="#F4FF8A" wireframe transparent opacity={0.6} />
                        </mesh>
                    );
                })}
            </group>
            {/* Spike nodules */}
            {[[0.8, 0.3, 0.5], [-0.7, -0.4, 0.6], [0.3, 0.7, -0.6]].map((pos, i) => (
                <mesh key={i} position={pos as [number, number, number]} scale={[0.15, 0.4, 0.15]}>
                    <coneGeometry args={[1, 1, 4]} />
                    <meshBasicMaterial color="#2E8F5A" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 8 Drone: Sharp pyramid with antenna spines
 */
export const Stage8Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const antennaRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.rotation.z += delta * 7; // Quick darting spin
        ref.current.scale.setScalar(ease * 18);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Antenna tips flicker
        antennaRefs.current.forEach((ant, i) => {
            if (!ant || !(ant.material instanceof THREE.MeshBasicMaterial)) return;
            ant.material.opacity = 0.5 + Math.sin(t * 10 + i * 3) * 0.4;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main pyramid */}
            <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[1, 2, 4]} />
                <meshBasicMaterial ref={bodyMatRef} color="#9DFF57" wireframe transparent opacity={0} />
            </mesh>
            {/* Segmented base ring */}
            <mesh position={[0, 0.5, 0]} rotation={[Math.PI / 2, 0, 0]} scale={1.1}>
                <torusGeometry args={[1, 0.08, 4, 8]} />
                <meshBasicMaterial color="#2E8F5A" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Antenna spines */}
            <mesh ref={el => antennaRefs.current[0] = el} position={[-0.5, 1.2, 0]} rotation={[0, 0, 0.3]} scale={[0.05, 0.6, 0.05]}>
                <cylinderGeometry args={[1, 0.3, 1, 4]} />
                <meshBasicMaterial color="#F4FF8A" transparent opacity={0.5} />
            </mesh>
            <mesh ref={el => antennaRefs.current[1] = el} position={[0.5, 1.2, 0]} rotation={[0, 0, -0.3]} scale={[0.05, 0.6, 0.05]}>
                <cylinderGeometry args={[1, 0.3, 1, 4]} />
                <meshBasicMaterial color="#F4FF8A" transparent opacity={0.5} />
            </mesh>
        </group>
    );
};

/**
 * Stage 8 Fighter: Double-pyramid thorax with blade wings and stinger
 */
export const Stage8Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);
    const stingerMatRef = useRef<THREE.MeshBasicMaterial>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const phase = data.seed * Math.PI * 2;
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 24);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease;
        }

        // Wings vibrate
        const wingVibrate = Math.sin(t * 20 + phase) * 0.05;
        if (wingLeftRef.current) wingLeftRef.current.rotation.z = -0.5 + wingVibrate;
        if (wingRightRef.current) wingRightRef.current.rotation.z = 0.5 - wingVibrate;

        // Stinger pulses brighter on lunges
        if (stingerMatRef.current) {
            stingerMatRef.current.opacity = 0.6 + Math.sin(t * 6 + phase) * 0.3;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Thorax body */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={[0.5, 1.3, 0.5]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#9DFF57" wireframe transparent opacity={0} />
            </mesh>
            {/* Blade-like wings */}
            <mesh ref={wingLeftRef} position={[-0.8, 0, 0]} rotation={[0, 0, -0.5]} scale={[1.4, 0.05, 0.5]}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#F4FF8A" wireframe transparent opacity={0.7} />
            </mesh>
            <mesh ref={wingRightRef} position={[0.8, 0, 0]} rotation={[0, 0, 0.5]} scale={[1.4, 0.05, 0.5]}>
                <tetrahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#F4FF8A" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Stinger tail */}
            <mesh position={[0, 0, 1.2]} rotation={[Math.PI / 2, 0, 0]} scale={[0.12, 0.8, 0.12]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial ref={stingerMatRef} color="#2E8F5A" wireframe transparent opacity={0.6} />
            </mesh>
        </group>
    );
};

/**
 * Stage 8 Elite: Beetle-like core with orbiting larva spheres
 */
export const Stage8Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const larvaRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.3;
        ref.current.scale.setScalar(ease * 36);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            // Core glow beats rapidly
            bodyMatRef.current.opacity = 0.6 + Math.sin(t * 6 + data.seed) * 0.25;
        }

        // Larvae orbit in staggered loop
        larvaRefs.current.forEach((larva, i) => {
            if (!larva) return;
            const offset = i * (Math.PI / 2);
            const angle = t * 1.2 + offset;
            const radius = 2 + Math.sin(t * 0.5 + i) * 0.3;
            larva.position.set(
                Math.cos(angle) * radius,
                Math.sin(t * 2 + i) * 0.5,
                Math.sin(angle) * radius
            );
            larva.rotation.x += delta * 3;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Beetle-like core */}
            <mesh scale={[1.2, 0.8, 1]}>
                <dodecahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#9DFF57" wireframe transparent opacity={0.6} />
            </mesh>
            {/* Shell segments */}
            <mesh position={[0, 0.5, 0]} scale={[1, 0.3, 0.8]}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#2E8F5A" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Orbiting larva spheres */}
            {[0, 1, 2, 3].map(i => (
                <mesh key={i} ref={el => larvaRefs.current[i] = el} scale={0.35}>
                    <sphereGeometry args={[1, 6, 6]} />
                    <meshBasicMaterial color="#F4FF8A" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 8 Boss: Queen-carapace frame with ribbed dome and mandible spikes
 */
export const Stage8Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const domeMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ribRefs = useRef<(THREE.Mesh | null)[]>([]);
    const mandibleRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        if (domeMatRef.current) {
            domeMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            domeMatRef.current.opacity = ease * 0.8;
        }

        // Rib segments ripple
        ribRefs.current.forEach((rib, i) => {
            if (!rib) return;
            const ripple = 1 + Math.sin(t * 3 - i * 0.4) * 0.1;
            rib.scale.x = ripple;
        });

        // Mandible spikes oscillate
        mandibleRefs.current.forEach((mand, i) => {
            if (!mand) return;
            const osc = Math.sin(t * 2) * 0.3;
            mand.rotation.z = (i === 0 ? 0.5 : -0.5) + osc * (i === 0 ? 1 : -1);
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Queen carapace dome */}
            <mesh scale={[2.5, 2, 2.5]}>
                <sphereGeometry args={[1, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshBasicMaterial ref={domeMatRef} color="#9DFF57" wireframe transparent opacity={0.8} side={THREE.DoubleSide} />
            </mesh>
            {/* Rib segments */}
            {Array.from({ length: 8 }).map((_, i) => {
                const angle = (i / 8) * Math.PI;
                return (
                    <mesh
                        key={i}
                        ref={el => ribRefs.current[i] = el}
                        position={[0, 0.5, 0]}
                        rotation={[0, angle, 0]}
                        scale={[2.5, 0.1, 0.1]}
                    >
                        <boxGeometry args={[1, 1, 1]} />
                        <meshBasicMaterial color="#2E8F5A" wireframe transparent opacity={0.6} />
                    </mesh>
                );
            })}
            {/* Mandible spikes */}
            <mesh ref={el => mandibleRefs.current[0] = el} position={[-1.5, -0.5, -2]} rotation={[0.5, 0, 0.5]} scale={[0.3, 0.3, 1.5]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial color="#F4FF8A" wireframe transparent opacity={0.8} />
            </mesh>
            <mesh ref={el => mandibleRefs.current[1] = el} position={[1.5, -0.5, -2]} rotation={[0.5, 0, -0.5]} scale={[0.3, 0.3, 1.5]}>
                <coneGeometry args={[1, 1, 4]} />
                <meshBasicMaterial color="#F4FF8A" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Inner core */}
            <mesh scale={1}>
                <icosahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#F4FF8A" wireframe transparent opacity={0.5} />
            </mesh>
        </group>
    );
};
