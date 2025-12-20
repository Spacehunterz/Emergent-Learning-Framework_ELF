import { useProjectileStore } from '../systems/WeaponSystem'
import { Trail } from '@react-three/drei'
import * as THREE from 'three'

export const ProjectileRenderer = () => {
    const { projectiles } = useProjectileStore()

    // Note: Projectile Movement is updated in CollisionManager.tsx to allow for frame-sync physics

    return (
        <group>
            {projectiles.map(p => {
                const isEnemy = p.owner === 'ENEMY'

                // --- VISUAL CONFIG ---
                // PLAYER: High-speed, thin, neon cyan "Neutron Bolt"
                // ENEMY: Slower, thick, neon red "Plasma Glob"

                const color = isEnemy ? '#ff2200' : '#00ffff'
                const coreColor = isEnemy ? '#ffaa00' : '#ffffff' // Hot white core for player
                const trailWidth = isEnemy ? 1.2 : 0.6
                // Player trail shortened significantly to prevent "ghosting"
                const trailLength = isEnemy ? 3 : 2

                return (
                    <group key={p.id} position={p.position} quaternion={p.rotation}>
                        {/* Trail Effect */}
                        <Trail
                            width={trailWidth}
                            length={trailLength}
                            color={new THREE.Color(color)}
                            attenuation={(t) => t * t * t} // Faster fade (Cubic)
                        >
                            {/* Projectile Core Mesh */}
                            <mesh rotation={[Math.PI / 2, 0, 0]}>
                                {isEnemy ? (
                                    // Enemy: Thicker Capsule/Orb
                                    <capsuleGeometry args={[0.3, 1.5, 4, 8]} />
                                ) : (
                                    // Player: Thin, sharp Needle
                                    <cylinderGeometry args={[0.1, 0.1, 4, 8]} />
                                )}
                                <meshBasicMaterial color={coreColor} toneMapped={false} />
                            </mesh>
                        </Trail>

                        {/* Outer Glow Overlay (Fake Volumetrics) */}
                        <mesh rotation={[Math.PI / 2, 0, 0]}>
                            {isEnemy ? (
                                <sphereGeometry args={[0.6, 16, 16]} />
                            ) : (
                                <cylinderGeometry args={[0.3, 0.05, 5, 8]} />
                            )}
                            <meshBasicMaterial
                                color={color}
                                transparent
                                opacity={0.3}
                                blending={THREE.AdditiveBlending}
                                depthWrite={false}
                            />
                        </mesh>

                        {/* Point Light Removed for Performance */}
                    </group>
                )
            })}
        </group>
    )
}
