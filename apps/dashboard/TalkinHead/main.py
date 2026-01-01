#!/usr/bin/env python3
"""
TalkinHead - Ivy Overlay Entry Point

This is the main entry point for the TalkinHead animated overlay system.
It creates the overlay, sets up event watching, and manages the application lifecycle.

Usage:
    python main.py

The overlay will appear in the bottom-right corner and respond to events
written to ~/.claude/ivy_events.json by Claude Code hooks.
"""

import os
import sys
import signal
import atexit
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer, Qt

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from ivy_overlay import IvyOverlay
from event_watcher import EventWatcher


# Lockfile for single-instance enforcement
LOCKFILE = Path.home() / ".elf-talkinhead.lock"


def check_single_instance() -> bool:
    """Check if another instance is running."""
    if LOCKFILE.exists():
        try:
            pid = int(LOCKFILE.read_text().strip())
            if sys.platform == "win32":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x00100000, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    print(f"TalkinHead already running (PID {pid}). Exiting.")
                    return False
            else:
                os.kill(pid, 0)
                print(f"TalkinHead already running (PID {pid}). Exiting.")
                return False
        except (ValueError, OSError, ProcessLookupError):
            pass
    LOCKFILE.write_text(str(os.getpid()))
    return True


def cleanup_lockfile():
    """Remove lockfile on exit."""
    try:
        if LOCKFILE.exists():
            LOCKFILE.unlink()
    except Exception:
        pass


class TalkinHeadApp:
    """Main application controller for TalkinHead."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("TalkinHead")

        # Store dashboard PID for orphan detection (from PID file)
        self.dashboard_pid = self._read_dashboard_pid()
        # Fallback to parent PID if no PID file
        self.parent_pid = self.dashboard_pid or os.getppid()

        # Goodbye/self-destruct state
        self._goodbye_pending = False

        # Create components
        self.overlay = IvyOverlay()
        self.watcher = EventWatcher()

        # Connect signals
        self.watcher.event_triggered.connect(self.overlay.play_phrase)
        self.overlay.quit_requested.connect(self._quit)

        # Parent process monitor disabled - causes false positives on Windows
        # due to OpenProcess permission issues across security contexts
        self.parent_monitor = None
        # self.parent_monitor = QTimer()
        # self.parent_monitor.timeout.connect(self._check_parent)
        # self.parent_monitor.start(1000)  # Check every second

        # Setup system tray (optional)
        self.tray = self._setup_tray()

        # Setup global shortcuts
        self._setup_shortcuts()

        # Handle SIGINT/SIGTERM gracefully
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _read_dashboard_pid(self) -> int | None:
        """Read dashboard PID from file written by run-dashboard.ps1."""
        pid_file = Path.home() / ".elf-dashboard.pid"
        try:
            if pid_file.exists():
                pid = int(pid_file.read_text().strip())
                print(f"Found dashboard PID file: {pid}")
                return pid
        except (ValueError, IOError) as e:
            print(f"Could not read PID file: {e}")
        return None

    def _setup_tray(self) -> QSystemTrayIcon:
        """Setup system tray icon with menu."""
        tray = QSystemTrayIcon(self.app)

        # Try to load icon, fall back to default
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            tray.setIcon(QIcon(str(icon_path)))
        else:
            # Use a default system icon
            tray.setIcon(self.app.style().standardIcon(
                self.app.style().SP_ComputerIcon
            ))

        # Create menu
        menu = QMenu()

        # Show/Hide action
        toggle_action = QAction("Toggle Overlay", menu)
        toggle_action.triggered.connect(self._toggle_overlay)
        menu.addAction(toggle_action)

        # Test phrase action
        test_action = QAction("Test Animation", menu)
        test_action.triggered.connect(lambda: self.overlay.play_phrase("completed"))
        menu.addAction(test_action)

        menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit (Ctrl+Q)", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.setToolTip("TalkinHead - Ivy Overlay")
        tray.show()

        return tray

    def _setup_shortcuts(self):
        """Setup global keyboard shortcuts."""
        # Shortcuts handled via tray menu - use right-click on tray icon
        pass

    def _toggle_overlay(self):
        """Toggle overlay visibility."""
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show()

    def _check_parent(self):
        """Check if dashboard process is still alive."""
        # First check: PID file deleted means dashboard exited cleanly
        pid_file = Path.home() / ".elf-dashboard.pid"
        if self.dashboard_pid and not pid_file.exists():
            print("Dashboard PID file removed - dashboard exited cleanly")
            self._parent_died()
            return

        # Second check: Process still running
        try:
            if sys.platform == "win32":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                SYNCHRONIZE = 0x00100000
                handle = kernel32.OpenProcess(SYNCHRONIZE, False, self.parent_pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return  # Process exists
                else:
                    self._parent_died()
            else:
                os.kill(self.parent_pid, 0)
        except (OSError, ProcessLookupError):
            self._parent_died()

    def _parent_died(self):
        """Handle parent process death - clean exit."""
        print("Parent process died, shutting down TalkinHead...")
        self._quit()

    def _signal_handler(self, signum, frame):
        """Handle termination signals gracefully."""
        print(f"Received signal {signum}, shutting down...")
        self._quit()

    def _quit(self):
        """
        Initiate shutdown with goodbye phrase.

        If a goodbye phrase exists, plays it first then self-destructs.
        Otherwise, shuts down immediately.
        """
        # Prevent multiple quit attempts
        if self._goodbye_pending:
            return

        # Check if goodbye folder exists with videos
        goodbye_dir = Path(__file__).parent / "Phrases" / "goodbye"
        has_goodbye = (goodbye_dir.is_dir() and
                       any(goodbye_dir.glob("*.mp4")))

        if has_goodbye:
            print("Playing goodbye phrase before shutdown...")
            self._goodbye_pending = True

            # Stop accepting new events
            self.watcher.stop()
            if self.parent_monitor:
                self.parent_monitor.stop()

            # Connect phrase_finished to final quit (one-shot)
            self.overlay.phrase_finished.connect(self._final_quit)

            # Play goodbye phrase
            self.overlay.play_phrase("goodbye")
        else:
            # No goodbye phrase, quit immediately
            self._final_quit()

    def _final_quit(self):
        """Final cleanup and exit after goodbye phrase finishes."""
        print("Goodbye complete. Shutting down...")

        # Stop the watcher (if not already stopped)
        self.watcher.stop()

        # Stop parent monitor (if not already stopped)
        if self.parent_monitor:
            self.parent_monitor.stop()

        # Hide tray
        if self.tray:
            self.tray.hide()

        # Close overlay
        self.overlay.close()

        # Quit app
        self.app.quit()

    def run(self) -> int:
        """Run the application."""
        # Show overlay
        self.overlay.show()

        # Start event watcher
        self.watcher.start()

        if self.dashboard_pid:
            print(f"TalkinHead started (monitoring dashboard PID: {self.dashboard_pid})")
        else:
            print(f"TalkinHead started (monitoring parent PID: {self.parent_pid})")
        print("Press Ctrl+Q or use tray menu to quit")

        # Run event loop
        return self.app.exec_()


def main():
    """Main entry point."""
    # Ensure high DPI scaling on Windows
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Single-instance check
    if not check_single_instance():
        sys.exit(0)

    # Register cleanup on exit
    atexit.register(cleanup_lockfile)

    # Create and run app
    talkinhead = TalkinHeadApp()
    sys.exit(talkinhead.run())


if __name__ == "__main__":
    main()
