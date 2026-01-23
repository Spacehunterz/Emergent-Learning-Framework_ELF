import React, { useMemo, useState, useEffect } from 'react';
import { HolographicCard } from '../ui/HolographicCard';
import { LearningVelocity } from '../learning-velocity';
import { motion, AnimatePresence } from 'framer-motion';
import { useDataContext } from '../../context/DataContext';
import {
  Brain, Star, TrendingUp, Activity, Target,
  AlertTriangle, CheckCircle, Maximize2, X
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { createPortal } from 'react-dom';
import { AnalyticsDrillDown, AnalyticsDrillDownType } from '../analytics';

interface CosmicAnalyticsViewProps {
  onNavigate?: (tab: string, domain?: string) => void;
}

// Animated particle
const Particle = ({ delay = 0 }: { delay?: number }) => {
  const randomX = Math.random() * 100;
  const randomDuration = 10 + Math.random() * 20;

  return (
    <motion.div
      className="absolute w-1 h-1 bg-cyan-400/30 rounded-full"
      style={{ left: `${randomX}%` }}
      initial={{ y: '100%', opacity: 0 }}
      animate={{
        y: '-100%',
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: randomDuration,
        delay,
        repeat: Infinity,
        ease: "linear"
      }}
    />
  );
};

// Animated ring visualization
const PulseRing = ({ color, size, delay = 0 }: { color: string; size: number; delay?: number }) => (
  <motion.div
    className="absolute rounded-full"
    style={{
      width: size,
      height: size,
      border: `2px solid ${color}`,
      top: '50%',
      left: '50%',
      marginTop: -size / 2,
      marginLeft: -size / 2,
    }}
    initial={{ scale: 0.8, opacity: 0.8 }}
    animate={{
      scale: [0.8, 1.2, 0.8],
      opacity: [0.8, 0, 0.8],
    }}
    transition={{
      duration: 3,
      delay,
      repeat: Infinity,
      ease: "easeInOut"
    }}
  />
);

// Animated stat display
const AnimatedNumber = ({ value, suffix = '' }: { value: number; suffix?: string }) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 1500;
    const steps = 60;
    const increment = value / steps;
    let current = 0;
    const interval = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(interval);
      } else {
        setDisplayValue(Math.floor(current));
      }
    }, duration / steps);

    return () => clearInterval(interval);
  }, [value]);

  return <span>{displayValue.toLocaleString()}{suffix}</span>;
};

// Clickable Gauge component
const ClickableGauge = ({
  value,
  label,
  color,
  onClick
}: {
  value: number;
  label: string;
  color: string;
  onClick?: () => void;
}) => {
  const percentage = Math.min(100, Math.max(0, value));
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <motion.div
      className="relative w-32 h-32 mx-auto cursor-pointer group"
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
    >
      {/* Background ring */}
      <svg className="w-full h-full -rotate-90">
        <circle
          cx="64"
          cy="64"
          r="45"
          fill="none"
          stroke="rgba(100, 116, 139, 0.2)"
          strokeWidth="8"
        />
        <motion.circle
          cx="64"
          cy="64"
          r="45"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
          style={{
            filter: `drop-shadow(0 0 10px ${color})`,
          }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="text-2xl font-bold"
          style={{ color }}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.5, type: "spring" }}
        >
          {percentage.toFixed(1)}%
        </motion.span>
        <span className="text-xs text-slate-500 uppercase">{label}</span>
        <span className="text-[10px] text-slate-600 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          Click for details
        </span>
      </div>

      {/* Glow effect */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: `radial-gradient(circle, ${color}20 0%, transparent 70%)`,
        }}
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.5, 0.8, 0.5],
        }}
        transition={{ duration: 2, repeat: Infinity }}
      />

      {/* Hover indicator */}
      <div className="absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Maximize2 className="w-4 h-4 text-slate-400" />
      </div>
    </motion.div>
  );
};

// Domain breakdown card with click
const DomainBreakdown = ({
  heuristics,
  onClick,
  onDomainClick
}: {
  heuristics: any[];
  onClick?: () => void;
  onDomainClick?: (domain: string) => void;
}) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const domainData = useMemo(() => {
    const counts: Record<string, number> = {};
    heuristics.forEach(h => {
      counts[h.domain] = (counts[h.domain] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
  }, [heuristics]);

  const colors = ['#38bdf8', '#4ade80', '#fbbf24', '#a78bfa', '#f87171', '#fb923c'];

  return (
    <div className="h-full">
      <div className="cursor-pointer" onClick={onClick}>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={domainData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={activeIndex !== null ? 85 : 80}
              paddingAngle={2}
              dataKey="value"
              onMouseEnter={(_, index) => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
              onClick={(data) => {
                if (onDomainClick) {
                  onDomainClick(data.name);
                }
              }}
            >
              {domainData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={colors[index % colors.length]}
                  stroke={activeIndex === index ? '#fff' : 'transparent'}
                  strokeWidth={activeIndex === index ? 2 : 0}
                  style={{
                    filter: activeIndex === index
                      ? `drop-shadow(0 0 15px ${colors[index % colors.length]})`
                      : `drop-shadow(0 0 8px ${colors[index % colors.length]}60)`,
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                  }}
                />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-slate-900/95 border border-slate-700 rounded-lg px-3 py-2 text-sm">
                      <p className="text-white font-semibold">{payload[0].name}</p>
                      <p className="text-cyan-400">{payload[0].value} heuristics</p>
                      <p className="text-[10px] text-slate-500 mt-1">Click to filter</p>
                    </div>
                  );
                }
                return null;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend - clickable */}
      <div className="grid grid-cols-2 gap-2 mt-4">
        {domainData.map((item, index) => (
          <motion.button
            key={item.name}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center gap-2 text-xs p-1 rounded hover:bg-white/5 transition-colors text-left"
            onClick={() => onDomainClick?.(item.name)}
          >
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: colors[index % colors.length] }}
            />
            <span className="text-slate-400 truncate">{item.name}</span>
            <span className="text-slate-500 ml-auto">{item.value}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
};

// Activity timeline mini chart with click
const ActivityTimeline = ({
  runs,
  onClick
}: {
  runs: any[];
  onClick?: () => void;
}) => {
  const chartData = useMemo(() => {
    const last7Days: Record<string, { success: number; failure: number }> = {};
    const now = new Date();

    for (let i = 6; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const key = date.toISOString().split('T')[0];
      last7Days[key] = { success: 0, failure: 0 };
    }

    runs.forEach(run => {
      const dateStr = run.started_at || run.created_at;
      if (dateStr) {
        const date = dateStr.split('T')[0];
        if (last7Days[date]) {
          if (run.status === 'success' || run.status === 'completed') last7Days[date].success++;
          else if (run.status === 'failure' || run.status === 'failed') last7Days[date].failure++;
        }
      }
    });

    return Object.entries(last7Days).map(([date, counts]) => ({
      date: date.slice(5), // MM-DD
      success: counts.success,
      failure: counts.failure,
    }));
  }, [runs]);

  return (
    <motion.div
      className="cursor-pointer group"
      whileHover={{ scale: 1.02 }}
      onClick={onClick}
    >
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <Maximize2 className="w-4 h-4 text-slate-400" />
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="successGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#4ade80" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#4ade80" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="failureGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f87171" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
          <YAxis hide />
          <Tooltip
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="bg-slate-900/95 border border-slate-700 rounded-lg px-3 py-2 text-xs">
                    <p className="text-slate-400 mb-1">{label}</p>
                    <p className="text-emerald-400">Success: {payload[0]?.value}</p>
                    <p className="text-red-400">Failed: {payload[1]?.value}</p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Area type="monotone" dataKey="success" stroke="#4ade80" fill="url(#successGradient)" strokeWidth={2} />
          <Area type="monotone" dataKey="failure" stroke="#f87171" fill="url(#failureGradient)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

// Expanded chart modal
const ExpandedChartModal = ({
  isOpen,
  onClose,
  title,
  children
}: {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) => {
  if (!isOpen) return null;

  return createPortal(
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[99998] flex items-center justify-center p-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          background: 'rgba(0, 0, 0, 0.9)',
          backdropFilter: 'blur(10px)',
        }}
        onClick={onClose}
      >
        <motion.div
          className="relative w-full max-w-5xl h-[80vh] rounded-2xl border overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.95) 100%)',
            borderColor: 'rgba(100, 116, 139, 0.3)',
          }}
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-slate-800">
            <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-fuchsia-400 uppercase tracking-wider">
              {title}
            </h2>
            <motion.button
              onClick={onClose}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              whileHover={{ scale: 1.1, rotate: 90 }}
              whileTap={{ scale: 0.9 }}
            >
              <X className="w-5 h-5" />
            </motion.button>
          </div>

          {/* Content */}
          <div className="p-6 h-[calc(100%-80px)] overflow-auto">
            {children}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
};

export const CosmicAnalyticsView: React.FC<CosmicAnalyticsViewProps> = ({ onNavigate }) => {
  const { stats, heuristics, runs, hotspots } = useDataContext();
  const [drillDownType, setDrillDownType] = useState<AnalyticsDrillDownType | null>(null);
  const [expandedChart, setExpandedChart] = useState<string | null>(null);

  const computedStats = useMemo(() => {
    const goldenCount = heuristics.filter(h => h.is_golden).length;
    const totalHeuristics = heuristics.length;
    const totalRuns = stats?.total_runs ?? 0;
    const successfulRuns = stats?.successful_runs ?? 0;
    const successRate = totalRuns > 0
      ? (successfulRuns / totalRuns) * 100
      : 0;
    const avgConfidence = stats?.avg_confidence ?? 0;

    return {
      goldenCount,
      totalHeuristics,
      successRate,
      avgConfidence: avgConfidence * 100,
      totalRuns,
      hotspotCount: hotspots?.length ?? 0,
    };
  }, [stats, heuristics, hotspots]);

  const handleDrillDownClose = () => {
    setDrillDownType(null);
  };

  const handleNavigate = (tab: string, domain?: string) => {
    setDrillDownType(null);
    onNavigate?.(tab, domain);
  };

  return (
    <>
      {/* Drill-down modal */}
      <AnalyticsDrillDown
        type={drillDownType!}
        isOpen={drillDownType !== null}
        onClose={handleDrillDownClose}
        onNavigate={handleNavigate}
      />

      {/* Expanded Learning Velocity modal */}
      <ExpandedChartModal
        isOpen={expandedChart === 'learning_velocity'}
        onClose={() => setExpandedChart(null)}
        title="Learning Velocity - 30 Day Analysis"
      >
        <div className="h-full">
          <LearningVelocity days={30} />
        </div>
      </ExpandedChartModal>

      <div className="w-full h-full overflow-y-auto p-8 pt-4 custom-scrollbar relative">
        {/* Animated background particles */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          {[...Array(20)].map((_, i) => (
            <Particle key={i} delay={i * 0.5} />
          ))}
        </div>

        <div className="max-w-7xl mx-auto space-y-8 relative z-10">
          {/* Header Section */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-end justify-between"
          >
            <div>
              <motion.h1
                className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-fuchsia-400 uppercase tracking-widest"
                animate={{
                  backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
                }}
                transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
                style={{
                  backgroundSize: '200% 200%',
                  filter: 'drop-shadow(0 0 20px rgba(34, 211, 238, 0.5))',
                }}
              >
                Neural Analytics
              </motion.h1>
              <p className="text-slate-400 font-mono text-sm mt-2">
                {">>"} SYSTEM_METRICS_ANALYSIS // MODE: INTERACTIVE
              </p>
            </div>
            <div className="flex gap-2">
              <motion.div
                className="px-3 py-1 bg-cyan-500/20 border border-cyan-500/50 rounded text-cyan-400 text-xs font-mono flex items-center gap-2"
                animate={{ borderColor: ['rgba(34, 211, 238, 0.5)', 'rgba(34, 211, 238, 0.8)', 'rgba(34, 211, 238, 0.5)'] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <motion.div
                  className="w-2 h-2 rounded-full bg-cyan-400"
                  animate={{ scale: [1, 1.2, 1], opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
                LIVE DATA
              </motion.div>
            </div>
          </motion.div>

          {/* Key Metrics Row - All Clickable */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            {[
              { label: 'Total Runs', value: computedStats.totalRuns, icon: Activity, color: '#38bdf8', drillDown: 'total_runs' as AnalyticsDrillDownType },
              { label: 'Success Rate', value: `${computedStats.successRate.toFixed(1)}%`, icon: TrendingUp, color: '#4ade80', drillDown: 'success_rate' as AnalyticsDrillDownType },
              { label: 'Heuristics', value: computedStats.totalHeuristics, icon: Brain, color: '#a78bfa', drillDown: 'heuristics' as AnalyticsDrillDownType },
              { label: 'Golden Rules', value: computedStats.goldenCount, icon: Star, color: '#fbbf24', drillDown: 'golden_rules' as AnalyticsDrillDownType },
            ].map((metric, index) => (
              <motion.div
                key={metric.label}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 * index }}
                className="relative p-4 rounded-xl overflow-hidden group cursor-pointer"
                style={{
                  background: `linear-gradient(135deg, ${metric.color}10 0%, transparent 100%)`,
                  border: `1px solid ${metric.color}30`,
                }}
                whileHover={{
                  scale: 1.02,
                  borderColor: `${metric.color}60`,
                  boxShadow: `0 0 30px ${metric.color}30`,
                }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setDrillDownType(metric.drillDown)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{metric.label}</p>
                    <p className="text-2xl font-bold" style={{ color: metric.color }}>
                      {typeof metric.value === 'number' ? <AnimatedNumber value={metric.value} /> : metric.value}
                    </p>
                  </div>
                  <motion.div
                    className="p-3 rounded-lg"
                    style={{ backgroundColor: `${metric.color}20` }}
                    whileHover={{ rotate: 10, scale: 1.1 }}
                  >
                    <metric.icon className="w-5 h-5" style={{ color: metric.color }} />
                  </motion.div>
                </div>

                {/* Click hint */}
                <div className="absolute bottom-2 right-2 text-[10px] text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity">
                  Click to expand
                </div>

                {/* Hover glow */}
                <motion.div
                  className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{
                    background: `radial-gradient(circle at center, ${metric.color}20 0%, transparent 70%)`,
                  }}
                />
              </motion.div>
            ))}
          </motion.div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Primary Chart - Spans 2 cols - Clickable */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="lg:col-span-2 bg-transparent"
            >
              <HolographicCard
                title="Learning Velocity"
                featured={true}
                className="h-full min-h-[400px] cursor-pointer group"
                onClick={() => setExpandedChart('learning_velocity')}
              >
                <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                  <Maximize2 className="w-5 h-5 text-slate-400" />
                </div>
                <LearningVelocity days={30} />
              </HolographicCard>
            </motion.div>

            {/* Stat Cards Column */}
            <div className="space-y-6">
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 }}
              >
                <HolographicCard title="System Health" delay={0.1}>
                  <ClickableGauge
                    value={computedStats.successRate}
                    label="Success"
                    color="#4ade80"
                    onClick={() => setDrillDownType('system_health')}
                  />
                </HolographicCard>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 }}
              >
                <HolographicCard title="Confidence Score" delay={0.2}>
                  <ClickableGauge
                    value={computedStats.avgConfidence}
                    label="Avg Conf"
                    color="#a78bfa"
                    onClick={() => setDrillDownType('confidence')}
                  />
                </HolographicCard>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 }}
              >
                <HolographicCard title="Hotspots" delay={0.3}>
                  <motion.div
                    className="flex items-center justify-between cursor-pointer group"
                    whileHover={{ scale: 1.02 }}
                    onClick={() => setDrillDownType('hotspots')}
                  >
                    <div className="relative">
                      <motion.div
                        className="w-16 h-16 rounded-full flex items-center justify-center"
                        style={{
                          background: 'linear-gradient(135deg, rgba(251, 146, 60, 0.2) 0%, rgba(251, 146, 60, 0.05) 100%)',
                          border: '2px solid rgba(251, 146, 60, 0.5)',
                        }}
                        animate={{
                          boxShadow: [
                            '0 0 20px rgba(251, 146, 60, 0.3)',
                            '0 0 40px rgba(251, 146, 60, 0.5)',
                            '0 0 20px rgba(251, 146, 60, 0.3)',
                          ],
                        }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        <Target className="w-8 h-8 text-orange-400" />
                      </motion.div>
                      <PulseRing color="rgba(251, 146, 60, 0.4)" size={80} />
                      <PulseRing color="rgba(251, 146, 60, 0.2)" size={100} delay={0.5} />
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-bold text-orange-400">
                        <AnimatedNumber value={computedStats.hotspotCount} />
                      </p>
                      <p className="text-xs text-slate-500">Active Zones</p>
                      <p className="text-[10px] text-slate-600 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        Click for details
                      </p>
                    </div>
                  </motion.div>
                </HolographicCard>
              </motion.div>
            </div>
          </div>

          {/* Secondary Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
            >
              <HolographicCard title="Domain Distribution" delay={0.4}>
                <DomainBreakdown
                  heuristics={heuristics}
                  onClick={() => setDrillDownType('domain_distribution')}
                  onDomainClick={(domain) => handleNavigate('heuristics', domain)}
                />
              </HolographicCard>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              <HolographicCard title="7-Day Activity" delay={0.5} className="relative">
                <ActivityTimeline
                  runs={runs}
                  onClick={() => setDrillDownType('activity')}
                />
                <div className="flex items-center justify-center gap-6 mt-4 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-emerald-400" />
                    <span className="text-slate-400">Success</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-400" />
                    <span className="text-slate-400">Failed</span>
                  </div>
                </div>
              </HolographicCard>
            </motion.div>
          </div>

          {/* Alert Section - Clickable */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.9 }}
          >
            <HolographicCard title="System Alerts" delay={0.6} className="border-amber-500/30">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {computedStats.successRate < 70 && (
                  <motion.button
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-left hover:bg-red-500/20 transition-colors"
                    onClick={() => setDrillDownType('success_rate')}
                    whileHover={{ x: 5 }}
                  >
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    >
                      <AlertTriangle className="w-5 h-5 text-red-400" />
                    </motion.div>
                    <div>
                      <p className="text-sm text-red-300 font-semibold">Low Success Rate</p>
                      <p className="text-xs text-red-400/70">Below 70% threshold</p>
                    </div>
                  </motion.button>
                )}

                {computedStats.goldenCount < 5 && (
                  <motion.button
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                    className="flex items-center gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-left hover:bg-amber-500/20 transition-colors"
                    onClick={() => setDrillDownType('golden_rules')}
                    whileHover={{ x: 5 }}
                  >
                    <Star className="w-5 h-5 text-amber-400" />
                    <div>
                      <p className="text-sm text-amber-300 font-semibold">Few Golden Rules</p>
                      <p className="text-xs text-amber-400/70">Consider promoting more</p>
                    </div>
                  </motion.button>
                )}

                <motion.button
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  className="flex items-center gap-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-left hover:bg-emerald-500/20 transition-colors"
                  onClick={() => setDrillDownType('system_health')}
                  whileHover={{ x: 5 }}
                >
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <div>
                    <p className="text-sm text-emerald-300 font-semibold">System Operational</p>
                    <p className="text-xs text-emerald-400/70">All services running</p>
                  </div>
                </motion.button>
              </div>
            </HolographicCard>
          </motion.div>
        </div>
      </div>
    </>
  );
};
