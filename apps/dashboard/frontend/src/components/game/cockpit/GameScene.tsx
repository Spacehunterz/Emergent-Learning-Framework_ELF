import { Suspense, Component, ReactNode, useEffect, useState, lazy } from 'react'
import { Canvas } from '@react-three/fiber'
import { XR } from '@react-three/xr'
// Lazy load the heavy 3D game component
const SpaceShooterScene = lazy(() => import('./SpaceShooterScene').then(module => ({ default: module.SpaceShooterScene })))
import { PauseMenu } from '../ui/PauseMenu'
import { MainMenu } from '../ui/MainMenu'
import { useGameSettings } from '../systems/GameSettings'
import { xrStore } from '../../xr/xrStore'

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
    const { isPaused, setPaused, showMainMenu } = useGameSettings()
    const [vrSupported, setVrSupported] = useState(false)

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                setPaused(!isPaused)
            }
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [isPaused, setPaused])

    useEffect(() => {
        return () => setPaused(false)
    }, [setPaused])

    useEffect(() => {
        let active = true
        const checkSupport = async () => {
            console.log('[VR DEBUG] Checking XR Support...')
            if (!navigator.xr) {
                console.warn('[VR DEBUG] navigator.xr is undefined. HTTPS required?')
                if (active) setVrSupported(false)
                return
            }
            try {
                const vrSupported = await navigator.xr.isSessionSupported('immersive-vr')
                console.log('[VR DEBUG] immersive-vr supported:', vrSupported)

                // Fallback check to see if *any* immersive mode works
                const arSupported = await navigator.xr.isSessionSupported('immersive-ar')
                console.log('[VR DEBUG] immersive-ar supported:', arSupported)

                if (active) setVrSupported(vrSupported)
            } catch (e) {
                console.error('[VR DEBUG] XR Check Error:', e)
                if (active) setVrSupported(false)
            }
        }
        checkSupport()
        return () => {
            active = false
        }
    }, [])

    return (
        <GameErrorBoundary>
            <div className="fixed inset-0 z-50 bg-black">
                {/* Main Menu Overlay */}
                <MainMenu />

                {/* Only show pause menu and VR button when not in main menu */}
                {!showMainMenu && <PauseMenu />}
                {!showMainMenu && vrSupported && (
                    <button
                        onClick={() => xrStore.enterVR()}
                        className="!absolute !bottom-6 !left-1/2 !-translate-x-1/2 !z-[60] !bg-slate-900/90 !border !border-indigo-500/50 !text-indigo-100 !font-mono !tracking-widest !uppercase !px-6 !py-3 !rounded-lg hover:!bg-indigo-900/80 transition-colors"
                    >
                        ENTER VR
                    </button>
                )}

                {/* 3D Scene */}
                <Canvas
                    dpr={[1, 1.5]}
                    camera={{ position: [0, 0, 0], fov: 70, near: 0.1, far: 1000 }}
                    gl={{ antialias: true, powerPreference: 'high-performance' }}
                >
                    <XR store={xrStore}>
                        <Suspense fallback={null}>
                            <SpaceShooterScene />
                        </Suspense>
                    </XR>
                </Canvas>
            </div>
        </GameErrorBoundary>
    )
}
