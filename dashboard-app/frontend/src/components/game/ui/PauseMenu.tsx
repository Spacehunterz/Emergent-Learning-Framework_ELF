import { useGameSettings } from '../systems/GameSettings'

export const PauseMenu = () => {
    const {
        sensitivityX, sensitivityY, smoothness,
        setSensitivityX, setSensitivityY, setSmoothness,
        isPaused, setPaused
    } = useGameSettings()

    if (!isPaused) return null

    return (
        <div style={{
            position: 'fixed', // Fixed to viewport, ignores parent container quirks
            top: 0, left: 0, width: '100vw', height: '100vh',
            backgroundColor: 'rgba(0,0,0,0.8)',
            display: 'flex', flexDirection: 'column',
            justifyContent: 'center', alignItems: 'center',
            zIndex: 10000, color: 'white', fontFamily: 'monospace' // Very high Z
        }}>
            <h1 className="text-4xl mb-8 font-bold text-cyan-400 tracking-widest">SYSTEM PAUSED</h1>

            <div className="bg-slate-900 p-8 rounded-xl border border-slate-700 w-96 space-y-6">

                {/* Sensitivity X */}
                <div>
                    <label className="flex justify-between mb-2">
                        <span>Horizontal Sens (X)</span>
                        <span className="text-cyan-400">{sensitivityX.toFixed(1)}</span>
                    </label>
                    <input
                        type="range" min="0.1" max="5.0" step="0.1"
                        value={sensitivityX}
                        onChange={(e) => setSensitivityX(parseFloat(e.target.value))}
                        className="w-full accent-cyan-500"
                    />
                </div>

                {/* Sensitivity Y */}
                <div>
                    <label className="flex justify-between mb-2">
                        <span>Vertical Sens (Y)</span>
                        <span className="text-cyan-400">{sensitivityY.toFixed(1)}</span>
                    </label>
                    <input
                        type="range" min="0.1" max="5.0" step="0.1"
                        value={sensitivityY}
                        onChange={(e) => setSensitivityY(parseFloat(e.target.value))}
                        className="w-full accent-cyan-500"
                    />
                </div>

                {/* Smoothness */}
                <div>
                    <label className="flex justify-between mb-2">
                        <span>Smoothness</span>
                        <span className="text-cyan-400">{smoothness.toFixed(2)}</span>
                    </label>
                    <input
                        type="range" min="0" max="0.5" step="0.01"
                        value={smoothness}
                        onChange={(e) => setSmoothness(parseFloat(e.target.value))}
                        className="w-full accent-cyan-500"
                    />
                </div>

                <button
                    onClick={() => setPaused(false)}
                    className="w-full py-3 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-bold mt-4"
                >
                    RESUME
                </button>
            </div>
        </div>
    )
}
