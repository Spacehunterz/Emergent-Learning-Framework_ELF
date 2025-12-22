import { useEffect, useState } from 'react'
import { ShoppingCart } from 'lucide-react'
import { useGameSettings } from '../systems/GameSettings'
import { useGame } from '../../../context/GameContext'
import { WeaponShop } from './WeaponShop'
import { usePlayerWeaponStore } from '../systems/PlayerWeaponStore'

export const PauseMenu = () => {
    const {
        sensitivityX, sensitivityY, smoothness,
        setSensitivityX, setSensitivityY, setSmoothness,
        isPaused, setPaused
    } = useGameSettings()
    const { setGameEnabled } = useGame()
    const [exitHint, setExitHint] = useState(false)
    const [shopOpen, setShopOpen] = useState(false)
    const credits = usePlayerWeaponStore(s => s.credits)

    useEffect(() => {
        if (isPaused) {
            setExitHint(false)
        } else {
            setShopOpen(false) // Close shop when unpausing
        }
    }, [isPaused])

    if (!isPaused) return null

    const handleResume = () => setPaused(false)
    const handleExitToDashboard = () => {
        setPaused(false)
        setGameEnabled(false)
    }
    const handleExitToDesktop = () => {
        setExitHint(false)
        window.close()
        setTimeout(() => {
            if (!window.closed) {
                setExitHint(true)
            }
        }, 200)
    }

    return (
        <div
            className="fixed inset-0 z-[100000] flex items-center justify-center bg-black/80 text-white font-mono"
            onClick={handleResume}
        >
            <div
                className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-950/90 p-6 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                <h1 className="text-center text-3xl font-bold text-cyan-400 tracking-widest mb-6">SYSTEM PAUSED</h1>

                <div className="space-y-5">
                    <div>
                        <label className="flex justify-between mb-2 text-sm">
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

                    <div>
                        <label className="flex justify-between mb-2 text-sm">
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

                    <div>
                        <label className="flex justify-between mb-2 text-sm">
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
                </div>

                {/* Credits Display */}
                <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg flex items-center justify-between">
                    <span className="text-sm text-yellow-400">CREDITS</span>
                    <span className="text-xl font-bold text-yellow-400 font-mono">{credits.toLocaleString()}</span>
                </div>

                <div className="mt-6 grid gap-3">
                    <button
                        onClick={handleResume}
                        className="w-full py-3 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-bold"
                    >
                        RESUME
                    </button>
                    <button
                        onClick={() => setShopOpen(true)}
                        className="w-full py-3 bg-gradient-to-r from-yellow-600 to-yellow-500 hover:from-yellow-500 hover:to-yellow-400 rounded text-white font-bold flex items-center justify-center gap-2"
                    >
                        <ShoppingCart className="w-5 h-5" />
                        WEAPON SHOP
                    </button>
                    <button
                        onClick={handleExitToDashboard}
                        className="w-full py-3 bg-slate-700 hover:bg-slate-600 rounded text-white font-bold"
                    >
                        EXIT TO DATA PLANETS
                    </button>
                    <button
                        onClick={handleExitToDesktop}
                        className="w-full py-3 bg-red-600 hover:bg-red-500 rounded text-white font-bold"
                    >
                        EXIT TO DESKTOP
                    </button>
                </div>

                {exitHint && (
                    <div className="mt-4 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-2">
                        Close this tab to exit. Your browser blocked window.close().
                    </div>
                )}
            </div>

            {/* Weapon Shop Modal */}
            <WeaponShop isOpen={shopOpen} onClose={() => setShopOpen(false)} />
        </div>
    )
}
