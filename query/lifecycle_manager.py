#!/usr/bin/env python3
"""
Heuristic Lifecycle Manager - Phase 1 Implementation

Implements critical fixes from the Skeptic Security Audit:
1. Dormant Recovery Mechanism
2. Rate-based Contradiction Threshold
3. Rate Limiting on Confidence Updates
4. Clear Eviction Policy

Based on: ceo-inbox/2025-12-12-heuristic-lifecycle-security-audit.md
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Configuration
DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

# Fraud detection integration
try:
    from fraud_detector import FraudDetector
    FRAUD_DETECTOR_AVAILABLE = True
except ImportError:
    FRAUD_DETECTOR_AVAILABLE = False

class HeuristicStatus(Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"

class UpdateType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CONTRADICTION = "contradiction"
    DECAY = "decay"
    REVIVAL = "revival"
    MANUAL = "manual"

@dataclass
class LifecycleConfig:
    """Configuration for lifecycle management."""
    # Dormancy thresholds
    dormant_after_days: int = 60
    archived_after_dormant_days: int = 90

    # Rate-based contradiction threshold
    min_applications_for_deprecation: int = 10
    contradiction_rate_threshold: float = 0.30  # 30%

    # Rate limiting
    max_updates_per_day: int = 5
    cooldown_minutes: int = 60  # Minimum time between updates

    # Eviction policy
    max_active_per_domain: int = 10
    max_dormant_per_domain: int = 20

    # Confidence bounds (prevent extreme values)
    min_confidence: float = 0.05
    max_confidence: float = 0.95

    # Decay settings
    decay_half_life_days: int = 14
    decay_floor: float = 0.20  # Below this = dormant

@dataclass
class Heuristic:
    """Represents a heuristic with lifecycle state."""
    id: int
    domain: str
    rule: str
    explanation: Optional[str]
    confidence: float
    times_validated: int
    times_violated: int
    times_contradicted: int
    status: str
    last_used_at: Optional[datetime]
    dormant_since: Optional[datetime]
    is_golden: bool
    created_at: datetime
    updated_at: datetime


class LifecycleManager:
    """
    Manages heuristic lifecycle with security fixes.

    Addresses vulnerabilities:
    - Bad heuristic immortality (rate limiting, symmetric updates)
    - Good heuristic unfair death (rate-based contradictions)
    - Rapid fire manipulation (rate limiting)
    - Domain limit knowledge loss (weighted eviction)
    - Total dormancy cascade (revival mechanism)
    """

    def __init__(self, db_path: Path = DB_PATH, config: Optional[LifecycleConfig] = None):
        self.db_path = db_path
        self.config = config or LifecycleConfig()
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        """Ensure all required migrations are applied."""
        conn = self._get_connection()
        try:
            # Check if heuristics table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='heuristics'"
            )
            if cursor.fetchone() is None:
                # Need to apply Phase 1 migration
                migration_path = self.db_path.parent / "migrations" / "002_heuristic_lifecycle_phase1.sql"
                if migration_path.exists():
                    with open(migration_path) as f:
                        conn.executescript(f.read())
                    conn.commit()

            # Check if Phase 2 (temporal smoothing) is applied
            cursor = conn.execute(
                "SELECT name FROM pragma_table_info('heuristics') WHERE name = 'confidence_ema'"
            )
            if cursor.fetchone() is None:
                # Need to apply Phase 2 migration
                migration_path = self.db_path.parent / "migrations" / "003_temporal_smoothing.sql"
                if migration_path.exists():
                    with open(migration_path) as f:
                        conn.executescript(f.read())
                    conn.commit()
        finally:
            conn.close()

    # =========================================================================
    # 1. RATE LIMITING
    # =========================================================================

    def can_update_confidence(self, heuristic_id: int, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if confidence update is allowed (rate limiting).

        Returns:
            (allowed, reason) tuple
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    last_confidence_update,
                    update_count_today,
                    update_count_reset_date
                FROM heuristics
                WHERE id = ?
            """, (heuristic_id,))
            row = cursor.fetchone()

            if not row:
                return False, "Heuristic not found"

            now = datetime.now()
            today = date.today()

            # Check daily limit
            if row['update_count_reset_date']:
                reset_date = datetime.strptime(row['update_count_reset_date'], '%Y-%m-%d').date()
                if reset_date == today and row['update_count_today'] >= self.config.max_updates_per_day:
                    return False, f"Daily limit reached ({self.config.max_updates_per_day} updates/day)"

            # Check cooldown
            if row['last_confidence_update']:
                last_update = datetime.fromisoformat(row['last_confidence_update'])
                cooldown_end = last_update + timedelta(minutes=self.config.cooldown_minutes)
                if now < cooldown_end:
                    remaining = (cooldown_end - now).seconds // 60
                    return False, f"Cooldown active ({remaining} minutes remaining)"

            return True, "Update allowed"
        finally:
            conn.close()

    def _record_update(self, conn: sqlite3.Connection, heuristic_id: int,
                       old_conf: float, new_conf: float, update_type: UpdateType,
                       reason: str, rate_limited: bool = False,
                       session_id: Optional[str] = None, agent_id: Optional[str] = None,
                       raw_target: Optional[float] = None, smoothed_delta: Optional[float] = None,
                       alpha_used: Optional[float] = None):
        """Record confidence update in audit trail."""
        conn.execute("""
            INSERT INTO confidence_updates
            (heuristic_id, old_confidence, new_confidence, delta, update_type,
             reason, rate_limited, session_id, agent_id, raw_target_confidence,
             smoothed_delta, alpha_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            heuristic_id, old_conf, new_conf, new_conf - old_conf,
            update_type.value, reason, 1 if rate_limited else 0,
            session_id, agent_id, raw_target, smoothed_delta, alpha_used
        ))

    # =========================================================================
    # PHASE 2: TEMPORAL SMOOTHING (EMA)
    # =========================================================================

    def _get_adaptive_alpha(self, heuristic_data: Dict, is_increase: bool,
                           ema_warmup_remaining: int) -> float:
        """
        Calculate adaptive alpha based on heuristic state.

        CEO Decisions (Locked):
        - Warmup (first 5 updates): alpha=0.30
        - High-confidence (>0.80): alpha=0.10 increase, 0.15 decrease
        - Low-confidence (<0.30): alpha=0.25 increase, 0.20 decrease
        - Mature (20+ apps): alpha=0.15 increase, 0.20 decrease
        - Immature: alpha=0.20 increase, 0.25 decrease

        Args:
            heuristic_data: Dict with 'confidence' and total applications
            is_increase: True if confidence is increasing, False if decreasing
            ema_warmup_remaining: Number of warmup updates remaining

        Returns:
            Alpha value (0 < alpha <= 1.0)
        """
        # Warmup phase - fast learning
        if ema_warmup_remaining > 0:
            return 0.30

        confidence = heuristic_data['confidence']
        total_apps = heuristic_data['total_apps']

        # High confidence zone (approaching golden)
        if confidence > 0.80:
            return 0.10 if is_increase else 0.15

        # Low confidence zone (struggling, allow recovery)
        if confidence < 0.30:
            return 0.25 if is_increase else 0.20

        # Mature middle range (steady state)
        if total_apps >= 20:
            return 0.15 if is_increase else 0.20

        # Immature but past warmup
        return 0.20 if is_increase else 0.25

    def _apply_ema(self, old_ema: float, raw_target: float, alpha: float) -> float:
        """
        Apply exponential moving average smoothing.

        Formula: new_EMA = alpha * raw_target + (1 - alpha) * old_EMA

        Args:
            old_ema: Previous EMA value
            raw_target: Target confidence without smoothing
            alpha: Smoothing factor (0 < alpha <= 1.0)

        Returns:
            New EMA value, clamped to [min_confidence, max_confidence]
        """
        new_ema = alpha * raw_target + (1 - alpha) * old_ema

        # Bounds check (defense in depth)
        return max(self.config.min_confidence,
                  min(self.config.max_confidence, new_ema))

    def update_confidence(self, heuristic_id: int, update_type: UpdateType,
                         reason: str = "", session_id: Optional[str] = None,
                         agent_id: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """
        Update heuristic confidence with EMA smoothing, rate limiting, and bounds.

        Phase 2 Enhancement: Applies exponential moving average to reduce noise.

        Implements symmetric confidence updates to prevent gaming:
        - Success: += 0.1 * (1 - confidence)  [diminishing returns at high conf]
        - Failure: -= 0.1 * confidence        [diminishing loss at low conf]
        - Contradiction: -= 0.15 * confidence [stronger penalty]

        Then applies EMA smoothing with adaptive alpha based on heuristic state.
        """
        # Check rate limit (unless forced)
        if not force:
            allowed, limit_reason = self.can_update_confidence(heuristic_id, session_id)
            if not allowed:
                return {
                    "success": False,
                    "rate_limited": True,
                    "reason": limit_reason
                }

        conn = self._get_connection()
        try:
            # Get current state with EMA fields
            cursor = conn.execute("""
                SELECT id, confidence, confidence_ema, ema_alpha, ema_warmup_remaining,
                       times_validated, times_violated, times_contradicted,
                       status, update_count_today, update_count_reset_date
                FROM heuristics WHERE id = ?
            """, (heuristic_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "reason": "Heuristic not found"}

            old_conf = row['confidence']
            old_ema = row['confidence_ema'] if row['confidence_ema'] is not None else old_conf
            ema_warmup = row['ema_warmup_remaining'] if row['ema_warmup_remaining'] is not None else 0
            today = date.today()

            # Calculate total applications for adaptive alpha
            total_apps = (
                (row['times_validated'] or 0) +
                (row['times_violated'] or 0) +
                (row['times_contradicted'] or 0)
            )

            # Calculate raw target confidence (Phase 1 formula)
            raw_target = old_conf
            alpha_used = 0.15  # Default, will be overridden
            new_ema = old_ema
            new_conf = old_conf

            if update_type == UpdateType.SUCCESS:
                # Diminishing returns at high confidence
                delta = 0.1 * (1 - old_conf)
                raw_target = min(old_conf + delta, self.config.max_confidence)
                conn.execute(
                    "UPDATE heuristics SET times_validated = times_validated + 1 WHERE id = ?",
                    (heuristic_id,)
                )

            elif update_type == UpdateType.FAILURE:
                # Symmetric: diminishing loss at low confidence
                delta = 0.1 * old_conf
                raw_target = max(old_conf - delta, self.config.min_confidence)
                conn.execute(
                    "UPDATE heuristics SET times_violated = times_violated + 1 WHERE id = ?",
                    (heuristic_id,)
                )

            elif update_type == UpdateType.CONTRADICTION:
                # Stronger penalty for contradictions
                delta = 0.15 * old_conf
                raw_target = max(old_conf - delta, self.config.min_confidence)
                conn.execute(
                    "UPDATE heuristics SET times_contradicted = COALESCE(times_contradicted, 0) + 1 WHERE id = ?",
                    (heuristic_id,)
                )

            elif update_type == UpdateType.DECAY:
                # Time-based decay - bypass EMA (decay is already gradual)
                raw_target = max(old_conf * 0.92, self.config.min_confidence)
                new_conf = raw_target
                # Skip EMA for decay
                alpha_used = 1.0
                new_ema = new_conf

            elif update_type == UpdateType.REVIVAL:
                # Reviving from dormancy - boost to minimum viable
                raw_target = max(old_conf, 0.35)
                new_conf = raw_target
                # Skip EMA for revival
                alpha_used = 1.0
                new_ema = new_conf

            # Apply EMA smoothing (except for DECAY and REVIVAL)
            if update_type not in [UpdateType.DECAY, UpdateType.REVIVAL]:
                # Determine if this is an increase or decrease
                is_increase = raw_target > old_ema

                # Get adaptive alpha
                heuristic_data = {
                    'confidence': old_conf,
                    'total_apps': total_apps
                }
                alpha_used = self._get_adaptive_alpha(heuristic_data, is_increase, ema_warmup)

                # Apply EMA
                new_ema = self._apply_ema(old_ema, raw_target, alpha_used)
                new_conf = new_ema

                # Decrement warmup counter if in warmup
                if ema_warmup > 0:
                    ema_warmup -= 1

            # Update the heuristic
            reset_date = row['update_count_reset_date']
            update_count = row['update_count_today'] or 0

            if reset_date != str(today):
                update_count = 1
                reset_date = str(today)
            else:
                update_count += 1

            now_iso = datetime.now().isoformat()
            conn.execute("""
                UPDATE heuristics SET
                    confidence = ?,
                    confidence_ema = ?,
                    ema_alpha = ?,
                    ema_warmup_remaining = ?,
                    last_confidence_update = ?,
                    last_ema_update = ?,
                    last_used_at = ?,
                    update_count_today = ?,
                    update_count_reset_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_conf, new_ema, alpha_used, ema_warmup, now_iso, now_iso,
                  now_iso, update_count, reset_date, heuristic_id))

            # Record in audit trail with EMA details
            smoothed_delta = new_ema - old_ema
            self._record_update(conn, heuristic_id, old_conf, new_conf, update_type,
                              reason, False, session_id, agent_id,
                              raw_target, smoothed_delta, alpha_used)

            conn.commit()

            # Run fraud detection after confidence update (non-blocking)
            fraud_result = self._check_fraud_after_update(heuristic_id, total_apps)

            result = {
                "success": True,
                "old_confidence": old_conf,
                "new_confidence": new_conf,
                "raw_target": raw_target,
                "delta": new_conf - old_conf,
                "delta_raw": raw_target - old_conf,
                "delta_smoothed": smoothed_delta,
                "smoothing_effect": abs((raw_target - old_conf) - smoothed_delta),
                "alpha": alpha_used,
                "in_warmup": row['ema_warmup_remaining'] > 0 if row['ema_warmup_remaining'] else False,
                "update_type": update_type.value,
                "updates_today": update_count
            }

            if fraud_result:
                result["fraud_check"] = fraud_result

            return result
        finally:
            conn.close()

    def _check_fraud_after_update(self, heuristic_id: int, total_apps: int) -> Optional[Dict[str, Any]]:
        """
        Run fraud detection after confidence update.

        Only runs if:
        - Fraud detector is available
        - Heuristic has sufficient applications (10+)

        Non-blocking: errors are caught and logged.

        Returns:
            Fraud report summary if run, None otherwise
        """
        if not FRAUD_DETECTOR_AVAILABLE:
            return None

        # Only check heuristics with sufficient history
        if total_apps < 10:
            return None

        try:
            detector = FraudDetector(db_path=self.db_path)
            report = detector.create_fraud_report(heuristic_id)

            # Return summary (not full report which could be large)
            return {
                "checked": True,
                "classification": report.classification,
                "fraud_score": round(report.fraud_score, 3),
                "signal_count": len(report.signals)
            }
        except Exception as e:
            # Non-blocking: log error but don't fail the confidence update
            return {
                "checked": False,
                "error": str(e)
            }

    # =========================================================================
    # 2. RATE-BASED CONTRADICTION THRESHOLD
    # =========================================================================

    def check_deprecation_threshold(self, heuristic_id: int) -> Dict[str, Any]:
        """
        Check if heuristic should be deprecated based on RATE, not count.

        Fix for: "Good heuristics dying from 3 contradictions"
        New rule: Deprecate only if contradiction_rate > 30% over 10+ applications
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    id, rule, domain, confidence,
                    times_validated, times_violated,
                    COALESCE(times_contradicted, 0) as times_contradicted,
                    COALESCE(min_applications, 10) as min_applications,
                    status
                FROM heuristics WHERE id = ?
            """, (heuristic_id,))
            row = cursor.fetchone()

            if not row:
                return {"should_deprecate": False, "reason": "Heuristic not found"}

            total_apps = row['times_validated'] + row['times_violated'] + row['times_contradicted']

            # Not enough data yet
            if total_apps < row['min_applications']:
                return {
                    "should_deprecate": False,
                    "reason": f"Insufficient applications ({total_apps}/{row['min_applications']})",
                    "total_applications": total_apps,
                    "required_applications": row['min_applications']
                }

            # Calculate contradiction rate
            contradiction_rate = row['times_contradicted'] / total_apps if total_apps > 0 else 0

            should_deprecate = contradiction_rate > self.config.contradiction_rate_threshold

            result = {
                "should_deprecate": should_deprecate,
                "contradiction_rate": round(contradiction_rate, 3),
                "threshold": self.config.contradiction_rate_threshold,
                "total_applications": total_apps,
                "times_contradicted": row['times_contradicted'],
                "times_validated": row['times_validated'],
                "times_violated": row['times_violated']
            }

            if should_deprecate:
                result["reason"] = f"Contradiction rate {contradiction_rate:.1%} exceeds {self.config.contradiction_rate_threshold:.0%} threshold"
                # Actually deprecate
                conn.execute("""
                    UPDATE heuristics SET status = 'deprecated', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (heuristic_id,))
                conn.commit()
            else:
                result["reason"] = f"Contradiction rate {contradiction_rate:.1%} is below {self.config.contradiction_rate_threshold:.0%} threshold"

            return result
        finally:
            conn.close()

    def get_at_risk_heuristics(self, domain: Optional[str] = None) -> List[Dict]:
        """Find heuristics approaching deprecation threshold."""
        conn = self._get_connection()
        try:
            # Use subquery to filter on calculated columns
            base_query = """
                SELECT * FROM (
                    SELECT
                        id, rule, domain, confidence,
                        times_validated, times_violated,
                        COALESCE(times_contradicted, 0) as times_contradicted,
                        (times_validated + times_violated + COALESCE(times_contradicted, 0)) as total_apps,
                        CASE
                            WHEN (times_validated + times_violated + COALESCE(times_contradicted, 0)) = 0 THEN 0
                            ELSE CAST(COALESCE(times_contradicted, 0) AS REAL) /
                                 (times_validated + times_violated + COALESCE(times_contradicted, 0))
                        END as contradiction_rate
                    FROM heuristics
                    WHERE COALESCE(status, 'active') = 'active'
            """
            params = []
            if domain:
                base_query += " AND domain = ?"
                params.append(domain)

            base_query += """
                ) AS h
                WHERE h.total_apps >= 5
                AND h.contradiction_rate > ?
                ORDER BY h.contradiction_rate DESC
            """
            params.append(self.config.contradiction_rate_threshold * 0.7)  # 70% of threshold = at risk

            cursor = conn.execute(base_query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # =========================================================================
    # 3. DORMANT RECOVERY MECHANISM
    # =========================================================================

    def make_dormant(self, heuristic_id: int, reason: str = "") -> bool:
        """Move heuristic to dormant status with revival conditions."""
        conn = self._get_connection()
        try:
            # Get current heuristic
            cursor = conn.execute(
                "SELECT id, rule, domain, confidence FROM heuristics WHERE id = ?",
                (heuristic_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            # Extract keywords for revival triggers
            keywords = self._extract_keywords(row['rule'])
            revival_conditions = {
                "keywords": keywords,
                "domain": row["domain"],
                "min_confidence_for_revival": 0.35,
                "created_at": datetime.now().isoformat()
            }

            # Update to dormant
            conn.execute("""
                UPDATE heuristics SET
                    status = 'dormant',
                    dormant_since = CURRENT_TIMESTAMP,
                    revival_conditions = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(revival_conditions), heuristic_id))

            # Create revival triggers
            for keyword in keywords[:5]:  # Top 5 keywords
                conn.execute("""
                    INSERT INTO revival_triggers (heuristic_id, trigger_type, trigger_value)
                    VALUES (?, 'keyword', ?)
                """, (heuristic_id, keyword))

            # Time-based revival trigger (check again in 90 days)
            conn.execute("""
                INSERT INTO revival_triggers (heuristic_id, trigger_type, trigger_value)
                VALUES (?, 'time_period', ?)
            """, (heuristic_id, "90"))

            conn.commit()
            return True
        finally:
            conn.close()

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from heuristic text."""
        # Remove common words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                    'through', 'during', 'before', 'after', 'above', 'below',
                    'between', 'under', 'again', 'further', 'then', 'once',
                    'here', 'there', 'when', 'where', 'why', 'how', 'all',
                    'each', 'few', 'more', 'most', 'other', 'some', 'such',
                    'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                    'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
                    'until', 'while', 'always', 'never', 'use', 'using'}

        # Tokenize and filter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stopwords]

        # Return unique keywords, preserving order
        seen = set()
        return [x for x in keywords if not (x in seen or seen.add(x))]

    def revive_heuristic(self, heuristic_id: int, reason: str = "") -> Dict[str, Any]:
        """
        Revive a dormant heuristic back to active status.

        Fix for: "Total dormancy cascade with no recovery"
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT id, status, confidence, dormant_since, times_revived
                FROM heuristics WHERE id = ?
            """, (heuristic_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "reason": "Heuristic not found"}

            if row['status'] != 'dormant':
                return {"success": False, "reason": f"Heuristic is {row['status']}, not dormant"}

            # Calculate revival confidence (slight penalty for being dormant)
            old_conf = row['confidence']
            revival_conf = max(old_conf, 0.35)  # At least 0.35 on revival

            # Update status
            conn.execute("""
                UPDATE heuristics SET
                    status = 'active',
                    confidence = ?,
                    dormant_since = NULL,
                    times_revived = COALESCE(times_revived, 0) + 1,
                    last_used_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (revival_conf, heuristic_id))

            # Record the revival
            self._record_update(conn, heuristic_id, old_conf, revival_conf,
                              UpdateType.REVIVAL, reason or "Manual revival")

            conn.commit()

            return {
                "success": True,
                "old_confidence": old_conf,
                "new_confidence": revival_conf,
                "times_revived": (row['times_revived'] or 0) + 1
            }
        finally:
            conn.close()

    def check_revival_triggers(self, context: str = "") -> List[Dict]:
        """
        Check all dormant heuristics for potential revival.

        Returns list of heuristics that should be revived based on context.
        """
        conn = self._get_connection()
        try:
            candidates = []

            # Get dormant heuristics with keyword triggers
            cursor = conn.execute("""
                SELECT DISTINCT h.id, h.rule, h.domain, h.confidence,
                       h.dormant_since, rt.trigger_value as keyword
                FROM heuristics h
                JOIN revival_triggers rt ON h.id = rt.heuristic_id
                WHERE h.status = 'dormant'
                  AND rt.trigger_type = 'keyword'
                  AND rt.is_active = 1
            """)

            context_lower = context.lower()
            for row in cursor.fetchall():
                if row['keyword'] in context_lower:
                    candidates.append({
                        "id": row['id'],
                        "rule": row['rule'],
                        "domain": row['domain'],
                        "confidence": row['confidence'],
                        "trigger": f"keyword:{row['keyword']}",
                        "dormant_since": row['dormant_since']
                    })

            # Check time-based triggers
            cursor = conn.execute("""
                SELECT h.id, h.rule, h.domain, h.confidence,
                       h.dormant_since, rt.trigger_value as days
                FROM heuristics h
                JOIN revival_triggers rt ON h.id = rt.heuristic_id
                WHERE h.status = 'dormant'
                  AND rt.trigger_type = 'time_period'
                  AND rt.is_active = 1
                  AND julianday('now') - julianday(h.dormant_since) >= CAST(rt.trigger_value AS INTEGER)
            """)

            for row in cursor.fetchall():
                candidates.append({
                    "id": row['id'],
                    "rule": row['rule'],
                    "domain": row['domain'],
                    "confidence": row['confidence'],
                    "trigger": f"time:{row['days']} days dormant",
                    "dormant_since": row['dormant_since']
                })

            return candidates
        finally:
            conn.close()

    # =========================================================================
    # 4. EVICTION POLICY
    # =========================================================================

    def get_eviction_candidates(self, domain: str) -> List[Dict]:
        """
        Get ranked list of eviction candidates for a domain.

        Eviction score = confidence × recency_factor × usage_factor
        Lower score = more likely to be evicted

        Fix for: "Knowledge loss at domain limit"
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM eviction_candidates
                WHERE domain = ? AND status = 'active'
                ORDER BY eviction_score ASC
            """, (domain,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def enforce_domain_limits(self, domain: str) -> Dict[str, Any]:
        """
        Enforce domain limits with intelligent eviction.

        - Active heuristics: soft limit 5, hard limit 10
        - When over limit, demote lowest-scoring to dormant (not delete!)
        """
        conn = self._get_connection()
        try:
            # Count active heuristics in domain
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM heuristics
                WHERE domain = ? AND status = 'active'
            """, (domain,))
            active_count = cursor.fetchone()['count']

            if active_count <= self.config.max_active_per_domain:
                return {
                    "action": "none",
                    "active_count": active_count,
                    "limit": self.config.max_active_per_domain
                }

            # Get eviction candidates
            candidates = self.get_eviction_candidates(domain)

            # Calculate how many to demote
            to_demote = active_count - self.config.max_active_per_domain
            demoted = []

            for candidate in candidates[:to_demote]:
                # Don't demote golden rules
                cursor = conn.execute(
                    "SELECT is_golden FROM heuristics WHERE id = ?",
                    (candidate['id'],)
                )
                if cursor.fetchone()['is_golden']:
                    continue

                # Make dormant instead of deleting
                self.make_dormant(candidate['id'], f"Domain limit enforcement in {domain}")
                demoted.append({
                    "id": candidate['id'],
                    "rule": candidate['rule'],
                    "eviction_score": candidate['eviction_score']
                })

            conn.commit()

            return {
                "action": "demoted_to_dormant",
                "demoted_count": len(demoted),
                "demoted": demoted,
                "active_count": active_count - len(demoted),
                "limit": self.config.max_active_per_domain
            }
        finally:
            conn.close()

    def cleanup_dormant(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Archive dormant heuristics that have been dormant too long.
        Does NOT delete - moves to archived status.
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT id, rule, domain, dormant_since
                FROM heuristics
                WHERE status = 'dormant'
                  AND julianday('now') - julianday(dormant_since) > ?
            """
            params = [self.config.archived_after_dormant_days]

            if domain:
                query += " AND domain = ?"
                params.append(domain)

            cursor = conn.execute(query, params)
            to_archive = cursor.fetchall()

            archived = []
            for row in to_archive:
                conn.execute("""
                    UPDATE heuristics SET status = 'archived', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (row['id'],))
                archived.append({"id": row['id'], "rule": row['rule']})

            conn.commit()

            return {
                "archived_count": len(archived),
                "archived": archived,
                "threshold_days": self.config.archived_after_dormant_days
            }
        finally:
            conn.close()

    # =========================================================================
    # 5. DOMAIN ELASTICITY (Phase 2B)
    # =========================================================================

    def get_domain_state(self, domain: str) -> Dict[str, Any]:
        """
        Get current state and counts for a domain.

        Returns:
            Dictionary with domain metadata including state, counts, and limits
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT
                    domain, soft_limit, hard_limit, ceo_override_limit,
                    current_count, state, overflow_entered_at,
                    grace_period_days, max_overflow_days,
                    expansion_min_confidence, expansion_min_validations, expansion_min_novelty,
                    avg_confidence, health_score, last_health_check,
                    created_at, updated_at
                FROM domain_metadata
                WHERE domain = ?
            """, (domain,))
            row = cursor.fetchone()

            if not row:
                # Domain doesn't exist yet, return defaults
                return {
                    "domain": domain,
                    "soft_limit": 5,
                    "hard_limit": 10,
                    "ceo_override_limit": None,
                    "current_count": 0,
                    "state": "normal",
                    "overflow_entered_at": None,
                    "days_in_overflow": 0,
                    "exists": False
                }

            result = dict(row)
            # Calculate days in overflow
            if result['overflow_entered_at']:
                overflow_date = datetime.fromisoformat(result['overflow_entered_at'])
                result['days_in_overflow'] = (datetime.now() - overflow_date).days
            else:
                result['days_in_overflow'] = 0

            result['exists'] = True
            return result
        finally:
            conn.close()

    def can_add_heuristic(self, domain: str) -> Tuple[bool, str]:
        """
        Check if domain can accept a new heuristic.

        Returns:
            (can_add, reason) tuple
        """
        state = self.get_domain_state(domain)

        # Check against hard limit (or CEO override)
        effective_limit = state.get('ceo_override_limit') or state['hard_limit']

        if state['current_count'] >= effective_limit:
            return False, f"Hard limit reached ({effective_limit} active heuristics)"

        return True, "OK"

    def check_expansion_eligibility(self, heuristic_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """
        Check if heuristic meets quality gate for expansion beyond soft limit.

        Quality gate criteria:
        1. Confidence >= expansion_min_confidence (default 0.70)
        2. Validations >= expansion_min_validations (default 3)
        3. Novelty >= expansion_min_novelty (default 0.60)
        4. Domain health >= 0.50

        Returns:
            Dictionary with eligibility decision and scores
        """
        state = self.get_domain_state(domain)
        confidence = heuristic_data.get('confidence', 0.0)
        validations = heuristic_data.get('times_validated', 0)
        rule_text = heuristic_data.get('rule', '')

        # Check if we're at or above soft limit
        if state['current_count'] < state['soft_limit']:
            return {
                "eligible": True,
                "reason": "Under soft limit, no quality gate needed",
                "quality_gate_passed": False,
                "below_soft_limit": True
            }

        # Calculate novelty score
        novelty = self.calculate_novelty_score(rule_text, domain)

        # Check quality criteria
        min_conf = state.get('expansion_min_confidence', 0.70)
        min_val = state.get('expansion_min_validations', 3)
        min_nov = state.get('expansion_min_novelty', 0.60)

        passes_confidence = confidence >= min_conf
        passes_validations = validations >= min_val
        passes_novelty = novelty >= min_nov

        # Domain health check
        health = state.get('health_score', 1.0) or 1.0
        passes_health = health >= 0.50

        all_passed = passes_confidence and passes_validations and passes_novelty and passes_health

        return {
            "eligible": all_passed,
            "reason": self._build_eligibility_reason(
                passes_confidence, passes_validations, passes_novelty, passes_health,
                confidence, validations, novelty, health,
                min_conf, min_val, min_nov
            ),
            "quality_gate_passed": all_passed,
            "below_soft_limit": False,
            "scores": {
                "confidence": confidence,
                "validations": validations,
                "novelty": novelty,
                "health": health
            },
            "thresholds": {
                "min_confidence": min_conf,
                "min_validations": min_val,
                "min_novelty": min_nov,
                "min_health": 0.50
            },
            "checks": {
                "confidence": passes_confidence,
                "validations": passes_validations,
                "novelty": passes_novelty,
                "health": passes_health
            }
        }

    def _build_eligibility_reason(self, pass_conf, pass_val, pass_nov, pass_health,
                                   conf, val, nov, health,
                                   min_conf, min_val, min_nov) -> str:
        """Build human-readable eligibility reason."""
        if pass_conf and pass_val and pass_nov and pass_health:
            return "Quality gate passed: all criteria met"

        failures = []
        if not pass_conf:
            failures.append(f"confidence {conf:.2f} < {min_conf:.2f}")
        if not pass_val:
            failures.append(f"validations {val} < {min_val}")
        if not pass_nov:
            failures.append(f"novelty {nov:.2f} < {min_nov:.2f}")
        if not pass_health:
            failures.append(f"domain health {health:.2f} < 0.50")

        return "Quality gate failed: " + ", ".join(failures)

    def calculate_novelty_score(self, new_rule: str, domain: str) -> float:
        """
        Calculate novelty score using Jaccard similarity on keywords.

        Returns:
            Novelty score from 0.0 (duplicate) to 1.0 (completely novel)
        """
        conn = self._get_connection()
        try:
            # Get existing active heuristics in domain
            cursor = conn.execute("""
                SELECT rule FROM heuristics
                WHERE domain = ? AND status = 'active'
            """, (domain,))

            existing_rules = [row['rule'] for row in cursor.fetchall()]

            if not existing_rules:
                return 1.0  # First heuristic is always novel

            new_keywords = set(self._extract_keywords(new_rule))
            if not new_keywords:
                return 0.5  # No keywords extracted, assume moderate novelty

            max_similarity = 0.0

            for existing_rule in existing_rules:
                existing_keywords = set(self._extract_keywords(existing_rule))
                if not existing_keywords:
                    continue

                # Jaccard similarity: |A ∩ B| / |A ∪ B|
                intersection = len(new_keywords & existing_keywords)
                union = len(new_keywords | existing_keywords)

                if union > 0:
                    similarity = intersection / union
                    max_similarity = max(max_similarity, similarity)

            # Novelty = 1 - max_similarity
            return 1.0 - max_similarity

        finally:
            conn.close()

    def trigger_contraction(self, domain: str) -> Dict[str, Any]:
        """
        Initiate graceful contraction for a domain in overflow.

        Returns:
            Dictionary with contraction results
        """
        state = self.get_domain_state(domain)

        if state['state'] != 'overflow':
            return {
                "success": False,
                "reason": f"Domain is in '{state['state']}' state, not overflow"
            }

        # Check if still in grace period
        if state['days_in_overflow'] < state['grace_period_days']:
            return {
                "success": False,
                "reason": f"In grace period ({state['days_in_overflow']}/{state['grace_period_days']} days)",
                "grace_period": True
            }

        # Calculate target reduction
        current = state['current_count']
        soft_limit = state['soft_limit']
        overflow_amount = current - soft_limit

        # Linear contraction: reduce by 1-2 per week
        days_past_grace = state['days_in_overflow'] - state['grace_period_days']
        weeks_past_grace = days_past_grace / 7
        target_reduction = min(int(weeks_past_grace * 2), overflow_amount)

        if target_reduction == 0:
            return {
                "success": False,
                "reason": "Not enough time elapsed for contraction",
                "days_past_grace": days_past_grace
            }

        # Try to merge first
        merge_result = self.find_merge_candidates(domain)
        merged_count = 0

        if merge_result['candidates']:
            # Perform merges
            for candidate_pair in merge_result['candidates'][:target_reduction]:
                merge_success = self.merge_heuristics(
                    candidate_pair['ids'],
                    f"Merged during overflow contraction: {candidate_pair['reason']}"
                )
                if merge_success['success']:
                    merged_count += 1

        # If merges aren't enough, evict low-scoring heuristics
        evicted_count = 0
        remaining_to_reduce = target_reduction - merged_count

        if remaining_to_reduce > 0:
            candidates = self.get_eviction_candidates(domain)
            for candidate in candidates[:remaining_to_reduce]:
                self.make_dormant(candidate['id'], "Evicted during overflow contraction")
                evicted_count += 1

        # Log contraction event
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO expansion_events
                (domain, event_type, count_before, count_after, reason)
                VALUES (?, 'contraction', ?, ?, ?)
            """, (domain, current, current - merged_count - evicted_count,
                  f"Merged {merged_count}, evicted {evicted_count}"))
            conn.commit()
        finally:
            conn.close()

        return {
            "success": True,
            "merged_count": merged_count,
            "evicted_count": evicted_count,
            "total_reduced": merged_count + evicted_count,
            "count_before": current,
            "count_after": current - merged_count - evicted_count
        }

    def find_merge_candidates(self, domain: str) -> Dict[str, Any]:
        """
        Find similar heuristics that could be merged.

        Returns:
            Dictionary with candidate pairs and similarity scores
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT id, rule, confidence, times_validated
                FROM heuristics
                WHERE domain = ? AND status = 'active' AND COALESCE(is_golden, 0) = 0
                ORDER BY confidence DESC
            """, (domain,))

            heuristics = [dict(row) for row in cursor.fetchall()]
            candidates = []

            # Compare all pairs
            for i, h1 in enumerate(heuristics):
                for h2 in heuristics[i+1:]:
                    # Calculate keyword similarity
                    kw1 = set(self._extract_keywords(h1['rule']))
                    kw2 = set(self._extract_keywords(h2['rule']))

                    if not kw1 or not kw2:
                        continue

                    intersection = len(kw1 & kw2)
                    union = len(kw1 | kw2)
                    similarity = intersection / union if union > 0 else 0

                    # Consider for merge if similarity >= 0.40
                    if similarity >= 0.40:
                        candidates.append({
                            "ids": [h1['id'], h2['id']],
                            "rules": [h1['rule'], h2['rule']],
                            "similarity": round(similarity, 3),
                            "reason": f"Similarity: {similarity:.1%}",
                            "auto_merge": similarity >= 0.60
                        })

            # Sort by similarity (highest first)
            candidates.sort(key=lambda x: x['similarity'], reverse=True)

            return {
                "domain": domain,
                "candidates": candidates,
                "auto_mergeable": [c for c in candidates if c['auto_merge']],
                "manual_review": [c for c in candidates if not c['auto_merge']]
            }

        finally:
            conn.close()

    def merge_heuristics(self, source_ids: List[int], merged_rule: str) -> Dict[str, Any]:
        """
        Merge multiple heuristics into one.

        Args:
            source_ids: List of heuristic IDs to merge
            merged_rule: The merged rule text (or reason for merge)

        Returns:
            Dictionary with merge result
        """
        if len(source_ids) < 2:
            return {"success": False, "reason": "Need at least 2 heuristics to merge"}

        conn = self._get_connection()
        try:
            # Get source heuristics
            placeholders = ','.join('?' * len(source_ids))
            cursor = conn.execute(f"""
                SELECT id, domain, rule, confidence, times_validated, times_violated,
                       times_contradicted, explanation
                FROM heuristics
                WHERE id IN ({placeholders}) AND status = 'active'
            """, source_ids)

            sources = [dict(row) for row in cursor.fetchall()]

            if len(sources) != len(source_ids):
                return {"success": False, "reason": "Some heuristics not found or not active"}

            # All must be from same domain
            domains = set(s['domain'] for s in sources)
            if len(domains) > 1:
                return {"success": False, "reason": "Cannot merge heuristics from different domains"}

            domain = sources[0]['domain']

            # Calculate merged properties
            total_validations = sum(s['times_validated'] for s in sources)
            total_violations = sum(s['times_violated'] for s in sources)
            total_contradictions = sum(s.get('times_contradicted') or 0 for s in sources)

            # Weighted average confidence
            if total_validations > 0:
                merged_confidence = sum(
                    s['confidence'] * s['times_validated'] for s in sources
                ) / total_validations
            else:
                merged_confidence = sum(s['confidence'] for s in sources) / len(sources)

            # Combine explanations
            explanations = [s['explanation'] for s in sources if s['explanation']]
            merged_explanation = " | ".join(explanations) if explanations else merged_rule

            # Create merged heuristic
            cursor = conn.execute("""
                INSERT INTO heuristics
                (domain, rule, explanation, confidence, times_validated, times_violated,
                 times_contradicted, status, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            """, (domain, f"[MERGED] {merged_rule}", merged_explanation,
                  merged_confidence, total_validations, total_violations, total_contradictions))

            target_id = cursor.lastrowid

            # Mark source heuristics as archived
            conn.execute(f"""
                UPDATE heuristics
                SET status = 'archived', updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
            """, source_ids)

            # Record merge
            conn.execute("""
                INSERT INTO heuristic_merges
                (source_ids, target_id, merge_reason, merge_strategy, similarity_score)
                VALUES (?, ?, ?, 'weighted_average', NULL)
            """, (json.dumps(source_ids), target_id, merged_rule))

            # Log expansion event
            conn.execute("""
                INSERT INTO expansion_events
                (domain, heuristic_id, event_type, count_before, count_after, reason)
                VALUES (?, ?, 'merge', ?, ?, ?)
            """, (domain, target_id, len(sources), 1, merged_rule))

            conn.commit()

            return {
                "success": True,
                "target_id": target_id,
                "merged_from": source_ids,
                "merged_confidence": round(merged_confidence, 3),
                "total_validations": total_validations,
                "total_violations": total_violations,
                "space_saved": len(sources) - 1
            }

        except Exception as e:
            conn.rollback()
            return {"success": False, "reason": f"Merge failed: {str(e)}"}
        finally:
            conn.close()

    # =========================================================================
    # 6. LIFECYCLE MAINTENANCE
    # =========================================================================

    def run_maintenance(self, enable_contraction: bool = True) -> Dict[str, Any]:
        """
        Run full lifecycle maintenance.

        - Apply decay to unused heuristics
        - Check dormancy thresholds
        - Enforce domain limits
        - Archive old dormant heuristics
        - Check revival triggers
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "decay": [],
            "made_dormant": [],
            "archived": [],
            "revivals_checked": [],
            "domain_enforcement": {}
        }

        conn = self._get_connection()
        try:
            # 1. Apply decay to heuristics not used in decay_half_life_days
            cursor = conn.execute("""
                SELECT id, confidence, last_used_at
                FROM heuristics
                WHERE status = 'active'
                  AND julianday('now') - julianday(COALESCE(last_used_at, created_at)) > ?
            """, (self.config.decay_half_life_days,))

            for row in cursor.fetchall():
                new_conf = max(row['confidence'] * 0.92, self.config.min_confidence)
                conn.execute("""
                    UPDATE heuristics SET confidence = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_conf, row['id']))
                results["decay"].append({
                    "id": row['id'],
                    "old_confidence": row['confidence'],
                    "new_confidence": new_conf
                })

                # Check if should go dormant
                if new_conf < self.config.decay_floor:
                    self.make_dormant(row['id'], "Confidence decayed below threshold")
                    results["made_dormant"].append(row['id'])

            conn.commit()
        finally:
            conn.close()

        # 2. Enforce domain limits
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT DISTINCT domain FROM heuristics WHERE status = 'active'")
            for row in cursor.fetchall():
                enforcement = self.enforce_domain_limits(row['domain'])
                if enforcement["action"] != "none":
                    results["domain_enforcement"][row['domain']] = enforcement
        finally:
            conn.close()

        # 3. Archive old dormant heuristics
        archive_result = self.cleanup_dormant()
        results["archived"] = archive_result["archived"]

        return results

    def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get statistics about heuristic lifecycle states."""
        conn = self._get_connection()
        try:
            stats = {}

            # Status distribution
            cursor = conn.execute("""
                SELECT
                    COALESCE(status, 'active') as status,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM heuristics
                GROUP BY COALESCE(status, 'active')
            """)
            stats["by_status"] = {row['status']: {
                "count": row['count'],
                "avg_confidence": round(row['avg_confidence'], 3) if row['avg_confidence'] else 0
            } for row in cursor.fetchall()}

            # Domain health
            cursor = conn.execute("SELECT * FROM domain_health ORDER BY active_count DESC")
            stats["domains"] = [dict(row) for row in cursor.fetchall()]

            # At-risk heuristics
            stats["at_risk"] = self.get_at_risk_heuristics()

            # Recent confidence updates
            cursor = conn.execute("""
                SELECT update_type, COUNT(*) as count, AVG(delta) as avg_delta
                FROM confidence_updates
                WHERE created_at > datetime('now', '-7 days')
                GROUP BY update_type
            """)
            stats["recent_updates"] = {row['update_type']: {
                "count": row['count'],
                "avg_delta": round(row['avg_delta'], 4) if row['avg_delta'] else 0
            } for row in cursor.fetchall()}

            return stats
        finally:
            conn.close()


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Heuristic Lifecycle Manager")
    parser.add_argument("command", choices=["stats", "maintenance", "check-revival", "at-risk"])
    parser.add_argument("--domain", help="Filter by domain")
    parser.add_argument("--context", help="Context for revival check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    manager = LifecycleManager()

    if args.command == "stats":
        result = manager.get_lifecycle_stats()
    elif args.command == "maintenance":
        result = manager.run_maintenance()
    elif args.command == "check-revival":
        result = manager.check_revival_triggers(args.context or "")
    elif args.command == "at-risk":
        result = manager.get_at_risk_heuristics(args.domain)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(json.dumps(result, indent=2, default=str))
