import { useGame } from '../../../context/GameContext'

export const GameOverScreen = () => {
    const { score, level, restartGame } = useGame()

    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="p-8 border border-red-500/50 bg-black/90 rounded-lg shadow-2xl shadow-red-900/50 text-center max-w-sm w-full relative overflow-hidden">
                {/* Scanline Effect */}
                <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.5)_50%)] bg-[length:100%_4px] pointer-events-none opacity-20" />

                <h1 className="text-5xl font-bold text-red-500 mb-2 tracking-widest uppercase dropped-shadow-lg glitch-text">
                    CRITICAL FAILURE
                </h1>

                <div className="flex justify-center my-6 space-x-8">
                    <div className="text-center">
                        <div className="text-xs text-red-400/70 mb-1">SCORE</div>
                        <div className="text-2xl font-mono text-white">{score.toLocaleString()}</div>
                    </div>
                    <div className="text-center">
                        <div className="text-xs text-red-400/70 mb-1">WAVE</div>
                        <div className="text-2xl font-mono text-cyan-400">{level}</div>
                    </div>
                </div>

                <div className="border-t border-red-900/30 my-6" />

                <button
                    onClick={restartGame}
                    className="w-full py-4 text-center bg-red-600 hover:bg-red-500 text-black font-bold text-xl uppercase tracking-widest transition-all duration-300 hover:scale-105 active:scale-95 shadow-lg shadow-red-500/20 clip-path-polygon"
                >
                    REBOOT SYSTEM
                </button>
            </div>

            {/* Global Glitch Animation Styles (if not present) */}
            <style>{`
                .glitch-text {
                    text-shadow: 2px 2px 0px #ff0000, -2px -2px 0px #00ffff;
                }
                .clip-path-polygon {
                    clip-path: polygon(10% 0, 100% 0, 100% 70%, 90% 100%, 0 100%, 0 30%);
                }
            `}</style>
        </div>
    )
}
