#!/usr/bin/env python3
"""
Dashboard V2: Enhanced visual dashboard with full emergent-learning integration.

Features:
- Heuristics/learnings/experiments panel
- Hot spots linked to related heuristics
- Timeline/trend visualization
- Findings aggregation
- DAG workflow visualization (D3.js)
- Interactive filters and search
- Agent performance matrix
- Anomaly detection alerts

USAGE:
    python dashboard_v2.py                    # Generate and open dashboard
    python dashboard_v2.py --output report.html
    python dashboard_v2.py --run-id 123       # Focus on specific run
    python dashboard_v2.py --serve            # Start local server
"""

import json
import os
import re
import sys
import sqlite3
import webbrowser
import http.server
import socketserver
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from collections import defaultdict
import html
import argparse
import statistics


class DashboardV2Generator:
    """Generate enhanced HTML dashboards with full learning integration."""

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.db_path = self.base_path / "memory" / "index.db"

    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_dashboard_data(self, run_id: int = None, days: int = 7) -> Dict:
        """Gather all data for enhanced dashboard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = {}

            # ============ WORKFLOW DATA ============
            # Recent workflow runs
            cursor.execute("""
                SELECT id, workflow_id, workflow_name, status, phase,
                       total_nodes, completed_nodes, failed_nodes,
                       started_at, completed_at, created_at
                FROM workflow_runs
                WHERE created_at > datetime('now', ?)
                ORDER BY created_at DESC
                LIMIT 50
            """, (f'-{days} days',))
            data['runs'] = [dict(row) for row in cursor.fetchall()]

            # Statistics
            cursor.execute("SELECT COUNT(*) FROM workflow_runs")
            data['total_runs'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM node_executions")
            data['total_executions'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM trails")
            data['total_trails'] = cursor.fetchone()[0]

            # Runs by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM workflow_runs GROUP BY status
            """)
            data['runs_by_status'] = dict(cursor.fetchall())

            # Executions by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM node_executions GROUP BY status
            """)
            data['executions_by_status'] = dict(cursor.fetchall())

            # ============ LEARNING DATA ============
            # Heuristics summary
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN is_golden = 1 THEN 1 ELSE 0 END) as golden,
                       AVG(confidence) as avg_confidence,
                       SUM(times_validated) as total_validations
                FROM heuristics
            """)
            row = cursor.fetchone()
            data['heuristics_summary'] = {
                'total': row['total'] or 0,
                'golden': row['golden'] or 0,
                'avg_confidence': row['avg_confidence'] or 0,
                'total_validations': row['total_validations'] or 0
            }

            # Top heuristics by confidence
            cursor.execute("""
                SELECT id, domain, rule, explanation, confidence,
                       times_validated, times_violated, is_golden
                FROM heuristics
                ORDER BY confidence DESC, times_validated DESC
                LIMIT 15
            """)
            data['top_heuristics'] = [dict(row) for row in cursor.fetchall()]

            # Golden rules
            cursor.execute("""
                SELECT id, domain, rule, explanation, confidence, times_validated
                FROM heuristics
                WHERE is_golden = 1
                ORDER BY times_validated DESC
            """)
            data['golden_rules'] = [dict(row) for row in cursor.fetchall()]

            # Heuristics by domain
            cursor.execute("""
                SELECT domain, COUNT(*) as count, AVG(confidence) as avg_conf
                FROM heuristics
                GROUP BY domain
                ORDER BY count DESC
            """)
            data['heuristics_by_domain'] = [dict(row) for row in cursor.fetchall()]

            # Learnings summary
            cursor.execute("""
                SELECT type, COUNT(*) as count
                FROM learnings
                GROUP BY type
            """)
            data['learnings_by_type'] = dict(cursor.fetchall())

            cursor.execute("SELECT COUNT(*) FROM learnings")
            data['total_learnings'] = cursor.fetchone()[0]

            # Recent learnings
            cursor.execute("""
                SELECT id, type, title, summary, domain, severity, created_at
                FROM learnings
                ORDER BY created_at DESC
                LIMIT 10
            """)
            data['recent_learnings'] = [dict(row) for row in cursor.fetchall()]

            # Experiments
            cursor.execute("""
                SELECT id, name, hypothesis, status, cycles_run, created_at
                FROM experiments
                ORDER BY created_at DESC
                LIMIT 10
            """)
            data['experiments'] = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM experiments GROUP BY status
            """)
            data['experiments_by_status'] = dict(cursor.fetchall())

            # CEO reviews pending
            cursor.execute("""
                SELECT id, title, context, recommendation, created_at
                FROM ceo_reviews
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """)
            data['pending_ceo_reviews'] = [dict(row) for row in cursor.fetchall()]

            # ============ HOT SPOTS WITH CONTEXT ============
            cursor.execute("""
                SELECT location, COUNT(*) as count, SUM(strength) as total_strength,
                       GROUP_CONCAT(DISTINCT scent) as scents,
                       GROUP_CONCAT(DISTINCT agent_id) as agents,
                       MAX(created_at) as last_activity
                FROM trails
                WHERE created_at > datetime('now', ?)
                GROUP BY location
                ORDER BY total_strength DESC
                LIMIT 20
            """, (f'-{days} days',))
            data['hotspots'] = [dict(row) for row in cursor.fetchall()]

            # Link hotspots to heuristics (by matching keywords in location)
            for hotspot in data['hotspots']:
                location = hotspot['location'].lower()
                # Extract filename without path
                filename = location.split('/')[-1].split('\\')[-1]
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename

                # Find related heuristics
                cursor.execute("""
                    SELECT id, rule, confidence, domain
                    FROM heuristics
                    WHERE LOWER(rule) LIKE ? OR LOWER(explanation) LIKE ?
                       OR LOWER(domain) LIKE ?
                    ORDER BY confidence DESC
                    LIMIT 3
                """, (f'%{base_name}%', f'%{base_name}%', f'%{base_name}%'))
                hotspot['related_heuristics'] = [dict(row) for row in cursor.fetchall()]

            # Trail scent distribution
            cursor.execute("""
                SELECT scent, COUNT(*) as count, SUM(strength) as total_strength
                FROM trails
                WHERE created_at > datetime('now', ?)
                GROUP BY scent
                ORDER BY count DESC
            """, (f'-{days} days',))
            data['trails_by_scent'] = [dict(row) for row in cursor.fetchall()]

            # ============ TIMELINE DATA ============
            # Activity by day
            cursor.execute("""
                SELECT DATE(created_at) as day, COUNT(*) as runs
                FROM workflow_runs
                WHERE created_at > datetime('now', ?)
                GROUP BY DATE(created_at)
                ORDER BY day
            """, (f'-{days} days',))
            data['runs_by_day'] = [dict(row) for row in cursor.fetchall()]

            # Trail activity by day
            cursor.execute("""
                SELECT DATE(created_at) as day,
                       COUNT(*) as trails,
                       SUM(strength) as total_strength
                FROM trails
                WHERE created_at > datetime('now', ?)
                GROUP BY DATE(created_at)
                ORDER BY day
            """, (f'-{days} days',))
            data['trails_by_day'] = [dict(row) for row in cursor.fetchall()]

            # Hot spot trends (which locations are getting hotter/cooler)
            cursor.execute("""
                SELECT location,
                       SUM(CASE WHEN created_at > datetime('now', '-1 day') THEN strength ELSE 0 END) as recent,
                       SUM(CASE WHEN created_at <= datetime('now', '-1 day') THEN strength ELSE 0 END) as older
                FROM trails
                WHERE created_at > datetime('now', ?)
                GROUP BY location
                HAVING recent > 0 OR older > 0
                ORDER BY (recent - older) DESC
                LIMIT 10
            """, (f'-{days} days',))
            data['hotspot_trends'] = [dict(row) for row in cursor.fetchall()]

            # ============ FINDINGS AGGREGATION ============
            cursor.execute("""
                SELECT ne.findings_json, ne.node_name, ne.created_at, wr.workflow_name
                FROM node_executions ne
                LEFT JOIN workflow_runs wr ON ne.run_id = wr.id
                WHERE ne.findings_json IS NOT NULL
                  AND ne.findings_json != '[]'
                  AND ne.findings_json != 'null'
                  AND ne.created_at > datetime('now', ?)
                ORDER BY ne.created_at DESC
                LIMIT 50
            """, (f'-{days} days',))

            all_findings = []
            for row in cursor.fetchall():
                try:
                    findings = json.loads(row['findings_json'] or '[]')
                    for f in findings:
                        f['node_name'] = row['node_name']
                        f['workflow_name'] = row['workflow_name']
                        f['found_at'] = row['created_at']
                        all_findings.append(f)
                except json.JSONDecodeError:
                    pass

            # Aggregate findings by type/importance
            findings_by_type = defaultdict(list)
            for f in all_findings:
                ftype = f.get('type', 'note')
                importance = f.get('importance', 'normal')
                findings_by_type[f"{importance}:{ftype}"].append(f)

            data['findings_aggregated'] = dict(findings_by_type)
            data['total_findings'] = len(all_findings)

            # ============ AGENT PERFORMANCE ============
            cursor.execute("""
                SELECT node_type,
                       COUNT(*) as total_runs,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successes,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures,
                       AVG(duration_ms) as avg_duration_ms
                FROM node_executions
                WHERE created_at > datetime('now', ?)
                GROUP BY node_type
            """, (f'-{days} days',))
            data['agent_performance'] = [dict(row) for row in cursor.fetchall()]

            # ============ ANOMALY DETECTION ============
            anomalies = []

            # Check for runs taking much longer than average
            cursor.execute("""
                SELECT AVG(
                    CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS INTEGER)
                ) as avg_duration
                FROM workflow_runs
                WHERE completed_at IS NOT NULL
            """)
            avg_duration = cursor.fetchone()['avg_duration'] or 0

            if avg_duration > 0:
                cursor.execute("""
                    SELECT id, workflow_name, started_at,
                           CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS INTEGER) as duration
                    FROM workflow_runs
                    WHERE completed_at IS NOT NULL
                      AND CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS INTEGER) > ?
                    ORDER BY duration DESC
                    LIMIT 5
                """, (avg_duration * 3,))  # 3x average
                for row in cursor.fetchall():
                    anomalies.append({
                        'type': 'slow_run',
                        'severity': 'warning',
                        'message': f"Run #{row['id']} ({row['workflow_name']}) took {row['duration']:.0f}s (avg: {avg_duration:.0f}s)",
                        'run_id': row['id']
                    })

            # Check for sudden hot spots (new locations with high activity)
            cursor.execute("""
                SELECT location, SUM(strength) as strength, COUNT(*) as count
                FROM trails
                WHERE created_at > datetime('now', '-1 day')
                  AND location NOT IN (
                      SELECT DISTINCT location FROM trails
                      WHERE created_at <= datetime('now', '-1 day')
                        AND created_at > datetime('now', '-7 days')
                  )
                GROUP BY location
                HAVING strength > 1.0
                ORDER BY strength DESC
                LIMIT 5
            """)
            for row in cursor.fetchall():
                anomalies.append({
                    'type': 'new_hotspot',
                    'severity': 'info',
                    'message': f"New hot spot: {row['location']} (strength: {row['strength']:.1f}, {row['count']} trails)",
                    'location': row['location']
                })

            # Check for consecutive failures
            cursor.execute("""
                SELECT node_name, COUNT(*) as fail_count
                FROM node_executions
                WHERE status = 'failed'
                  AND created_at > datetime('now', '-1 day')
                GROUP BY node_name
                HAVING fail_count >= 3
            """)
            for row in cursor.fetchall():
                anomalies.append({
                    'type': 'repeated_failure',
                    'severity': 'error',
                    'message': f"Node '{row['node_name']}' failed {row['fail_count']} times in 24h",
                    'node_name': row['node_name']
                })

            # Check for heuristics being violated
            cursor.execute("""
                SELECT rule, times_violated, confidence
                FROM heuristics
                WHERE times_violated > 0
                  AND confidence > 0.7
                ORDER BY times_violated DESC
                LIMIT 3
            """)
            for row in cursor.fetchall():
                anomalies.append({
                    'type': 'heuristic_violated',
                    'severity': 'warning',
                    'message': f"High-confidence heuristic violated {row['times_violated']}x: {row['rule'][:60]}...",
                    'confidence': row['confidence']
                })

            data['anomalies'] = anomalies

            # ============ RECENT FAILURES ============
            cursor.execute("""
                SELECT ne.id, ne.node_name, ne.node_type, ne.error_message, ne.error_type,
                       ne.created_at, ne.duration_ms, wr.workflow_name, wr.id as run_id
                FROM node_executions ne
                LEFT JOIN workflow_runs wr ON ne.run_id = wr.id
                WHERE ne.status = 'failed'
                ORDER BY ne.created_at DESC
                LIMIT 10
            """)
            data['recent_failures'] = [dict(row) for row in cursor.fetchall()]

            # ============ WORKFLOW GRAPH DATA ============
            if run_id:
                cursor.execute("""
                    SELECT * FROM workflow_runs WHERE id = ?
                """, (run_id,))
                row = cursor.fetchone()
                if row:
                    data['selected_run'] = dict(row)

                cursor.execute("""
                    SELECT * FROM node_executions
                    WHERE run_id = ?
                    ORDER BY created_at
                """, (run_id,))
                data['run_executions'] = [dict(row) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT * FROM conductor_decisions
                    WHERE run_id = ?
                    ORDER BY created_at
                """, (run_id,))
                data['run_decisions'] = [dict(row) for row in cursor.fetchall()]

                # Get workflow edges if workflow_id exists
                workflow_id = data['selected_run'].get('workflow_id')
                if workflow_id:
                    cursor.execute("""
                        SELECT from_node, to_node, condition, edge_type
                        FROM workflow_edges
                        WHERE workflow_id = ?
                    """, (workflow_id,))
                    data['workflow_edges'] = [dict(row) for row in cursor.fetchall()]
                else:
                    data['workflow_edges'] = []

            # ============ METRICS ============
            cursor.execute("""
                SELECT metric_type, metric_name,
                       AVG(metric_value) as avg_value,
                       MAX(metric_value) as max_value,
                       MIN(metric_value) as min_value,
                       COUNT(*) as sample_count
                FROM metrics
                WHERE timestamp > datetime('now', ?)
                GROUP BY metric_type, metric_name
            """, (f'-{days} days',))
            data['metrics_summary'] = [dict(row) for row in cursor.fetchall()]

            return data

    def generate_html(self, data: Dict) -> str:
        """Generate enhanced HTML dashboard."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conductor Dashboard V2</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="dashboard">
        <header>
            <div class="header-left">
                <h1>Conductor Dashboard</h1>
                <span class="version">v2.0</span>
            </div>
            <div class="header-right">
                <div class="filter-controls">
                    <select id="timeRange" onchange="filterByTime(this.value)">
                        <option value="1">Last 24h</option>
                        <option value="7" selected>Last 7 days</option>
                        <option value="30">Last 30 days</option>
                        <option value="all">All time</option>
                    </select>
                    <input type="text" id="searchBox" placeholder="Search hot spots..." onkeyup="filterHotspots(this.value)">
                </div>
                <span class="timestamp">Generated: {timestamp}</span>
            </div>
        </header>

        {self._generate_anomaly_alerts(data.get('anomalies', []))}

        {self._generate_stats_row(data)}

        {self._generate_intelligence_panel(data)}

        {self._generate_run_detail(data) if data.get('selected_run') else ""}

        <div class="grid-3">
            <div class="card">
                <h2>Recent Workflow Runs</h2>
                {self._generate_runs_table(data.get('runs', []))}
            </div>

            <div class="card">
                <h2>Trail Hot Spots</h2>
                <div class="scent-filters">
                    {self._generate_scent_filters(data.get('trails_by_scent', []))}
                </div>
                <div id="hotspots-container">
                    {self._generate_enhanced_hotspots(data.get('hotspots', []))}
                </div>
            </div>

            <div class="card">
                <h2>Findings Summary</h2>
                {self._generate_findings_panel(data)}
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <h2>Activity Timeline</h2>
                <div id="timeline-chart" class="chart-container"></div>
                {self._generate_timeline_data_script(data)}
            </div>

            <div class="card">
                <h2>Hot Spot Trends</h2>
                {self._generate_hotspot_trends(data.get('hotspot_trends', []))}
            </div>
        </div>

        <div class="grid-2">
            <div class="card">
                <h2>Agent Performance</h2>
                {self._generate_agent_performance(data.get('agent_performance', []))}
            </div>

            <div class="card">
                <h2>Recent Failures</h2>
                {self._generate_failures(data.get('recent_failures', []))}
            </div>
        </div>

        <div class="card full-width">
            <h2>Top Heuristics</h2>
            {self._generate_heuristics_table(data.get('top_heuristics', []))}
        </div>
    </div>

    <script>
        {self._get_javascript()}
    </script>
</body>
</html>"""

    def _get_css(self) -> str:
        """Get all CSS styles."""
        return """
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-card: #21262d;
            --bg-hover: #30363d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent: #58a6ff;
            --accent-hover: #79c0ff;
            --success: #3fb950;
            --warning: #d29922;
            --error: #f85149;
            --info: #58a6ff;
            --purple: #a371f7;
            --border: #30363d;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 20px;
            font-size: 14px;
        }

        .dashboard {
            max-width: 1600px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .header-left {
            display: flex;
            align-items: baseline;
            gap: 10px;
        }

        h1 {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .version {
            font-size: 12px;
            color: var(--text-muted);
            background: var(--bg-card);
            padding: 2px 8px;
            border-radius: 12px;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .filter-controls {
            display: flex;
            gap: 8px;
        }

        .filter-controls select,
        .filter-controls input {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
        }

        .filter-controls input {
            width: 200px;
        }

        .filter-controls select:focus,
        .filter-controls input:focus {
            outline: none;
            border-color: var(--accent);
        }

        .timestamp {
            color: var(--text-muted);
            font-size: 12px;
        }

        /* Grids */
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 16px;
        }

        .grid-3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 16px;
        }

        .grid-4 {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 16px;
        }

        @media (max-width: 1200px) {
            .grid-3 { grid-template-columns: repeat(2, 1fr); }
            .grid-4 { grid-template-columns: repeat(2, 1fr); }
        }

        @media (max-width: 768px) {
            .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; }
        }

        /* Cards */
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 16px;
        }

        .card.full-width {
            margin-bottom: 16px;
        }

        .card h2 {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Stats Row */
        .stats-row {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 16px;
            margin-bottom: 16px;
        }

        @media (max-width: 1200px) {
            .stats-row { grid-template-columns: repeat(3, 1fr); }
        }

        .stat-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 16px;
            text-align: center;
        }

        .stat-value {
            font-size: 32px;
            font-weight: 600;
            color: var(--accent);
            line-height: 1;
        }

        .stat-value.success { color: var(--success); }
        .stat-value.warning { color: var(--warning); }
        .stat-value.error { color: var(--error); }
        .stat-value.purple { color: var(--purple); }

        .stat-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }

        .stat-sublabel {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* Anomaly Alerts */
        .anomaly-container {
            margin-bottom: 16px;
        }

        .anomaly-alert {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 8px;
            font-size: 13px;
        }

        .anomaly-alert.error {
            background: rgba(248, 81, 73, 0.1);
            border: 1px solid rgba(248, 81, 73, 0.4);
            color: var(--error);
        }

        .anomaly-alert.warning {
            background: rgba(210, 153, 34, 0.1);
            border: 1px solid rgba(210, 153, 34, 0.4);
            color: var(--warning);
        }

        .anomaly-alert.info {
            background: rgba(88, 166, 255, 0.1);
            border: 1px solid rgba(88, 166, 255, 0.4);
            color: var(--info);
        }

        .anomaly-icon {
            font-size: 16px;
        }

        /* Intelligence Panel */
        .intelligence-panel {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }

        @media (max-width: 1200px) {
            .intelligence-panel { grid-template-columns: repeat(3, 1fr); }
        }

        .intel-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 12px;
        }

        .intel-card h3 {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .intel-stat {
            font-size: 24px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .intel-detail {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        th, td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }

        th {
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        tr:hover {
            background: var(--bg-hover);
        }

        /* Status badges */
        .status {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
        }

        .status-completed { background: rgba(63, 185, 80, 0.2); color: var(--success); }
        .status-running { background: rgba(88, 166, 255, 0.2); color: var(--info); }
        .status-failed { background: rgba(248, 81, 73, 0.2); color: var(--error); }
        .status-pending { background: rgba(210, 153, 34, 0.2); color: var(--warning); }

        /* Hot spots */
        .hotspot {
            padding: 10px 12px;
            margin-bottom: 8px;
            background: var(--bg-card);
            border-radius: 6px;
            border-left: 3px solid var(--accent);
            cursor: pointer;
            transition: background 0.2s;
        }

        .hotspot:hover {
            background: var(--bg-hover);
        }

        .hotspot-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .hotspot-location {
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            color: var(--text-primary);
            word-break: break-all;
        }

        .hotspot-strength {
            font-weight: 600;
            color: var(--accent);
            font-size: 14px;
        }

        .hotspot-details {
            margin-top: 6px;
            font-size: 11px;
            color: var(--text-secondary);
        }

        .hotspot-heuristics {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--border);
            display: none;
        }

        .hotspot.expanded .hotspot-heuristics {
            display: block;
        }

        .heuristic-link {
            font-size: 11px;
            color: var(--text-secondary);
            padding: 4px 0;
            display: block;
        }

        .heuristic-link:before {
            content: "\\2022";
            margin-right: 6px;
            color: var(--accent);
        }

        /* Scent tags */
        .scent-tag {
            display: inline-block;
            padding: 1px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 500;
            margin-left: 4px;
        }

        .scent-discovery { background: rgba(63, 185, 80, 0.2); color: var(--success); }
        .scent-warning { background: rgba(210, 153, 34, 0.2); color: var(--warning); }
        .scent-blocker { background: rgba(248, 81, 73, 0.2); color: var(--error); }
        .scent-hot { background: rgba(163, 113, 247, 0.2); color: var(--purple); }
        .scent-exploration { background: rgba(88, 166, 255, 0.2); color: var(--info); }

        .scent-filters {
            display: flex;
            gap: 6px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }

        .scent-filter {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            cursor: pointer;
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            transition: all 0.2s;
        }

        .scent-filter:hover,
        .scent-filter.active {
            border-color: var(--accent);
            color: var(--accent);
        }

        /* Trends */
        .trend-item {
            display: flex;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
        }

        .trend-item:last-child {
            border-bottom: none;
        }

        .trend-location {
            flex: 1;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            color: var(--text-primary);
        }

        .trend-indicator {
            width: 80px;
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
        }

        .trend-up { color: var(--error); }
        .trend-down { color: var(--success); }
        .trend-stable { color: var(--text-muted); }

        .trend-bar {
            height: 4px;
            background: var(--bg-card);
            border-radius: 2px;
            flex: 1;
            position: relative;
            overflow: hidden;
        }

        .trend-bar-fill {
            position: absolute;
            height: 100%;
            border-radius: 2px;
        }

        /* Agent performance */
        .agent-row {
            display: grid;
            grid-template-columns: 1fr 60px 80px 100px;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
            align-items: center;
        }

        .agent-row:last-child {
            border-bottom: none;
        }

        .agent-name {
            font-weight: 500;
            color: var(--text-primary);
        }

        .agent-stat {
            text-align: center;
            font-size: 13px;
        }

        .success-rate {
            font-weight: 600;
        }

        .success-rate.high { color: var(--success); }
        .success-rate.medium { color: var(--warning); }
        .success-rate.low { color: var(--error); }

        /* Failures */
        .failure-item {
            padding: 12px;
            margin-bottom: 8px;
            background: var(--bg-card);
            border-radius: 6px;
            border-left: 3px solid var(--error);
        }

        .failure-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .failure-node {
            font-weight: 600;
            color: var(--text-primary);
        }

        .failure-time {
            font-size: 11px;
            color: var(--text-muted);
        }

        .failure-workflow {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        .failure-error {
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 11px;
            color: var(--error);
            margin-top: 8px;
            padding: 8px;
            background: var(--bg-primary);
            border-radius: 4px;
            overflow-x: auto;
        }

        /* Findings */
        .finding-group {
            margin-bottom: 12px;
        }

        .finding-group-header {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .finding-count {
            background: var(--bg-card);
            padding: 1px 6px;
            border-radius: 10px;
            font-size: 10px;
        }

        .finding-item {
            padding: 6px 10px;
            background: var(--bg-card);
            border-radius: 4px;
            margin-bottom: 4px;
            font-size: 12px;
            color: var(--text-primary);
        }

        .finding-critical { border-left: 2px solid var(--error); }
        .finding-high { border-left: 2px solid var(--warning); }
        .finding-normal { border-left: 2px solid var(--info); }
        .finding-low { border-left: 2px solid var(--text-muted); }

        /* Heuristics table */
        .heuristic-rule {
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .confidence-bar {
            width: 60px;
            height: 6px;
            background: var(--bg-card);
            border-radius: 3px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-right: 6px;
        }

        .confidence-fill {
            height: 100%;
            border-radius: 3px;
            background: var(--success);
        }

        .golden-badge {
            display: inline-block;
            padding: 1px 6px;
            border-radius: 3px;
            font-size: 10px;
            background: rgba(210, 153, 34, 0.2);
            color: var(--warning);
        }

        /* Chart container */
        .chart-container {
            height: 200px;
            position: relative;
        }

        /* Run detail */
        .run-detail {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 16px;
        }

        .run-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }

        .run-title {
            font-size: 18px;
            font-weight: 600;
        }

        .run-meta {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* DAG Visualization */
        .dag-container {
            background: var(--bg-card);
            border-radius: 6px;
            padding: 16px;
            min-height: 200px;
        }

        .dag-node {
            padding: 8px 16px;
            background: var(--bg-secondary);
            border: 2px solid var(--border);
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
        }

        .dag-node.completed { border-color: var(--success); }
        .dag-node.running { border-color: var(--info); }
        .dag-node.failed { border-color: var(--error); }
        .dag-node.pending { border-color: var(--warning); }

        .dag-edge {
            stroke: var(--border);
            stroke-width: 2;
            fill: none;
            marker-end: url(#arrowhead);
        }

        /* Empty states */
        .empty-state {
            text-align: center;
            padding: 32px;
            color: var(--text-muted);
        }

        /* Links */
        a {
            color: var(--accent);
            text-decoration: none;
        }

        a:hover {
            color: var(--accent-hover);
            text-decoration: underline;
        }

        /* Scrollable */
        .scrollable {
            max-height: 400px;
            overflow-y: auto;
        }

        .scrollable::-webkit-scrollbar {
            width: 6px;
        }

        .scrollable::-webkit-scrollbar-track {
            background: var(--bg-card);
        }

        .scrollable::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 3px;
        }
        """

    def _get_javascript(self) -> str:
        """Get all JavaScript code."""
        return """
        // Toggle hotspot expansion
        document.querySelectorAll('.hotspot').forEach(el => {
            el.addEventListener('click', () => {
                el.classList.toggle('expanded');
            });
        });

        // Filter hotspots by search
        function filterHotspots(query) {
            const hotspots = document.querySelectorAll('.hotspot');
            query = query.toLowerCase();
            hotspots.forEach(h => {
                const location = h.querySelector('.hotspot-location').textContent.toLowerCase();
                h.style.display = location.includes(query) ? 'block' : 'none';
            });
        }

        // Filter by scent type
        function filterByScent(scent, btn) {
            const hotspots = document.querySelectorAll('.hotspot');
            const isActive = btn.classList.contains('active');

            // Toggle active state
            document.querySelectorAll('.scent-filter').forEach(b => b.classList.remove('active'));
            if (!isActive && scent !== 'all') {
                btn.classList.add('active');
            }

            hotspots.forEach(h => {
                if (scent === 'all' || isActive) {
                    h.style.display = 'block';
                } else {
                    const hasScent = h.dataset.scents && h.dataset.scents.includes(scent);
                    h.style.display = hasScent ? 'block' : 'none';
                }
            });
        }

        // Filter by time range (would need server-side support for full impl)
        function filterByTime(days) {
            // For now, just reload with query param
            if (days !== 'all') {
                window.location.search = '?days=' + days;
            }
        }

        // Draw timeline chart
        function drawTimelineChart(runsData, trailsData) {
            const container = document.getElementById('timeline-chart');
            if (!container || (!runsData.length && !trailsData.length)) {
                container.innerHTML = '<div class="empty-state">No activity data</div>';
                return;
            }

            const margin = {top: 20, right: 30, bottom: 30, left: 40};
            const width = container.clientWidth - margin.left - margin.right;
            const height = 160 - margin.top - margin.bottom;

            // Clear previous
            container.innerHTML = '';

            const svg = d3.select(container)
                .append('svg')
                .attr('width', width + margin.left + margin.right)
                .attr('height', height + margin.top + margin.bottom)
                .append('g')
                .attr('transform', `translate(${margin.left},${margin.top})`);

            // Parse dates
            const parseDate = d3.timeParse('%Y-%m-%d');
            runsData.forEach(d => d.date = parseDate(d.day));
            trailsData.forEach(d => d.date = parseDate(d.day));

            // Scales
            const allDates = [...runsData.map(d => d.date), ...trailsData.map(d => d.date)].filter(d => d);
            if (allDates.length === 0) return;

            const x = d3.scaleTime()
                .domain(d3.extent(allDates))
                .range([0, width]);

            const maxRuns = d3.max(runsData, d => d.runs) || 1;
            const maxTrails = d3.max(trailsData, d => d.trails) || 1;
            const yRuns = d3.scaleLinear()
                .domain([0, maxRuns])
                .range([height, 0]);

            // Axes
            svg.append('g')
                .attr('transform', `translate(0,${height})`)
                .call(d3.axisBottom(x).ticks(5).tickFormat(d3.timeFormat('%m/%d')))
                .attr('color', '#8b949e');

            svg.append('g')
                .call(d3.axisLeft(yRuns).ticks(5))
                .attr('color', '#8b949e');

            // Runs line
            const runLine = d3.line()
                .x(d => x(d.date))
                .y(d => yRuns(d.runs))
                .curve(d3.curveMonotoneX);

            svg.append('path')
                .datum(runsData.filter(d => d.date))
                .attr('fill', 'none')
                .attr('stroke', '#58a6ff')
                .attr('stroke-width', 2)
                .attr('d', runLine);

            // Runs dots
            svg.selectAll('.run-dot')
                .data(runsData.filter(d => d.date))
                .enter()
                .append('circle')
                .attr('cx', d => x(d.date))
                .attr('cy', d => yRuns(d.runs))
                .attr('r', 4)
                .attr('fill', '#58a6ff');

            // Trails area (scaled to fit)
            const yTrails = d3.scaleLinear()
                .domain([0, maxTrails])
                .range([height, height * 0.3]);

            const trailArea = d3.area()
                .x(d => x(d.date))
                .y0(height)
                .y1(d => yTrails(d.trails))
                .curve(d3.curveMonotoneX);

            svg.append('path')
                .datum(trailsData.filter(d => d.date))
                .attr('fill', 'rgba(163, 113, 247, 0.2)')
                .attr('d', trailArea);

            // Legend
            const legend = svg.append('g')
                .attr('transform', `translate(${width - 100}, 0)`);

            legend.append('circle').attr('cx', 0).attr('cy', 0).attr('r', 4).attr('fill', '#58a6ff');
            legend.append('text').attr('x', 10).attr('y', 4).text('Runs').attr('fill', '#8b949e').attr('font-size', '10px');

            legend.append('rect').attr('x', -2).attr('y', 12).attr('width', 8).attr('height', 8).attr('fill', 'rgba(163, 113, 247, 0.5)');
            legend.append('text').attr('x', 10).attr('y', 20).text('Trails').attr('fill', '#8b949e').attr('font-size', '10px');
        }

        // Initialize chart when DOM ready
        document.addEventListener('DOMContentLoaded', () => {
            if (window.timelineRunsData && window.timelineTrailsData) {
                drawTimelineChart(window.timelineRunsData, window.timelineTrailsData);
            }
        });

        // Redraw on resize
        window.addEventListener('resize', () => {
            if (window.timelineRunsData && window.timelineTrailsData) {
                drawTimelineChart(window.timelineRunsData, window.timelineTrailsData);
            }
        });
        """

    def _generate_anomaly_alerts(self, anomalies: List[Dict]) -> str:
        """Generate anomaly alert banners."""
        if not anomalies:
            return ""

        alerts = []
        icons = {'error': '!!!', 'warning': '!!', 'info': '*'}

        for a in anomalies[:5]:  # Show max 5
            severity = a.get('severity', 'info')
            icon = icons.get(severity, '*')
            alerts.append(f"""
                <div class="anomaly-alert {severity}">
                    <span class="anomaly-icon">{icon}</span>
                    <span>{html.escape(a.get('message', ''))}</span>
                </div>
            """)

        return f"""
        <div class="anomaly-container">
            {''.join(alerts)}
        </div>
        """

    def _generate_stats_row(self, data: Dict) -> str:
        """Generate top stats row."""
        execs = data.get('executions_by_status', {})
        runs = data.get('runs_by_status', {})

        failed_nodes = execs.get('failed', 0)
        completed_runs = runs.get('completed', 0)
        total_runs = data.get('total_runs', 0)

        return f"""
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-value">{total_runs}</div>
                <div class="stat-label">Total Runs</div>
                <div class="stat-sublabel">{completed_runs} completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data.get('total_executions', 0)}</div>
                <div class="stat-label">Executions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value purple">{data.get('total_trails', 0)}</div>
                <div class="stat-label">Trails</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {'error' if failed_nodes > 0 else ''}">{failed_nodes}</div>
                <div class="stat-label">Failed Nodes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value success">{data.get('heuristics_summary', {}).get('total', 0)}</div>
                <div class="stat-label">Heuristics</div>
                <div class="stat-sublabel">{data.get('heuristics_summary', {}).get('golden', 0)} golden</div>
            </div>
            <div class="stat-card">
                <div class="stat-value warning">{data.get('total_findings', 0)}</div>
                <div class="stat-label">Findings</div>
            </div>
        </div>
        """

    def _generate_intelligence_panel(self, data: Dict) -> str:
        """Generate the learning intelligence panel."""
        h_summary = data.get('heuristics_summary', {})
        l_by_type = data.get('learnings_by_type', {})
        exp_by_status = data.get('experiments_by_status', {})
        pending_ceo = len(data.get('pending_ceo_reviews', []))

        avg_conf = h_summary.get('avg_confidence', 0)
        conf_pct = f"{avg_conf * 100:.0f}%" if avg_conf else "N/A"

        return f"""
        <div class="intelligence-panel">
            <div class="intel-card">
                <h3>Golden Rules</h3>
                <div class="intel-stat">{h_summary.get('golden', 0)}</div>
                <div class="intel-detail">Constitutional principles</div>
            </div>
            <div class="intel-card">
                <h3>Heuristics</h3>
                <div class="intel-stat">{h_summary.get('total', 0)}</div>
                <div class="intel-detail">Avg confidence: {conf_pct}</div>
            </div>
            <div class="intel-card">
                <h3>Learnings</h3>
                <div class="intel-stat">{data.get('total_learnings', 0)}</div>
                <div class="intel-detail">
                    {l_by_type.get('failure', 0)} failures,
                    {l_by_type.get('success', 0)} successes
                </div>
            </div>
            <div class="intel-card">
                <h3>Experiments</h3>
                <div class="intel-stat">{exp_by_status.get('active', 0)}</div>
                <div class="intel-detail">
                    {exp_by_status.get('completed', 0)} completed
                </div>
            </div>
            <div class="intel-card">
                <h3>CEO Queue</h3>
                <div class="intel-stat" style="color: {'var(--warning)' if pending_ceo > 0 else 'var(--text-muted)'}">
                    {pending_ceo}
                </div>
                <div class="intel-detail">Pending decisions</div>
            </div>
        </div>
        """

    def _generate_runs_table(self, runs: List[Dict]) -> str:
        """Generate workflow runs table."""
        if not runs:
            return '<div class="empty-state">No workflow runs found</div>'

        rows = []
        for run in runs[:15]:
            status = run.get('status', 'unknown')
            status_class = f"status-{status}"
            nodes = f"{run.get('completed_nodes') or 0}/{run.get('total_nodes') or 0}"
            failed = run.get('failed_nodes') or 0
            name = html.escape(run.get('workflow_name') or f"Run #{run['id']}")

            rows.append(f"""
                <tr>
                    <td><a href="?run_id={run['id']}">#{run['id']}</a></td>
                    <td>{name}</td>
                    <td><span class="status {status_class}">{status}</span></td>
                    <td>{nodes}</td>
                    <td style="color: {'var(--error)' if failed else 'inherit'}">{failed}</td>
                </tr>
            """)

        return f"""
        <div class="scrollable">
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Nodes</th>
                    <th>Failed</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        </div>
        """

    def _generate_scent_filters(self, trails_by_scent: List[Dict]) -> str:
        """Generate scent filter buttons."""
        filters = ['<span class="scent-filter" onclick="filterByScent(\'all\', this)">All</span>']

        for item in trails_by_scent[:6]:
            scent = item.get('scent', 'unknown')
            count = item.get('count', 0)
            filters.append(
                f'<span class="scent-filter" onclick="filterByScent(\'{scent}\', this)">'
                f'{scent} ({count})</span>'
            )

        return ''.join(filters)

    def _generate_enhanced_hotspots(self, hotspots: List[Dict]) -> str:
        """Generate enhanced hotspots with heuristic links."""
        if not hotspots:
            return '<div class="empty-state">No trail activity</div>'

        items = []
        max_strength = max(h.get('total_strength', 0) for h in hotspots) if hotspots else 1

        for spot in hotspots[:12]:
            location = html.escape(spot.get('location', '')[:60])
            strength = spot.get('total_strength') or 0
            count = spot.get('count', 0)
            scents = (spot.get('scents') or '').split(',')
            agents = (spot.get('agents') or '').split(',')
            related = spot.get('related_heuristics', [])

            scent_tags = ''.join([
                f'<span class="scent-tag scent-{s.strip()}">{s.strip()}</span>'
                for s in scents if s.strip()
            ])

            # Heuristic links
            heuristic_html = ""
            if related:
                links = []
                for h in related:
                    conf = h.get('confidence', 0)
                    rule = html.escape(h.get('rule', '')[:80])
                    links.append(f'<span class="heuristic-link">{rule} ({conf:.0%})</span>')
                heuristic_html = f"""
                    <div class="hotspot-heuristics">
                        <div style="font-size: 10px; color: var(--text-muted); margin-bottom: 4px;">
                            Related Heuristics:
                        </div>
                        {''.join(links)}
                    </div>
                """

            scents_data = ','.join(scents)
            items.append(f"""
                <div class="hotspot" data-scents="{scents_data}">
                    <div class="hotspot-header">
                        <span class="hotspot-location">{location}{scent_tags}</span>
                        <span class="hotspot-strength">{strength:.1f}</span>
                    </div>
                    <div class="hotspot-details">
                        {count} trails from {len([a for a in agents if a.strip()])} agents
                    </div>
                    {heuristic_html}
                </div>
            """)

        return f'<div class="scrollable">{"".join(items)}</div>'

    def _generate_findings_panel(self, data: Dict) -> str:
        """Generate findings aggregation panel."""
        findings = data.get('findings_aggregated', {})

        if not findings:
            return '<div class="empty-state">No findings recorded</div>'

        # Sort by importance
        importance_order = ['critical', 'high', 'normal', 'low']
        groups = []

        for key, items in sorted(findings.items(),
                                  key=lambda x: (importance_order.index(x[0].split(':')[0])
                                               if x[0].split(':')[0] in importance_order else 99)):
            parts = key.split(':')
            importance = parts[0] if parts else 'normal'
            ftype = parts[1] if len(parts) > 1 else 'note'

            finding_items = []
            for f in items[:3]:  # Max 3 per group
                content = html.escape(f.get('content', '')[:100])
                finding_items.append(
                    f'<div class="finding-item finding-{importance}">{content}</div>'
                )

            groups.append(f"""
                <div class="finding-group">
                    <div class="finding-group-header">
                        {importance.upper()}: {ftype}
                        <span class="finding-count">{len(items)}</span>
                    </div>
                    {''.join(finding_items)}
                </div>
            """)

        return f'<div class="scrollable">{"".join(groups[:6])}</div>'

    def _generate_timeline_data_script(self, data: Dict) -> str:
        """Generate script with timeline data."""
        runs_data = json.dumps(data.get('runs_by_day', []))
        trails_data = json.dumps(data.get('trails_by_day', []))

        return f"""
        <script>
            window.timelineRunsData = {runs_data};
            window.timelineTrailsData = {trails_data};
        </script>
        """

    def _generate_hotspot_trends(self, trends: List[Dict]) -> str:
        """Generate hotspot trends visualization."""
        if not trends:
            return '<div class="empty-state">No trend data available</div>'

        items = []
        for t in trends[:10]:
            location = html.escape(t.get('location', '')[:40])
            recent = t.get('recent', 0) or 0
            older = t.get('older', 0) or 0
            diff = recent - older

            if diff > 0.5:
                trend_class = 'trend-up'
                trend_icon = '^'
            elif diff < -0.5:
                trend_class = 'trend-down'
                trend_icon = 'v'
            else:
                trend_class = 'trend-stable'
                trend_icon = '-'

            # Bar visualization
            total = recent + older
            recent_pct = (recent / total * 100) if total > 0 else 0

            items.append(f"""
                <div class="trend-item">
                    <span class="trend-location">{location}</span>
                    <div class="trend-indicator {trend_class}">
                        <span>{trend_icon}</span>
                        <span>{diff:+.1f}</span>
                    </div>
                </div>
            """)

        return f'<div class="scrollable">{"".join(items)}</div>'

    def _generate_agent_performance(self, performance: List[Dict]) -> str:
        """Generate agent performance matrix."""
        if not performance:
            return '<div class="empty-state">No performance data</div>'

        rows = []
        for p in performance:
            agent_type = p.get('node_type', 'unknown')
            total = p.get('total_runs', 0)
            successes = p.get('successes', 0)
            failures = p.get('failures', 0)
            avg_duration = p.get('avg_duration_ms', 0) or 0

            success_rate = (successes / total * 100) if total > 0 else 0
            rate_class = 'high' if success_rate >= 90 else 'medium' if success_rate >= 70 else 'low'

            duration_str = f"{avg_duration/1000:.1f}s" if avg_duration > 1000 else f"{avg_duration:.0f}ms"

            rows.append(f"""
                <div class="agent-row">
                    <span class="agent-name">{html.escape(agent_type or 'single')}</span>
                    <span class="agent-stat">{total}</span>
                    <span class="agent-stat success-rate {rate_class}">{success_rate:.0f}%</span>
                    <span class="agent-stat">{duration_str}</span>
                </div>
            """)

        return f"""
        <div class="agent-row" style="font-weight: 600; color: var(--text-secondary);">
            <span>Agent Type</span>
            <span style="text-align: center;">Runs</span>
            <span style="text-align: center;">Success</span>
            <span style="text-align: center;">Avg Time</span>
        </div>
        {''.join(rows)}
        """

    def _generate_failures(self, failures: List[Dict]) -> str:
        """Generate failures list."""
        if not failures:
            return '<div class="empty-state">No recent failures</div>'

        items = []
        for f in failures[:8]:
            node_name = html.escape(f.get('node_name') or 'Unknown')
            workflow = html.escape(f.get('workflow_name') or 'Ad-hoc')
            error = html.escape((f.get('error_message') or 'No error message')[:150])
            time_str = f.get('created_at', '')[:16] if f.get('created_at') else ''

            items.append(f"""
                <div class="failure-item">
                    <div class="failure-header">
                        <span class="failure-node">{node_name}</span>
                        <span class="failure-time">{time_str}</span>
                    </div>
                    <div class="failure-workflow">{workflow}</div>
                    <div class="failure-error">{error}</div>
                </div>
            """)

        return f'<div class="scrollable">{"".join(items)}</div>'

    def _generate_heuristics_table(self, heuristics: List[Dict]) -> str:
        """Generate heuristics table."""
        if not heuristics:
            return '<div class="empty-state">No heuristics found</div>'

        rows = []
        for h in heuristics:
            domain = html.escape(h.get('domain') or 'general')
            rule = html.escape(h.get('rule', '')[:80])
            confidence = h.get('confidence', 0) or 0
            validated = h.get('times_validated', 0)
            violated = h.get('times_violated', 0)
            is_golden = h.get('is_golden', False)

            golden_badge = '<span class="golden-badge">GOLDEN</span>' if is_golden else ''
            conf_pct = confidence * 100

            rows.append(f"""
                <tr>
                    <td>{domain}</td>
                    <td class="heuristic-rule" title="{html.escape(h.get('rule', ''))}">{rule}</td>
                    <td>
                        <span class="confidence-bar">
                            <span class="confidence-fill" style="width: {conf_pct}%"></span>
                        </span>
                        {conf_pct:.0f}%
                    </td>
                    <td>{validated}</td>
                    <td style="color: {'var(--error)' if violated > 0 else 'inherit'}">{violated}</td>
                    <td>{golden_badge}</td>
                </tr>
            """)

        return f"""
        <div class="scrollable">
        <table>
            <thead>
                <tr>
                    <th>Domain</th>
                    <th>Rule</th>
                    <th>Confidence</th>
                    <th>Validated</th>
                    <th>Violated</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        </div>
        """

    def _generate_run_detail(self, data: Dict) -> str:
        """Generate detailed run view with DAG."""
        run = data.get('selected_run')
        if not run:
            return ""

        executions = data.get('run_executions', [])
        edges = data.get('workflow_edges', [])
        decisions = data.get('run_decisions', [])

        status = run.get('status', 'unknown')
        status_class = f"status-{status}"

        # Build DAG nodes
        dag_nodes = []
        node_positions = {}

        # Simple layout: left to right
        for i, ex in enumerate(executions):
            node_id = ex.get('node_id', f'node{i}')
            node_name = html.escape(ex.get('node_name') or node_id)
            node_status = ex.get('status', 'pending')
            duration = ex.get('duration_ms')
            duration_str = f" ({duration}ms)" if duration else ""

            node_positions[node_id] = (100 + i * 150, 80)
            dag_nodes.append({
                'id': node_id,
                'name': node_name,
                'status': node_status,
                'x': 100 + i * 150,
                'y': 80,
                'duration': duration_str
            })

        # Generate SVG DAG
        dag_width = max(400, len(executions) * 150 + 100)
        dag_svg = self._generate_dag_svg(dag_nodes, edges, dag_width)

        # Decisions log
        decisions_html = ""
        if decisions:
            decision_items = []
            for d in decisions[:5]:
                dtype = d.get('decision_type', 'unknown')
                reason = html.escape(d.get('reason', '')[:100])
                decision_items.append(f'<div style="padding: 4px 0; font-size: 12px;">[{dtype}] {reason}</div>')
            decisions_html = f"""
                <div style="margin-top: 16px;">
                    <h4 style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">Decisions</h4>
                    {''.join(decision_items)}
                </div>
            """

        return f"""
        <div class="run-detail">
            <div class="run-header">
                <div>
                    <div class="run-title">Run #{run['id']}: {html.escape(run.get('workflow_name') or 'Ad-hoc')}</div>
                    <div class="run-meta">
                        Phase: {run.get('phase', 'unknown')} |
                        Started: {run.get('started_at', 'N/A')[:19]} |
                        Completed: {(run.get('completed_at') or 'Running')[:19]}
                    </div>
                </div>
                <span class="status {status_class}">{status}</span>
            </div>

            <h3 style="font-size: 13px; margin-bottom: 12px;">Workflow Graph</h3>
            <div class="dag-container">
                {dag_svg}
            </div>

            {decisions_html}
        </div>
        """

    def _generate_dag_svg(self, nodes: List[Dict], edges: List[Dict], width: int) -> str:
        """Generate SVG DAG visualization."""
        if not nodes:
            return '<div class="empty-state">No nodes to display</div>'

        height = 160

        # Build node elements
        node_elements = []
        for n in nodes:
            status_color = {
                'completed': '#3fb950',
                'running': '#58a6ff',
                'failed': '#f85149',
                'pending': '#d29922'
            }.get(n['status'], '#6e7681')

            node_elements.append(f"""
                <g transform="translate({n['x']}, {n['y']})">
                    <rect x="-50" y="-20" width="100" height="40" rx="6"
                          fill="#21262d" stroke="{status_color}" stroke-width="2"/>
                    <text x="0" y="0" text-anchor="middle" fill="#e6edf3"
                          font-size="11" dominant-baseline="middle">
                        {n['name'][:12]}
                    </text>
                    <text x="0" y="12" text-anchor="middle" fill="#8b949e"
                          font-size="9" dominant-baseline="middle">
                        {n['duration']}
                    </text>
                </g>
            """)

        # Build edge elements (simple horizontal connections)
        edge_elements = []
        for i in range(len(nodes) - 1):
            x1 = nodes[i]['x'] + 50
            x2 = nodes[i + 1]['x'] - 50
            y = nodes[i]['y']
            edge_elements.append(f"""
                <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"
                      stroke="#30363d" stroke-width="2" marker-end="url(#arrowhead)"/>
            """)

        return f"""
        <svg width="{width}" height="{height}" style="display: block; margin: 0 auto;">
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7"
                        refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#30363d"/>
                </marker>
            </defs>
            {''.join(edge_elements)}
            {''.join(node_elements)}
        </svg>
        """

    def generate_and_save(self, output_path: str = None, run_id: int = None, days: int = 7) -> str:
        """Generate dashboard and save to file."""
        data = self.get_dashboard_data(run_id=run_id, days=days)
        html_content = self.generate_html(data)

        if output_path is None:
            output_path = self.base_path / "conductor" / "dashboard_v2.html"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(html_content, encoding='utf-8')
        return str(output_path)


def serve_dashboard(port: int = 8766, base_path: str = None):
    """Start a local HTTP server for the dashboard."""
    generator = DashboardV2Generator(base_path)
    dashboard_dir = generator.base_path / "conductor"

    class DashboardHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard_dir), **kwargs)

        def do_GET(self):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            run_id = int(params.get('run_id', [0])[0]) or None
            days = int(params.get('days', [7])[0])

            generator.generate_and_save(run_id=run_id, days=days)

            # Serve the dashboard file
            self.path = '/dashboard_v2.html'
            super().do_GET()

    print(f"Serving dashboard at http://localhost:{port}")
    print("Press Ctrl+C to stop")

    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")


def main():
    parser = argparse.ArgumentParser(description="Conductor Dashboard V2 Generator")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--run-id", type=int, help="Focus on specific run")
    parser.add_argument("--days", type=int, default=7, help="Days of history (default: 7)")
    parser.add_argument("--serve", action="store_true", help="Start local server")
    parser.add_argument("--port", type=int, default=8766, help="Server port (default: 8766)")
    parser.add_argument("--no-open", action="store_true", help="Don't open in browser")

    args = parser.parse_args()

    if args.serve:
        serve_dashboard(args.port)
    else:
        generator = DashboardV2Generator()
        output = generator.generate_and_save(args.output, args.run_id, args.days)
        print(f"Dashboard V2 generated: {output}")

        if not args.no_open:
            webbrowser.open(f"file://{output}")


if __name__ == "__main__":
    main()
