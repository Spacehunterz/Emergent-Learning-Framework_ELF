import React, { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { Enemy, getSpawnEase } from '../systems/EnemySystem';

// Stage 18: Temporal/Glitch themed - #00FFFF, #FF00FF, #FFFFFF
const getHealthColor = (hp: number, maxHp: number) => {
    const healthPct = hp / maxHp;
    if (healthPct > 0.5) return '#00FFFF'; // Cyan
    if (healthPct > 0.25) return '#FF00FF'; // Magenta
    return '#FFFFFF'; // White
};

/**
 * Stage 18 Asteroid: Glitching box with jittering vertices and flickering colors
 */
export const Stage18Asteroid = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const mainMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const glitchRefs = useRef<(THREE.Mesh | null)[]>([]);

    const rotSpeed = useMemo(() => ({
        x: 0.05 + Math.random() * 0.06,
        y: 0.06 + Math.random() * 0.07,
        z: 0.04 + Math.random() * 0.05
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

        // Occasional teleport jitter
        if (Math.random() > 0.98) {
            ref.current.position.x += (Math.random() - 0.5) * 5;
            ref.current.position.y += (Math.random() - 0.5) * 5;
        }

        if (mainMatRef.current) {
            // Rapid color cycling during glitch
            const glitch = Math.random() > 0.9;
            if (glitch) {
                mainMatRef.current.color.set(['#00FFFF', '#FF00FF', '#FFFFFF'][Math.floor(Math.random() * 3)]);
            } else {
                mainMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            }
            mainMatRef.current.opacity = ease * (glitch ? 0.5 : 0.85);
        }

        // Glitch fragments jitter
        glitchRefs.current.forEach((frag) => {
            if (!frag) return;
            if (Math.random() > 0.9) {
                frag.position.x = (Math.random() - 0.5) * 0.5;
                frag.position.y = (Math.random() - 0.5) * 0.5;
                frag.position.z = (Math.random() - 0.5) * 0.5;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Glitching box */}
            <mesh>
                <boxGeometry args={[1.5, 1.5, 1.5]} />
                <meshBasicMaterial ref={mainMatRef} color="#00FFFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Glitch fragments */}
            {[0, 1, 2].map(i => (
                <mesh
                    key={i}
                    ref={el => glitchRefs.current[i] = el}
                    scale={0.3}
                >
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color={['#00FFFF', '#FF00FF', '#FFFFFF'][i]} transparent opacity={0.6} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 18 Drone: White sphere with ghost trail of fading magenta copies
 */
export const Stage18Drone = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyMatRef = useRef<THREE.MeshBasicMaterial>(null);
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

        // Jerky discrete movement
        if (Math.random() > 0.95) {
            ref.current.position.x += (Math.random() - 0.5) * 3;
        }

        if (bodyMatRef.current) {
            bodyMatRef.current.color.set(getHealthColor(data.hp, data.maxHp));
            bodyMatRef.current.opacity = ease * 0.9;
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
            {/* Main body */}
            <mesh>
                <sphereGeometry args={[0.5, 10, 8]} />
                <meshBasicMaterial ref={bodyMatRef} color="#FFFFFF" transparent opacity={0} />
            </mesh>
            {/* Ghost trail */}
            {[0, 1, 2, 3, 4].map(i => (
                <mesh
                    key={i}
                    ref={el => trailRefs.current[i] = el}
                    scale={0.4 - i * 0.05}
                >
                    <sphereGeometry args={[1, 8, 6]} />
                    <meshBasicMaterial color="#FF00FF" transparent opacity={0.3} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 18 Fighter: Glitched ship that flickers in and out of existence
 */
export const Stage18Fighter = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const partsRef = useRef<THREE.Group>(null);
    const partMatRefs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);

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

        // Parts get displaced by glitch shader effect
        if (partsRef.current && Math.random() > 0.9) {
            partsRef.current.children.forEach((child, i) => {
                if (child instanceof THREE.Mesh) {
                    child.position.x = (Math.random() - 0.5) * 0.3;
                    child.position.y = (Math.random() - 0.5) * 0.3;
                }
            });
        }

        partMatRefs.current.forEach((mat, i) => {
            if (!mat) return;
            mat.color.set(getHealthColor(data.hp, data.maxHp));
            mat.opacity = ease * (Math.random() > 0.1 ? 0.85 : 0.3);
        });
    });

    return (
        <group ref={ref} scale={0}>
            <group ref={partsRef}>
                {/* Glitched body parts */}
                <mesh position={[0, 0, 0]} scale={[0.6, 1.5, 0.3]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial ref={el => partMatRefs.current[0] = el} color="#00FFFF" wireframe transparent opacity={0.8} />
                </mesh>
                <mesh position={[-0.5, 0, 0]} scale={[0.8, 0.3, 0.2]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial ref={el => partMatRefs.current[1] = el} color="#FF00FF" transparent opacity={0.7} />
                </mesh>
                <mesh position={[0.5, 0, 0]} scale={[0.8, 0.3, 0.2]}>
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial ref={el => partMatRefs.current[2] = el} color="#FF00FF" transparent opacity={0.7} />
                </mesh>
            </group>
            {/* Glitch artifacts */}
            <mesh position={[0.2, 0.3, 0]} scale={0.15}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#FFFFFF" transparent opacity={0.5} />
            </mesh>
        </group>
    );
};

/**
 * Stage 18 Elite: Torus knot with disappearing/reappearing faces and frozen orbiting fragments
 */
export const Stage18Elite = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const knotMatRef = useRef<THREE.MeshBasicMaterial>(null);
    const fragmentRefs = useRef<(THREE.Mesh | null)[]>([]);

    const fragments = useMemo(() =>
        Array.from({ length: 6 }, (_, i) => ({
            angle: (i / 6) * Math.PI * 2,
            dist: 1.5 + Math.random() * 0.5,
            frozen: Math.random() > 0.5
        })), []);

    useFrame((state, delta) => {
        if (!ref.current) return;
        const t = state.clock.getElapsedTime();
        const ease = getSpawnEase(data.createdAt);

        ref.current.position.copy(data.position);
        ref.current.scale.setScalar(ease * 36);

        // Rapid color cycling
        if (knotMatRef.current) {
            const phase = Math.floor(t * 8) % 3;
            knotMatRef.current.color.set(['#00FFFF', '#FF00FF', '#FFFFFF'][phase]);
            knotMatRef.current.opacity = ease * (Math.random() > 0.1 ? 0.8 : 0.3);
        }

        // Some fragments frozen, some moving
        fragmentRefs.current.forEach((frag, i) => {
            if (!frag) return;
            if (!fragments[i].frozen) {
                frag.rotation.x += delta * 2;
                frag.rotation.y += delta * 3;
            }
            if (frag.material instanceof THREE.MeshBasicMaterial) {
                frag.material.opacity = 0.4 + Math.sin(t * 5 + i) * 0.3;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Central torus knot */}
            <mesh>
                <torusKnotGeometry args={[0.8, 0.25, 64, 8]} />
                <meshBasicMaterial ref={knotMatRef} color="#00FFFF" wireframe transparent opacity={0} />
            </mesh>
            {/* Frozen time fragments */}
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
                    <meshBasicMaterial color={f.frozen ? '#FFFFFF' : '#FF00FF'} transparent opacity={0.6} />
                </mesh>
            ))}
        </group>
    );
};

/**
 * Stage 18 Boss: Colossal humanoid of white blocks with unstable form and digital artifacts
 */
export const Stage18Boss = ({ data }: { data: Enemy }) => {
    const ref = useRef<THREE.Group>(null);
    const bodyPartsRef = useRef<(THREE.Mesh | null)[]>([]);
    const artifactRefs = useRef<(THREE.Mesh | null)[]>([]);

    const artifacts = useMemo(() =>
        Array.from({ length: 10 }, () => ({
            basePos: new THREE.Vector3(
                (Math.random() - 0.5) * 6,
                (Math.random() - 0.5) * 6,
                (Math.random() - 0.5) * 3
            ),
            color: ['#00FFFF', '#FF00FF'][Math.floor(Math.random() * 2)]
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

        // Body parts glitch and reposition
        bodyPartsRef.current.forEach((part, i) => {
            if (!part) return;
            if (Math.random() > 0.95) {
                part.position.x += (Math.random() - 0.5) * 0.5;
                part.position.y += (Math.random() - 0.5) * 0.5;
            }
            if (part.material instanceof THREE.MeshBasicMaterial) {
                part.material.color.set(getHealthColor(data.hp, data.maxHp));
                part.material.opacity = ease * (Math.random() > 0.1 ? 0.85 : 0.4);
            }
        });

        // Digital artifacts flicker
        artifactRefs.current.forEach((art, i) => {
            if (!art) return;
            art.visible = Math.random() > 0.3;
            art.position.copy(artifacts[i].basePos);
            if (Math.random() > 0.8) {
                art.position.x += (Math.random() - 0.5) * 2;
                art.position.y += (Math.random() - 0.5) * 2;
            }
        });
    });

    return (
        <group ref={ref} scale={0}>
            {/* Humanoid body made of blocks */}
            {/* Head */}
            <mesh ref={el => bodyPartsRef.current[0] = el} position={[0, 2, 0]} scale={0.8}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#FFFFFF" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Torso */}
            <mesh ref={el => bodyPartsRef.current[1] = el} position={[0, 0.5, 0]} scale={[1.2, 2, 0.6]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#FFFFFF" wireframe transparent opacity={0.8} />
            </mesh>
            {/* Arms */}
            <mesh ref={el => bodyPartsRef.current[2] = el} position={[-1.5, 0.5, 0]} scale={[0.5, 1.8, 0.5]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#00FFFF" transparent opacity={0.7} />
            </mesh>
            <mesh ref={el => bodyPartsRef.current[3] = el} position={[1.5, 0.5, 0]} scale={[0.5, 1.8, 0.5]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#00FFFF" transparent opacity={0.7} />
            </mesh>
            {/* Legs */}
            <mesh ref={el => bodyPartsRef.current[4] = el} position={[-0.5, -1.5, 0]} scale={[0.5, 1.5, 0.5]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#FF00FF" transparent opacity={0.7} />
            </mesh>
            <mesh ref={el => bodyPartsRef.current[5] = el} position={[0.5, -1.5, 0]} scale={[0.5, 1.5, 0.5]}>
                <boxGeometry args={[1, 1, 1]} />
                <meshBasicMaterial color="#FF00FF" transparent opacity={0.7} />
            </mesh>
            {/* Digital artifacts */}
            {artifacts.map((a, i) => (
                <mesh
                    key={i}
                    ref={el => artifactRefs.current[i] = el}
                    position={a.basePos.toArray()}
                    scale={0.2}
                >
                    <boxGeometry args={[1, 1, 1]} />
                    <meshBasicMaterial color={a.color} transparent opacity={0.5} />
                </mesh>
            ))}
        </group>
    );
};
