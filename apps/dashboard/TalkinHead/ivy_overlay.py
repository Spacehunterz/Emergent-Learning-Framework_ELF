"""
Ivy Overlay - TalkinHead Video Overlay System
==============================================
PyQt5 frameless transparent overlay for playing Ivy avatar videos.

Features:
- True alpha transparency via PNG sequences (rembg processed)
- Ping-pong idle loop for seamless animation
- Phrase video playback with signal on completion
- Ctrl+drag to reposition
- Alt+mouse up/down to resize
- Position/size persistence to config.json
- 30fps display timer
"""

import sys
import os
import json
import cv2
import numpy as np

from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QCursor, QFont

# Pygame for reliable audio playback
import pygame
pygame.mixer.init()

# Win32 for global key state detection (Windows)
import ctypes
user32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key
VK_Q = 0x51  # Q key

# Script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
IDLE_FRAMES_DIR = os.path.join(SCRIPT_DIR, "idle_frames")
PHRASES_DIR = os.path.join(SCRIPT_DIR, "Phrases")


class IvyOverlay(QWidget):
    """
    Transparent overlay window for Ivy avatar video playback.

    Signals:
        phrase_finished: Emitted when a phrase video completes playback
        quit_requested: Emitted when user presses Ctrl+Q (for goodbye sequence)
    """

    phrase_finished = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # State tracking
        self.running = True
        self.idle_frame_idx = 0
        self.phrase_frame_idx = 0
        self.is_playing_phrase = False

        # Interaction states
        self.drag_enabled = False  # Ctrl held - drag mode
        self.resize_enabled = False  # Alt held - resize mode
        self.drag_position = QPoint()
        self.mouse_hovering = False  # Mouse over overlay

        # Resize state (Alt + mouse up/down)
        self.resize_start_y = 0  # Mouse Y when resize started
        self.resize_start_scale = 0.3  # Scale when resize started
        self.display_scale = 0.3  # Default to 30% size
        self.base_width = 0
        self.base_height = 0

        # Frame storage
        self.idle_frames = []
        self.phrase_frames = []
        self.current_phrase_name = ""
        self.current_phrase_path = ""

        # Audio channel for phrase playback
        self.audio_channel = None

        # Load config first
        config = self.load_config()

        # Load idle frames (PNG sequence with blinks embedded)
        idle_frames_raw = []
        if os.path.isdir(IDLE_FRAMES_DIR):
            idle_frames_raw = self.load_png_sequence(IDLE_FRAMES_DIR)
        else:
            # Fallback to video file
            idle_video = os.path.join(SCRIPT_DIR, "idle_pingpong.mp4")
            idle_frames_raw = self.load_video_frames(idle_video)
        if not idle_frames_raw:
            print(f"ERROR: Could not load idle frames from: {IDLE_FRAMES_DIR}")
            sys.exit(1)

        # Build ping-pong loop: forward → reverse (skip endpoints to avoid stutter)
        idle_reversed = list(reversed(idle_frames_raw[1:-1]))
        self.idle_frames = idle_frames_raw + idle_reversed
        print(f"Idle loop: {len(idle_frames_raw)} forward + {len(idle_reversed)} reverse = {len(self.idle_frames)} total")

        # Set base dimensions from first frame
        h, w = self.idle_frames[0].shape[:2]
        self.base_width = w
        self.base_height = h

        # Apply saved scale
        if 'display_scale' in config:
            self.display_scale = config['display_scale']

        # Setup window
        self._setup_window(config)
        # Render first frame immediately (before timers/event loop)
        # This ensures the window is visible when show() is called
        if self.idle_frames:
            self._display_frame(self.idle_frames[0])

        # Create hover tooltip (separate window)
        self._setup_tooltip()


        # Key check timer (for Ctrl and Alt detection) - 16ms for responsiveness
        self.key_timer = QTimer()
        self.key_timer.timeout.connect(self._check_modifier_keys)
        self.key_timer.start(16)  # 16ms (~60fps) for responsive mode switching

        # Frame update timer (30fps)
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._update_display)
        self.frame_timer.start(33)  # ~30fps

        print(f"Ivy Overlay initialized")
        print(f"  Idle frames: {len(self.idle_frames)}")
        print(f"  Base size: {self.base_width}x{self.base_height}")
        print(f"  Display scale: {self.display_scale}")
        print(f"  Ctrl+drag to move, Alt+mouse up/down to resize")

    def load_png_sequence(self, directory):
        """
        Load PNG sequence with true alpha transparency.

        Args:
            directory: Path to directory containing PNG frames

        Returns:
            List of BGRA frames with alpha channel
        """
        if not os.path.isdir(directory):
            print(f"PNG directory not found: {directory}")
            return []

        # Get all PNG files sorted
        png_files = sorted([f for f in os.listdir(directory) if f.endswith('.png')])
        if not png_files:
            print(f"No PNG files in: {directory}")
            return []

        frames = []
        for png_file in png_files:
            path = os.path.join(directory, png_file)
            # Load with alpha channel (cv2.IMREAD_UNCHANGED preserves alpha)
            frame = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if frame is None:
                continue

            # Ensure BGRA format
            if frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
            elif frame.shape[2] == 4:
                # PNG is RGBA, OpenCV loads as BGRA - already correct
                pass

            frames.append(frame)

        print(f"Loaded {directory}: {len(frames)} PNG frames (true-alpha)")
        return frames

    def load_video_frames(self, path, use_alpha_keying=None):
        """
        Load video frames from file.
        For videos with true alpha (WebM), preserves the alpha channel.
        For regular videos (MP4), applies black background removal.

        Args:
            path: Path to video file
            use_alpha_keying: Force alpha keying on/off. None = auto-detect.

        Returns:
            List of BGRA frames with alpha channel
        """
        if not os.path.exists(path):
            print(f"Video not found: {path}")
            return []

        # Auto-detect: WebM files have true alpha, skip keying
        if use_alpha_keying is None:
            use_alpha_keying = not path.lower().endswith('.webm')

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"Cannot open video: {path}")
            return []

        frames = []
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if use_alpha_keying:
                # Add alpha channel with black keyed out (for MP4)
                frame_bgra = self.add_alpha(frame, threshold=15)
            else:
                # Video has true alpha - convert to BGRA preserving alpha
                if frame.shape[2] == 4:
                    frame_bgra = frame  # Already BGRA
                else:
                    frame_bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
                    frame_bgra[:, :, 3] = 255  # Full opacity if no alpha

            frames.append(frame_bgra)

        cap.release()

        if not frames:
            return []

        mode = "alpha-keying" if use_alpha_keying else "true-alpha"
        print(f"Loaded {path}: {frame_count} frames ({mode})")
        return frames

    def add_alpha(self, frame, threshold=15):
        """
        Convert BGR frame to BGRA with black background keyed out.
        Includes face mask to prevent see-through on face area.

        Args:
            frame: BGR image (numpy array)
            threshold: Brightness threshold below which pixels become transparent

        Returns:
            BGRA image with alpha channel
        """
        # Convert to BGRA
        if len(frame.shape) == 2:
            # Grayscale
            frame_bgra = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGRA)
        elif frame.shape[2] == 3:
            # BGR
            frame_bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        elif frame.shape[2] == 4:
            # Already BGRA
            frame_bgra = frame.copy()
        else:
            frame_bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

        h, w = frame_bgra.shape[:2]

        # Create alpha mask based on brightness
        # Convert BGR channels to grayscale for brightness detection
        gray = cv2.cvtColor(frame_bgra[:, :, :3], cv2.COLOR_BGR2GRAY)

        # Pixels below threshold are transparent, above are opaque
        # Use gradient transition for anti-aliasing
        gradient_width = 10
        low = threshold
        high = threshold + gradient_width

        # Smooth transition from 0 to 255
        alpha_float = np.clip((gray.astype(np.float32) - low) / (high - low), 0, 1)
        alpha = (alpha_float * 255).astype(np.uint8)

        # Apply slight feathering for smoother edges
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

        # Create face mask - ellipse covering head area
        # This prevents accidental transparency on face features
        face_mask = np.zeros((h, w), dtype=np.uint8)

        # Head ellipse centered horizontally, positioned for robot head
        center_x = w // 2
        center_y = int(h * 0.38)  # Head center at 38% from top
        axis_x = int(w * 0.22)    # Head width reduced 20%
        axis_y = int(h * 0.26)    # Head height reduced 20%

        cv2.ellipse(face_mask, (center_x, center_y), (axis_x, axis_y),
                    0, 0, 360, 255, -1)

        # Feather the face mask edges for smooth blending
        face_mask = cv2.GaussianBlur(face_mask, (31, 31), 0)

        # In face region, set minimum alpha to prevent see-through
        # Where face_mask is high, ensure alpha is at least 180
        face_mask_float = face_mask.astype(np.float32) / 255.0
        min_alpha = 180

        # Blend: where face_mask is 1, use max(alpha, min_alpha)
        # where face_mask is 0, use original alpha
        alpha_boosted = np.maximum(alpha, (face_mask_float * min_alpha).astype(np.uint8))

        # Final alpha is blend between original and boosted based on face mask
        alpha = (alpha.astype(np.float32) * (1 - face_mask_float) +
                 alpha_boosted.astype(np.float32) * face_mask_float).astype(np.uint8)

        frame_bgra[:, :, 3] = alpha
        return frame_bgra

    def play_phrase(self, phrase_name):
        """
        Play a phrase video once, then return to idle loop.
        Supports phrase pools: if Phrases/{phrase_name}/ folder exists,
        cycles through videos in that folder sequentially.
        Prefers PNG sequences (true alpha) over video files.

        Args:
            phrase_name: Name of phrase (without .mp4 extension) or pool folder name
        """
        # Check for phrase pool folder first
        pool_dir = os.path.join(PHRASES_DIR, phrase_name)
        phrase_path = None
        frames_dir = None

        if os.path.isdir(pool_dir):
            # Get all mp4 files in pool, sorted for consistent order
            pool_files = sorted([f for f in os.listdir(pool_dir) if f.endswith('.mp4')])
            if not pool_files:
                print(f"Empty phrase pool: {pool_dir}")
                return False

            # Get current pool index from config
            config = self.load_config()
            pool_indices = config.get('pool_indices', {})
            current_idx = pool_indices.get(phrase_name, 0)

            # Get next video in cycle
            phrase_file = pool_files[current_idx % len(pool_files)]
            phrase_path = os.path.join(pool_dir, phrase_file)

            # Check for PNG sequence folder
            frames_dir = os.path.join(pool_dir, f"{os.path.splitext(phrase_file)[0]}_frames")

            # Update index for next time (cycle through)
            pool_indices[phrase_name] = (current_idx + 1) % len(pool_files)
            config['pool_indices'] = pool_indices
            self._save_config_dict(config)

            print(f"Pool '{phrase_name}': playing {current_idx + 1}/{len(pool_files)} - {phrase_file}")
        else:
            # Single phrase file
            phrase_path = os.path.join(PHRASES_DIR, f"{phrase_name}.mp4")
            frames_dir = os.path.join(PHRASES_DIR, f"{phrase_name}_frames")

        # Try PNG sequence first (true alpha), fall back to video
        if frames_dir and os.path.isdir(frames_dir):
            self.phrase_frames = self.load_png_sequence(frames_dir)
            if self.phrase_frames:
                print(f"  Using PNG sequence: {frames_dir}")
        else:
            # Fall back to video file
            if not os.path.exists(phrase_path):
                print(f"Phrase not found: {phrase_path}")
                return False

            # Load phrase video frames
            cap = cv2.VideoCapture(phrase_path)
            if not cap.isOpened():
                print(f"Cannot open phrase video: {phrase_path}")
                return False

            self.phrase_frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_bgra = self.add_alpha(frame, threshold=15)
                self.phrase_frames.append(frame_bgra)

            cap.release()
            print(f"  Using video with alpha-keying: {phrase_path}")

        if not self.phrase_frames:
            print(f"No frames loaded for phrase: {phrase_name}")
            return False

        # Debug: check phrase dimensions vs base dimensions
        ph, pw = self.phrase_frames[0].shape[:2]
        print(f"Playing phrase: {phrase_name} ({len(self.phrase_frames)} frames)")
        print(f"  Phrase dims: {pw}x{ph}, Base dims: {self.base_width}x{self.base_height}")
        if pw != self.base_width or ph != self.base_height:
            print(f"  WARNING: Dimension mismatch!")

        # Preload audio FIRST (before starting video)
        audio_path = phrase_path.replace('.mp4', '.mp3')
        audio_ready = False
        if os.path.exists(audio_path):
            try:
                pygame.mixer.music.load(audio_path)
                audio_ready = True
                print(f"Audio loaded: {audio_path}")
            except Exception as e:
                print(f"Audio error: {e}")
        else:
            print(f"No audio file: {audio_path}")

        # Start audio FIRST, then video
        if audio_ready:
            pygame.mixer.music.play()

        # 45ms delay to sync audio with video
        import time
        time.sleep(0.045)

        # Start from frame 0 (no skip needed with time delay)
        self.phrase_frame_idx = 0

        # Switch to phrase mode
        self.current_phrase_name = phrase_name
        self.current_phrase_path = phrase_path
        self.is_playing_phrase = True

        return True

    def _on_phrase_complete(self):
        """Called when phrase video finishes playing."""
        print(f"Phrase complete: {self.current_phrase_name}")

        # Stop audio
        pygame.mixer.music.stop()

        # Return to idle mode
        self.is_playing_phrase = False
        self.phrase_frames = []
        self.current_phrase_name = ""
        self.current_phrase_path = ""

        # Emit signal
        self.phrase_finished.emit()

    def _update_display(self):
        """30fps timer callback - advance frame and update display."""
        is_phrase = False
        if self.is_playing_phrase:
            # Playing phrase video
            if self.phrase_frame_idx < len(self.phrase_frames):
                frame = self.phrase_frames[self.phrase_frame_idx]
                self.phrase_frame_idx += 1
                is_phrase = True
            else:
                # Phrase finished
                self._on_phrase_complete()
                # Show idle frame
                if self.idle_frames:
                    frame = self.idle_frames[self.idle_frame_idx % len(self.idle_frames)]
                else:
                    return
        else:
            # Idle loop
            if self.idle_frames:
                frame = self.idle_frames[self.idle_frame_idx % len(self.idle_frames)]
                self.idle_frame_idx += 1
            else:
                return

        # Display the frame
        self._display_frame(frame, is_phrase=is_phrase)

    def _display_frame(self, frame, is_phrase=False):
        """Display a BGRA frame on the QLabel."""
        if frame is None:
            return

        h, w = frame.shape[:2]

        # Convert BGRA to RGBA for Qt
        frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGBA)

        # Create QImage - need to copy data to avoid memory issues
        q_img = QImage(
            frame_rgba.tobytes(),
            w, h,
            4 * w,
            QImage.Format_RGBA8888
        )

        pixmap = QPixmap.fromImage(q_img)
        self.label.setPixmap(pixmap)

    def _setup_window(self, config):
        """Configure frameless transparent always-on-top window."""
        # Window flags for transparent click-through overlay
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowTransparentForInput |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Calculate display size
        display_w = int(self.base_width * self.display_scale)
        display_h = int(self.base_height * self.display_scale)

        # Create label filling window
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, display_w, display_h)
        self.label.setScaledContents(True)

        # Set window size
        self.setFixedSize(display_w, display_h)

        # Position - use saved or default to lower-right corner
        if 'x' in config and 'y' in config:
            self.move(config['x'], config['y'])
        else:
            # Lower-right corner with small margin
            screen = QApplication.primaryScreen().geometry()
            margin = 20
            x = screen.width() - display_w - margin
            y = screen.height() - display_h - margin - 40  # Extra for taskbar
            self.move(x, y)

    def _setup_tooltip(self):
        """Create hover tooltip as separate window."""
        self.tooltip = QLabel()
        self.tooltip.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.tooltip.setAttribute(Qt.WA_TranslucentBackground)
        self.tooltip.setAttribute(Qt.WA_ShowWithoutActivating)

        # Tooltip content
        self.tooltip.setText("Ctrl+Q  Close\nCtrl+Click  Move\nAlt+Click  Resize")

        # Style: semi-transparent dark background, white text
        self.tooltip.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 200);
                color: rgba(255, 255, 255, 220);
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 13px;
                font-family: Consolas, monospace;
            }
        """)
        self.tooltip.adjustSize()

    def _update_tooltip_position(self):
        """Position tooltip above the overlay."""
        if not self.tooltip.isVisible():
            return
        # Position above overlay, centered
        overlay_geo = self.geometry()
        tooltip_w = self.tooltip.width()
        tooltip_h = self.tooltip.height()
        x = overlay_geo.x() + (overlay_geo.width() - tooltip_w) // 2
        y = overlay_geo.y() - tooltip_h - 8  # 8px gap above
        self.tooltip.move(x, y)

    def _check_modifier_keys(self):
        """Check for Ctrl (drag), Alt (resize), Ctrl+Q (quit), and mouse hover."""
        ctrl_held = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        alt_held = (user32.GetAsyncKeyState(VK_MENU) & 0x8000) != 0
        q_held = (user32.GetAsyncKeyState(VK_Q) & 0x8000) != 0

        # Check mouse hover for tooltip
        mouse_pos = QCursor.pos()
        overlay_geo = self.geometry()
        is_hovering = overlay_geo.contains(mouse_pos)

        if is_hovering and not self.mouse_hovering:
            # Mouse entered - show tooltip
            self.mouse_hovering = True
            self._update_tooltip_position()
            self.tooltip.show()
        elif not is_hovering and self.mouse_hovering:
            # Mouse left - hide tooltip
            self.mouse_hovering = False
            self.tooltip.hide()
        elif is_hovering and self.mouse_hovering:
            # Still hovering - update position (in case overlay moved)
            self._update_tooltip_position()

        # Ctrl+Q to quit (only when hovering over overlay)
        if ctrl_held and q_held and is_hovering:
            print("Ctrl+Q pressed - requesting quit...")
            self.quit_requested.emit()
            return

        # Track current interaction states
        was_interactive = self.drag_enabled or self.resize_enabled
        need_interaction = (ctrl_held or alt_held) and is_hovering

        # Update mode states
        self.drag_enabled = ctrl_held and not alt_held  # Ctrl only = drag
        self.resize_enabled = alt_held and not ctrl_held  # Alt only = resize

        if need_interaction and not was_interactive:
            # Entering interaction mode - hide tooltip
            self.tooltip.hide()
            self.mouse_hovering = False

            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.show()
            self.raise_()
            self.activateWindow()
            self.setFocus()
            self.grabMouse()  # Always grab mouse in interaction mode

            # Capture starting position for resize mode
            if self.resize_enabled:
                self.resize_start_y = QCursor.pos().y()
                self.resize_start_scale = self.display_scale
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.OpenHandCursor)
        elif not need_interaction and was_interactive:
            # Exiting interaction mode - always release mouse
            self.releaseMouse()
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.WindowTransparentForInput |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self.show()
            self.setCursor(Qt.ArrowCursor)
            self.save_config()
        elif need_interaction:
            # Update cursor based on current mode
            if self.resize_enabled:
                self.setCursor(Qt.SizeVerCursor)
            elif self.drag_enabled:
                self.setCursor(Qt.OpenHandCursor)

    def mousePressEvent(self, event):
        """Handle mouse press for drag."""
        if event.button() == Qt.LeftButton and self.drag_enabled:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag and resize."""
        if self.resize_enabled:
            # Alt + mouse up/down = resize
            # Moving up = bigger, moving down = smaller
            current_y = QCursor.pos().y()
            delta_y = self.resize_start_y - current_y  # Invert: up is positive

            # Scale factor: 200 pixels of movement = 1.0 scale change
            scale_change = delta_y / 200.0
            new_scale = max(0.1, min(2.0, self.resize_start_scale + scale_change))

            if abs(new_scale - self.display_scale) > 0.01:  # Only update if changed
                self.display_scale = new_scale

                # Update window and label size
                new_w = int(self.base_width * self.display_scale)
                new_h = int(self.base_height * self.display_scale)

                self.setFixedSize(new_w, new_h)
                self.label.setGeometry(0, 0, new_w, new_h)

            event.accept()
        elif event.buttons() == Qt.LeftButton and self.drag_enabled:
            # Ctrl + drag = move
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if self.drag_enabled:
            self.setCursor(Qt.OpenHandCursor)
            self.save_config()

    def save_config(self):
        """Save position and size to config.json."""
        try:
            config = {
                "x": self.x(),
                "y": self.y(),
                "display_scale": self.display_scale
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _save_config_dict(self, config):
        """Save full config dict to config.json, preserving window position/scale."""
        try:
            # Preserve current position/scale
            config['x'] = self.x()
            config['y'] = self.y()
            config['display_scale'] = self.display_scale
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_config(self):
        """Load position and size from config.json."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
        return {}

    def closeEvent(self, event):
        """Handle window close."""
        self.running = False
        self.tooltip.hide()
        self.tooltip.close()
        self.save_config()
        print("Ivy Overlay closed")
        event.accept()


def main():
    """Main entry point."""
    print("=" * 50)
    print("Ivy Overlay - TalkinHead System")
    print("=" * 50)

    app = QApplication(sys.argv)

    overlay = IvyOverlay()
    overlay.show()

    # Connect phrase_finished signal for demonstration
    overlay.phrase_finished.connect(lambda: print("Signal: phrase_finished emitted"))

    # Test phrase playback after 2 seconds (optional demo)
    # QTimer.singleShot(2000, lambda: overlay.play_phrase("complete"))

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
