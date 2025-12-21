import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Play, BookOpen, Settings, ChevronLeft, Mouse, Shield, Zap, Target, Heart, Crosshair } from 'lucide-react'
import { useGameSettings, GraphicsQuality, GRAPHICS_PRESETS } from '../systems/GameSettings'
import { useSound } from '../systems/SoundManager'

type MenuScreen = 'main' | 'howToPlay' | 'settings'

export const MainMenu: React.FC = () => {
    const { showMainMenu, setShowMainMenu, graphicsQuality, setGraphicsQuality } = useGameSettings()
    const sound = useSound()
    const [currentScreen, setCurrentScreen] = useState<MenuScreen>('main')

    const handlePlayGame = () => {
        sound.playUiClick()
        setShowMainMenu(false)
    }

    const handleNavigation = (screen: MenuScreen) => {
        sound.playUiClick()
        setCurrentScreen(screen)
    }

    const handleQualityChange = (quality: GraphicsQuality) => {
        sound.playUiClick()
        setGraphicsQuality(quality)
    }

    if (!showMainMenu) return null

    return (
        <div className="fixed inset-0 z-[200000] flex items-center justify-center bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
            {/* Animated starfield background */}
            <div className="absolute inset-0 overflow-hidden">
                {Array.from({ length: 100 }).map((_, i) => (
                    <div
                        key={i}
                        className="absolute w-1 h-1 bg-white rounded-full animate-pulse"
                        style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            opacity: 0.2 + Math.random() * 0.5,
                            animationDelay: `${Math.random() * 2}s`,
                            animationDuration: `${2 + Math.random() * 3}s`
                        }}
                    />
                ))}
            </div>

            <AnimatePresence mode="wait">
                {/* MAIN MENU */}
                {currentScreen === 'main' && (
                    <motion.div
                        key="main"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="relative z-10 text-center"
                    >
                        {/* Game Title */}
                        <motion.h1
                            initial={{ scale: 0.8 }}
                            animate={{ scale: 1 }}
                            className="text-6xl font-black tracking-[0.3em] text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 mb-2"
                        >
                            COSMIC
                        </motion.h1>
                        <motion.h2
                            initial={{ scale: 0.8 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.1 }}
                            className="text-4xl font-bold tracking-[0.5em] text-white/80 mb-16"
                        >
                            STRIKER
                        </motion.h2>

                        {/* Menu Buttons */}
                        <div className="flex flex-col gap-4 items-center">
                            <motion.button
                                whileHover={{ scale: 1.05, boxShadow: '0 0 30px rgba(6, 182, 212, 0.5)' }}
                                whileTap={{ scale: 0.95 }}
                                onClick={handlePlayGame}
                                onMouseEnter={() => sound.playUiHover()}
                                className="w-72 py-4 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-white font-bold text-xl rounded-lg flex items-center justify-center gap-3 shadow-[0_0_20px_rgba(6,182,212,0.3)] border border-cyan-400/30 transition-all"
                            >
                                <Play className="w-6 h-6" />
                                PLAY GAME
                            </motion.button>

                            <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => handleNavigation('howToPlay')}
                                onMouseEnter={() => sound.playUiHover()}
                                className="w-72 py-4 bg-white/5 hover:bg-white/10 text-white font-bold text-xl rounded-lg flex items-center justify-center gap-3 border border-white/10 hover:border-white/30 transition-all"
                            >
                                <BookOpen className="w-6 h-6" />
                                HOW TO PLAY
                            </motion.button>

                            <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => handleNavigation('settings')}
                                onMouseEnter={() => sound.playUiHover()}
                                className="w-72 py-4 bg-white/5 hover:bg-white/10 text-white font-bold text-xl rounded-lg flex items-center justify-center gap-3 border border-white/10 hover:border-white/30 transition-all"
                            >
                                <Settings className="w-6 h-6" />
                                SETTINGS
                            </motion.button>
                        </div>

                        {/* Version */}
                        <p className="mt-16 text-slate-500 text-sm tracking-wider">
                            v1.0 | Emergent Learning Framework
                        </p>
                    </motion.div>
                )}

                {/* HOW TO PLAY */}
                {currentScreen === 'howToPlay' && (
                    <motion.div
                        key="howToPlay"
                        initial={{ opacity: 0, x: 50 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -50 }}
                        className="relative z-10 bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-8 max-w-2xl w-full mx-4 shadow-[0_0_50px_rgba(6,182,212,0.2)]"
                    >
                        <button
                            onClick={() => handleNavigation('main')}
                            onMouseEnter={() => sound.playUiHover()}
                            className="absolute top-4 left-4 p-2 hover:bg-white/10 rounded-lg transition-colors flex items-center gap-2 text-slate-400 hover:text-white"
                        >
                            <ChevronLeft className="w-5 h-5" />
                            Back
                        </button>

                        <h2 className="text-3xl font-bold text-center text-cyan-400 mb-8 tracking-wider">
                            HOW TO PLAY
                        </h2>

                        {/* Controls Section */}
                        <div className="space-y-6">
                            <h3 className="text-lg font-bold text-white border-b border-white/10 pb-2 flex items-center gap-2">
                                <Mouse className="w-5 h-5 text-cyan-400" />
                                CONTROLS
                            </h3>

                            <div className="grid gap-4">
                                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-lg">
                                    <div className="w-24 h-12 bg-slate-800 rounded-lg flex items-center justify-center border border-cyan-500/30">
                                        <span className="text-cyan-400 font-mono font-bold">LEFT</span>
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-white font-bold flex items-center gap-2">
                                            <Crosshair className="w-4 h-4 text-cyan-400" />
                                            Fire Weapons
                                        </div>
                                        <div className="text-slate-400 text-sm">Hold to auto-fire. Watch your energy!</div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-lg">
                                    <div className="w-24 h-12 bg-slate-800 rounded-lg flex items-center justify-center border border-purple-500/30">
                                        <span className="text-purple-400 font-mono font-bold">MIDDLE</span>
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-white font-bold flex items-center gap-2">
                                            <Zap className="w-4 h-4 text-purple-400" />
                                            Activate Overcharge
                                        </div>
                                        <div className="text-slate-400 text-sm">Consume stored charge for a turbo burst. Build charge by killing enemies.</div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-lg">
                                    <div className="w-24 h-12 bg-slate-800 rounded-lg flex items-center justify-center border border-blue-500/30">
                                        <span className="text-blue-400 font-mono font-bold">RIGHT</span>
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-white font-bold flex items-center gap-2">
                                            <Shield className="w-4 h-4 text-blue-400" />
                                            Shield Bubble
                                        </div>
                                        <div className="text-slate-400 text-sm">Hold to deploy shield. Reflects projectiles! Drains shield energy.</div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-lg">
                                    <div className="w-24 h-12 bg-slate-800 rounded-lg flex items-center justify-center border border-white/20">
                                        <span className="text-white font-mono font-bold">MOVE</span>
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-white font-bold flex items-center gap-2">
                                            <Target className="w-4 h-4 text-white" />
                                            Aim
                                        </div>
                                        <div className="text-slate-400 text-sm">Move mouse to aim. Click to lock pointer.</div>
                                    </div>
                                </div>
                            </div>

                            {/* Powerups Section */}
                            <h3 className="text-lg font-bold text-white border-b border-white/10 pb-2 pt-4 flex items-center gap-2">
                                <Zap className="w-5 h-5 text-yellow-400" />
                                POWERUPS
                            </h3>

                            <div className="grid grid-cols-3 gap-4">
                                <div className="bg-white/5 p-4 rounded-lg text-center">
                                    <Heart className="w-8 h-8 text-red-400 mx-auto mb-2" />
                                    <div className="text-white font-bold text-sm">HEALTH</div>
                                    <div className="text-slate-400 text-xs">Repair hull</div>
                                </div>
                                <div className="bg-white/5 p-4 rounded-lg text-center">
                                    <Shield className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                                    <div className="text-white font-bold text-sm">SHIELD</div>
                                    <div className="text-slate-400 text-xs">Recharge shields</div>
                                </div>
                                <div className="bg-white/5 p-4 rounded-lg text-center">
                                    <Zap className="w-8 h-8 text-orange-400 mx-auto mb-2" />
                                    <div className="text-white font-bold text-sm">TURBO</div>
                                    <div className="text-slate-400 text-xs">Weapon boost</div>
                                </div>
                            </div>

                            <p className="text-center text-slate-500 text-sm mt-4">
                                Shoot powerups to collect them!
                            </p>
                        </div>
                    </motion.div>
                )}

                {/* SETTINGS */}
                {currentScreen === 'settings' && (
                    <motion.div
                        key="settings"
                        initial={{ opacity: 0, x: 50 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -50 }}
                        className="relative z-10 bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-8 max-w-md w-full mx-4 shadow-[0_0_50px_rgba(6,182,212,0.2)]"
                    >
                        <button
                            onClick={() => handleNavigation('main')}
                            onMouseEnter={() => sound.playUiHover()}
                            className="absolute top-4 left-4 p-2 hover:bg-white/10 rounded-lg transition-colors flex items-center gap-2 text-slate-400 hover:text-white"
                        >
                            <ChevronLeft className="w-5 h-5" />
                            Back
                        </button>

                        <h2 className="text-3xl font-bold text-center text-cyan-400 mb-8 tracking-wider">
                            SETTINGS
                        </h2>

                        {/* Graphics Quality */}
                        <div className="space-y-4">
                            <h3 className="text-lg font-bold text-white border-b border-white/10 pb-2">
                                GRAPHICS QUALITY
                            </h3>

                            <div className="grid grid-cols-3 gap-3">
                                {(['low', 'medium', 'high'] as GraphicsQuality[]).map((quality) => (
                                    <button
                                        key={quality}
                                        onClick={() => handleQualityChange(quality)}
                                        onMouseEnter={() => sound.playUiHover()}
                                        className={`py-3 px-4 rounded-lg font-bold uppercase transition-all ${
                                            graphicsQuality === quality
                                                ? 'bg-cyan-500 text-white shadow-[0_0_15px_rgba(6,182,212,0.5)]'
                                                : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white'
                                        }`}
                                    >
                                        {quality}
                                    </button>
                                ))}
                            </div>

                            {/* Quality Details */}
                            <div className="mt-6 p-4 bg-white/5 rounded-lg">
                                <h4 className="text-sm font-bold text-slate-400 mb-3">CURRENT SETTINGS</h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-slate-400">Star Count</span>
                                        <span className="text-white">{GRAPHICS_PRESETS[graphicsQuality].starCount.toLocaleString()}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-400">Explosion Particles</span>
                                        <span className="text-white">{GRAPHICS_PRESETS[graphicsQuality].explosionParticles}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-400">Shadows</span>
                                        <span className={GRAPHICS_PRESETS[graphicsQuality].shadowsEnabled ? 'text-green-400' : 'text-red-400'}>
                                            {GRAPHICS_PRESETS[graphicsQuality].shadowsEnabled ? 'ON' : 'OFF'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-400">Bloom</span>
                                        <span className={GRAPHICS_PRESETS[graphicsQuality].bloomEnabled ? 'text-green-400' : 'text-red-400'}>
                                            {GRAPHICS_PRESETS[graphicsQuality].bloomEnabled ? 'ON' : 'OFF'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-400">Anti-aliasing</span>
                                        <span className={GRAPHICS_PRESETS[graphicsQuality].antialiasing ? 'text-green-400' : 'text-red-400'}>
                                            {GRAPHICS_PRESETS[graphicsQuality].antialiasing ? 'ON' : 'OFF'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
