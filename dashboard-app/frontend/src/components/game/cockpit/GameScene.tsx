import { Suspense, Component, ReactNode, useCallback, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { XR, createXRStore } from '@react-three/xr'
import { SpaceShooterScene } from './SpaceShooterScene'
import { useGame } from '../../../context/GameContext'
import { HudState } from './Hud'

// Create the XR store outside of the component to maintain state
const store = createXRStore()

// Simple local ErrorBoundary for the game view
class GameErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean, error: Error | null }> {
    constructor(props: { children: ReactNode }) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error: Error) {
        return { hasError: true, error }
    }

    componentDidCatch(error: Error) {
        console.error("Game Rendering Error:", error)
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black text-red-500 font-mono p-10 text-center">
                    <h2 className="text-4xl font-bold mb-4 border-2 border-red-500 p-4 rounded">SYSTEM FAILURE</h2>
                    <p className="max-w-xl text-lg mb-8">
                        COCKPIT RENDERING SUBSYSTEM CRASHED.
                        <br />
                        <span className="text-sm opacity-70 mt-4 block">{this.state.error?.message}</span>
                    </p>
                    <button
                        onClick={() => window.location.reload()}
                        className="px-6 py-2 bg-red-900/50 hover:bg-red-800 border border-red-500 text-white rounded transition-colors"
                    >
                        REBOOT SYSTEM
                    </button>
                </div>
            )
        }
        return this.props.children
    }
}

export const GameScene = () => {
    const { isGameEnabled } = useGame()
    const [, setHudStatus] = useState<HudState>({
        stageLabel: 'Asteroid Ring',
        stageObjective: 'Target practice: clear the debris field.',
        stageIndex: 1,
        stageStatus: 'Engage',
        bossHealth: null,
        bossSegments: null
    })
    const handleHudUpdate = useCallback((next: HudState) => {
        setHudStatus(next)
    }, [])

    if (!isGameEnabled) return null

    return (
        <GameErrorBoundary>
            <div className="fixed inset-0 z-50 bg-black">
                {/* VR Enable Button - Only visible if VR is supported */}
                <button
                    onClick={() => store.enterVR()}
                    className="!absolute !bottom-6 !left-1/2 !-translate-x-1/2 !z-[60] !bg-slate-900/90 !border !border-indigo-500/50 !text-indigo-100 !font-mono !tracking-widest !uppercase !px-6 !py-3 !rounded-lg hover:!bg-indigo-900/80 transition-colors"
                >
                    ENTER VR
                </button>

                {/* 3D Scene */}
                <Canvas
                    dpr={[1, 1.5]}
                    camera={{ position: [0, 0, 0], fov: 70, near: 0.1, far: 1000 }}
                    gl={{ antialias: true, powerPreference: 'high-performance' }}
                >
                    <XR store={store}>
                        <Suspense fallback={null}>
                            <SpaceShooterScene onHudUpdate={handleHudUpdate} resetKey={0} />
                        </Suspense>
                    </XR>
                </Canvas>
            </div>
        </GameErrorBoundary>
    )
}
