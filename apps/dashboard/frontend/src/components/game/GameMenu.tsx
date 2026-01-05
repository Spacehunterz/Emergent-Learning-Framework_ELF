import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Trophy, Github, Lock, Rocket, Sparkles, Navigation, Zap, Crown } from 'lucide-react';
import { useGame } from '../../context/GameContext';
import { useSound } from './systems/SoundManager';
import { Leaderboard } from './Leaderboard';

type MenuTab = 'ships' | 'trails' | 'leaderboard';

export const GameMenu: React.FC = () => {
    const {
        isMenuOpen,
        toggleMenu,
        score,

        unlockedCursors,
        githubUser,
        login,
        logout,
        verifyStar,
        setIsSetupOpen,
        isGameEnabled,
        toggleGameMode,
        activeShip,
        setActiveShip,
        activeTrail,
        setActiveTrail,
        viewMode,
        toggleViewMode
    } = useGame();
    const sound = useSound();

    const [activeTab, setActiveTab] = useState<MenuTab>('ships');

    const handleLoginClick = async () => {
        try {
            const res = await fetch('/api/setup/status');
            const data = await res.json();
            if (data.configured) {
                login();
            } else {
                setIsSetupOpen(true);
            }
        } catch (e) {
            login();
        }
    };

    return (
        <AnimatePresence>
            {isMenuOpen && (
                <div className="fixed inset-0 z-[100000] flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="w-full max-w-4xl bg-slate-900 border border-cyan-500/30 rounded-2xl overflow-hidden shadow-[0_0_50px_rgba(6,182,212,0.3)] flex flex-col max-h-[80vh]"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 border-b border-cyan-500/20 bg-cyan-950/20 shrink-0">
                            <div className="flex items-center gap-3">
                                <Trophy className="w-6 h-6 text-cyan-400" />
                                <h2 className="text-xl font-bold text-white tracking-widest uppercase font-mono">
                                    Cosmic <span className="text-cyan-400">Armory</span>
                                </h2>
                            </div>
                            <div className="flex items-center gap-6">
                                <div className="text-right">
                                    <div className="text-xs text-slate-400 uppercase tracking-wider">Current Score</div>
                                    <div className="text-2xl font-black text-white font-mono">{score.toLocaleString()}</div>
                                </div>
                                <button
                                    onClick={toggleMenu}
                                    className="p-2 hover:bg-white/10 rounded-full transition-colors"
                                >
                                    <X className="w-6 h-6 text-slate-400 hover:text-white" />
                                </button>
                            </div>
                        </div>

                        {/* Content Grid */}
                        <div className="grid grid-cols-[240px_1fr] flex-1 min-h-0">
                            {/* Sidebar / Navigation */}
                            <div className="p-4 border-r border-white/5 bg-black/20 overflow-y-auto flex flex-col gap-2">
                                {/* Toggle Game Mode */}
                                <button
                                    onClick={toggleGameMode}
                                    className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all mb-4 ${isGameEnabled
                                        ? 'bg-red-500/20 border-red-500 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                                        : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'
                                        }`}
                                >
                                    <Zap className="w-4 h-4" />
                                    <span className="font-bold text-sm">
                                        {isGameEnabled ? 'GAME MODE: ON' : 'GAME MODE: OFF'}
                                    </span>
                                </button>

                                {/* Toggle View Mode */}
                                {isGameEnabled && (
                                    <button
                                        onClick={toggleViewMode}
                                        className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all mb-4 ${viewMode === 'cockpit'
                                            ? 'bg-purple-500/20 border-purple-500 text-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.3)]'
                                            : 'bg-blue-500/20 border-blue-500 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]'
                                            }`}
                                    >
                                        <Navigation className="w-4 h-4" />
                                        <span className="font-bold text-sm">
                                            {viewMode === 'cockpit' ? '3D COCKPIT' : '2D ARCADE'}
                                        </span>
                                    </button>
                                )}

                                {/* Tabs */}


                                <button
                                    onClick={() => { setActiveTab('ships'); sound.playUiClick() }}
                                    onMouseEnter={() => sound.playUiHover()}
                                    className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all ${activeTab === 'ships' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:bg-white/5'}`}
                                >
                                    <Rocket className="w-4 h-4" />
                                    <span className="font-bold text-sm">Ships</span>
                                </button>

                                <button
                                    onClick={() => { setActiveTab('trails'); sound.playUiClick() }}
                                    onMouseEnter={() => sound.playUiHover()}
                                    className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all ${activeTab === 'trails' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:bg-white/5'}`}
                                >
                                    <Sparkles className="w-4 h-4" />
                                    <span className="font-bold text-sm">Trails</span>
                                </button>

                                <button
                                    onClick={() => { setActiveTab('leaderboard'); sound.playUiClick() }}
                                    onMouseEnter={() => sound.playUiHover()}
                                    className={`w-full flex items-center gap-3 p-3 rounded-lg transition-all ${activeTab === 'leaderboard' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'text-slate-400 hover:bg-white/5'}`}
                                >
                                    <Crown className="w-4 h-4" />
                                    <span className="font-bold text-sm">Leaderboard</span>
                                </button>

                                <div className="mt-auto pt-8">
                                    {githubUser ? (
                                        <div className="flex items-center gap-3 bg-white/5 p-2 rounded-lg border border-green-500/30">
                                            <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center border border-green-500/50 overflow-hidden">
                                                {githubUser.avatar_url ? (
                                                    <img src={githubUser.avatar_url} alt={githubUser.username} />
                                                ) : (
                                                    <Github className="w-5 h-5 text-green-400" />
                                                )}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-xs text-green-400 font-mono">PILOT IDENTIFIED</div>
                                                <div className="text-sm font-bold truncate">{githubUser.username}</div>
                                            </div>
                                            <button
                                                onClick={logout}
                                                className="text-[10px] bg-red-500/10 hover:bg-red-500/20 text-red-500 px-2 py-1 rounded transition-colors"
                                            >
                                                LOGOUT
                                            </button>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={handleLoginClick}
                                            className="w-full py-3 bg-[#24292e] hover:bg-[#2f363d] text-white rounded-lg flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98] shadow-lg border border-white/10"
                                        >
                                            <Github className="w-5 h-5" />
                                            <span className="font-bold">Link GitHub</span>
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Main Panel Content */}
                            <div className="p-6 overflow-y-auto custom-scrollbar bg-slate-900/50">



                                {/* SHIPS TAB */}
                                {activeTab === 'ships' && (
                                    <div className="space-y-4">
                                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Select Ship</h3>

                                        {/* Default Cursor */}
                                        <div
                                            onClick={() => setActiveShip('default')}
                                            className={`relative p-4 rounded-xl border transition-all cursor-pointer ${activeShip === 'default'
                                                ? 'bg-purple-500/20 border-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.2)]'
                                                : 'bg-white/5 border-white/10 hover:border-white/30'
                                                }`}
                                        >
                                            <div className="flex justify-between items-center">
                                                <div className="flex items-center gap-3">
                                                    <Navigation className="w-5 h-5 text-slate-400" />
                                                    <div>
                                                        <div className="font-bold text-white">System Cursor</div>
                                                        <div className="text-xs text-slate-500">Standard interface pointer.</div>
                                                    </div>
                                                </div>
                                                {activeShip === 'default' && <div className="text-xs font-bold text-purple-400 bg-purple-400/10 px-2 py-1 rounded">EQUIPPED</div>}
                                            </div>
                                        </div>



                                        {/* Star Ship - Locked behind GitHub star */}
                                        <div
                                            onClick={() => unlockedCursors.includes('star_ship') ? setActiveShip('star_ship') : verifyStar()}
                                            className={`relative p-4 rounded-xl border transition-all cursor-pointer ${activeShip === 'star_ship'
                                                ? 'bg-amber-500/20 border-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.2)]'
                                                : 'bg-white/5 border-white/10 hover:border-white/30'
                                                }`}
                                        >
                                            <div className="flex justify-between items-center">
                                                <div className="flex items-center gap-3">
                                                    <div className={`p-2 rounded-lg ${activeShip === 'star_ship' ? 'bg-amber-500/20' : 'bg-slate-800'}`}>
                                                        {unlockedCursors.includes('star_ship') ? (
                                                            <Rocket className={`w-5 h-5 ${activeShip === 'star_ship' ? 'text-amber-400' : 'text-slate-400'}`} />
                                                        ) : (
                                                            <Lock className="w-5 h-5 text-slate-500" />
                                                        )}
                                                    </div>
                                                    <div>
                                                        <div className="font-bold text-white">Star Fighter</div>
                                                        <div className="text-xs text-slate-500">Interceptor class. Gold plating.</div>
                                                    </div>
                                                </div>
                                                {!unlockedCursors.includes('star_ship') && (
                                                    <span className="text-[10px] uppercase font-bold text-amber-500/80 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20">
                                                        Star Repo to Unlock
                                                    </span>
                                                )}
                                                {activeShip === 'star_ship' && <div className="text-xs font-bold text-amber-400 bg-amber-400/10 px-2 py-1 rounded">EQUIPPED</div>}
                                            </div>
                                        </div>

                                        {/* Drone */}
                                        <div
                                            onClick={() => unlockedCursors.includes('star_ship') ? setActiveShip('drone') : verifyStar()}
                                            className={`relative p-4 rounded-xl border transition-all cursor-pointer ${activeShip === 'drone'
                                                ? 'bg-emerald-500/20 border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
                                                : 'bg-white/5 border-white/10 hover:border-white/30'
                                                }`}
                                        >
                                            <div className="flex justify-between items-center">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-full border border-emerald-500 bg-emerald-900/20 flex items-center justify-center">
                                                        {unlockedCursors.includes('star_ship') ? (
                                                            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                                        ) : (
                                                            <Lock className="w-4 h-4 text-emerald-500/50" />
                                                        )}
                                                    </div>
                                                    <div>
                                                        <div className="font-bold text-white">Surveillance Drone</div>
                                                        <div className="text-xs text-slate-500">Autonomous unit. High precision.</div>
                                                    </div>
                                                </div>
                                                {!unlockedCursors.includes('star_ship') && (
                                                    <span className="text-[10px] uppercase font-bold text-emerald-500/80 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
                                                        Star Repo to Unlock
                                                    </span>
                                                )}
                                                {activeShip === 'drone' && <div className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded">EQUIPPED</div>}
                                            </div>
                                        </div>

                                        {/* Glitch */}
                                        <div
                                            onClick={() => unlockedCursors.includes('star_ship') ? setActiveShip('glitch') : verifyStar()}
                                            className={`relative p-4 rounded-xl border transition-all cursor-pointer ${activeShip === 'glitch'
                                                ? 'bg-fuchsia-500/20 border-fuchsia-500 shadow-[0_0_15px_rgba(217,70,239,0.2)]'
                                                : 'bg-white/5 border-white/10 hover:border-white/30'
                                                }`}
                                        >
                                            <div className="flex justify-between items-center">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded border border-fuchsia-500 bg-slate-800 flex items-center justify-center overflow-hidden">
                                                        {unlockedCursors.includes('star_ship') ? (
                                                            <>
                                                                <div className="absolute inset-0 bg-fuchsia-500/20 animate-pulse" />
                                                                <div className="text-xs font-mono text-fuchsia-400 font-bold">ERR</div>
                                                            </>
                                                        ) : (
                                                            <Lock className="w-4 h-4 text-fuchsia-500/50" />
                                                        )}
                                                    </div>
                                                    <div>
                                                        <div className="font-bold text-white">System Glitch</div>
                                                        <div className="text-xs text-slate-500">Anomaly detected. Unstable.</div>
                                                    </div>
                                                </div>
                                                {!unlockedCursors.includes('star_ship') && (
                                                    <span className="text-[10px] uppercase font-bold text-fuchsia-500/80 bg-fuchsia-500/10 px-2 py-1 rounded border border-fuchsia-500/20">
                                                        Star Repo to Unlock
                                                    </span>
                                                )}
                                                {activeShip === 'glitch' && <div className="text-xs font-bold text-fuchsia-400 bg-fuchsia-400/10 px-2 py-1 rounded">EQUIPPED</div>}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* TRAILS TAB */}
                                {activeTab === 'trails' && (
                                    <div className="grid grid-cols-2 gap-4">
                                        <div
                                            onClick={() => setActiveTrail('none')}
                                            className={`p-4 rounded-xl border text-center transition-all cursor-pointer ${activeTrail === 'none'
                                                ? 'bg-slate-700 border-white/50'
                                                : 'bg-white/5 border-white/10 hover:bg-white/10'
                                                }`}
                                        >
                                            <div className="text-sm font-bold">No Trail</div>
                                        </div>

                                        <div
                                            onClick={() => unlockedCursors.includes('star_ship') ? setActiveTrail('cyan') : verifyStar()}
                                            className={`p-4 rounded-xl border text-center transition-all cursor-pointer ${activeTrail === 'cyan'
                                                ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                                                : 'bg-white/5 border-white/10 hover:bg-white/10 text-cyan-700'
                                                }`}
                                        >
                                            <div className="flex items-center justify-center gap-2">
                                                {!unlockedCursors.includes('star_ship') && <Lock className="w-3 h-3 text-slate-500" />}
                                                <div className="text-sm font-bold">Cyan Ion</div>
                                            </div>
                                            {!unlockedCursors.includes('star_ship') && (
                                                <div className="text-[9px] text-cyan-500/60 mt-1">⭐ Star to Unlock</div>
                                            )}
                                        </div>

                                        <div
                                            onClick={() => unlockedCursors.includes('star_trail') ? setActiveTrail('star') : verifyStar()}
                                            className={`p-4 rounded-xl border text-center transition-all cursor-pointer ${activeTrail === 'star'
                                                ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                                                : 'bg-white/5 border-white/10 hover:bg-white/10 text-amber-700'
                                                }`}
                                        >
                                            <div className="flex items-center justify-center gap-2">
                                                {!unlockedCursors.includes('star_trail') && <Lock className="w-3 h-3 text-slate-500" />}
                                                <div className="text-sm font-bold">Star Dust</div>
                                            </div>
                                            {!unlockedCursors.includes('star_trail') && (
                                                <div className="text-[9px] text-amber-500/60 mt-1">⭐ Star to Unlock</div>
                                            )}
                                        </div>

                                        <div
                                            onClick={() => unlockedCursors.includes('star_ship') ? setActiveTrail('plasma') : verifyStar()}
                                            className={`p-4 rounded-xl border text-center transition-all cursor-pointer ${activeTrail === 'plasma'
                                                ? 'bg-rose-500/20 border-rose-500 text-rose-300'
                                                : 'bg-white/5 border-white/10 hover:bg-white/10 text-rose-700'
                                                }`}
                                        >
                                            <div className="flex items-center justify-center gap-2">
                                                {!unlockedCursors.includes('star_ship') && <Lock className="w-3 h-3 text-slate-500" />}
                                                <div className="text-sm font-bold">Plasma Burn</div>
                                            </div>
                                            {!unlockedCursors.includes('star_ship') && (
                                                <div className="text-[9px] text-rose-500/60 mt-1">⭐ Star to Unlock</div>
                                            )}
                                        </div>

                                        <div
                                            onClick={() => unlockedCursors.includes('star_ship') ? setActiveTrail('fire') : verifyStar()}
                                            className={`p-4 rounded-xl border text-center transition-all cursor-pointer ${activeTrail === 'fire'
                                                ? 'bg-orange-500/20 border-orange-500 text-orange-300'
                                                : 'bg-white/5 border-white/10 hover:bg-white/10 text-orange-700'
                                                }`}
                                        >
                                            <div className="flex items-center justify-center gap-2">
                                                {!unlockedCursors.includes('star_ship') && <Lock className="w-3 h-3 text-slate-500" />}
                                                <div className="text-sm font-bold">Solar Flare</div>
                                            </div>
                                            {!unlockedCursors.includes('star_ship') && (
                                                <div className="text-[9px] text-orange-500/60 mt-1">⭐ Star to Unlock</div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* LEADERBOARD TAB */}
                                {activeTab === 'leaderboard' && (
                                    <Leaderboard compact={false} maxEntries={10} />
                                )}

                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence >
    );
};
