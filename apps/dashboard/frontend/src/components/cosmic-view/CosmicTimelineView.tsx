import React, { useState, useMemo, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TimelineEvent, Heuristic } from '../../types';
import {
  Clock, Play, Pause, SkipBack, SkipForward, CheckCircle,
  Brain, Star, AlertTriangle, FileText, Zap, Rocket, Shield
} from 'lucide-react';
import { format, isToday, isYesterday } from 'date-fns';

interface CosmicTimelineViewProps {
  events: TimelineEvent[];
  heuristics: Heuristic[];
  onEventClick?: (event: TimelineEvent) => void;
}

const eventConfig: Record<string, { icon: any; color: string; glowColor: string; label: string }> = {
  task_start: { icon: Rocket, color: '#38bdf8', glowColor: 'rgba(56, 189, 248, 0.6)', label: 'Mission Launched' },
  task_end: { icon: CheckCircle, color: '#4ade80', glowColor: 'rgba(74, 222, 128, 0.6)', label: 'Mission Complete' },
  heuristic_consulted: { icon: Brain, color: '#a78bfa', glowColor: 'rgba(167, 139, 250, 0.6)', label: 'Neural Sync' },
  heuristic_validated: { icon: Shield, color: '#4ade80', glowColor: 'rgba(74, 222, 128, 0.6)', label: 'Pattern Verified' },
  heuristic_violated: { icon: Zap, color: '#f87171', glowColor: 'rgba(248, 113, 113, 0.6)', label: 'Anomaly Detected' },
  failure_recorded: { icon: AlertTriangle, color: '#fb923c', glowColor: 'rgba(251, 146, 60, 0.6)', label: 'Incident Logged' },
  golden_promoted: { icon: Star, color: '#fbbf24', glowColor: 'rgba(251, 191, 36, 0.6)', label: 'Ascension Event' },
};

// Animated star particle
const StarParticle = ({ delay = 0 }: { delay?: number }) => (
  <motion.div
    className="absolute w-1 h-1 bg-white rounded-full"
    initial={{ opacity: 0, scale: 0 }}
    animate={{
      opacity: [0, 1, 0],
      scale: [0, 1, 0],
    }}
    transition={{
      duration: 3,
      delay,
      repeat: Infinity,
      ease: "easeInOut"
    }}
    style={{
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
    }}
  />
);

// Cosmic event node
const EventNode = ({
  event,
  config,
  index,
  isActive,
  onClick
}: {
  event: TimelineEvent;
  config: typeof eventConfig[string];
  index: number;
  isActive: boolean;
  onClick: () => void;
}) => {
  const Icon = config?.icon || FileText;

  return (
    <motion.div
      initial={{ opacity: 0, x: -50 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05, duration: 0.5, ease: "easeOut" }}
      className="relative group cursor-pointer"
      onClick={onClick}
    >
      {/* Connection beam */}
      <motion.div
        className="absolute left-6 top-10 w-0.5 h-full"
        style={{
          background: `linear-gradient(to bottom, ${config?.color || '#64748b'}40, transparent)`,
        }}
        initial={{ scaleY: 0 }}
        animate={{ scaleY: 1 }}
        transition={{ delay: index * 0.05 + 0.3, duration: 0.5 }}
      />

      <div className="flex items-start gap-4 p-4">
        {/* Event orb */}
        <motion.div
          className="relative z-10 flex-shrink-0"
          whileHover={{ scale: 1.2 }}
          animate={isActive ? { scale: [1, 1.2, 1] } : {}}
          transition={{ duration: 0.5 }}
        >
          {/* Glow ring */}
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{
              background: `radial-gradient(circle, ${config?.glowColor || 'rgba(100, 116, 139, 0.6)'} 0%, transparent 70%)`,
            }}
            animate={{
              scale: [1, 1.5, 1],
              opacity: [0.8, 0.3, 0.8],
            }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />

          {/* Core */}
          <div
            className="relative w-12 h-12 rounded-full flex items-center justify-center"
            style={{
              background: `linear-gradient(135deg, ${config?.color || '#64748b'}40 0%, ${config?.color || '#64748b'}20 100%)`,
              border: `2px solid ${config?.color || '#64748b'}80`,
              boxShadow: `0 0 20px ${config?.glowColor || 'rgba(100, 116, 139, 0.4)'}`,
            }}
          >
            <Icon
              className="w-5 h-5"
              style={{ color: config?.color || '#64748b' }}
            />
          </div>
        </motion.div>

        {/* Event content */}
        <motion.div
          className="flex-1 min-w-0"
          whileHover={{ x: 5 }}
          transition={{ duration: 0.2 }}
        >
          <div
            className="rounded-xl p-4 backdrop-blur-sm transition-all duration-300 group-hover:backdrop-blur-md"
            style={{
              background: `linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.6) 100%)`,
              border: `1px solid ${config?.color || '#64748b'}30`,
              boxShadow: isActive ? `0 0 30px ${config?.glowColor || 'rgba(100, 116, 139, 0.3)'}` : 'none',
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span
                  className="text-sm font-bold uppercase tracking-wider"
                  style={{ color: config?.color || '#64748b' }}
                >
                  {config?.label || event.event_type}
                </span>
                {event.domain && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                    {event.domain}
                  </span>
                )}
              </div>
              <span className="text-xs text-slate-500 font-mono">
                {format(new Date(event.timestamp), 'HH:mm:ss')}
              </span>
            </div>

            {/* Description */}
            <p className="text-sm text-slate-300 leading-relaxed">
              {event.description}
            </p>

            {/* File path */}
            {event.file_path && (
              <div className="mt-3 flex items-center gap-2 text-xs">
                <FileText className="w-3 h-3 text-cyan-400" />
                <span className="text-cyan-400 font-mono truncate">
                  {event.file_path}
                  {event.line_number && `:${event.line_number}`}
                </span>
              </div>
            )}

            {/* Hover indicator */}
            <motion.div
              className="absolute inset-0 rounded-xl pointer-events-none"
              initial={{ opacity: 0 }}
              whileHover={{ opacity: 1 }}
              style={{
                background: `linear-gradient(135deg, ${config?.color || '#64748b'}10 0%, transparent 100%)`,
              }}
            />
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};

// Date separator
const DateSeparator = ({ date }: { date: string }) => {
  const dateObj = new Date(date);
  let label = format(dateObj, 'EEEE, MMMM d');
  if (isToday(dateObj)) label = 'Today';
  else if (isYesterday(dateObj)) label = 'Yesterday';

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative py-6"
    >
      <div className="absolute inset-0 flex items-center">
        <div className="w-full h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
      </div>
      <div className="relative flex justify-center">
        <div className="px-6 py-2 bg-slate-900/80 backdrop-blur-sm rounded-full border border-cyan-500/30">
          <span className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-fuchsia-400 uppercase tracking-widest">
            {label}
          </span>
        </div>
      </div>
    </motion.div>
  );
};

export const CosmicTimelineView: React.FC<CosmicTimelineViewProps> = ({
  events,
  heuristics: _heuristics,
  onEventClick
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [filterType, setFilterType] = useState<string | null>(null);
  const [speed, setSpeed] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  // Group events by date
  const groupedEvents = useMemo(() => {
    const filtered = filterType
      ? events.filter(e => e.event_type === filterType)
      : events;

    const groups: { [key: string]: TimelineEvent[] } = {};
    filtered.forEach(event => {
      const date = format(new Date(event.timestamp), 'yyyy-MM-dd');
      if (!groups[date]) groups[date] = [];
      groups[date].push(event);
    });
    return groups;
  }, [events, filterType]);

  const dates = Object.keys(groupedEvents).sort().reverse();

  // Playback animation
  useEffect(() => {
    if (!isPlaying || events.length === 0) return;

    const interval = setInterval(() => {
      setPlaybackIndex(prev => {
        if (prev >= events.length - 1) {
          setIsPlaying(false);
          return 0;
        }
        return prev + 1;
      });
    }, 1000 / speed);

    return () => clearInterval(interval);
  }, [isPlaying, events.length, speed]);

  // Event stats
  const stats = useMemo(() => {
    const total = events.length;
    const byType = events.reduce((acc, e) => {
      acc[e.event_type] = (acc[e.event_type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    return { total, byType };
  }, [events]);

  return (
    <div className="w-full h-full flex flex-col overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(30)].map((_, i) => (
          <StarParticle key={i} delay={i * 0.2} />
        ))}
      </div>

      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b border-slate-800/50">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-6"
        >
          <div>
            <h1 className="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-purple-400 to-fuchsia-400 uppercase tracking-widest">
              Temporal Stream
            </h1>
            <p className="text-slate-500 font-mono text-xs mt-1">
              {">>"} EVENT_CHRONICLE // {stats.total} RECORDS
            </p>
          </div>

          {/* Playback controls */}
          <div className="flex items-center gap-4">
            <motion.div
              className="flex items-center gap-1 p-1 rounded-lg bg-slate-800/50 border border-slate-700/50"
              whileHover={{ borderColor: 'rgba(56, 189, 248, 0.5)' }}
            >
              <motion.button
                onClick={() => setPlaybackIndex(Math.max(0, playbackIndex - 1))}
                className="p-2 rounded hover:bg-slate-700/50 text-slate-400 hover:text-cyan-400 transition"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
              >
                <SkipBack className="w-4 h-4" />
              </motion.button>
              <motion.button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`p-2 rounded transition ${isPlaying ? 'bg-cyan-500/20 text-cyan-400' : 'hover:bg-slate-700/50 text-slate-400 hover:text-cyan-400'}`}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </motion.button>
              <motion.button
                onClick={() => setPlaybackIndex(Math.min(events.length - 1, playbackIndex + 1))}
                className="p-2 rounded hover:bg-slate-700/50 text-slate-400 hover:text-cyan-400 transition"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
              >
                <SkipForward className="w-4 h-4" />
              </motion.button>
            </motion.div>

            <select
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="bg-slate-800/50 text-sm text-white rounded-lg px-3 py-2 border border-slate-700/50 focus:border-cyan-500/50 focus:outline-none"
            >
              <option value={0.5}>0.5x</option>
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={5}>5x</option>
            </select>
          </div>
        </motion.div>

        {/* Event type filters */}
        <div className="flex flex-wrap gap-2">
          <motion.button
            onClick={() => setFilterType(null)}
            className={`px-3 py-1.5 rounded-full text-xs font-mono transition-all
              ${!filterType
                ? 'bg-gradient-to-r from-cyan-500/20 to-fuchsia-500/20 border border-cyan-500/50 text-white'
                : 'bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white hover:border-slate-600'}`}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            ALL ({stats.total})
          </motion.button>
          {Object.entries(eventConfig).map(([type, config]) => (
            <motion.button
              key={type}
              onClick={() => setFilterType(filterType === type ? null : type)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono transition-all
                ${filterType === type
                  ? 'border text-white'
                  : 'bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white'}`}
              style={{
                borderColor: filterType === type ? `${config.color}80` : undefined,
                backgroundColor: filterType === type ? `${config.color}20` : undefined,
              }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: config.color }}
              />
              <span>{config.label}</span>
              <span className="opacity-50">({stats.byType[type] || 0})</span>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Timeline content */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto custom-scrollbar p-6"
      >
        <AnimatePresence mode="wait">
          {dates.length > 0 ? (
            <motion.div
              key={filterType || 'all'}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {dates.map((date) => (
                <div key={date}>
                  <DateSeparator date={date} />
                  <div className="space-y-2">
                    {groupedEvents[date].map((event, eventIndex) => {
                      const config = eventConfig[event.event_type];
                      const globalIndex = events.indexOf(event);

                      return (
                        <EventNode
                          key={event.id}
                          event={event}
                          config={config}
                          index={eventIndex}
                          isActive={globalIndex === playbackIndex && isPlaying}
                          onClick={() => onEventClick?.(event)}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full text-center"
            >
              <motion.div
                animate={{
                  rotate: 360,
                  scale: [1, 1.1, 1],
                }}
                transition={{
                  rotate: { duration: 20, repeat: Infinity, ease: "linear" },
                  scale: { duration: 2, repeat: Infinity, ease: "easeInOut" }
                }}
                className="w-24 h-24 rounded-full border-2 border-dashed border-slate-700 flex items-center justify-center mb-6"
              >
                <Clock className="w-10 h-10 text-slate-600" />
              </motion.div>
              <p className="text-slate-500 font-mono text-sm">
                No temporal events detected
              </p>
              <p className="text-slate-600 text-xs mt-2">
                Events will appear here as they occur
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default CosmicTimelineView;
