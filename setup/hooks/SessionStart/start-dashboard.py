#!/usr/bin/env python3
"""
Session Start Hook - Start Dashboard Servers
Cross-platform (Windows, macOS, Linux), non-blocking.
"""

import subprocess
import sys
import os
import socket
from pathlib import Path

DASHBOARD_URL = "http://localhost:3001"


def is_port_in_use(port):
    """Check if a port is already in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            return result == 0
    except Exception:
        return False


def start_backend_windows(python_exe, cwd):
    """Start backend using PowerShell Start-Process."""
    ps_cmd = f'Start-Process -FilePath "{python_exe}" -ArgumentList "-m","uvicorn","main:app","--host","127.0.0.1","--port","8888" -WorkingDirectory "{cwd}" -WindowStyle Hidden'
    subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)


def start_frontend_windows(cwd):
    """Start frontend using PowerShell Start-Process."""
    ps_cmd = f'Start-Process -FilePath "bun" -ArgumentList "run","dev" -WorkingDirectory "{cwd}" -WindowStyle Hidden'
    subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)


def start_server_unix(cmd, cwd):
    """Start a detached server on Unix."""
    subprocess.Popen(f'nohup {cmd} > /dev/null 2>&1 &', cwd=cwd, shell=True, start_new_session=True)


def main():
    dashboard_dir = Path.home() / ".claude" / "emergent-learning" / "dashboard-app"
    if not dashboard_dir.exists():
        return

    results = []
    any_started = False
    python_exe = sys.executable

    # Backend
    backend_dir = dashboard_dir / "backend"
    port_8888_used = is_port_in_use(8888)
    
    if backend_dir.exists() and not port_8888_used:
        try:
            if sys.platform == 'win32':
                start_backend_windows(python_exe, str(backend_dir))
            else:
                start_server_unix(f'"{python_exe}" -m uvicorn main:app --host 127.0.0.1 --port 8888', str(backend_dir))
            results.append("Backend: starting")
            any_started = True
        except Exception as e:
            results.append(f"Backend: error ({e})")
    elif port_8888_used:
        results.append("Backend: running")
    else:
        results.append("Backend: no dir")

    # Frontend
    frontend_dir = dashboard_dir / "frontend"
    port_3001_used = is_port_in_use(3001)
    
    if frontend_dir.exists() and not port_3001_used:
        try:
            if sys.platform == 'win32':
                start_frontend_windows(str(frontend_dir))
            else:
                start_server_unix('bun run dev', str(frontend_dir))
            results.append("Frontend: starting")
            any_started = True
        except Exception as e:
            results.append(f"Frontend: error ({e})")
    elif port_3001_used:
        results.append("Frontend: running")
    else:
        results.append("Frontend: no dir")

    # Browser
    browser_msg = ""
    if any_started:
        try:
            if sys.platform == 'win32':
                os.startfile(DASHBOARD_URL)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', DASHBOARD_URL])
            else:
                subprocess.Popen(['xdg-open', DASHBOARD_URL])
            browser_msg = " | Browser"
        except:
            pass

    if results:
        print(f"\033[96m[Dashboard]\033[0m {' | '.join(results)}{browser_msg}")


if __name__ == "__main__":
    main()
