#!/usr/bin/env python3
"""
Cross-platform development task runner for Emergent Learning Framework.
Works on Windows, macOS, and Linux without requiring Make.

Usage:
    python dev.py setup     # First-time setup
    python dev.py test      # Run tests
    python dev.py test-fast # Run tests (skip slow ones)
    python dev.py lint      # Check code quality
    python dev.py clean     # Clean cache files
    python dev.py help      # Show all commands
"""

import subprocess
import sys
import os
from pathlib import Path

# Colors for terminal output (ANSI codes)
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

ROOT = Path(__file__).parent.resolve()


def run(cmd: str, cwd: Path = ROOT, check: bool = True) -> int:
    """Run a shell command."""
    print(f"{BOLD}> {cmd}{RESET}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and result.returncode != 0:
        print(f"{RED}Command failed with exit code {result.returncode}{RESET}")
    return result.returncode


def cmd_help():
    """Show available commands."""
    print(f"""
{BOLD}Emergent Learning Framework - Development Commands{RESET}

{GREEN}Setup:{RESET}
  python dev.py setup           Install all dependencies (first-time setup)

{GREEN}Testing:{RESET}
  python dev.py test            Run all tests
  python dev.py test-fast       Run tests (skip slow ones marked with @pytest.mark.slow)
  python dev.py test-cov        Run tests with coverage report

{GREEN}Code Quality:{RESET}
  python dev.py lint            Check code style (ruff)
  python dev.py format          Auto-format code (ruff format)
  python dev.py typecheck       Run type checking (mypy)

{GREEN}Cleanup:{RESET}
  python dev.py clean           Remove cache and build artifacts

{GREEN}Development:{RESET}
  python dev.py dev-backend     Start backend API server
  python dev.py dev-frontend    Start frontend dev server

{GREEN}Help:{RESET}
  python dev.py help            Show this help message
""")


def cmd_setup():
    """Install all dependencies."""
    print(f"{GREEN}Setting up Emergent Learning Framework...{RESET}\n")

    print("Step 1: Checking Python version...")
    run(f"{sys.executable} --version")

    print("\nStep 2: Installing Python dependencies...")
    run(f"{sys.executable} -m pip install --upgrade pip")
    run(f"{sys.executable} -m pip install -r requirements.txt")

    # Install dev dependencies
    print("\nStep 3: Installing dev dependencies...")
    run(f"{sys.executable} -m pip install pytest pytest-asyncio ruff mypy")

    # Install package in editable mode
    print("\nStep 4: Installing package in editable mode...")
    run(f"{sys.executable} -m pip install -e .")

    # Backend dependencies
    backend_req = ROOT / "apps" / "dashboard" / "backend" / "requirements.txt"
    if backend_req.exists():
        print("\nStep 5: Installing backend dependencies...")
        run(f"{sys.executable} -m pip install -r {backend_req}")

    # Frontend dependencies
    frontend_dir = ROOT / "apps" / "dashboard" / "frontend"
    if frontend_dir.exists() and (frontend_dir / "package.json").exists():
        print("\nStep 6: Installing frontend dependencies...")
        run("npm ci", cwd=frontend_dir, check=False)

    # Verify setup
    print("\nStep 7: Verifying setup...")
    result = run(f"{sys.executable} -m pytest tests/ --collect-only -q", check=False)

    if result == 0:
        print(f"\n{GREEN}Setup complete! Run 'python dev.py test' to verify.{RESET}")
    else:
        print(f"\n{YELLOW}Setup completed with warnings. Check output above.{RESET}")


def cmd_test():
    """Run all tests."""
    run(f"{sys.executable} -m pytest tests/ -v --tb=short")


def cmd_test_fast():
    """Run tests, skip slow ones."""
    # Note: -m filter only works if tests are marked with @pytest.mark.slow
    # Without marked tests, this runs all tests
    run(f'{sys.executable} -m pytest tests/ -v --tb=short -m "not slow"', check=False)


def cmd_test_cov():
    """Run tests with coverage."""
    run(f"{sys.executable} -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html")
    print(f"\n{GREEN}Coverage report: htmlcov/index.html{RESET}")


def cmd_lint():
    """Check code quality."""
    print("Running code linting...\n")
    run(f"{sys.executable} -m ruff check src/ tests/ --ignore E501,F401", check=False)


def cmd_format():
    """Auto-format code."""
    print("Auto-formatting code...\n")
    run(f"{sys.executable} -m ruff format src/ tests/")
    run(f"{sys.executable} -m ruff check src/ tests/ --fix --ignore E501,F401", check=False)


def cmd_typecheck():
    """Run type checking."""
    print("Running type checking...\n")
    run(f"{sys.executable} -m mypy src/ --ignore-missing-imports", check=False)


def cmd_clean():
    """Remove cache and build artifacts."""
    import shutil

    print("Cleaning up...")
    patterns = [
        "**/__pycache__",
        "**/.pytest_cache",
        "**/.mypy_cache",
        "**/.ruff_cache",
        "htmlcov",
        ".coverage",
        "*.egg-info",
    ]

    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                print(f"  Removed: {path}")
            elif path.is_file():
                path.unlink()
                print(f"  Removed: {path}")

    print(f"{GREEN}Cleanup complete!{RESET}")


def cmd_dev_backend():
    """Start backend API server."""
    backend_dir = ROOT / "apps" / "dashboard" / "backend"
    run(f"{sys.executable} -m uvicorn main:app --reload --host 0.0.0.0 --port 8888", cwd=backend_dir)


def cmd_dev_frontend():
    """Start frontend dev server."""
    frontend_dir = ROOT / "apps" / "dashboard" / "frontend"
    run("npm run dev", cwd=frontend_dir)


COMMANDS = {
    "help": cmd_help,
    "setup": cmd_setup,
    "test": cmd_test,
    "test-fast": cmd_test_fast,
    "test-cov": cmd_test_cov,
    "lint": cmd_lint,
    "format": cmd_format,
    "typecheck": cmd_typecheck,
    "clean": cmd_clean,
    "dev-backend": cmd_dev_backend,
    "dev-frontend": cmd_dev_frontend,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "-h", "--help"):
        cmd_help()
        return

    command = sys.argv[1]
    if command not in COMMANDS:
        print(f"{RED}Unknown command: {command}{RESET}")
        print(f"Run 'python dev.py help' for available commands.")
        sys.exit(1)

    COMMANDS[command]()


if __name__ == "__main__":
    main()
