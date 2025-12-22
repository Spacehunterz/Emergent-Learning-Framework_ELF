import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 15: Fungal/Spore themed - #D2691E, #FF7F50, #A0522D
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#D2691E'; // Chocolate
    if (healthPct > 0.25) return '#FF7F50'; // Coral
    return '#A0522D'; // Sienna
};

/**
 * Stage 15 Asteroid: Lumpy brown sphere with coral mushroom caps, spore puffs
 */
export const Stage15Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const capRefs = useRef<(THREE.Group | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.03 + Math.random() * 0.04,
        y: 0.04 + Math.random() * 0.05,
        z: 0.02 + Math.random() * 0.03
    }), []);

    const mushrooms = useMemo(() =>
        Array.from({ length: 4 }, () => ({
            pos: new THREE.Vector3(
                (Math.random() - 0.5) * 1.5,
                (Math.random() - 0.5) * 1.5,
                (Math.random() - 0.5) * 1.5
            ).normalize().multiplyScalar(0.9),
            scale: 0.15 + Math.random() * 0.1,
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
            // Random color flashing
            const glitch = Math.random() > 0.9;
            if (glitch) {
                mainMatRef.current.color.set(['#D2691E', '#FF7F50', '#A0522D'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            mainMatRef.current.opacity = ease * (glitch ? 0.5 : 0.85);
        }

        // Mushroom caps wobble with jitter
        capRefs.current.forEach((cap, i) => {
            if (!cap) return;
            cap.rotation.x = Math.sin(t * 2 + mushrooms[i].phase) * 0.1;

            // Jitter positions
            if (Math.random() > 0.9) {
                const m = mushrooms[i];
                cap.position.x = m.pos.x + (Math.random() - 0.5) * 0.2;
                cap.position.y = m.pos.y + (Math.random() - 0.5) * 0.2;
                cap.position.z = m.pos.z + (Math.random() - 0.5) * 0.2;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Lumpy organic core */}
            <mesh>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial ref={mainMatRef} color="#D2691E" transparent opacity={0} />
            </mesh>
            {/* Mushroom growths */}
            {mushrooms.map((m, i) => (
                <group
                    key={i}
                    ref={el => capRefs.current[i] = el}
                    position={m.pos.toArray()}
                    scale={m.scale}
                >
                    {/* Stem */}
                    <mesh position={[0, -0.3, 0]}>
                        <cylinderGeometry args={[0.2, 0.3, 0.6, 6]} />
                        <meshBasicMaterial color="#A0522D" transparent opacity={0.8} />
                    </mesh>
                    {/* Cap */}
                    <mesh>
                        <sphereGeometry args={[0.6, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2]} />
                        <meshBasicMaterial color="#FF7F50" transparent opacity={0.85} />
                    </mesh>
                </group>
            ))}
        </group>
    );
};

/**
 * Stage 15 Drone: Single wobbly mushroom with coral cap and sienna stem
 */
export const Stage15Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const capMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const capRef = useRef<THREE.Mesh>(null);
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
        ref.current.lookAt(0, 0, 0);
        ref.current.scale.setScalar(ease * 18);

        // Wobbly movement with jerky discrete jumps
        ref.current.rotation.z = Math.sin(t * 3) * 0.15;
        ref.current.rotation.x = Math.cos(t * 2.5) * 0.1;

        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
        }

        if (capMatRef.current) {
            capMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            capMatRef.current.opacity = ease * 0.9;
        }

        // Cap pulses slightly
        if (capRef.current) {
            capRef.current.scale.setScalar(1 + Math.sin(t * 4) * 0.05);
        }

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
            {/* Ghost trail */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh
                    key={i}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.4 - i * 0.05}
                >
                    <sphereGeometry args={[0.8, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2]} />
                    <meshBasicMaterial color="#A0522D" transparent opacity={0.3} />
                </mesh>
            ))}
            {/* Sienna stem */}
            <mesh position={[0, -0.5, 0]}>
                <cylinderGeometry args={[0.2, 0.35, 1, 8]} />
                <meshBasicMaterial color="#A0522D" transparent opacity={0.85} />
            </mesh>
            {/* Coral cap with spots */}
            <mesh ref={capRef}>
                <sphereGeometry args={[0.8, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshBasicMaterial ref={capMatRef} color="#FF7F50" transparent opacity={0} />
            </mesh>
            {/* Brown spots on cap */}
            {[0, 1, 2, 3].map(i => (
                <mesh
                    key={i}
                    position={[
                        Math.cos(i * Math.PI / 2) * 0.4,
                        0.2,
                        Math.sin(i * Math.PI / 2) * 0.4
                    ]}
                    scale={0.12}
                >
                    <sphereGeometry args={[1, 6, 4]} />
                    <meshBasicMaterial color="#8B4513" transparent opacity={0.7} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 15 Fighter: Slug-like body with pulsating coral sacs
 */
export const Stage15Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const sacRefs = useRef<(THREE.Mesh | null)[]>([]);

    const sacs = useMemo(() => [
        { pos: [-0.5, 0.2, 0], phase: 0 },
        { pos: [0, 0.25, 0], phase: 1 },
        { pos: [0.5, 0.2, 0], phase: 2 },
        { pos: [-0.3, 0.15, 0.3], phase: 0.5 },
        { pos: [0.3, 0.15, 0.3], phase: 1.5 }
    ], []);

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
            bodyMatRef.current.opacity = ease * (Math.random() > 0.1 ? 0.85 : 0.3);
        }

        // Sacs inflate and deflate rhythmically
        sacRefs.current.forEach((sac, i) => {
            if (!sac) return;
            const inflate = 0.8 + Math.sin(t * 2 + sacs[i].phase) * 0.3;
            sac.scale.setScalar(0.2 * inflate);
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Slug body */}
            <mesh rotation={[0, 0, Math.PI / 2]} scale={[0.4, 1.2, 0.35]}>
                <capsuleGeometry args={[1, 1, 8, 12]} />
                <meshBasicMaterial ref={bodyMatRef} color="#D2691E" transparent opacity={0} />
            </mesh>
            {/* Pulsating coral sacs */}
            {sacs.map((s, i) => (
                <mesh
                    key={i}
                    ref={el => sacRefs.current[i] = el}
                    position={s.pos as [number, number, number]}
                    scale={0.2}
                >
                    <sphereGeometry args={[1, 8, 6]} />
                    <meshBasicMaterial color="#FF7F50" transparent opacity={0.8} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 15 Elite: Brown icosahedron core with spreading root tendrils and glowing spore pods
 */
export const Stage15Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const coreMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const podRefs = useRef<(THREE.Mesh | null)[]>([]);
    const rootGroupRef = useRef<THREE.Group>(null);

    const roots = useMemo(() =>
        Array.from({ length: 6 }, (_, i) => ({
            angle: (i / 6) * Math.PI * 2,
            length: 1.5 + Math.random() * 0.5
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 36);

        if (coreMatRef.current) {
            // Rapid color cycling
            const phase = Math.floor(t * 8) % 3;
            coreMatRef.current.color.set(['#D2691E', '#FF7F50', '#A0522D'][phase]);
            coreMatRef.current.opacity = ease * (Math.random() > 0.1 ? 0.8 : 0.3);
        }

        // Roots sway slightly
        if (rootGroupRef.current) {
            rootGroupRef.current.rotation.y += delta * 0.3;
        }

        // Pods pulse with light and jitter
        podRefs.current.forEach((pod, i) => {
            if (!pod || !(pod.material instanceof THREE.MeshBasicMaterial)) return;
            pod.material.opacity = 0.5 + Math.sin(t * 3 + i) * 0.4;
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Central core */}
            <mesh>
                <icosahedronGeometry args={[0.8, 0]} />
                <meshBasicMaterial ref={coreMatRef} color="#D2691E" transparent opacity={0} />
            </mesh>
            {/* Root web with pods */}
            <group ref={rootGroupRef}>
                {roots.map((r, i) => (
                    <group key={i} rotation={[0, r.angle, 0]}>
                        {/* Root tendril */}
                        <mesh position={[r.length / 2, 0, 0]} rotation={[0, 0, Math.PI / 2]} scale={[0.08, r.length, 0.08]}>
                            <cylinderGeometry args={[1, 0.5, 1, 6]} />
                            <meshBasicMaterial color="#A0522D" transparent opacity={0.7} />
                        </mesh>
                        {/* Glowing pod at end */}
                        <mesh
                            ref={el => podRefs.current[i] = el}
                            position={[r.length, 0, 0]}
                            scale={0.25}
                        >
                            <sphereGeometry args={[1, 8, 6]} />
                            <meshBasicMaterial color="#FF7F50" transparent opacity={0.7} />
                        </mesh>
                    </group>
                ))}
            </group>
        </group>
    );
};

/**
 * Stage 15 Boss: Colossal mushroom with huge cap that tilts and releases spore clouds
 */
export const Stage15Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const capRef = useRef<THREE.Mesh>(null);
    const capMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const sporeRefs = useRef<(THREE.Mesh | null)[]>([]);

    const spores = useMemo(() =>
        Array.from({ length: 15 }, () => ({
            basePos: new THREE.Vector3(
                (Math.random() - 0.5) * 4,
                Math.random() * 2,
                (Math.random() - 0.5) * 4
            ),
            speed: 0.5 + Math.random() * 0.5,
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

        // Cap tilts periodically
        if (capRef.current) {
            capRef.current.rotation.x = Math.sin(t * 0.5) * 0.15;
            capRef.current.rotation.z = Math.cos(t * 0.4) * 0.1;
        }

        if (capMatRef.current) {
            capMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            capMatRef.current.opacity = ease * (Math.random() > 0.1 ? 0.9 : 0.4);
        }

        // Spores drift upward
        sporeRefs.current.forEach((spore, i) => {
            if (!spore) return;
            const s = spores[i];
            spore.position.y = s.basePos.y + ((t * s.speed) % 3);
            spore.position.x = s.basePos.x + Math.sin(t + s.phase) * 0.3;
            spore.position.z = s.basePos.z + Math.cos(t + s.phase) * 0.3;
            if (spore.material instanceof THREE.MeshBasicMaterial) {
                spore.material.opacity = 0.3 + Math.sin(t * 2 + s.phase) * 0.2;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Massive stem */}
            <mesh position={[0, -1.5, 0]} scale={[1, 2, 1]}>
                <cylinderGeometry args={[0.8, 1.2, 2, 12]} />
                <meshBasicMaterial color="#A0522D" transparent opacity={0.85} />
            </mesh>
            {/* Huge cap */}
            <group ref={capRef}>
                <mesh scale={[3.5, 1.2, 3.5]}>
                    <sphereGeometry args={[1, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
                    <meshBasicMaterial ref={capMatRef} color="#FF7F50" transparent opacity={0} />
                </mesh>
                {/* Glowing coral patterns */}
                <mesh scale={[3.2, 0.1, 3.2]} position={[0, 0.1, 0]}>
                    <ringGeometry args={[0.5, 1, 8]} />
                    <meshBasicMaterial color="#D2691E" transparent opacity={0.6} side={THREE.DoubleSide} />
                </mesh>
            </group>
            {/* Drifting spores */}
            {spores.map((s, i) => (
                <mesh
                    key={i}
                    ref={el => sporeRefs.current[i] = el}
                    position={s.basePos.toArray()}
                    scale={0.1}
                >
                    <sphereGeometry args={[1, 4, 4]} />
                    <meshBasicMaterial color="#A0522D" transparent opacity={0.4} />
                </mesh>
            ))}
        </group>
    );
};
