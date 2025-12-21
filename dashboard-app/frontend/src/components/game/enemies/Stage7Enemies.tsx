import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 7: Ancient/Relic themed - #D4A373, #8C5A3C, #F4E1A6
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#D4A373'; // Sandy tan
    if (healthPct > 0.25) return '#F4E1A6'; // Light gold
    return '#8C5A3C'; // Dark bronze
};

/**
 * Stage 7 Asteroid: Weathered stone monolith with carved glyph lines
 */
export const Stage7Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const glyphRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.12 + Math.random() * 0.15,
        y: 0.08 + Math.random() * 0.1,
        z: 0.05 + Math.random() * 0.08
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

        // Glyphs glow in traveling band
        glyphRefs.current.forEach((glyph, i) => {
            if (!glyph || !(glyph.material instanceof THREE.MeshBasicMaterial)) return;
            const wave = Math.sin(t * 2 - i * 0.5 + data.seed) * 0.5 + 0.5;
            glyph.material.opacity = 0.3 + wave * 0.5;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main monolith chunk */}
            <mesh scale={[1.3, 0.9, 0.8]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={mainMatRef} color="#D4A373" wireframe transparent opacity={0} />
            </mesh>
            {/* Carved glyph lines */}
            {[0, 1, 2, 3].map(i => (
                <mesh
                    key={i}
                    ref={el => glyphRefs.current[i] = el}
                    position={[0, -0.3 + i * 0.2, 0.45]}
                    scale={[0.8 - i * 0.1, 0.05, 0.02]}
                >
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color="#F4E1A6" transparent opacity={0.3} />
                </mesh>
            ))}
            {/* Inner structure */}
            <mesh scale={0.5}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#8C5A3C" wireframe transparent opacity={0.5} />
            </mesh>
        </group>
    );
};

/**
 * Stage 7 Drone: Small pyramid with stepped ziggurat ridges
 */
export const Stage7Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ridgeRefs = useRef<(THREE.Mesh | null)[]>([]);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.rotation.z += delta * 5;
        ref.current.scale.setScalar(ease * 18);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
        }

        // Ridge highlights blink in sequence
        ridgeRefs.current.forEach((ridge, i) => {
            if (!ridge || !(ridge.material instanceof THREE.MeshBasicMaterial)) return;
            const blink = Math.sin(t * 6 + i * 1.5) > 0.5 ? 0.8 : 0.4;
            ridge.material.opacity = blink;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main pyramid with blunt apex */}
            <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[1, 1.8, 4]} />
                <meshBasicMaterial ref={bodyMatRef} color="#D4A373" wireframe transparent opacity={0} />
            </mesh>
            {/* Stepped ziggurat ridges */}
            {[0.3, 0.6, 0.9].map((y, i) => (
                <mesh key={i} ref={el => ridgeRefs.current[i] = el} position={[0, y - 0.5, 0]} scale={[1.1 - i * 0.2, 0.1, 1.1 - i * 0.2]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color="#F4E1A6" transparent opacity={0.4} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 7 Fighter: Double-pyramid with slab wings and obelisk spine
 */
export const Stage7Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingLeftRef = useRef<THREE.Mesh>(null);
    const wingRightRef = useRef<THREE.Mesh>(null);
    const spineMatRef = useRef<THREE.MeshBasicMaterial>(null);

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

        // Wings bob slightly
        const wingBob = Math.sin(t * 2.5 + phase) * 0.08;
        if (wingLeftRef.current) wingLeftRef.current.position.y = wingBob;
        if (wingRightRef.current) wingRightRef.current.position.y = wingBob;

        // Spine glow pulses
        if (spineMatRef.current) {
            spineMatRef.current.opacity = 0.5 + Math.sin(t * 4 + phase) * 0.3;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Double-pyramid body */}
            <mesh rotation={[Math.PI / 2, 0, 0]} scale={[0.6, 1.4, 0.6]}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#D4A373" wireframe transparent opacity={0} />
            </mesh>
            {/* Slab-like wings */}
            <mesh ref={wingLeftRef} position={[-1.2, 0, 0]} scale={[1, 0.15, 0.6]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#8C5A3C" wireframe transparent opacity={0.7} />
            </mesh>
            <mesh ref={wingRightRef} position={[1.2, 0, 0]} scale={[1, 0.15, 0.6]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#8C5A3C" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Central obelisk spine */}
            <mesh position={[0, 0.8, 0]} scale={[0.15, 0.8, 0.15]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={spineMatRef} color="#F4E1A6" transparent opacity={0.5} />
            </mesh>
        </group>
    );
};

/**
 * Stage 7 Elite: Relic core with orbiting square tablets and floating cap
 */
export const Stage7Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const tabletRefs = useRef<(THREE.Mesh | null)[]>([]);
    const capRef = useRef<THREE.Mesh>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.rotation.y += delta * 0.2;
        ref.current.scale.setScalar(ease * 36);

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease;
        }

        // Tablets orbit
        tabletRefs.current.forEach((tablet, i) => {
            if (!tablet) return;
            const angle = t * 0.8 + (i * Math.PI);
            tablet.position.set(Math.cos(angle) * 2, 0, Math.sin(angle) * 2);
            tablet.rotation.y = angle;
        });

        // Cap rises and falls
        if (capRef.current) {
            capRef.current.position.y = 1.5 + Math.sin(t * 1.5) * 0.3;
            capRef.current.rotation.y += delta * 0.5;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Relic core */}
            <mesh scale={[1, 1.2, 1]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={bodyMatRef} color="#D4A373" wireframe transparent opacity={0} />
            </mesh>
            <mesh scale={0.6}>
                <octahedronGeometry args={[1, 0]} />
                <meshBasicMaterial color="#F4E1A6" wireframe transparent opacity={0.7} />
            </mesh>
            {/* Orbiting square tablets */}
            {[0, 1].map(i => (
                <mesh key={i} ref={el => tabletRefs.current[i] = el} scale={[0.6, 0.8, 0.1]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color="#8C5A3C" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
            {/* Floating top cap */}
            <mesh ref={capRef} position={[0, 1.5, 0]} scale={0.5}>
                <coneGeometry args={[1, 0.6, 4]} />
                <meshBasicMaterial color="#F4E1A6" wireframe transparent opacity={0.8} />
            </mesh>
        </group>
    );
};

/**
 * Stage 7 Boss: Massive temple gate frame with layered arches
 */
export const Stage7Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const frameMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const archRefs = useRef<(THREE.Mesh | null)[]>([]);
    const glyphRingRef = useRef<THREE.Mesh>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 15);

        if (frameMatRef.current) {
            frameMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            frameMatRef.current.opacity = ease * 0.8;
        }

        // Arches rotate slowly
        archRefs.current.forEach((arch, i) => {
            if (!arch) return;
            arch.rotation.z += delta * (0.1 + i * 0.05);
        });

        // Center glyph ring spins faster
        if (glyphRingRef.current) {
            glyphRingRef.current.rotation.z += delta * 1.5;
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Main temple gate frame */}
            <mesh scale={[3, 4, 0.5]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial ref={frameMatRef} color="#D4A373" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Hollow center */}
            <mesh scale={[2, 3, 0.6]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#8C5A3C" wireframe transparent opacity={0.4} />
            </mesh>
            {/* Layered arches */}
            {[0, 1, 2].map(i => (
                <mesh
                    key={i}
                    ref={el => archRefs.current[i] = el}
                    rotation={[Math.PI / 2, 0, 0]}
                    scale={1.8 - i * 0.3}
                >
                    <torusGeometry args={[1, 0.1, 4, 8]} />
                    <meshBasicMaterial color="#F4E1A6" wireframe transparent opacity={0.6} />
                </mesh>
            ))}
            {/* Center glyph ring */}
            <mesh ref={glyphRingRef} rotation={[Math.PI / 2, 0, 0]} scale={0.8}>
                <torusGeometry args={[1, 0.15, 6, 12]} />
                <meshBasicMaterial color="#F4E1A6" transparent opacity={0.7} />
            </mesh>
            {/* Corner pillars */}
            {[[-1.8, -2], [1.8, -2], [-1.8, 2], [1.8, 2]].map((pos, i) => (
                <mesh key={i} position={[pos[0], pos[1], 0]} scale={[0.3, 0.8, 0.3]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color="#8C5A3C" wireframe transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};
