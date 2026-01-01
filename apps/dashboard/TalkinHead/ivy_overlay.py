"""
Ivy Overlay - TalkinHead Video Overlay System
==============================================
PyQt5 frameless transparent overlay for playing Ivy avatar videos.

Features:
- Black background removal with threshold-based alpha
- Ping-pong idle loop for seamless animation
- Phrase video playback with signal on completion
- Ctrl+click drag to reposition
- Alt+mouse wheel to resize
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
from PyQt5.QtGui import QImage, QPixmap

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
IDLE_VIDEO = os.path.join(SCRIPT_DIR, "Ivy.mp4")
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

        # Drag state
        self.drag_enabled = False
        self.drag_position = QPoint()

        # Resize state
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

        # Load idle video frames
        self.idle_frames = self.load_video_frames(IDLE_VIDEO)
        if not self.idle_frames:
            print(f"ERROR: Could not load idle video: {IDLE_VIDEO}")
            sys.exit(1)

        # Set base dimensions from first frame
        h, w = self.idle_frames[0].shape[:2]
        self.base_width = w
        self.base_height = h

        # Apply saved scale
        if 'display_scale' in config:
            self.display_scale = config['display_scale']

        # Setup window
        self._setup_window(config)

        # Key check timer (for Ctrl and Alt detection)
        self.key_timer = QTimer()
        self.key_timer.timeout.connect(self._check_modifier_keys)
        self.key_timer.start(50)  # 50ms

        # Frame update timer (30fps)
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._update_display)
        self.frame_timer.start(33)  # ~30fps

        print(f"Ivy Overlay initialized")
        print(f"  Idle frames: {len(self.idle_frames)}")
        print(f"  Base size: {self.base_width}x{self.base_height}")
        print(f"  Display scale: {self.display_scale}")
        print(f"  Ctrl+click to drag, Alt+wheel to resize")

    def load_video_frames(self, path):
        """
        Load video frames from file with black background removal.
        Creates ping-pong loop for seamless idle animation.

        Args:
            path: Path to video file

        Returns:
            List of BGRA frames with alpha channel (black keyed out)
        """
        if not os.path.exists(path):
            print(f"Video not found: {path}")
            return []

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

            # Add alpha channel with black keyed out
            frame_bgra = self.add_alpha(frame, threshold=15)
            frames.append(frame_bgra)

        cap.release()

        if not frames:
            return []

        # Create ping-pong loop (forward + reversed without duplicating endpoints)
        # Original: [0, 1, 2, 3, 4]
        # Reversed: [3, 2, 1] (exclude endpoints)
        # Result: [0, 1, 2, 3, 4, 3, 2, 1] -> loops seamlessly
        if len(frames) > 2:
            reversed_frames = frames[-2:0:-1]  # From second-to-last to second (exclusive of endpoints)
            frames = frames + reversed_frames

        print(f"Loaded {path}: {frame_count} frames -> {len(frames)} frames (ping-pong)")
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

        # Create face mask - ellipse covering face region (upper-center area)
        # This prevents accidental transparency on dark face features (eyes, mouth shadows)
        face_mask = np.zeros((h, w), dtype=np.uint8)

        # Face ellipse centered horizontally, in upper portion of frame
        # Typical Heygen avatar has face in upper 60% of frame
        center_x = w // 2
        center_y = int(h * 0.30)  # Face center roughly 30% from top
        axis_x = int(w * 0.25)    # Face width ~50% of frame width
        axis_y = int(h * 0.22)    # Face height ~44% of frame height

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

        Args:
            phrase_name: Name of phrase (without .mp4 extension) or pool folder name
        """
        # Check for phrase pool folder first
        pool_dir = os.path.join(PHRASES_DIR, phrase_name)
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

            # Update index for next time (cycle through)
            pool_indices[phrase_name] = (current_idx + 1) % len(pool_files)
            config['pool_indices'] = pool_indices
            self._save_config_dict(config)

            print(f"Pool '{phrase_name}': playing {current_idx + 1}/{len(pool_files)} - {phrase_file}")
        else:
            # Single phrase file
            phrase_path = os.path.join(PHRASES_DIR, f"{phrase_name}.mp4")

        if not os.path.exists(phrase_path):
            print(f"Phrase video not found: {phrase_path}")
            return False

        # Load phrase video frames (not ping-pong - play once)
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

        if not self.phrase_frames:
            print(f"No frames in phrase video: {phrase_path}")
            return False

        print(f"Playing phrase: {phrase_name} ({len(self.phrase_frames)} frames)")

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
        if self.is_playing_phrase:
            # Playing phrase video
            if self.phrase_frame_idx < len(self.phrase_frames):
                frame = self.phrase_frames[self.phrase_frame_idx]
                self.phrase_frame_idx += 1
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
        self._display_frame(frame)

    def _display_frame(self, frame):
        """Display a BGRA frame on the QLabel."""
        if frame is None:
            return

        h, w = frame.shape[:2]

        # Convert BGRA to RGBA for Qt
        frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGBA)

        # Create QImage
        q_img = QImage(
            frame_rgba.data,
            w, h,
            4 * w,  # bytes per line
            QImage.Format_RGBA8888
        )

        pixmap = QPixmap.fromImage(q_img)

        # Scale if display_scale != 1.0
        if self.display_scale != 1.0:
            new_w = int(w * self.display_scale)
            new_h = int(h * self.display_scale)
            pixmap = pixmap.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

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

        # Create label for displaying frames
        self.label = QLabel(self)

        # Calculate display size
        display_w = int(self.base_width * self.display_scale)
        display_h = int(self.base_height * self.display_scale)

        self.label.setFixedSize(display_w, display_h)
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

    def _check_modifier_keys(self):
        """Check for Ctrl (drag), Alt (resize), and Ctrl+Q (quit) key states."""
        ctrl_held = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        alt_held = (user32.GetAsyncKeyState(VK_MENU) & 0x8000) != 0
        q_held = (user32.GetAsyncKeyState(VK_Q) & 0x8000) != 0

        # Ctrl+Q to quit (emit signal for goodbye sequence)
        if ctrl_held and q_held:
            print("Ctrl+Q pressed - requesting quit...")
            self.quit_requested.emit()
            return

        # Track if we need interaction mode (either Ctrl for drag or Alt for resize)
        need_interaction = ctrl_held or alt_held

        if need_interaction and not self.drag_enabled:
            self.drag_enabled = True
            # Remove click-through to allow interaction
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.show()
            if ctrl_held:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.SizeAllCursor)
        elif not need_interaction and self.drag_enabled:
            self.drag_enabled = False
            # Restore click-through
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

    def mousePressEvent(self, event):
        """Handle mouse press for drag."""
        if event.button() == Qt.LeftButton and self.drag_enabled:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag."""
        if event.buttons() == Qt.LeftButton and self.drag_enabled:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if self.drag_enabled:
            self.setCursor(Qt.OpenHandCursor)
            self.save_config()

    def wheelEvent(self, event):
        """Handle mouse wheel for resize (Alt+wheel)."""
        alt_held = (user32.GetAsyncKeyState(VK_MENU) & 0x8000) != 0

        if alt_held:
            # Get scroll delta
            delta = event.angleDelta().y()

            # Adjust scale (scroll up = bigger, scroll down = smaller)
            scale_change = 0.05 if delta > 0 else -0.05
            new_scale = max(0.2, min(3.0, self.display_scale + scale_change))

            if new_scale != self.display_scale:
                self.display_scale = new_scale

                # Update window and label size
                new_w = int(self.base_width * self.display_scale)
                new_h = int(self.base_height * self.display_scale)

                self.setFixedSize(new_w, new_h)
                self.label.setFixedSize(new_w, new_h)

                self.save_config()
                print(f"Scale: {self.display_scale:.2f} ({new_w}x{new_h})")

            event.accept()
        else:
            event.ignore()

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
