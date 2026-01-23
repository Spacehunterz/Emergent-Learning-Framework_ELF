import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Activity, TrendingUp, Brain, Star, Target, CheckCircle,
  XCircle, Clock, Zap, ChevronRight, ExternalLink, BarChart3,
  PieChart as PieChartIcon, LineChart as LineChartIcon
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadialBarChart,
  RadialBar, Legend, Scatter, ScatterChart, ZAxis
} from 'recharts';
import { useDataContext } from '../../context/DataContext';

// Types for drill-down
export type AnalyticsDrillDownType =
  | 'total_runs'
  | 'success_rate'
  | 'heuristics'
  | 'golden_rules'
  | 'system_health'
  | 'confidence'
  | 'hotspots'
  | 'domain_distribution'
  | 'activity'
  | 'learning_velocity';

interface AnalyticsDrillDownProps {
  type: AnalyticsDrillDownType;
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (tab: string, domain?: string) => void;
}

// Cosmic color palette
const COLORS = {
  cyan: '#22d3ee',
  violet: '#a78bfa',
  emerald: '#4ade80',
  amber: '#fbbf24',
  rose: '#f472b6',
  orange: '#fb923c',
  red: '#f87171',
  blue: '#3b82f6',
  indigo: '#6366f1',
  teal: '#14b8a6',
};

const PIE_COLORS = [COLORS.cyan, COLORS.violet, COLORS.emerald, COLORS.amber, COLORS.rose, COLORS.orange];

// Animated star background
const StarField = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {[...Array(100)].map((_, i) => (
      <motion.div
        key={i}
        className="absolute w-1 h-1 bg-white rounded-full"
        initial={{ opacity: 0 }}
        animate={{
          opacity: [0, Math.random() * 0.8 + 0.2, 0],
          scale: [0.5, 1, 0.5],
        }}
        transition={{
          duration: Math.random() * 3 + 2,
          repeat: Infinity,
          delay: Math.random() * 2,
        }}
        style={{
          left: `${Math.random() * 100}%`,
          top: `${Math.random() * 100}%`,
        }}
      />
    ))}
  </div>
);

// Custom cosmic tooltip
const CosmicTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="px-4 py-3 rounded-xl border backdrop-blur-md"
      style={{
        background: 'rgba(15, 23, 42, 0.95)',
        borderColor: 'rgba(167, 139, 250, 0.4)',
        boxShadow: '0 0 30px rgba(167, 139, 250, 0.3)',
      }}
    >
      <p className="text-xs text-slate-400 mb-2 font-mono">{label}</p>
      {payload.map((entry: any, index: number) => (
        <p key={index} className="text-sm font-bold flex items-center gap-2" style={{ color: entry.color }}>
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
        </p>
      ))}
    </motion.div>
  );
};

// Metric stat card with click action
const MetricCard = ({
  icon: Icon,
  label,
  value,
  color,
  subtext,
  onClick
}: {
  icon: any;
  label: string;
  value: string | number;
  color: string;
  subtext?: string;
  onClick?: () => void;
}) => (
  <motion.div
    className="p-5 rounded-2xl border cursor-pointer group relative overflow-hidden"
    style={{
      background: `linear-gradient(135deg, ${color}15 0%, ${color}05 100%)`,
      borderColor: `${color}40`,
    }}
    whileHover={{
      scale: 1.02,
      borderColor: `${color}80`,
      boxShadow: `0 0 40px ${color}30`,
    }}
    whileTap={{ scale: 0.98 }}
    onClick={onClick}
  >
    {/* Animated glow on hover */}
    <motion.div
      className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
      style={{
        background: `radial-gradient(circle at 50% 50%, ${color}20 0%, transparent 70%)`,
      }}
    />

    <div className="relative z-10">
      <div className="flex items-center justify-between mb-3">
        <div
          className="p-3 rounded-xl"
          style={{ background: `${color}25` }}
        >
          <Icon className="w-6 h-6" style={{ color }} />
        </div>
        <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-slate-400 transition-colors" />
      </div>
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p
        className="text-3xl font-black"
        style={{
          color,
          textShadow: `0 0 30px ${color}50`,
        }}
      >
        {value}
      </p>
      {subtext && <p className="text-xs text-slate-600 mt-1">{subtext}</p>}
    </div>
  </motion.div>
);

// Interactive radial gauge
const InteractiveGauge = ({
  value,
  label,
  color,
  onClick,
  size = 180
}: {
  value: number;
  label: string;
  color: string;
  onClick?: () => void;
  size?: number;
}) => {
  const percentage = Math.min(100, Math.max(0, value));
  const circumference = 2 * Math.PI * 70;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <motion.div
      className="relative cursor-pointer group"
      style={{ width: size, height: size }}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
    >
      <svg className="w-full h-full -rotate-90">
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r="70"
          fill="none"
          stroke="rgba(100, 116, 139, 0.15)"
          strokeWidth="12"
        />
        {/* Animated progress ring */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r="70"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
          style={{
            filter: `drop-shadow(0 0 15px ${color})`,
          }}
        />
        {/* Glow effect on hover */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r="70"
          fill="none"
          stroke={color}
          strokeWidth="20"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="opacity-0 group-hover:opacity-30 transition-opacity"
          style={{
            filter: `blur(8px)`,
          }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="text-4xl font-black"
          style={{ color }}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.5, type: "spring" }}
        >
          {percentage.toFixed(1)}%
        </motion.span>
        <span className="text-xs text-slate-500 uppercase tracking-wider mt-1">{label}</span>
        <span className="text-[10px] text-slate-600 mt-2 group-hover:text-slate-400 transition-colors">
          Click for details
        </span>
      </div>
    </motion.div>
  );
};

// Domain breakdown with interactive segments
const InteractiveDomainChart = ({
  heuristics,
  onDomainClick
}: {
  heuristics: any[];
  onDomainClick?: (domain: string) => void;
}) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const domainData = useMemo(() => {
    const counts: Record<string, { count: number; golden: number }> = {};
    heuristics.forEach(h => {
      if (!counts[h.domain]) counts[h.domain] = { count: 0, golden: 0 };
      counts[h.domain].count++;
      if (h.is_golden) counts[h.domain].golden++;
    });
    return Object.entries(counts)
      .map(([name, data]) => ({ name, value: data.count, golden: data.golden }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [heuristics]);

  return (
    <div className="h-full">
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={domainData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={activeIndex !== null ? 110 : 100}
            paddingAngle={3}
            dataKey="value"
            onMouseEnter={(_, index) => setActiveIndex(index)}
            onMouseLeave={() => setActiveIndex(null)}
            onClick={(data) => onDomainClick?.(data.name)}
            style={{ cursor: 'pointer' }}
          >
            {domainData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={PIE_COLORS[index % PIE_COLORS.length]}
                stroke={activeIndex === index ? '#fff' : 'transparent'}
                strokeWidth={activeIndex === index ? 2 : 0}
                style={{
                  filter: activeIndex === index
                    ? `drop-shadow(0 0 15px ${PIE_COLORS[index % PIE_COLORS.length]})`
                    : `drop-shadow(0 0 5px ${PIE_COLORS[index % PIE_COLORS.length]}60)`,
                  transition: 'all 0.3s ease',
                }}
              />
            ))}
          </Pie>
          <Tooltip content={<CosmicTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Interactive legend */}
      <div className="grid grid-cols-2 gap-2 mt-4 px-4">
        {domainData.map((item, index) => (
          <motion.button
            key={item.name}
            className="flex items-center gap-2 p-2 rounded-lg hover:bg-white/5 transition-colors text-left"
            whileHover={{ x: 5 }}
            onClick={() => onDomainClick?.(item.name)}
          >
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
            />
            <span className="text-xs text-slate-400 truncate flex-1">{item.name}</span>
            <span className="text-xs text-slate-500">{item.value}</span>
            {item.golden > 0 && (
              <Star className="w-3 h-3 text-amber-400" />
            )}
          </motion.button>
        ))}
      </div>
    </div>
  );
};

// Runs timeline with interactive elements
const InteractiveRunsTimeline = ({
  runs,
  onRunClick
}: {
  runs: any[];
  onRunClick?: (run: any) => void;
}) => {
  const chartData = useMemo(() => {
    const last14Days: Record<string, { success: number; failure: number; pending: number; date: string }> = {};
    const now = new Date();

    for (let i = 13; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const key = date.toISOString().split('T')[0];
      last14Days[key] = {
        success: 0,
        failure: 0,
        pending: 0,
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      };
    }

    runs.forEach(run => {
      const date = (run.started_at || run.created_at)?.split('T')[0];
      if (date && last14Days[date]) {
        if (run.status === 'success' || run.status === 'completed') last14Days[date].success++;
        else if (run.status === 'failure' || run.status === 'failed') last14Days[date].failure++;
        else last14Days[date].pending++;
      }
    });

    return Object.values(last14Days);
  }, [runs]);

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} barGap={2}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
          <XAxis
            dataKey="date"
            stroke="rgba(100,116,139,0.5)"
            fontSize={10}
            tick={{ fill: '#64748b' }}
          />
          <YAxis stroke="rgba(100,116,139,0.5)" fontSize={10} tick={{ fill: '#64748b' }} />
          <Tooltip content={<CosmicTooltip />} />
          <Bar
            dataKey="success"
            stackId="a"
            fill={COLORS.emerald}
            radius={[0, 0, 0, 0]}
            name="Success"
          />
          <Bar
            dataKey="failure"
            stackId="a"
            fill={COLORS.red}
            radius={[0, 0, 0, 0]}
            name="Failed"
          />
          <Bar
            dataKey="pending"
            stackId="a"
            fill={COLORS.amber}
            radius={[4, 4, 0, 0]}
            name="Pending"
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Recent runs list */}
      <div className="mt-6 space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Recent Runs</p>
        {runs.slice(0, 10).map((run, i) => (
          <motion.button
            key={run.id || i}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all text-left"
            whileHover={{ x: 5 }}
            onClick={() => onRunClick?.(run)}
          >
            <div className="flex items-center gap-3">
              {run.status === 'success' || run.status === 'completed' ? (
                <CheckCircle className="w-4 h-4 text-emerald-400" />
              ) : run.status === 'failure' || run.status === 'failed' ? (
                <XCircle className="w-4 h-4 text-red-400" />
              ) : (
                <Clock className="w-4 h-4 text-amber-400" />
              )}
              <div>
                <p className="text-sm text-white">{run.workflow_name || run.agent_type || 'Run'}</p>
                <p className="text-xs text-slate-500">{run.phase || run.status}</p>
              </div>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-600" />
          </motion.button>
        ))}
      </div>
    </div>
  );
};

// Confidence breakdown by domain
const ConfidenceBreakdown = ({ heuristics }: { heuristics: any[] }) => {
  const domainConfidence = useMemo(() => {
    const domains: Record<string, { total: number; sum: number }> = {};
    heuristics.forEach(h => {
      if (!domains[h.domain]) domains[h.domain] = { total: 0, sum: 0 };
      domains[h.domain].total++;
      domains[h.domain].sum += h.confidence || 0;
    });
    return Object.entries(domains)
      .map(([domain, data]) => ({
        domain,
        confidence: data.total > 0 ? (data.sum / data.total) * 100 : 0,
        count: data.total,
      }))
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 8);
  }, [heuristics]);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={domainConfidence} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
        <XAxis type="number" domain={[0, 100]} stroke="rgba(100,116,139,0.5)" fontSize={10} />
        <YAxis
          dataKey="domain"
          type="category"
          stroke="rgba(100,116,139,0.5)"
          fontSize={10}
          width={100}
          tick={{ fill: '#94a3b8' }}
        />
        <Tooltip content={<CosmicTooltip />} />
        <Bar
          dataKey="confidence"
          name="Confidence %"
          radius={[0, 8, 8, 0]}
        >
          {domainConfidence.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.confidence >= 80 ? COLORS.emerald : entry.confidence >= 60 ? COLORS.cyan : COLORS.amber}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

// Hotspots scatter visualization
const HotspotsVisualization = ({
  hotspots,
  onHotspotClick
}: {
  hotspots: any[];
  onHotspotClick?: (hotspot: any) => void;
}) => {
  const scatterData = useMemo(() => {
    return hotspots.slice(0, 50).map((h, i) => ({
      x: h.trail_count || Math.random() * 100,
      y: (h.scents?.length || 0) * 10 + Math.random() * 20,
      z: h.trail_count || 10,
      name: h.location || `Hotspot ${i}`,
      ...h,
    }));
  }, [hotspots]);

  return (
    <div>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(100,116,139,0.1)" />
          <XAxis
            type="number"
            dataKey="x"
            name="Trail Count"
            stroke="rgba(100,116,139,0.5)"
            fontSize={10}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Activity"
            stroke="rgba(100,116,139,0.5)"
            fontSize={10}
          />
          <ZAxis type="number" dataKey="z" range={[50, 400]} />
          <Tooltip content={<CosmicTooltip />} />
          <Scatter
            name="Hotspots"
            data={scatterData}
            fill={COLORS.orange}
            onClick={(data) => onHotspotClick?.(data)}
            style={{ cursor: 'pointer' }}
          >
            {scatterData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS.orange}
                style={{
                  filter: `drop-shadow(0 0 8px ${COLORS.orange})`,
                }}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Hotspot list */}
      <div className="mt-6 space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Active Hotspots</p>
        {hotspots.slice(0, 8).map((hotspot, i) => (
          <motion.button
            key={i}
            className="w-full p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-all text-left"
            whileHover={{ x: 5 }}
            onClick={() => onHotspotClick?.(hotspot)}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-white font-mono truncate">{hotspot.location}</span>
              <span className="text-xs text-orange-400">{hotspot.trail_count} trails</span>
            </div>
            <div className="flex gap-1 flex-wrap">
              {hotspot.scents?.slice(0, 3).map((scent: string, j: number) => (
                <span
                  key={j}
                  className="text-[10px] px-2 py-0.5 rounded-full bg-orange-500/10 text-orange-300 border border-orange-500/20"
                >
                  {scent}
                </span>
              ))}
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
};

// Golden vs Regular comparison
const GoldenComparison = ({
  heuristics,
  onViewAll
}: {
  heuristics: any[];
  onViewAll?: () => void;
}) => {
  const goldenHeuristics = heuristics.filter(h => h.is_golden);
  const regularHeuristics = heuristics.filter(h => !h.is_golden);

  const comparisonData = [
    {
      name: 'Golden Rules',
      value: goldenHeuristics.length,
      avgConfidence: goldenHeuristics.reduce((sum, h) => sum + (h.confidence || 0), 0) / (goldenHeuristics.length || 1) * 100,
      fill: COLORS.amber
    },
    {
      name: 'Regular',
      value: regularHeuristics.length,
      avgConfidence: regularHeuristics.reduce((sum, h) => sum + (h.confidence || 0), 0) / (regularHeuristics.length || 1) * 100,
      fill: COLORS.violet
    },
  ];

  return (
    <div>
      <div className="grid grid-cols-2 gap-6 mb-6">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={comparisonData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {comparisonData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.fill}
                  style={{ filter: `drop-shadow(0 0 10px ${entry.fill})` }}
                />
              ))}
            </Pie>
            <Tooltip content={<CosmicTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        <div className="flex flex-col justify-center space-y-4">
          {comparisonData.map((item, i) => (
            <div key={i} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {i === 0 ? <Star className="w-4 h-4 text-amber-400" /> : <Brain className="w-4 h-4 text-violet-400" />}
                <span className="text-sm text-slate-300">{item.name}</span>
              </div>
              <div className="text-right">
                <p className="text-xl font-bold" style={{ color: item.fill }}>{item.value}</p>
                <p className="text-xs text-slate-500">{item.avgConfidence.toFixed(1)}% avg conf</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent golden rules */}
      <div className="space-y-2">
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Recent Golden Rules</p>
        {goldenHeuristics.slice(0, 5).map((h, i) => (
          <motion.div
            key={h.id || i}
            className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20"
            whileHover={{ x: 5 }}
          >
            <p className="text-sm text-amber-200 line-clamp-2">{h.rule}</p>
            <p className="text-xs text-amber-400/60 mt-1">{h.domain}</p>
          </motion.div>
        ))}
      </div>

      <motion.button
        className="w-full mt-6 py-3 rounded-xl font-bold text-sm uppercase tracking-wider transition-all"
        style={{
          background: `linear-gradient(135deg, ${COLORS.violet}30 0%, ${COLORS.rose}30 100%)`,
          border: `1px solid ${COLORS.violet}50`,
          color: COLORS.violet,
        }}
        whileHover={{
          scale: 1.02,
          boxShadow: `0 0 30px ${COLORS.violet}40`,
        }}
        whileTap={{ scale: 0.98 }}
        onClick={onViewAll}
      >
        View All Heuristics
      </motion.button>
    </div>
  );
};

// Main drill-down component
export const AnalyticsDrillDown: React.FC<AnalyticsDrillDownProps> = ({
  type,
  isOpen,
  onClose,
  onNavigate,
}) => {
  const { stats, heuristics, runs, hotspots } = useDataContext();
  const [animateIn, setAnimateIn] = useState(false);

  useEffect(() => {
    if (isOpen) {
      requestAnimationFrame(() => setAnimateIn(true));
    } else {
      setAnimateIn(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Get header info based on type
  const getHeaderInfo = () => {
    switch (type) {
      case 'total_runs':
        return {
          title: 'WORKFLOW RUNS',
          subtitle: 'Complete execution history and performance analysis',
          icon: BarChart3,
          color: COLORS.cyan
        };
      case 'success_rate':
        return {
          title: 'SUCCESS RATE',
          subtitle: 'System reliability and health metrics',
          icon: TrendingUp,
          color: COLORS.emerald
        };
      case 'heuristics':
        return {
          title: 'HEURISTICS',
          subtitle: 'Learned patterns and institutional knowledge',
          icon: Brain,
          color: COLORS.violet
        };
      case 'golden_rules':
        return {
          title: 'GOLDEN RULES',
          subtitle: 'Constitutional principles guiding all operations',
          icon: Star,
          color: COLORS.amber
        };
      case 'system_health':
        return {
          title: 'SYSTEM HEALTH',
          subtitle: 'Detailed health metrics and diagnostics',
          icon: Activity,
          color: COLORS.emerald
        };
      case 'confidence':
        return {
          title: 'CONFIDENCE ANALYSIS',
          subtitle: 'Confidence distribution across domains',
          icon: Target,
          color: COLORS.violet
        };
      case 'hotspots':
        return {
          title: 'HOTSPOTS',
          subtitle: 'Areas of concentrated activity and interest',
          icon: Target,
          color: COLORS.orange
        };
      case 'domain_distribution':
        return {
          title: 'DOMAIN DISTRIBUTION',
          subtitle: 'Heuristic distribution across knowledge domains',
          icon: PieChartIcon,
          color: COLORS.cyan
        };
      case 'activity':
        return {
          title: 'ACTIVITY TIMELINE',
          subtitle: 'Historical run activity and trends',
          icon: LineChartIcon,
          color: COLORS.rose
        };
      case 'learning_velocity':
        return {
          title: 'LEARNING VELOCITY',
          subtitle: 'Rate of knowledge acquisition over time',
          icon: Zap,
          color: COLORS.teal
        };
      default:
        return {
          title: 'ANALYTICS',
          subtitle: 'Detailed metrics and insights',
          icon: Activity,
          color: COLORS.violet
        };
    }
  };

  const header = getHeaderInfo();
  const HeaderIcon = header.icon;

  // Render content based on type
  const renderContent = () => {
    switch (type) {
      case 'total_runs':
      case 'success_rate':
      case 'activity':
        const successRate = stats?.total_runs ? (stats.successful_runs / stats.total_runs) * 100 : 0;
        return (
          <div className="space-y-8">
            {/* Quick stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard
                icon={BarChart3}
                label="Total Runs"
                value={stats?.total_runs || 0}
                color={COLORS.cyan}
                onClick={() => onNavigate?.('runs')}
              />
              <MetricCard
                icon={CheckCircle}
                label="Successful"
                value={stats?.successful_runs || 0}
                color={COLORS.emerald}
              />
              <MetricCard
                icon={XCircle}
                label="Failed"
                value={stats?.failed_runs || 0}
                color={COLORS.red}
              />
              <MetricCard
                icon={Activity}
                label="Today"
                value={stats?.runs_today || 0}
                color={COLORS.violet}
              />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Success gauge */}
              <div className="p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Success Rate</h3>
                <div className="flex justify-center">
                  <InteractiveGauge
                    value={successRate}
                    label="Success"
                    color={successRate >= 80 ? COLORS.emerald : successRate >= 50 ? COLORS.amber : COLORS.red}
                  />
                </div>
              </div>

              {/* Runs timeline - spans 2 cols */}
              <div className="lg:col-span-2 p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">14-Day Activity</h3>
                <InteractiveRunsTimeline
                  runs={runs}
                  onRunClick={(run) => console.log('Run clicked:', run)}
                />
              </div>
            </div>
          </div>
        );

      case 'heuristics':
      case 'golden_rules':
        return (
          <div className="space-y-8">
            {/* Quick stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard
                icon={Brain}
                label="Total Heuristics"
                value={heuristics.length}
                color={COLORS.violet}
                onClick={() => onNavigate?.('heuristics')}
              />
              <MetricCard
                icon={Star}
                label="Golden Rules"
                value={heuristics.filter(h => h.is_golden).length}
                color={COLORS.amber}
              />
              <MetricCard
                icon={CheckCircle}
                label="Validations"
                value={stats?.total_validations || 0}
                color={COLORS.emerald}
              />
              <MetricCard
                icon={Target}
                label="Avg Confidence"
                value={`${((stats?.avg_confidence || 0) * 100).toFixed(0)}%`}
                color={COLORS.cyan}
              />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Golden vs Regular</h3>
                <GoldenComparison
                  heuristics={heuristics}
                  onViewAll={() => onNavigate?.('heuristics')}
                />
              </div>

              <div className="p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Confidence by Domain</h3>
                <ConfidenceBreakdown heuristics={heuristics} />
              </div>
            </div>
          </div>
        );

      case 'system_health':
        const healthScore = stats?.total_runs ? (stats.successful_runs / stats.total_runs) * 100 : 0;
        return (
          <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50 flex flex-col items-center" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Overall Health</h3>
                <InteractiveGauge
                  value={healthScore}
                  label="Health"
                  color={healthScore >= 80 ? COLORS.emerald : healthScore >= 50 ? COLORS.amber : COLORS.red}
                  size={200}
                />
              </div>

              <div className="md:col-span-2 p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Health Indicators</h3>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: 'Run Success', value: healthScore, color: COLORS.emerald },
                    { label: 'Confidence', value: (stats?.avg_confidence || 0) * 100, color: COLORS.violet },
                    { label: 'Validation Rate', value: 85, color: COLORS.cyan },
                    { label: 'System Uptime', value: 99.9, color: COLORS.teal },
                  ].map((metric, i) => (
                    <div key={i} className="p-4 rounded-xl bg-white/5">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-slate-500">{metric.label}</span>
                        <span className="text-lg font-bold" style={{ color: metric.color }}>{metric.value.toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full"
                          style={{ backgroundColor: metric.color }}
                          initial={{ width: 0 }}
                          animate={{ width: `${metric.value}%` }}
                          transition={{ duration: 1, delay: i * 0.1 }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );

      case 'confidence':
        return (
          <div className="space-y-8">
            <div className="p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Confidence by Domain</h3>
              <ConfidenceBreakdown heuristics={heuristics} />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {['High (80%+)', 'Medium (60-80%)', 'Low (40-60%)', 'Critical (<40%)'].map((range, i) => {
                const colors = [COLORS.emerald, COLORS.cyan, COLORS.amber, COLORS.red];
                const counts = [
                  heuristics.filter(h => (h.confidence || 0) >= 0.8).length,
                  heuristics.filter(h => (h.confidence || 0) >= 0.6 && (h.confidence || 0) < 0.8).length,
                  heuristics.filter(h => (h.confidence || 0) >= 0.4 && (h.confidence || 0) < 0.6).length,
                  heuristics.filter(h => (h.confidence || 0) < 0.4).length,
                ];
                return (
                  <MetricCard
                    key={i}
                    icon={Target}
                    label={range}
                    value={counts[i]}
                    color={colors[i]}
                  />
                );
              })}
            </div>
          </div>
        );

      case 'hotspots':
        return (
          <div className="space-y-8">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <MetricCard icon={Target} label="Active Hotspots" value={hotspots.length} color={COLORS.orange} />
              <MetricCard icon={Activity} label="Total Trails" value={hotspots.reduce((sum, h) => sum + (h.trail_count || 0), 0)} color={COLORS.rose} />
              <MetricCard icon={Brain} label="Unique Scents" value={new Set(hotspots.flatMap(h => h.scents || [])).size} color={COLORS.violet} />
            </div>

            <div className="p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Hotspot Distribution</h3>
              <HotspotsVisualization
                hotspots={hotspots}
                onHotspotClick={(h) => console.log('Hotspot clicked:', h)}
              />
            </div>
          </div>
        );

      case 'domain_distribution':
        return (
          <div className="space-y-8">
            <div className="p-6 rounded-2xl border bg-gradient-to-br from-slate-900/80 to-slate-800/50" style={{ borderColor: 'rgba(100,116,139,0.2)' }}>
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Domain Distribution</h3>
              <InteractiveDomainChart
                heuristics={heuristics}
                onDomainClick={(domain) => onNavigate?.('heuristics', domain)}
              />
            </div>
          </div>
        );

      default:
        return (
          <div className="text-center text-slate-400 py-20">
            <p>No detailed view available for this metric</p>
          </div>
        );
    }
  };

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[99999] flex items-start justify-center pt-16 pb-10 px-4 overflow-y-auto"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={{
            background: 'radial-gradient(ellipse at top, rgba(15, 23, 42, 0.98) 0%, rgba(0, 0, 0, 0.99) 100%)',
            backdropFilter: 'blur(20px)',
          }}
          onClick={onClose}
        >
          <StarField />

          <motion.div
            className="relative w-full max-w-6xl"
            initial={{ y: 50, scale: 0.95 }}
            animate={{ y: 0, scale: 1 }}
            exit={{ y: 50, scale: 0.95 }}
            transition={{ type: "spring", damping: 25 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-4">
                <motion.div
                  className="p-4 rounded-2xl"
                  style={{
                    background: `linear-gradient(135deg, ${header.color}30 0%, ${header.color}10 100%)`,
                    boxShadow: `0 0 40px ${header.color}30`,
                  }}
                  animate={{
                    boxShadow: [
                      `0 0 40px ${header.color}30`,
                      `0 0 60px ${header.color}50`,
                      `0 0 40px ${header.color}30`,
                    ],
                  }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  <HeaderIcon className="w-8 h-8" style={{ color: header.color }} />
                </motion.div>
                <div>
                  <motion.h1
                    className="text-3xl font-black tracking-wider"
                    style={{
                      color: header.color,
                      textShadow: `0 0 30px ${header.color}50`,
                    }}
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: 0.1 }}
                  >
                    {header.title}
                  </motion.h1>
                  <motion.p
                    className="text-sm text-slate-500"
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: 0.2 }}
                  >
                    {header.subtitle}
                  </motion.p>
                </div>
              </div>

              <motion.button
                onClick={onClose}
                className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-all"
                whileHover={{ scale: 1.1, rotate: 90 }}
                whileTap={{ scale: 0.9 }}
              >
                <X className="w-6 h-6" />
              </motion.button>
            </div>

            {/* Content */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              {renderContent()}
            </motion.div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
};

export default AnalyticsDrillDown;
