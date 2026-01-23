import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle, XCircle, Clock, AlertTriangle, Search,
  ChevronRight, FileCode, RotateCcw, Eye, Zap,
  Cpu, GitBranch, Timer, Activity
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface Run {
  id: string;
  status: 'success' | 'failure' | 'running' | 'pending';
  agent_type: string;
  description: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  files_touched: string[];
  error_message?: string;
  metadata?: Record<string, any>;
}

interface CosmicRunsViewProps {
  runs: Run[];
  onRetry?: (runId: string) => void;
  onOpenInEditor?: (path: string, line?: number) => void;
  onViewChanges?: (runId: string) => void;
}

const statusConfig: Record<string, { icon: any; color: string; glowColor: string; label: string; pulse?: boolean }> = {
  success: { icon: CheckCircle, color: '#4ade80', glowColor: 'rgba(74, 222, 128, 0.5)', label: 'COMPLETE' },
  failure: { icon: XCircle, color: '#f87171', glowColor: 'rgba(248, 113, 113, 0.5)', label: 'FAILED' },
  running: { icon: Activity, color: '#38bdf8', glowColor: 'rgba(56, 189, 248, 0.5)', label: 'ACTIVE', pulse: true },
  pending: { icon: Clock, color: '#a78bfa', glowColor: 'rgba(167, 139, 250, 0.5)', label: 'QUEUED' },
};

// Animated orbital ring
const OrbitalRing = ({ size, duration, color, reverse = false }: { size: number; duration: number; color: string; reverse?: boolean }) => (
  <motion.div
    className="absolute rounded-full border"
    style={{
      width: size,
      height: size,
      borderColor: `${color}30`,
      top: '50%',
      left: '50%',
      marginTop: -size / 2,
      marginLeft: -size / 2,
    }}
    animate={{ rotate: reverse ? -360 : 360 }}
    transition={{ duration, repeat: Infinity, ease: "linear" }}
  >
    <div
      className="absolute w-2 h-2 rounded-full"
      style={{
        backgroundColor: color,
        boxShadow: `0 0 10px ${color}`,
        top: 0,
        left: '50%',
        marginLeft: -4,
        marginTop: -4,
      }}
    />
  </motion.div>
);

// Run status orb with animations
const StatusOrb = ({ status, size = 48 }: { status: string; size?: number }) => {
  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {/* Orbital rings for running status */}
      {config.pulse && (
        <>
          <OrbitalRing size={size + 20} duration={3} color={config.color} />
          <OrbitalRing size={size + 35} duration={5} color={config.color} reverse />
        </>
      )}

      {/* Pulse effect */}
      {config.pulse && (
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{ backgroundColor: `${config.color}30` }}
          animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      )}

      {/* Main orb */}
      <motion.div
        className="absolute inset-0 rounded-full flex items-center justify-center"
        style={{
          background: `radial-gradient(circle at 30% 30%, ${config.color}40 0%, ${config.color}10 100%)`,
          border: `2px solid ${config.color}60`,
          boxShadow: `0 0 20px ${config.glowColor}, inset 0 0 20px ${config.color}20`,
        }}
        animate={config.pulse ? { scale: [1, 1.05, 1] } : {}}
        transition={{ duration: 1, repeat: Infinity }}
      >
        <Icon className="w-5 h-5" style={{ color: config.color }} />
      </motion.div>
    </div>
  );
};

// Stats card component
const StatCard = ({ label, value, icon: Icon, color }: { label: string; value: number | string; icon: any; color: string }) => (
  <motion.div
    className="relative p-4 rounded-xl overflow-hidden"
    style={{
      background: `linear-gradient(135deg, ${color}10 0%, transparent 100%)`,
      border: `1px solid ${color}30`,
    }}
    whileHover={{ scale: 1.02, borderColor: `${color}60` }}
    transition={{ duration: 0.2 }}
  >
    <div className="flex items-center justify-between">
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
        <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      </div>
      <div
        className="p-3 rounded-lg"
        style={{ backgroundColor: `${color}20` }}
      >
        <Icon className="w-5 h-5" style={{ color }} />
      </div>
    </div>
  </motion.div>
);

// Run card component
const RunCard = ({
  run,
  isExpanded,
  onToggle,
  onRetry,
  onOpenInEditor,
  onViewChanges
}: {
  run: Run;
  isExpanded: boolean;
  onToggle: () => void;
  onRetry?: (runId: string) => void;
  onOpenInEditor?: (path: string) => void;
  onViewChanges?: (runId: string) => void;
}) => {
  const config = statusConfig[run.status] || statusConfig.pending;

  const formatDuration = (ms: number | null) => {
    if (ms === null) return '--:--';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative rounded-xl overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.7) 100%)',
        border: `1px solid ${isExpanded ? config.color + '50' : 'rgba(100, 116, 139, 0.2)'}`,
        boxShadow: isExpanded ? `0 0 30px ${config.glowColor}` : 'none',
      }}
    >
      {/* Top accent line */}
      <motion.div
        className="absolute top-0 left-0 right-0 h-0.5"
        style={{ backgroundColor: config.color }}
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: 0.5 }}
      />

      {/* Main content */}
      <div
        className="p-4 cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center gap-4">
          {/* Status orb */}
          <StatusOrb status={run.status} size={48} />

          {/* Run info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <span className="text-white font-semibold truncate">{run.description}</span>
              <span
                className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase"
                style={{
                  backgroundColor: `${config.color}20`,
                  color: config.color,
                  border: `1px solid ${config.color}40`
                }}
              >
                {config.label}
              </span>
            </div>

            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Cpu className="w-3 h-3" />
                {run.agent_type}
              </span>
              <span className="flex items-center gap-1">
                <Timer className="w-3 h-3" />
                {formatDuration(run.duration_ms)}
              </span>
              <span className="flex items-center gap-1">
                <FileCode className="w-3 h-3" />
                {run.files_touched.length} files
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
              </span>
            </div>
          </div>

          {/* Expand button */}
          <motion.div
            animate={{ rotate: isExpanded ? 90 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronRight className="w-5 h-5 text-slate-500" />
          </motion.div>
        </div>
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-2 border-t border-slate-800/50">
              {/* Error message */}
              {run.error_message && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30"
                >
                  <div className="flex items-center gap-2 text-red-400 text-sm mb-1">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="font-semibold">Error</span>
                  </div>
                  <p className="text-red-300 text-sm font-mono">{run.error_message}</p>
                </motion.div>
              )}

              {/* Files touched */}
              {run.files_touched.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Files Modified</p>
                  <div className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
                    {run.files_touched.map((file, index) => (
                      <motion.button
                        key={file}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        onClick={() => onOpenInEditor?.(file)}
                        className="w-full flex items-center gap-2 p-2 rounded-lg bg-slate-800/50 hover:bg-slate-800 text-left transition group"
                      >
                        <FileCode className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                        <span className="text-sm text-slate-300 truncate group-hover:text-cyan-400 transition">
                          {file}
                        </span>
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2">
                {run.status === 'failure' && onRetry && (
                  <motion.button
                    onClick={() => onRetry(run.id)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 text-sm transition"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <RotateCcw className="w-4 h-4" />
                    Retry Run
                  </motion.button>
                )}
                {onViewChanges && (
                  <motion.button
                    onClick={() => onViewChanges(run.id)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 text-sm transition"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Eye className="w-4 h-4" />
                    View Changes
                  </motion.button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export const CosmicRunsView: React.FC<CosmicRunsViewProps> = ({
  runs,
  onRetry,
  onOpenInEditor,
  onViewChanges
}) => {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filter runs
  const filteredRuns = useMemo(() => {
    return runs.filter(run => {
      if (statusFilter && run.status !== statusFilter) return false;
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          run.description.toLowerCase().includes(query) ||
          run.agent_type.toLowerCase().includes(query) ||
          run.files_touched.some(f => f.toLowerCase().includes(query))
        );
      }
      return true;
    });
  }, [runs, statusFilter, searchQuery]);

  // Stats
  const stats = useMemo(() => {
    const total = runs.length;
    const success = runs.filter(r => r.status === 'success').length;
    const failure = runs.filter(r => r.status === 'failure').length;
    const running = runs.filter(r => r.status === 'running').length;
    const avgDuration = runs
      .filter(r => r.duration_ms)
      .reduce((sum, r) => sum + (r.duration_ms || 0), 0) / (runs.filter(r => r.duration_ms).length || 1);

    return { total, success, failure, running, avgDuration };
  }, [runs]);

  return (
    <div className="w-full h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b border-slate-800/50">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-6"
        >
          <div>
            <h1 className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 uppercase tracking-widest">
              Mission Control
            </h1>
            <p className="text-slate-500 font-mono text-xs mt-1">
              {">>"} AGENT_OPERATIONS // {stats.total} MISSIONS
            </p>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search missions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 w-64"
            />
          </div>
        </motion.div>

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard label="Total Runs" value={stats.total} icon={GitBranch} color="#38bdf8" />
          <StatCard label="Successful" value={stats.success} icon={CheckCircle} color="#4ade80" />
          <StatCard label="Failed" value={stats.failure} icon={XCircle} color="#f87171" />
          <StatCard
            label="Avg Duration"
            value={stats.avgDuration > 0 ? `${(stats.avgDuration / 1000).toFixed(1)}s` : '--'}
            icon={Timer}
            color="#a78bfa"
          />
        </div>

        {/* Status filters */}
        <div className="flex gap-2">
          <motion.button
            onClick={() => setStatusFilter(null)}
            className={`px-4 py-2 rounded-lg text-sm font-mono transition-all ${
              !statusFilter
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/50 text-white'
                : 'bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white'
            }`}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            ALL
          </motion.button>
          {Object.entries(statusConfig).map(([status, config]) => (
            <motion.button
              key={status}
              onClick={() => setStatusFilter(statusFilter === status ? null : status)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-mono transition-all ${
                statusFilter === status
                  ? 'border text-white'
                  : 'bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white'
              }`}
              style={{
                borderColor: statusFilter === status ? `${config.color}80` : undefined,
                backgroundColor: statusFilter === status ? `${config.color}20` : undefined,
              }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color }} />
              {config.label}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Runs list */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
        <div className="space-y-3">
          <AnimatePresence>
            {filteredRuns.map((run, index) => (
              <motion.div
                key={run.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ delay: index * 0.05 }}
              >
                <RunCard
                  run={run}
                  isExpanded={expandedId === run.id}
                  onToggle={() => setExpandedId(expandedId === run.id ? null : run.id)}
                  onRetry={onRetry}
                  onOpenInEditor={onOpenInEditor}
                  onViewChanges={onViewChanges}
                />
              </motion.div>
            ))}
          </AnimatePresence>

          {filteredRuns.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                className="w-20 h-20 rounded-full border-2 border-dashed border-slate-700 flex items-center justify-center mb-6"
              >
                <Zap className="w-8 h-8 text-slate-600" />
              </motion.div>
              <p className="text-slate-500 font-mono">No missions found</p>
              <p className="text-slate-600 text-sm mt-2">
                {searchQuery ? 'Try adjusting your search' : 'Runs will appear here as agents complete tasks'}
              </p>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CosmicRunsView;
