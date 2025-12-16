import React from 'react';
import { HolographicCard } from '../ui/HolographicCard';
import { LearningVelocity } from '../learning-velocity';
import { motion } from 'framer-motion';

export const CosmicAnalyticsView: React.FC = () => {
    return (
        <div className="w-full h-full overflow-y-auto p-8 pt-20 custom-scrollbar">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header Section */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-end justify-between"
                >
                    <div>
                        <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-fuchsia-400 uppercase tracking-widest filter drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                            Neural Analytics
                        </h1>
                        <p className="text-slate-400 font-mono text-sm mt-2">
                            {">>"} SYSTEM_METRICS_ANALYSIS // MODE: DEEP_DIVE
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <div className="px-3 py-1 bg-cyan-500/20 border border-cyan-500/50 rounded text-cyan-400 text-xs font-mono">
                            LIVE DATA
                        </div>
                    </div>
                </motion.div>

                {/* Main Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Primary Chart - Spans 2 cols */}
                    <div className="lg:col-span-2 bg-transparent">
                        <HolographicCard title="Learning Velocity" featured={true} className="h-full min-h-[400px]">
                            <LearningVelocity days={30} />
                        </HolographicCard>
                    </div>

                    {/* Stat Cards Column */}
                    <div className="space-y-6">
                        <HolographicCard title="Run Efficiency" delay={0.1}>
                            <div className="relative pt-2">
                                <div className="flex justify-between items-end mb-2">
                                    <span className="text-3xl font-bold text-white">84.3%</span>
                                    <span className="text-green-400 text-sm">▲ 12.5%</span>
                                </div>
                                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                                    <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full w-[84%]" />
                                </div>
                                <p className="text-xs text-slate-500 mt-3">
                                    Weekly efficiency rating based on heuristic validation success.
                                </p>
                            </div>
                        </HolographicCard>

                        <HolographicCard title="Active Heuristics" delay={0.2}>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="text-center p-2 bg-slate-800/50 rounded-lg">
                                    <div className="text-xl font-bold text-amber-400">12</div>
                                    <div className="text-[10px] text-slate-400 uppercase">Golden</div>
                                </div>
                                <div className="text-center p-2 bg-slate-800/50 rounded-lg">
                                    <div className="text-xl font-bold text-cyan-400">145</div>
                                    <div className="text-[10px] text-slate-400 uppercase">Active</div>
                                </div>
                            </div>
                        </HolographicCard>

                        <HolographicCard title="System Alerts" delay={0.3} className="border-red-500/30">
                            <div className="space-y-3">
                                <div className="flex items-center gap-3 text-sm text-red-300 bg-red-500/10 p-2 rounded border border-red-500/20">
                                    <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                                    <span>Anomaly detected in Sector 7G</span>
                                </div>
                                <div className="flex items-center gap-3 text-sm text-orange-300 bg-orange-500/10 p-2 rounded border border-orange-500/20">
                                    <div className="w-2 h-2 rounded-full bg-orange-500" />
                                    <span>Performance variance: +5%</span>
                                </div>
                            </div>
                        </HolographicCard>
                    </div>
                </div>
            </div>
        </div>
    );
};
