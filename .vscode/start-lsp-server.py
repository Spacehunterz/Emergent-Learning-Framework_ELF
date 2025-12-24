#!/usr/bin/env python
"""
Start the Python LSP Server for Claude Code.
This script launches pylsp (Python Language Server Protocol) on a TCP socket.
Claude Code can connect to it for code intelligence.
"""

import os
import sys
import subprocess
import socket
from pathlib import Path

def find_free_port(start=2087, end=2100):
    """Find an available TCP port."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free ports available in range {start}-{end}")

def main():
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Activate venv
    venv_path = project_root / ".venv"
    if venv_path.exists():
        # Set up path to use venv
        if sys.platform == "win32":
            scripts_dir = venv_path / "Scripts"
        else:
            scripts_dir = venv_path / "bin"

        if sys.executable != str(scripts_dir / ("python.exe" if sys.platform == "win32" else "python")):
            os.environ["VIRTUAL_ENV"] = str(venv_path)
            os.environ["PATH"] = str(scripts_dir) + os.pathsep + os.environ.get("PATH", "")

    # Find a free port
    port = find_free_port()

    print(f"Starting Python LSP Server on port {port}...")
    print(f"Configuration: {project_root}/pylsp_config.py")
    print(f"Connect Claude Code to: tcp://127.0.0.1:{port}")
    print()

    # Start pylsp server
    cmd = [
        sys.executable, "-m", "pylsp",
        "--tcp",
        f"--port={port}",
        "--verbose",
    ]

    print(f"Command: {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, cwd=str(project_root))
    except KeyboardInterrupt:
        print("\nLSP Server stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
