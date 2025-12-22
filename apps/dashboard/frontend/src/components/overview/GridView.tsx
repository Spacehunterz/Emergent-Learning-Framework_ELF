import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useDataContext } from '../../context';

interface GridViewProps {
    onDomainSelect?: (domain: string) => void;
}

export function GridView({ onDomainSelect }: GridViewProps) {
    const { heuristics } = useDataContext();

    // Extract domains from heuristics with stats (same logic as SolarSystemView)
    const domains = useMemo(() => {
        const d: Record<string, { count: number; goldenCount: number; totalConfidence: number }> = {};

        heuristics.forEach(h => {
            const domainName = h.domain || 'general';
            if (!d[domainName]) {
                d[domainName] = { count: 0, goldenCount: 0, totalConfidence: 0 };
            }
            d[domainName].count++;
            if (h.is_golden) d[domainName].goldenCount++;
            d[domainName].totalConfidence += h.confidence || 0.5;
        });

        return Object.entries(d).map(([name, data]) => ({
            name,
            count: data.count,
            goldenCount: data.goldenCount,
            avgConfidence: data.count > 0 ? data.totalConfidence / data.count : 0.5,
        })).sort((a, b) => b.count - a.count); // Sort by count descending
    }, [heuristics]);

    if (domains.length === 0) {
        return (
            <div className="container mx-auto px-4 py-8 pt-24 h-screen flex items-center justify-center">
                <div className="text-center text-slate-400">
                    <div className="text-6xl mb-4">🌌</div>
                    <p className="text-xl">No domains yet</p>
                    <p className="text-sm mt-2">Heuristics will appear here organized by domain</p>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8 pt-24 custom-scrollbar h-screen overflow-y-auto pb-24">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            >
                {domains.map((domain, idx) => (
                    <motion.div
                        key={domain.name}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.1 }}
                        className="glass-panel p-6 rounded-2xl border border-white/10 hover:border-white/30 transition-all hover:bg-white/5 cursor-pointer group shadow-lg hover:shadow-cyan-500/20"
                        onClick={() => onDomainSelect?.(domain.name)}
                    >
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <h3 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 group-hover:to-cyan-300 transition-all uppercase tracking-wider">
                                    {domain.name}
                                </h3>
                                <div className="text-xs text-slate-500 font-mono mt-1">DOMAIN NODE</div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <div className="bg-black/40 rounded-lg p-3 border border-white/5">
                                <div className="text-2xl font-mono text-white font-bold">{domain.count}</div>
                                <div className="text-[10px] text-slate-400 uppercase tracking-widest">Heuristics</div>
                            </div>
                            <div className="bg-black/40 rounded-lg p-3 border border-white/5">
                                <div className="text-2xl font-mono text-amber-400 font-bold">{domain.goldenCount}</div>
                                <div className="text-[10px] text-slate-400 uppercase tracking-widest">Golden</div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between text-xs text-slate-400 uppercase tracking-wider">
                                <span>Confidence</span>
                                <span className="text-white font-mono">{(domain.avgConfidence * 100).toFixed(0)}%</span>
                            </div>
                            <div className="h-1.5 bg-black/50 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-cyan-500 rounded-full transition-all duration-1000"
                                    style={{ width: `${domain.avgConfidence * 100}%` }}
                                />
                            </div>
                        </div>

                        <button className="w-full mt-6 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/20 text-xs font-bold uppercase tracking-widest text-slate-300 hover:text-white transition-all flex items-center justify-center gap-2 group-hover:gap-3">
                            <span>Inspect Domain</span>
                            <span>→</span>
                        </button>
                    </motion.div>
                ))}
            </motion.div>
        </div>
    );
}

export default GridView;
