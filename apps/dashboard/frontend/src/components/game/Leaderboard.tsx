import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Trophy,
    Medal,
    Crown,
    Star,
    ChevronUp,
    ChevronDown,
    Loader2,
    Users,
    Sparkles
} from 'lucide-react';
import { useGame } from '../../context/GameContext';

// ============================================================================
// Types
// ============================================================================

export interface LeaderboardEntry {
    rank: number;
    username: string;
    avatar_url?: string;
    score: number;
    level?: number;
    isCurrentUser?: boolean;
}

export interface LeaderboardProps {
    /** Pre-loaded entries (optional - will fetch if not provided) */
    entries?: LeaderboardEntry[];
    /** Custom fetch function for leaderboard data */
    fetchLeaderboard?: () => Promise<LeaderboardEntry[]>;
    /** Maximum entries to display */
    maxEntries?: number;
    /** Show rank change indicators */
    showRankChange?: boolean;
    /** Custom title */
    title?: string;
    /** Compact mode for smaller spaces */
    compact?: boolean;
    /** Callback when user clicks an entry */
    onEntryClick?: (entry: LeaderboardEntry) => void;
}

// ============================================================================
// Mock Data (for demonstration - remove in production)
// ============================================================================

const MOCK_LEADERBOARD: LeaderboardEntry[] = [
    { rank: 1, username: 'CosmicDestroyer', score: 2847500, level: 42, avatar_url: 'https://avatars.githubusercontent.com/u/1?v=4' },
    { rank: 2, username: 'StarPilot_X', score: 2156000, level: 38, avatar_url: 'https://avatars.githubusercontent.com/u/2?v=4' },
    { rank: 3, username: 'NebulaCrusher', score: 1892300, level: 35, avatar_url: 'https://avatars.githubusercontent.com/u/3?v=4' },
    { rank: 4, username: 'VoidWalker99', score: 1654200, level: 32 },
    { rank: 5, username: 'PhotonRider', score: 1423100, level: 29, avatar_url: 'https://avatars.githubusercontent.com/u/5?v=4' },
    { rank: 6, username: 'GalacticAce', score: 1287600, level: 27 },
    { rank: 7, username: 'AsteroidHunter', score: 1098500, level: 24, avatar_url: 'https://avatars.githubusercontent.com/u/7?v=4' },
    { rank: 8, username: 'WarpDriveMaster', score: 956400, level: 22 },
    { rank: 9, username: 'CometChaser', score: 823700, level: 20, avatar_url: 'https://avatars.githubusercontent.com/u/9?v=4' },
    { rank: 10, username: 'SolarFlareKid', score: 712300, level: 18 },
];

// ============================================================================
// Utility Functions
// ============================================================================

const formatScore = (score: number): string => {
    if (score >= 1000000) {
        return `${(score / 1000000).toFixed(1)}M`;
    }
    if (score >= 1000) {
        return `${(score / 1000).toFixed(1)}K`;
    }
    return score.toLocaleString();
};

const getRankIcon = (rank: number): React.ReactNode => {
    switch (rank) {
        case 1:
            return <Crown className="w-5 h-5 text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.8)]" />;
        case 2:
            return <Medal className="w-5 h-5 text-slate-300 drop-shadow-[0_0_6px_rgba(203,213,225,0.6)]" />;
        case 3:
            return <Medal className="w-5 h-5 text-amber-600 drop-shadow-[0_0_6px_rgba(180,83,9,0.6)]" />;
        default:
            return null;
    }
};

const getRankStyles = (rank: number, isCurrentUser: boolean): string => {
    if (isCurrentUser) {
        return 'bg-cyan-500/20 border-cyan-500/50 shadow-[0_0_20px_rgba(6,182,212,0.3)]';
    }
    switch (rank) {
        case 1:
            return 'bg-amber-500/10 border-amber-500/30 hover:border-amber-500/50';
        case 2:
            return 'bg-slate-400/10 border-slate-400/30 hover:border-slate-400/50';
        case 3:
            return 'bg-amber-700/10 border-amber-700/30 hover:border-amber-700/50';
        default:
            return 'bg-white/5 border-white/10 hover:border-white/30';
    }
};

// ============================================================================
// Sub-Components
// ============================================================================

const LeaderboardSkeleton: React.FC<{ count?: number }> = ({ count = 5 }) => (
    <div className="space-y-3">
        {Array.from({ length: count }).map((_, i) => (
            <div
                key={i}
                className="flex items-center gap-4 p-3 rounded-lg bg-white/5 border border-white/10 animate-pulse"
            >
                <div className="w-8 h-8 rounded-full bg-slate-700" />
                <div className="flex-1 space-y-2">
                    <div className="h-4 bg-slate-700 rounded w-32" />
                    <div className="h-3 bg-slate-700/50 rounded w-20" />
                </div>
                <div className="h-6 bg-slate-700 rounded w-24" />
            </div>
        ))}
    </div>
);

const EmptyState: React.FC = () => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center py-12 text-center"
    >
        <div className="w-16 h-16 rounded-full bg-slate-800 border border-cyan-500/30 flex items-center justify-center mb-4">
            <Users className="w-8 h-8 text-cyan-500/50" />
        </div>
        <h3 className="text-lg font-bold text-white mb-2">No Pilots Yet</h3>
        <p className="text-sm text-slate-400 max-w-xs">
            Be the first to claim your place in the cosmic rankings!
        </p>
        <div className="mt-4 flex items-center gap-2 text-cyan-400 text-sm">
            <Sparkles className="w-4 h-4" />
            <span>Start playing to appear here</span>
        </div>
    </motion.div>
);

interface LeaderboardRowProps {
    entry: LeaderboardEntry;
    index: number;
    compact?: boolean;
    onClick?: () => void;
}

const LeaderboardRow: React.FC<LeaderboardRowProps> = ({
    entry,
    index,
    compact = false,
    onClick
}) => {
    const isTopThree = entry.rank <= 3;
    const rankIcon = getRankIcon(entry.rank);
    const rowStyles = getRankStyles(entry.rank, entry.isCurrentUser || false);

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
                delay: index * 0.05,
                type: 'spring',
                stiffness: 300,
                damping: 30
            }}
            whileHover={{
                scale: 1.02,
                transition: { duration: 0.2 }
            }}
            onClick={onClick}
            className={`
                relative flex items-center gap-4
                ${compact ? 'p-2' : 'p-3'}
                rounded-xl border transition-all cursor-pointer
                ${rowStyles}
                group
            `}
        >
            {/* Rank Badge */}
            <div className={`
                flex items-center justify-center
                ${compact ? 'w-8 h-8' : 'w-10 h-10'}
                rounded-lg font-mono font-bold
                ${isTopThree
                    ? 'bg-gradient-to-br from-slate-800 to-slate-900 border border-white/20'
                    : 'bg-slate-800/50'
                }
            `}>
                {rankIcon || (
                    <span className={`
                        ${entry.isCurrentUser ? 'text-cyan-400' : 'text-slate-400'}
                        ${compact ? 'text-sm' : 'text-base'}
                    `}>
                        {entry.rank}
                    </span>
                )}
            </div>

            {/* Avatar */}
            <div className={`
                relative
                ${compact ? 'w-8 h-8' : 'w-10 h-10'}
                rounded-full overflow-hidden
                border-2
                ${entry.isCurrentUser
                    ? 'border-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)]'
                    : isTopThree
                        ? 'border-amber-500/50'
                        : 'border-slate-600'
                }
                bg-slate-800
            `}>
                {entry.avatar_url ? (
                    <img
                        src={entry.avatar_url}
                        alt={entry.username}
                        className="w-full h-full object-cover"
                        loading="lazy"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-500 font-bold text-sm">
                        {entry.username.charAt(0).toUpperCase()}
                    </div>
                )}
                {entry.isCurrentUser && (
                    <div className="absolute inset-0 bg-cyan-500/20 animate-pulse" />
                )}
            </div>

            {/* User Info */}
            <div className="flex-1 min-w-0">
                <div className={`
                    font-bold truncate
                    ${entry.isCurrentUser ? 'text-cyan-300' : 'text-white'}
                    ${compact ? 'text-sm' : 'text-base'}
                `}>
                    {entry.username}
                    {entry.isCurrentUser && (
                        <span className="ml-2 text-xs text-cyan-500 font-normal">(You)</span>
                    )}
                </div>
                {!compact && entry.level && (
                    <div className="text-xs text-slate-500 flex items-center gap-1">
                        <Star className="w-3 h-3" />
                        Level {entry.level}
                    </div>
                )}
            </div>

            {/* Score */}
            <div className="text-right">
                <div className={`
                    font-mono font-black
                    ${entry.isCurrentUser
                        ? 'text-cyan-400'
                        : isTopThree
                            ? 'text-amber-400'
                            : 'text-white'
                    }
                    ${compact ? 'text-sm' : 'text-lg'}
                `}>
                    {formatScore(entry.score)}
                </div>
                {!compact && (
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">
                        points
                    </div>
                )}
            </div>

            {/* Hover Glow Effect */}
            <div className={`
                absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100
                transition-opacity pointer-events-none
                ${entry.isCurrentUser
                    ? 'bg-gradient-to-r from-cyan-500/5 to-transparent'
                    : 'bg-gradient-to-r from-white/5 to-transparent'
                }
            `} />
        </motion.div>
    );
};

interface UserRankBannerProps {
    currentUser: LeaderboardEntry;
    isInTopList: boolean;
}

const UserRankBanner: React.FC<UserRankBannerProps> = ({ currentUser, isInTopList }) => {
    if (isInTopList) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 relative"
        >
            {/* Separator */}
            <div className="flex items-center gap-4 mb-4">
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent" />
                <span className="text-xs text-slate-500 uppercase tracking-wider">Your Position</span>
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent" />
            </div>

            {/* User Row */}
            <LeaderboardRow
                entry={{ ...currentUser, isCurrentUser: true }}
                index={0}
            />

            {/* Distance Indicator */}
            <div className="mt-2 flex items-center justify-center gap-2 text-xs text-slate-400">
                <ChevronUp className="w-4 h-4 text-cyan-500" />
                <span>
                    {currentUser.rank > 10
                        ? `${currentUser.rank - 10} positions to Top 10`
                        : 'Almost there!'
                    }
                </span>
            </div>
        </motion.div>
    );
};

// ============================================================================
// Main Component
// ============================================================================

export const Leaderboard: React.FC<LeaderboardProps> = ({
    entries: propEntries,
    fetchLeaderboard,
    maxEntries = 10,
    showRankChange = false,
    title = 'Cosmic Rankings',
    compact = false,
    onEntryClick
}) => {
    const { githubUser, score } = useGame();
    const [entries, setEntries] = useState<LeaderboardEntry[]>(propEntries || []);
    const [isLoading, setIsLoading] = useState(!propEntries);
    const [error, setError] = useState<string | null>(null);

    // Fetch leaderboard data
    useEffect(() => {
        const loadLeaderboard = async () => {
            if (propEntries) {
                setEntries(propEntries);
                return;
            }

            setIsLoading(true);
            setError(null);

            try {
                if (fetchLeaderboard) {
                    const data = await fetchLeaderboard();
                    setEntries(data);
                } else {
                    // Try to fetch from API, fallback to mock data
                    try {
                        const res = await fetch('/api/game/leaderboard', {
                            credentials: 'include'
                        });
                        if (res.ok) {
                            const data = await res.json();
                            setEntries(data.entries || []);
                        } else {
                            // Use mock data for demo
                            setEntries(MOCK_LEADERBOARD);
                        }
                    } catch {
                        // Use mock data for demo
                        setEntries(MOCK_LEADERBOARD);
                    }
                }
            } catch (err) {
                setError('Failed to load leaderboard');
                console.error('Leaderboard fetch error:', err);
            } finally {
                setIsLoading(false);
            }
        };

        loadLeaderboard();
    }, [propEntries, fetchLeaderboard]);

    // Process entries with current user highlighting
    const processedEntries = useMemo(() => {
        let processed = entries.slice(0, maxEntries).map(entry => ({
            ...entry,
            isCurrentUser: githubUser?.username === entry.username
        }));

        return processed;
    }, [entries, maxEntries, githubUser]);

    // Find current user's position
    const currentUserEntry = useMemo(() => {
        if (!githubUser) return null;

        // Check if user is in the current list
        const inList = entries.find(e => e.username === githubUser.username);
        if (inList) return { ...inList, isCurrentUser: true };

        // If not in list, create a placeholder entry
        // In production, this would come from the API
        return {
            rank: entries.length + Math.floor(Math.random() * 50) + 1,
            username: githubUser.username,
            avatar_url: githubUser.avatar_url,
            score: score,
            isCurrentUser: true
        };
    }, [entries, githubUser, score]);

    const isCurrentUserInTop = useMemo(() => {
        if (!currentUserEntry) return false;
        return currentUserEntry.rank <= maxEntries;
    }, [currentUserEntry, maxEntries]);

    return (
        <div className={`${compact ? 'p-4' : 'p-6'} bg-slate-900/80 rounded-2xl border border-cyan-500/20`}>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-cyan-500/20 border border-cyan-500/30">
                        <Trophy className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                        <h2 className={`
                            font-bold text-white tracking-wider uppercase font-mono
                            ${compact ? 'text-sm' : 'text-lg'}
                        `}>
                            {title}
                        </h2>
                        <div className="text-xs text-slate-500">
                            Top {maxEntries} Pilots
                        </div>
                    </div>
                </div>

                {isLoading && (
                    <Loader2 className="w-5 h-5 text-cyan-500 animate-spin" />
                )}
            </div>

            {/* Content */}
            <AnimatePresence mode="wait">
                {isLoading ? (
                    <motion.div
                        key="loading"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <LeaderboardSkeleton count={compact ? 5 : maxEntries} />
                    </motion.div>
                ) : error ? (
                    <motion.div
                        key="error"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="text-center py-8 text-red-400"
                    >
                        <p>{error}</p>
                        <button
                            onClick={() => window.location.reload()}
                            className="mt-2 text-sm text-cyan-400 hover:text-cyan-300"
                        >
                            Try Again
                        </button>
                    </motion.div>
                ) : processedEntries.length === 0 ? (
                    <motion.div
                        key="empty"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <EmptyState />
                    </motion.div>
                ) : (
                    <motion.div
                        key="list"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="space-y-2"
                    >
                        {processedEntries.map((entry, index) => (
                            <LeaderboardRow
                                key={entry.username}
                                entry={entry}
                                index={index}
                                compact={compact}
                                onClick={() => onEntryClick?.(entry)}
                            />
                        ))}

                        {/* Show user's position if not in top list */}
                        {currentUserEntry && !isCurrentUserInTop && (
                            <UserRankBanner
                                currentUser={currentUserEntry}
                                isInTopList={isCurrentUserInTop}
                            />
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Footer Stats */}
            {!isLoading && !error && processedEntries.length > 0 && (
                <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-500">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1">
                            <Crown className="w-3 h-3 text-amber-400" />
                            <span>Gold</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <Medal className="w-3 h-3 text-slate-300" />
                            <span>Silver</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <Medal className="w-3 h-3 text-amber-600" />
                            <span>Bronze</span>
                        </div>
                    </div>
                    <div className="text-cyan-500/70">
                        Updated live
                    </div>
                </div>
            )}
        </div>
    );
};

// ============================================================================
// Standalone Modal Variant
// ============================================================================

interface LeaderboardModalProps extends LeaderboardProps {
    isOpen: boolean;
    onClose: () => void;
}

export const LeaderboardModal: React.FC<LeaderboardModalProps> = ({
    isOpen,
    onClose,
    ...leaderboardProps
}) => {
    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100000] flex items-center justify-center bg-black/80 backdrop-blur-sm">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="w-full max-w-lg mx-4 shadow-[0_0_50px_rgba(6,182,212,0.3)]"
                    >
                        <div className="relative">
                            <Leaderboard {...leaderboardProps} />
                            <button
                                onClick={onClose}
                                className="absolute top-4 right-4 p-2 hover:bg-white/10 rounded-full transition-colors"
                            >
                                <span className="sr-only">Close</span>
                                <svg
                                    className="w-5 h-5 text-slate-400 hover:text-white"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M6 18L18 6M6 6l12 12"
                                    />
                                </svg>
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};

export default Leaderboard;
