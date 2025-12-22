import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 19: Holy/Angelic themed - #FFFFFF, #FFD700, #ADD8E6
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#FFFFFF'; // White
    if (healthPct > 0.25) return '#FFD700'; // Gold
    return '#ADD8E6'; // LightBlue
};

/**
 * Stage 19 Asteroid: Smooth white marble sphere with veins of gold, radiant glow
 */
export const Stage19Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const glowMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const veinRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.02 + Math.random() * 0.02,
        y: 0.03 + Math.random() * 0.03,
        z: 0.015 + Math.random() * 0.02
    }), []);

    const veins = useMemo(() =>
        Array.from({ length: 5 }, () => ({
            rot: new THREE.Euler(Math.random() * Math.PI, Math.random() * Math.PI, 0),
            scale: 0.8 + Math.random() * 0.3
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
            // Divine radiance flashing
            const radiant = Math.random() > 0.9;
            if (radiant) {
                mainMatRef.current.color.set(['#FFFFFF', '#FFD700', '#ADD8E6'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            mainMatRef.current.opacity = ease * (radiant ? 1.0 : 0.9);
        }

        // Holy flicker - intense pulsing during radiant moments
        if (glowMatRef.current) {
            const radiant = Math.random() > 0.95;
            glowMatRef.current.opacity = radiant ? 0.6 : (0.2 + Math.sin(t * 2) * 0.1);
        }

        // Gold veins shimmer with jitter
        veinRefs.current.forEach((vein, i) => {
            if (!vein || !(vein.material instanceof THREE.MeshBasicMaterial)) return;
            vein.material.opacity = 0.5 + Math.sin(t * 3 + i) * 0.3;
            // Angelic shimmer - veins jitter
            if (Math.random() > 0.9) {
                vein.position.x = (Math.random() - 0.5) * 0.2;
                vein.position.y = (Math.random() - 0.5) * 0.2;
                vein.position.z = (Math.random() - 0.5) * 0.2;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* White marble sphere */}
            <mesh>
                <sphereGeometry args={[1, 16, 12]} />
                <meshBasicMaterial ref={mainMatRef} color="#FFFFFF" transparent opacity={0} />
            </mesh>
            {/* Outer glow */}
            <mesh scale={1.2}>
                <sphereGeometry args={[1, 12, 8]} />
                <meshBasicMaterial ref={glowMatRef} color="#FFFFFF" transparent opacity={0.2} />
            </mesh>
            {/* Gold veins */}
            {veins.map((v, i) => (
                <mesh
                    key={i}
                    ref={el => veinRefs.current[i] = el}
                    rotation={v.rot}
                    scale={v.scale}
                >
                    <torusGeometry args={[0.9, 0.02, 4, 16]} />
                    <meshBasicMaterial color="#FFD700" transparent opacity={0.6} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 19 Drone: Glowing golden octahedron with rotating white halo
 */
export const Stage19Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const haloRef = useRef<THREE.Mesh>(null);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.lookAt(0, 0, 0);
        ref.current.rotation.z += delta * 0.5;
        ref.current.scale.setScalar(ease * 18);

        // Jerky discrete movement
        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
        }

        if (bodyMatRef.current) {
            // Divine radiance flashing
            const radiant = Math.random() > 0.9;
            if (radiant) {
                bodyMatRef.current.color.set(['#FFFFFF', '#FFD700', '#ADD8E6'][Math.floor(Math.random() * 3)]);
            } else {
                bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            bodyMatRef.current.opacity = ease * (radiant ? 1.0 : 0.9);
        }

        // Halo rotates and shimmers
        if (haloRef.current) {
            haloRef.current.rotation.z += delta * 2;
            // Angelic shimmer - halo jitters
            if (Math.random() > 0.9) {
                haloRef.current.position.x = (Math.random() - 0.5) * 0.3;
                haloRef.current.position.y = 0.8 + (Math.random() - 0.5) * 0.3;
                haloRef.current.position.z = (Math.random() - 0.5) * 0.3;
            }
            if (haloRef.current.material instanceof THREE.MeshBasicMaterial) {
                // Holy flicker
                const radiant = Math.random() > 0.95;
                haloRef.current.material.opacity = radiant ? 1.0 : 0.8;
            }
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Golden core */}
            <mesh>
                <octahedronGeometry args={[0.6, 0]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FFD700" transparent opacity={0} />
            </mesh>
            {/* Inner glow */}
            <mesh scale={0.5}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#FFFFFF" transparent opacity={0.5} />
            </mesh>
            {/* Floating halo */}
            <mesh ref={haloRef} position={[0, 0.8, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[0.5, 0.05, 8, 24]} />
                <meshBasicMaterial color="#FFFFFF" transparent opacity={0.8} />
            </mesh>
        </group>
    );
};

/**
 * Stage 19 Fighter: Sleek white bird with golden-trimmed wings that flap majestically
 */
export const Stage19Fighter = ({ data }: { data: Enemy }) => {
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
        ref.current.scale.setScalar(ease * 24);

        // Flicker in and out
        const visible = Math.sin(t * 20) > -0.8;
        ref.current.visible = visible;

        if (bodyMatRef.current) {
            // Divine radiance flashing
            const radiant = Math.random() > 0.9;
            if (radiant) {
                bodyMatRef.current.color.set(['#FFFFFF', '#FFD700', '#ADD8E6'][Math.floor(Math.random() * 3)]);
            } else {
                bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            bodyMatRef.current.opacity = ease * (radiant ? 1.0 : 0.9);
        }

        // Majestic wing flapping with shimmer
        const flapAngle = Math.sin(t * 1.5 + phase) * 0.4;
        if (wingLeftRef.current) {
            wingLeftRef.current.rotation.z = 0.2 + flapAngle;
            // Angelic shimmer - wings jitter
            if (Math.random() > 0.9) {
                wingLeftRef.current.position.x = -0.2 + (Math.random() - 0.5) * 0.3;
                wingLeftRef.current.position.y = 0.3 + (Math.random() - 0.5) * 0.3;
            }
            if (wingLeftRef.current.material instanceof THREE.MeshBasicMaterial) {
                // Holy flicker
                const radiant = Math.random() > 0.95;
                wingLeftRef.current.material.opacity = radiant ? 1.0 : 0.7;
            }
        }
        if (wingRightRef.current) {
            wingRightRef.current.rotation.z = -0.2 - flapAngle;
            // Angelic shimmer - wings jitter
            if (Math.random() > 0.9) {
                wingRightRef.current.position.x = -0.2 + (Math.random() - 0.5) * 0.3;
                wingRightRef.current.position.y = -0.3 + (Math.random() - 0.5) * 0.3;
            }
            if (wingRightRef.current.material instanceof THREE.MeshBasicMaterial) {
                // Holy flicker
                const radiant = Math.random() > 0.95;
                wingRightRef.current.material.opacity = radiant ? 1.0 : 0.7;
            }
        }
    });

    return (
        <group ref={ref} scale={0}>
            {/* Sleek white body */}
            <mesh rotation={[0, 0, Math.PI / 2]} scale={[0.3, 1.2, 0.25]}>
                <capsuleGeometry args={[1, 1, 4, 12]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FFFFFF" transparent opacity={0} />
            </mesh>
            {/* Head */}
            <mesh position={[0.8, 0.1, 0]} scale={0.25}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#FFFFFF" transparent opacity={0.9} />
            </mesh>
            {/* Large golden-trimmed wings */}
            <mesh ref={wingLeftRef} position={[-0.2, 0.3, 0]} rotation={[0, 0, 0.2]}>
                <planeGeometry args={[1.8, 0.6]} />
                <meshBasicMaterial color="#FFD700" transparent opacity={0.7} side={THREE.DoubleSide} />
            </mesh>
            <mesh ref={wingRightRef} position={[-0.2, -0.3, 0]} rotation={[0, 0, -0.2]}>
                <planeGeometry args={[1.8, 0.6]} />
                <meshBasicMaterial color="#FFD700" transparent opacity={0.7} side={THREE.DoubleSide} />
            </mesh>
            {/* Wing white inner */}
            <mesh position={[-0.2, 0.3, 0.01]} rotation={[0, 0, 0.2]}>
                <planeGeometry args={[1.5, 0.4]} />
                <meshBasicMaterial color="#FFFFFF" transparent opacity={0.8} side={THREE.DoubleSide} />
            </mesh>
            <mesh position={[-0.2, -0.3, 0.01]} rotation={[0, 0, -0.2]}>
                <planeGeometry args={[1.5, 0.4]} />
                <meshBasicMaterial color="#FFFFFF" transparent opacity={0.8} side={THREE.DoubleSide} />
            </mesh>
        </group>
    );
};

/**
 * Stage 19 Elite: Glowing white icosahedron surrounded by golden orrery rings
 */
export const Stage19Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const coreMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const ringRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rings = useMemo(() => [
        { tiltX: 0, tiltY: 0, speed: 1, scale: 1.5 },
        { tiltX: Math.PI / 4, tiltY: 0, speed: -0.7, scale: 1.8 },
        { tiltX: 0, tiltY: Math.PI / 4, speed: 0.5, scale: 2.1 }
    ], []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 36);

        if (coreMatRef.current) {
            // Divine radiance flashing with rapid color cycling
            const radiant = Math.random() > 0.9;
            if (radiant) {
                coreMatRef.current.color.set(['#FFFFFF', '#FFD700', '#ADD8E6'][Math.floor(Math.random() * 3)]);
                coreMatRef.current.opacity = ease * 1.0;
            } else {
                const phase = Math.floor(t * 8) % 3;
                coreMatRef.current.color.set(['#FFFFFF', '#FFD700', '#ADD8E6'][phase]);
                coreMatRef.current.opacity = ease * (0.7 + Math.sin(t * 2) * 0.2);
            }
        }

        // Orrery rings rotate in opposite directions with shimmer
        ringRefs.current.forEach((ring, i) => {
            if (!ring) return;
            ring.rotation.z += delta * rings[i].speed;
            // Angelic shimmer - rings pulse scale
            if (Math.random() > 0.95) {
                ring.scale.setScalar(rings[i].scale * (1 + (Math.random() - 0.5) * 0.15));
            }
            if (ring.material instanceof THREE.MeshBasicMaterial) {
                // Holy flicker
                const radiant = Math.random() > 0.95;
                ring.material.opacity = radiant ? 0.9 : 0.6;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Glowing white core */}
            <mesh>
                <icosahedronGeometry args={[0.8, 0]} />
                <meshBasicMaterial ref={coreMatRef} color="#FFFFFF" transparent opacity={0} />
            </mesh>
            {/* Inner glow */}
            <mesh scale={0.6}>
                <sphereGeometry args={[1, 8, 6]} />
                <meshBasicMaterial color="#ADD8E6" transparent opacity={0.5} />
            </mesh>
            {/* Golden orrery rings */}
            {rings.map((r, i) => (
                <mesh
                    key={i}
                    ref={el => ringRefs.current[i] = el}
                    rotation={[r.tiltX, r.tiltY, 0]}
                    scale={r.scale}
                >
                    <ringGeometry args={[0.9, 1, 32]} />
                    <meshBasicMaterial color="#FFD700" transparent opacity={0.6} side={THREE.DoubleSide} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 19 Boss: Seraphic figure with slender white form and three pairs of beating golden wings
 */
export const Stage19Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const wingPairRefs = useRef<(THREE.Group | null)[]>([]);
    const auraMatRef = useRef<THREE.MeshBasicMaterial>(null);

    const wingPairs = useMemo(() => [
        { y: 1.5, scale: 1.2, phase: 0 },
        { y: 0.5, scale: 1.5, phase: 0.5 },
        { y: -0.5, scale: 1.0, phase: 1.0 }
    ], []);

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

        if (bodyMatRef.current) {
            // Divine radiance flashing
            const radiant = Math.random() > 0.9;
            if (radiant) {
                bodyMatRef.current.color.set(['#FFFFFF', '#FFD700', '#ADD8E6'][Math.floor(Math.random() * 3)]);
            } else {
                bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            bodyMatRef.current.opacity = ease * 0.9 * (Math.random() > 0.1 ? 1 : 0.3);
        }

        // Radiant aura pulses with holy flicker
        if (auraMatRef.current) {
            const radiant = Math.random() > 0.95;
            auraMatRef.current.opacity = radiant ? 0.5 : (0.15 + Math.sin(t * 2) * 0.1);
        }

        // Wing pairs beat slowly with angelic shimmer
        wingPairRefs.current.forEach((pair, i) => {
            if (!pair) return;
            const beat = Math.sin(t * 1.2 + wingPairs[i].phase) * 0.3;

            // Wings jitter during divine power spikes
            if (Math.random() > 0.9) {
                pair.position.x = (Math.random() - 0.5) * 0.4;
                pair.position.z = -0.3 + (Math.random() - 0.5) * 0.3;
            }

            pair.children.forEach((wing, j) => {
                if (wing instanceof THREE.Mesh) {
                    wing.rotation.z = j === 0 ? 0.3 + beat : -0.3 - beat;
                    if (wing.material instanceof THREE.MeshBasicMaterial) {
                        // Holy flicker - wings pulse brightly
                        const radiant = Math.random() > 0.95;
                        wing.material.opacity = radiant ? 1.0 : 0.8;
                    }
                }
            });
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Radiant aura */}
            <mesh scale={5}>
                <sphereGeometry args={[1, 12, 8]} />
                <meshBasicMaterial ref={auraMatRef} color="#FFFFFF" transparent opacity={0.15} />
            </mesh>
            {/* Slender humanoid form */}
            <mesh scale={[0.4, 2.5, 0.3]}>
                <capsuleGeometry args={[1, 1, 4, 12]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FFFFFF" transparent opacity={0} />
            </mesh>
            {/* Head */}
            <mesh position={[0, 2.2, 0]} scale={0.5}>
                <sphereGeometry args={[1, 10, 8]} />
                <meshBasicMaterial color="#FFFFFF" transparent opacity={0.9} />
            </mesh>
            {/* Halo */}
            <mesh position={[0, 2.8, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[0.6, 0.08, 8, 24]} />
                <meshBasicMaterial color="#FFD700" transparent opacity={0.9} />
            </mesh>
            {/* Three pairs of golden wings */}
            {wingPairs.map((wp, i) => (
                <group key={i} ref={el => wingPairRefs.current[i] = el} position={[0, wp.y, -0.3]}>
                    {/* Left wing */}
                    <mesh position={[-1, 0, 0]} rotation={[0, 0, 0.3]} scale={[wp.scale, 0.4, 0.05]}>
                        <planeGeometry args={[2, 1]} />
                        <meshBasicMaterial color="#FFD700" transparent opacity={0.8} side={THREE.DoubleSide} />
                    </mesh>
                    {/* Right wing */}
                    <mesh position={[1, 0, 0]} rotation={[0, 0, -0.3]} scale={[wp.scale, 0.4, 0.05]}>
                        <planeGeometry args={[2, 1]} />
                        <meshBasicMaterial color="#FFD700" transparent opacity={0.8} side={THREE.DoubleSide} />
                    </mesh>
                </group>
            ))}
            {/* Light blue energy waves */}
            {[0, 1, 2].map(i => (
                <mesh key={i} position={[0, 0, 0.5 + i * 0.3]} rotation={[0, 0, i * 0.5]}>
                    <ringGeometry args={[1.5 + i * 0.5, 1.6 + i * 0.5, 6]} />
                    <meshBasicMaterial color="#ADD8E6" transparent opacity={0.3 - i * 0.08} side={THREE.DoubleSide} />
                </mesh>
            ))}
        </group>
    );
};
