#!/usr/bin/env python3
"""
Dashboard: Visual HTML dashboard for workflow runs and hot spots.

Generates an interactive HTML dashboard showing:
- Workflow runs with status
- Node execution graph
- Trail hot spots (heatmap)
- Findings timeline
- Statistics

USAGE:
    python dashboard.py                    # Generate and open dashboard
    python dashboard.py --output report.html
    python dashboard.py --run-id 123       # Focus on specific run
    python dashboard.py --serve            # Start local server
"""

import json
import os
import sys
import sqlite3
import webbrowser
import http.server
import socketserver
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from contextlib import contextmanager
import html
import argparse


class DashboardGenerator:
    """Generate HTML dashboards for conductor data."""

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
        """Gather all data for dashboard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = {}

            # Recent workflow runs
            cursor.execute("""
                SELECT id, workflow_name, status, phase,
                       total_nodes, completed_nodes, failed_nodes,
                       started_at, completed_at
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

            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM workflow_runs GROUP BY status
            """)
            data['runs_by_status'] = dict(cursor.fetchall())

            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM node_executions GROUP BY status
            """)
            data['executions_by_status'] = dict(cursor.fetchall())

            # Hot spots
            cursor.execute("""
                SELECT location, COUNT(*) as count, SUM(strength) as total_strength,
                       GROUP_CONCAT(DISTINCT scent) as scents
                FROM trails
                WHERE created_at > datetime('now', ?)
                GROUP BY location
                ORDER BY total_strength DESC
                LIMIT 20
            """, (f'-{days} days',))
            data['hotspots'] = [dict(row) for row in cursor.fetchall()]

            # Trail scent distribution
            cursor.execute("""
                SELECT scent, COUNT(*) as count
                FROM trails GROUP BY scent
            """)
            data['trails_by_scent'] = dict(cursor.fetchall())

            # Recent failures
            cursor.execute("""
                SELECT ne.id, ne.node_name, ne.error_message, ne.error_type,
                       ne.created_at, wr.workflow_name
                FROM node_executions ne
                LEFT JOIN workflow_runs wr ON ne.run_id = wr.id
                WHERE ne.status = 'failed'
                ORDER BY ne.created_at DESC
                LIMIT 10
            """)
            data['recent_failures'] = [dict(row) for row in cursor.fetchall()]

            # If specific run requested
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

            return data

    def generate_html(self, data: Dict) -> str:
        """Generate HTML dashboard from data."""
        runs_html = self._generate_runs_table(data.get('runs', []))
        hotspots_html = self._generate_hotspots(data.get('hotspots', []))
        failures_html = self._generate_failures(data.get('recent_failures', []))
        stats_html = self._generate_stats(data)
        run_detail_html = self._generate_run_detail(data) if data.get('selected_run') else ""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conductor Dashboard</title>
    <style>
        :root {{
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-card: #0f3460;
            --text-primary: #eee;
            --text-secondary: #aaa;
            --accent: #e94560;
            --success: #4ade80;
            --warning: #fbbf24;
            --error: #ef4444;
            --info: #60a5fa;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
        }}

        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--bg-card);
        }}

        h1 {{
            font-size: 2rem;
            color: var(--accent);
        }}

        .timestamp {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}

        .card h2 {{
            font-size: 1.1rem;
            color: var(--text-secondary);
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}

        .stat {{
            text-align: center;
            padding: 15px;
            background: var(--bg-card);
            border-radius: 8px;
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }}

        .stat-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}

        th, td {{
            padding: 12px 8px;
            text-align: left;
            border-bottom: 1px solid var(--bg-card);
        }}

        th {{
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
        }}

        tr:hover {{
            background: var(--bg-card);
        }}

        .status {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }}

        .status-completed {{ background: var(--success); color: #000; }}
        .status-running {{ background: var(--info); color: #000; }}
        .status-failed {{ background: var(--error); color: #fff; }}
        .status-pending {{ background: var(--warning); color: #000; }}

        .hotspot {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin-bottom: 8px;
            background: var(--bg-card);
            border-radius: 8px;
            border-left: 4px solid var(--accent);
        }}

        .hotspot-location {{
            font-family: monospace;
            color: var(--text-primary);
            word-break: break-all;
        }}

        .hotspot-strength {{
            font-weight: bold;
            color: var(--accent);
            min-width: 60px;
            text-align: right;
        }}

        .scent-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75rem;
            margin-left: 5px;
        }}

        .scent-discovery {{ background: var(--success); color: #000; }}
        .scent-warning {{ background: var(--warning); color: #000; }}
        .scent-blocker {{ background: var(--error); color: #fff; }}
        .scent-hot {{ background: var(--accent); color: #fff; }}

        .failure-item {{
            padding: 12px;
            margin-bottom: 10px;
            background: var(--bg-card);
            border-radius: 8px;
            border-left: 4px solid var(--error);
        }}

        .failure-node {{
            font-weight: bold;
            color: var(--text-primary);
        }}

        .failure-error {{
            color: var(--error);
            font-family: monospace;
            font-size: 0.85rem;
            margin-top: 5px;
        }}

        .failure-time {{
            color: var(--text-secondary);
            font-size: 0.8rem;
            margin-top: 5px;
        }}

        .run-detail {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
        }}

        .run-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }}

        .node-graph {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }}

        .node {{
            padding: 10px 15px;
            background: var(--bg-card);
            border-radius: 8px;
            border: 2px solid transparent;
            font-size: 0.9rem;
        }}

        .node-completed {{ border-color: var(--success); }}
        .node-running {{ border-color: var(--info); }}
        .node-failed {{ border-color: var(--error); }}
        .node-pending {{ border-color: var(--warning); }}

        .empty-state {{
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }}

        @media (max-width: 768px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
            .stat-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <header>
            <h1>Conductor Dashboard</h1>
            <span class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
        </header>

        {stats_html}

        {run_detail_html}

        <div class="grid">
            <div class="card">
                <h2>Recent Workflow Runs</h2>
                {runs_html}
            </div>

            <div class="card">
                <h2>Trail Hot Spots</h2>
                {hotspots_html}
            </div>
        </div>

        <div class="card">
            <h2>Recent Failures</h2>
            {failures_html}
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds if served
        if (window.location.protocol !== 'file:') {{
            setTimeout(() => window.location.reload(), 30000);
        }}
    </script>
</body>
</html>"""

    def _generate_stats(self, data: Dict) -> str:
        """Generate statistics cards."""
        runs_by_status = data.get('runs_by_status', {})
        execs_by_status = data.get('executions_by_status', {})

        return f"""
        <div class="grid" style="grid-template-columns: repeat(4, 1fr);">
            <div class="stat">
                <div class="stat-value">{data.get('total_runs', 0)}</div>
                <div class="stat-label">Total Runs</div>
            </div>
            <div class="stat">
                <div class="stat-value">{data.get('total_executions', 0)}</div>
                <div class="stat-label">Executions</div>
            </div>
            <div class="stat">
                <div class="stat-value">{data.get('total_trails', 0)}</div>
                <div class="stat-label">Trails</div>
            </div>
            <div class="stat">
                <div class="stat-value">{execs_by_status.get('failed', 0)}</div>
                <div class="stat-label">Failed Nodes</div>
            </div>
        </div>
        """

    def _generate_runs_table(self, runs: List[Dict]) -> str:
        """Generate workflow runs table."""
        if not runs:
            return '<div class="empty-state">No workflow runs found</div>'

        rows = []
        for run in runs[:15]:
            status_class = f"status-{run['status']}"
            nodes = f"{run['completed_nodes'] or 0}/{run['total_nodes'] or 0}"
            failed = run['failed_nodes'] or 0
            name = html.escape(run['workflow_name'] or f"Run #{run['id']}")

            rows.append(f"""
                <tr>
                    <td><a href="?run_id={run['id']}" style="color: var(--accent);">#{run['id']}</a></td>
                    <td>{name}</td>
                    <td><span class="status {status_class}">{run['status']}</span></td>
                    <td>{nodes}</td>
                    <td style="color: {'var(--error)' if failed else 'inherit'}">{failed}</td>
                </tr>
            """)

        return f"""
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
        """

    def _generate_hotspots(self, hotspots: List[Dict]) -> str:
        """Generate hotspots visualization."""
        if not hotspots:
            return '<div class="empty-state">No trail activity</div>'

        items = []
        max_strength = max(h['total_strength'] for h in hotspots) if hotspots else 1

        for spot in hotspots[:10]:
            location = html.escape(spot['location'][:50])
            strength = spot['total_strength'] or 0
            scents = (spot['scents'] or '').split(',')

            scent_tags = ''.join([
                f'<span class="scent-tag scent-{s.strip()}">{s.strip()}</span>'
                for s in scents if s.strip()
            ])

            # Bar width based on relative strength
            bar_pct = min(100, (strength / max_strength) * 100) if max_strength else 0

            items.append(f"""
                <div class="hotspot" style="background: linear-gradient(90deg, var(--bg-card) {bar_pct}%, transparent {bar_pct}%);">
                    <span class="hotspot-location">{location}{scent_tags}</span>
                    <span class="hotspot-strength">{strength:.1f}</span>
                </div>
            """)

        return ''.join(items)

    def _generate_failures(self, failures: List[Dict]) -> str:
        """Generate failures list."""
        if not failures:
            return '<div class="empty-state">No recent failures</div>'

        items = []
        for f in failures:
            node_name = html.escape(f['node_name'] or 'Unknown')
            error = html.escape((f['error_message'] or 'No error message')[:200])
            workflow = html.escape(f['workflow_name'] or 'Ad-hoc')
            time_str = f['created_at'] or ''

            items.append(f"""
                <div class="failure-item">
                    <div class="failure-node">{node_name}</div>
                    <div style="color: var(--text-secondary); font-size: 0.85rem;">{workflow}</div>
                    <div class="failure-error">{error}</div>
                    <div class="failure-time">{time_str}</div>
                </div>
            """)

        return ''.join(items)

    def _generate_run_detail(self, data: Dict) -> str:
        """Generate detailed run view."""
        run = data.get('selected_run')
        if not run:
            return ""

        executions = data.get('run_executions', [])
        status_class = f"status-{run['status']}"

        nodes_html = []
        for ex in executions:
            node_class = f"node-{ex['status']}"
            node_name = html.escape(ex['node_name'] or ex['node_id'])
            duration = f"{ex['duration_ms']}ms" if ex['duration_ms'] else ""
            nodes_html.append(f"""
                <div class="node {node_class}" title="{duration}">
                    {node_name}
                </div>
            """)

        return f"""
        <div class="run-detail">
            <div class="run-header">
                <div>
                    <h2>Run #{run['id']}: {html.escape(run['workflow_name'] or 'Ad-hoc')}</h2>
                    <p style="color: var(--text-secondary);">
                        Phase: {run['phase']} |
                        Started: {run['started_at']} |
                        Completed: {run['completed_at'] or 'Running'}
                    </p>
                </div>
                <span class="status {status_class}">{run['status']}</span>
            </div>
            <h3>Node Executions</h3>
            <div class="node-graph">
                {''.join(nodes_html) if nodes_html else '<span style="color: var(--text-secondary);">No executions</span>'}
            </div>
        </div>
        """

    def generate_and_save(self, output_path: str = None, run_id: int = None, days: int = 7) -> str:
        """Generate dashboard and save to file."""
        data = self.get_dashboard_data(run_id=run_id, days=days)
        html_content = self.generate_html(data)

        if output_path is None:
            output_path = self.base_path / "conductor" / "dashboard.html"

        Path(output_path).write_text(html_content, encoding='utf-8')
        return str(output_path)


def serve_dashboard(port: int = 8765, base_path: str = None):
    """Start a local HTTP server for the dashboard."""
    generator = DashboardGenerator(base_path)
    dashboard_dir = generator.base_path / "conductor"

    class DashboardHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard_dir), **kwargs)

        def do_GET(self):
            # Regenerate dashboard on each request
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            run_id = int(params.get('run_id', [0])[0]) or None

            generator.generate_and_save(run_id=run_id)
            super().do_GET()

    print(f"Serving dashboard at http://localhost:{port}")
    print("Press Ctrl+C to stop")

    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")


def main():
    parser = argparse.ArgumentParser(description="Conductor Dashboard Generator")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--run-id", type=int, help="Focus on specific run")
    parser.add_argument("--days", type=int, default=7, help="Days of history (default: 7)")
    parser.add_argument("--serve", action="store_true", help="Start local server")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    parser.add_argument("--no-open", action="store_true", help="Don't open in browser")

    args = parser.parse_args()

    if args.serve:
        serve_dashboard(args.port)
    else:
        generator = DashboardGenerator()
        output = generator.generate_and_save(args.output, args.run_id, args.days)
        print(f"Dashboard generated: {output}")

        if not args.no_open:
            webbrowser.open(f"file://{output}")


if __name__ == "__main__":
    main()
