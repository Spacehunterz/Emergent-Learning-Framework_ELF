"""
Data Face Overlay - Amplitude-Based Instant Lip Sync
=====================================================
Uses pre-generated mouth frames and audio amplitude to drive lip animation.

Features:
- Native resolution support (no forced downscaling)
- Alpha channel video support (.webm with transparency)
- Blends between 6 mouth positions based on audio amplitude
- ANIMATED mouth frames: video loops instead of static images (if available)
- True click-through hologram mode
- Hold Ctrl to drag/reposition
"""

import sys
import cv2
import numpy as np
import threading
import socket
import time
import os
import json
import argparse
import queue
import random
import math

from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap

# Win32 for global key state detection
import ctypes
user32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key
VK_SHIFT = 0x10  # Shift key
VK_Q = 0x51

# Audio
try:
    import sounddevice as sd
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("WARNING: sounddevice/soundfile not available")

# Config file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "overlay_config.json")
MOUTH_FRAMES_DIR = os.path.join(SCRIPT_DIR, "mouth_frames")
MOUTH_FRAMES_FEMALE_DIR = os.path.join(SCRIPT_DIR, "mouth_frames_female")
MOUTH_FRAMES_ANIMATED_DIR = os.path.join(SCRIPT_DIR, "mouth_frames_animated")
CHARACTERS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "characters")

# =============================================================================
# BLINK CONTROLLER - Natural procedural eye blinking
# =============================================================================

class BlinkController:
    """
    Natural blink timing controller.
    Produces random blinks at ~15-20 per minute with natural timing variation.
    """
    def __init__(self):
        self.next_blink_time = time.time() + random.uniform(2, 5)
        self.blink_duration = 0.15  # 150ms blink
        self.blink_start = 0
        self.is_blinking = False
        self.blink_phase = 0  # 0=open, 1=closing, 2=closed, 3=opening
        self.phase_start = 0
    
    def update(self):
        """Update blink state. Returns current eye state: 'open', 'half', 'closed'"""
        now = time.time()
        
        if self.is_blinking:
            # Calculate phase within blink
            elapsed = now - self.blink_start
            
            # Blink phases: close (0.05s) -> hold closed (0.05s) -> open (0.05s)
            if elapsed < 0.05:
                return 'half'  # Closing
            elif elapsed < 0.10:
                return 'closed'  # Held closed
            elif elapsed < 0.15:
                return 'half'  # Opening
            else:
                # Blink complete
                self.is_blinking = False
                self.next_blink_time = now + random.uniform(2, 6)  # 10-30 blinks/min
                return 'open'
        else:
            # Check if it's time to blink
            if now >= self.next_blink_time:
                self.is_blinking = True
                self.blink_start = now
                return 'half'  # Start closing
            return 'open'



def create_antialiased_alpha(bgr_image, dark_threshold=8, feather_pixels=2):
    """
    Create anti-aliased alpha channel from dark background.

    Instead of hard binary threshold (causes jagged edges), this uses:
    1. Gradient threshold for smooth transitions at edges
    2. Optional feathering via blur for softer edges

    Args:
        bgr_image: BGR or BGRA image (uses first 3 channels)
        dark_threshold: Pixels darker than this become transparent
        feather_pixels: Blur radius for edge softening (0 = no feather)

    Returns:
        Alpha channel as uint8 array (0-255)
    """
    # Convert to grayscale for brightness detection
    if len(bgr_image.shape) == 3 and bgr_image.shape[2] >= 3:
        gray = cv2.cvtColor(bgr_image[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = bgr_image

    # Create soft alpha with gradient transition instead of hard threshold
    # Pixels below dark_threshold are transparent
    # Pixels above dark_threshold+gradient_width are opaque
    # Pixels in between have smooth gradient
    gradient_width = 8  # Transition zone width in brightness values

    low = dark_threshold
    high = dark_threshold + gradient_width

    # Normalize to 0-1 range with smooth transition
    alpha_float = np.clip((gray.astype(np.float32) - low) / (high - low), 0, 1)

    # Apply slight feathering to soften edges
    if feather_pixels > 0:
        kernel_size = feather_pixels * 2 + 1
        alpha_float = cv2.GaussianBlur(alpha_float, (kernel_size, kernel_size), 0)

    # Convert to uint8
    alpha = (alpha_float * 255).astype(np.uint8)

    return alpha


def create_silhouette_alpha(bgr_image, edge_threshold=15, feather_pixels=2):
    """
    Create alpha based on simple threshold - background is pure black (0,0,0).

    Anything brighter than threshold is opaque, pure black is transparent.
    No morphological operations to avoid artifacts.

    Args:
        bgr_image: BGR or BGRA image
        edge_threshold: Brightness threshold (pixels > this are opaque)
        feather_pixels: Edge feathering for smooth outline

    Returns:
        Alpha channel as uint8 array (0-255)
    """
    if len(bgr_image.shape) == 3 and bgr_image.shape[2] >= 3:
        gray = cv2.cvtColor(bgr_image[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = bgr_image

    # Simple threshold: anything above threshold is opaque
    # Background is pure black (0), so even threshold=2 catches the figure
    alpha = (gray > edge_threshold).astype(np.uint8) * 255

    # Feather edges for smooth anti-aliasing
    if feather_pixels > 0:
        kernel_size = feather_pixels * 2 + 1
        alpha = cv2.GaussianBlur(alpha, (kernel_size, kernel_size), 0)

    return alpha


def create_fixed_silhouette_mask(bgr_image, edge_threshold=8, feather_pixels=2, shrink_percent=5):
    """
    Create a FIXED silhouette mask from a reference frame.
    Uses morphological ops to fill the interior completely.
    This mask is computed ONCE and reused for all frames.

    Args:
        bgr_image: Reference frame (usually first frame)
        edge_threshold: Brightness threshold to detect figure
        feather_pixels: Edge feathering
        shrink_percent: Shrink the mask by this percentage to avoid edge artifacts

    Returns:
        Alpha mask as uint8 array (0-255)
    """
    if len(bgr_image.shape) == 3 and bgr_image.shape[2] >= 3:
        gray = cv2.cvtColor(bgr_image[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = bgr_image

    # Detect figure pixels
    mask = (gray > edge_threshold).astype(np.uint8) * 255

    # Morphological close to fill gaps (larger kernel to fill head gap)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # Find and fill contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(gray)
    if contours:
        cv2.drawContours(filled, contours, -1, 255, -1)

    # Shrink the mask by erosion to pull edges in (avoid black artifacts)
    if shrink_percent > 0:
        h, w = filled.shape[:2]
        # Calculate erosion size based on image dimensions
        erosion_size = int(min(h, w) * shrink_percent / 100)
        erosion_size = max(3, erosion_size)  # At least 3 pixels
        erode_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erosion_size, erosion_size))
        filled = cv2.erode(filled, erode_kernel, iterations=1)

    # Cut off top with flat line at forehead level (avoids round top issues)
    h, w = filled.shape[:2]
    # Find where content actually starts (first row with significant pixels)
    row_sums = np.sum(filled > 128, axis=1)
    content_rows = np.where(row_sums > w * 0.1)[0]  # Rows with >10% content
    if len(content_rows) > 0:
        top_content = content_rows[0]
        # Cut flat a bit below the very top (forehead area)
        cut_line = top_content + int(h * 0.02)  # 2% down from content start
        filled[:cut_line, :] = 0  # Make everything above the cut transparent

    # Feather edges
    if feather_pixels > 0:
        kernel_size = feather_pixels * 2 + 1
        filled = cv2.GaussianBlur(filled, (kernel_size, kernel_size), 0)

    return filled


def resize_with_antialiasing(image, target_size, interpolation=cv2.INTER_LANCZOS4):
    """
    Resize image with proper anti-aliasing for large downscales.

    For significant downscales (>2x), applies Gaussian blur before resize
    to prevent aliasing/moire patterns.

    Args:
        image: Input image (any channel count)
        target_size: (width, height) tuple
        interpolation: cv2 interpolation method

    Returns:
        Resized image
    """
    h, w = image.shape[:2]
    target_w, target_h = target_size

    # Calculate scale factor
    scale_w = w / target_w
    scale_h = h / target_h
    scale = max(scale_w, scale_h)

    # For large downscales, apply Gaussian blur first to prevent aliasing
    if scale > 2.0:
        # Blur kernel size proportional to scale factor
        # Rule of thumb: kernel_size = scale / 2, must be odd
        kernel_size = int(scale / 2)
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel_size = max(3, min(kernel_size, 15))  # Clamp between 3 and 15

        # Apply blur to RGB channels (preserve alpha if present)
        if len(image.shape) == 3 and image.shape[2] == 4:
            # BGRA: blur RGB, keep alpha separate
            rgb = image[:, :, :3]
            alpha = image[:, :, 3]
            rgb_blurred = cv2.GaussianBlur(rgb, (kernel_size, kernel_size), 0)
            image = np.dstack([rgb_blurred, alpha])
        else:
            image = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

    # Perform the resize
    resized = cv2.resize(image, target_size, interpolation=interpolation)

    return resized


class SignalBridge(QObject):
    """Thread-safe signals"""
    update_frame = pyqtSignal(np.ndarray)
    quit_signal = pyqtSignal()


class AmplitudeOverlay(QWidget):
    def __init__(self, width=None, character=None):
        """
        Initialize the overlay.

        Args:
            width: Target width in pixels. If None, uses native video resolution.
            character: specific character ID to load (from characters/ dir)
        """
        super().__init__()

        self.signal_bridge = SignalBridge()
        self.signal_bridge.update_frame.connect(self._display_frame)
        self.signal_bridge.quit_signal.connect(self.close)

        # State
        self.running = True
        self.current_amplitude = 0.0
        self.target_amplitude = 0.0
        self.audio_playing = False
        self.idle_frame_idx = 0
        self.mouth_frame_idx = 0  # Synchronized index for animated mouth frames
        self.use_animated_mouth = False  # Will be set True if animated videos found

        # Audio queue - ensures phrases complete before next plays
        self.audio_queue = queue.Queue()
        self.queue_processor_running = True

        # Smoothing for amplitude transitions
        self.amplitude_smoothing = 0.3  # Lower = smoother

        # Procedural animation
        self.blink_controller = BlinkController()
        self.blink_frames = {}  # Will hold eyes_open, eyes_half, eyes_closed
        self.start_time = time.time()  # For breathing animation
        self.breathing_enabled = True
        self.blinking_enabled = False  # Disabled - procedural blink looks bad
        
        # Face switching (Ctrl+Alt+Shift)
        self.current_face = 'robot'  # 'robot' or 'female'
        self.mouth_frames_robot = None
        self.mouth_frames_female = None
        self.face_switch_cooldown = 0

        # Drag state
        self.drag_enabled = False
        self.drag_position = QPoint()

        # Resize state (Alt+drag)
        self.resize_enabled = False
        self.resize_start_y = 0
        self.resize_start_size = 0
        self.display_scale = 1.0  # Current display scale factor

        # Character setup
        self.character_id = character
        if self.character_id:
            self.current_face = self.character_id
            self.mouth_frames_dir = os.path.join(CHARACTERS_DIR, self.character_id, "frames")
            print(f"Loading character: {self.character_id} from {self.mouth_frames_dir}")
        else:
            self.current_face = 'robot'
            self.mouth_frames_dir = MOUTH_FRAMES_DIR

        # Load config - width=None means use native resolution
        self.target_width = width
        config = self._load_config()
        if width is None and 'width' in config:
            self.target_width = config.get('width')  # Can still be None

        # Load idle video FIRST to get target dimensions
        self.idle_frames, idle_w, idle_h = self._load_idle_video()
        self.idle_frame_idx = 0

        # Use idle video dimensions as the standard
        if idle_w and idle_h:
            self.final_width = idle_w
            self.final_height = idle_h
        else:
            self.final_width = self.target_width
            self.final_height = self.target_width  # Square fallback

        # Try to load animated mouth frames first, fall back to static
        self.mouth_frames = self._load_mouth_videos()
        if self.mouth_frames and self.use_animated_mouth:
            print("Using ANIMATED mouth frames (video loops)")
        else:
            # Fall back to static mouth frames
            self.mouth_frames = self._load_mouth_frames()
            if not self.mouth_frames:
                print("ERROR: No mouth frames found!")
                sys.exit(1)
            print("Using STATIC mouth frames")

        # Load blink frames for procedural eye animation
        self._load_blink_frames()
        
        # Store robot frames, then load female frames too
        self.mouth_frames_robot = self.mouth_frames.copy()
        self._load_female_mouth_frames()

        # Setup window
        self._setup_window(config)

        # Start UDP server for commands
        self.server_thread = threading.Thread(target=self._udp_server, daemon=True)
        self.server_thread.start()

        # Start audio queue processor thread
        self.queue_thread = threading.Thread(target=self._process_audio_queue, daemon=True)
        self.queue_thread.start()

        # Frame update timer (30 fps for smooth blending)
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._update_display)
        self.frame_timer.start(33)  # ~30fps

        # Idle animation timer
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self._idle_blink)
        self.idle_timer.start(3000)  # Blink every 3 seconds

        # Key check timer
        self.key_timer = QTimer()
        self.key_timer.timeout.connect(self._check_modifier_keys)
        self.key_timer.start(50)

    def _load_idle_video(self):
        """Load idle animation video frames - returns (frames, width, height)

        Searches for idle video in order: idle.webm, idle.mp4, data_idle_512.mp4
        Crops black borders and watermark, uses ping-pong loop.
        """
        # Search for idle video
        idle_candidates = ["idle.webm", "idle.mp4", "data_idle_512.mp4"]
        idle_video_path = None
        for candidate in idle_candidates:
            path = os.path.join(SCRIPT_DIR, candidate)
            if os.path.exists(path):
                idle_video_path = path
                break

        if not idle_video_path:
            print(f"WARNING: No idle video found. Tried: {idle_candidates}")
            return [], 0, 0

        cap = cv2.VideoCapture(idle_video_path)
        if not cap.isOpened():
            print(f"ERROR: Cannot open idle video: {idle_video_path}")
            return [], 0, 0

        # Get video dimensions
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Scan ALL frames to find maximum content extent (head moves during animation)
        print("Scanning all frames for content bounds...")
        min_top = orig_h
        max_bottom = 0
        min_left = orig_w
        max_right = 0

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            row_sums = np.sum(gray > 10, axis=1)
            col_sums = np.sum(gray > 10, axis=0)
            rows_with_content = np.where(row_sums > 50)[0]
            cols_with_content = np.where(col_sums > 50)[0]

            if len(rows_with_content) > 0 and len(cols_with_content) > 0:
                min_top = min(min_top, rows_with_content[0])
                max_bottom = max(max_bottom, rows_with_content[-1])
                min_left = min(min_left, cols_with_content[0])
                max_right = max(max_right, cols_with_content[-1])

        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to start
        print(f"Scanned {frame_count} frames")

        if min_top < orig_h and max_bottom > 0:
            # Small padding for safety, crop watermark at bottom
            crop_top = max(0, min_top - 5)
            crop_bottom = min(orig_h, max_bottom - 100)  # Extra crop for watermark
            crop_left = max(0, min_left - 5)
            crop_right = min(orig_w, max_right + 5)
        else:
            crop_top, crop_bottom, crop_left, crop_right = 0, orig_h, 0, orig_w

        crop_w = crop_right - crop_left
        crop_h = crop_bottom - crop_top
        print(f"Cropping: ({crop_left},{crop_top}) to ({crop_right},{crop_bottom}) = {crop_w}x{crop_h}")

        # Store crop bounds for mouth frames
        self.crop_bounds = (crop_top, crop_bottom, crop_left, crop_right)

        # Determine final size after crop
        if self.target_width is None:
            final_w = crop_w
            final_h = crop_h
        else:
            scale = self.target_width / crop_w
            final_w = self.target_width
            final_h = int(crop_h * scale)

        # Read all frames first
        raw_frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Crop first
            frame = frame[crop_top:crop_bottom, crop_left:crop_right]

            # Scale if needed - use anti-aliased resize for large downscales
            if self.target_width is not None:
                frame = resize_with_antialiasing(frame, (final_w, final_h))

            raw_frames.append(frame)

        cap.release()

        # Compute FIXED silhouette mask from FIRST frame only
        # This mask stays constant - head grows into it but never clips
        if raw_frames:
            self.fixed_silhouette_mask = create_fixed_silhouette_mask(raw_frames[0], edge_threshold=5, feather_pixels=2, shrink_percent=0)
            print(f"Fixed silhouette mask computed from frame 0")
        else:
            self.fixed_silhouette_mask = None

        # Apply the SAME fixed mask to ALL frames
        frames = []
        for frame in raw_frames:
            frame_bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
            if self.fixed_silhouette_mask is not None:
                frame_bgra[:, :, 3] = self.fixed_silhouette_mask
            else:
                frame_bgra[:, :, 3] = create_silhouette_alpha(frame, edge_threshold=5, feather_pixels=2)
            frames.append(frame_bgra)

        # Create ping-pong loop for smooth animation
        if len(frames) > 1:
            reversed_frames = frames[-2:0:-1]
            frames = frames + reversed_frames

        print(f"Loaded: {os.path.basename(idle_video_path)} - {len(frames)} frames @ {final_w}x{final_h} (ping-pong)")
        return frames, final_w, final_h

    def _load_mouth_videos(self):
        """Load animated mouth position videos - each mouth position is a video loop.

        Returns dict mapping position name to list of frames (same structure as idle_frames).
        All videos must have the same frame count for synchronized blending.
        """
        if not os.path.exists(MOUTH_FRAMES_ANIMATED_DIR):
            print(f"Animated mouth frames directory not found: {MOUTH_FRAMES_ANIMATED_DIR}")
            return None

        video_files = {
            'closed': 'mouth_closed.mp4',
            'slight': 'mouth_slight.mp4',
            'medium': 'mouth_medium.mp4',
            'wide': 'mouth_wide.mp4',
            'eee': 'mouth_eee.mp4',
            'ooo': 'mouth_ooo.mp4',
        }

        mouth_videos = {}
        frame_counts = []

        for name, filename in video_files.items():
            path = os.path.join(MOUTH_FRAMES_ANIMATED_DIR, filename)
            if not os.path.exists(path):
                print(f"  Missing animated mouth video: {filename}")
                continue

            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                print(f"  Cannot open: {filename}")
                continue

            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Apply same crop as idle video if bounds available
                if hasattr(self, 'crop_bounds') and self.crop_bounds:
                    crop_top, crop_bottom, crop_left, crop_right = self.crop_bounds
                    h, w = frame.shape[:2]
                    if h >= crop_bottom and w >= crop_right:
                        frame = frame[crop_top:crop_bottom, crop_left:crop_right]

                # Resize with anti-aliasing for large downscales
                frame = resize_with_antialiasing(frame, (self.final_width, self.final_height))

                # Convert to BGRA - use SAME fixed silhouette mask as idle video
                frame_bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
                if hasattr(self, 'fixed_silhouette_mask') and self.fixed_silhouette_mask is not None:
                    frame_bgra[:, :, 3] = self.fixed_silhouette_mask
                else:
                    frame_bgra[:, :, 3] = create_silhouette_alpha(frame, edge_threshold=5, feather_pixels=2)

                frames.append(frame_bgra)

            cap.release()

            if frames:
                # Create ping-pong loop like idle video
                if len(frames) > 1:
                    reversed_frames = frames[-2:0:-1]
                    frames = frames + reversed_frames

                mouth_videos[name] = frames
                frame_counts.append(len(frames))
                print(f"  Loaded animated: {name} ({len(frames)} frames)")

        # Verify all videos have same frame count
        if mouth_videos and len(set(frame_counts)) > 1:
            print(f"WARNING: Frame count mismatch: {frame_counts}")
            print("  All animated mouth videos should have same frame count!")

        # Need at least closed and one open position
        if 'closed' in mouth_videos and len(mouth_videos) >= 2:
            self.use_animated_mouth = True
            self.mouth_video_length = frame_counts[0] if frame_counts else 0
            return mouth_videos

        return None

    def _load_mouth_frames(self):
        """Load all mouth position frames - sized to match idle video.

        NOTE: Mouth frames MUST be generated from the same source/framing as idle video!
        If frames are from data_upscaled.png (2704x3612 portrait), they will look wrong.
        Regenerate from data_front_512.png (512x512) for correct alignment.
        """
        frames = {}
        frame_files = {
            'closed': 'mouth_closed.png',
            'slight': 'mouth_slight.png',
            'medium': 'mouth_medium.png',
            'wide': 'mouth_wide.png',
            'eee': 'mouth_eee.png',
            'ooo': 'mouth_ooo.png',
        }

        for name, filename in frame_files.items():
            path = os.path.join(self.mouth_frames_dir, filename)
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    src_h, src_w = img.shape[:2]

                    # Apply same crop as idle video if bounds available
                    if hasattr(self, 'crop_bounds') and self.crop_bounds:
                        crop_top, crop_bottom, crop_left, crop_right = self.crop_bounds
                        # Only crop if image is same size as original idle video
                        if src_h >= crop_bottom and src_w >= crop_right:
                            img = img[crop_top:crop_bottom, crop_left:crop_right]

                    # Resize with anti-aliasing for large downscales (4K -> display size)
                    img = resize_with_antialiasing(img, (self.final_width, self.final_height))

                    # Ensure BGRA format - use SAME fixed silhouette mask as idle video
                    if len(img.shape) == 2:
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
                    elif img.shape[2] == 3:
                        img_bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                        img = img_bgra

                    # Use existing alpha if image has transparency, otherwise generate silhouette
                    if img.shape[2] == 4 and np.any(img[:, :, 3] < 250):
                        # Image already has transparency - keep it
                        pass
                    elif hasattr(self, 'fixed_silhouette_mask') and self.fixed_silhouette_mask is not None:
                        img[:, :, 3] = self.fixed_silhouette_mask
                    else:
                        img[:, :, 3] = create_silhouette_alpha(img, edge_threshold=5, feather_pixels=2)

                    frames[name] = img
                    print(f"Loaded: {name} ({self.final_width}x{self.final_height}) [from {src_w}x{src_h}]")

        return frames

    def _load_blink_frames(self):
        """Load blink frames (eyes_open, eyes_half, eyes_closed) for procedural blinking"""
        blink_files = {
            'open': 'eyes_open.png',
            'half': 'eyes_half.png', 
            'closed': 'eyes_closed.png',
        }
        
        for state, filename in blink_files.items():
            path = os.path.join(self.mouth_frames_dir, filename)
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    src_h, src_w = img.shape[:2]
                    
                    # Apply same crop as idle video
                    if hasattr(self, 'crop_bounds') and self.crop_bounds:
                        crop_top, crop_bottom, crop_left, crop_right = self.crop_bounds
                        if src_h >= crop_bottom and src_w >= crop_right:
                            img = img[crop_top:crop_bottom, crop_left:crop_right]
                    
                    # Resize to match display
                    img = resize_with_antialiasing(img, (self.final_width, self.final_height))
                    
                    # Ensure BGRA with silhouette mask
                    if len(img.shape) == 2:
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
                    elif img.shape[2] == 3:
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                    
                    if hasattr(self, 'fixed_silhouette_mask') and self.fixed_silhouette_mask is not None:
                        img[:, :, 3] = self.fixed_silhouette_mask
                    
                    self.blink_frames[state] = img
                    print(f"Loaded blink: {state}")
        
        if self.blink_frames:
            print(f"Blink frames loaded: {list(self.blink_frames.keys())}")
        else:
            print("No blink frames found - blinking disabled")
            self.blinking_enabled = False

    def _load_female_mouth_frames(self):
        """Load female face mouth frames for face switching"""
        if not os.path.exists(MOUTH_FRAMES_FEMALE_DIR):
            print(f"Female mouth frames not found: {MOUTH_FRAMES_FEMALE_DIR}")
            return
            
        frames = {}
        frame_files = {
            'closed': 'mouth_closed.png',
            'slight': 'mouth_slight.png',
            'medium': 'mouth_medium.png',
            'wide': 'mouth_wide.png',
            'eee': 'mouth_eee.png',
            'ooo': 'mouth_ooo.png',
        }
        
        for name, filename in frame_files.items():
            path = os.path.join(MOUTH_FRAMES_FEMALE_DIR, filename)
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    src_h, src_w = img.shape[:2]
                    
                    # DON'T apply crop_bounds - female frames have different composition
                    # Just resize to match display size
                    img = resize_with_antialiasing(img, (self.final_width, self.final_height))
                    
                    if len(img.shape) == 2:
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
                    elif img.shape[2] == 3:
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                    
                    # Use existing alpha if image has transparency
                    if img.shape[2] == 4 and np.any(img[:, :, 3] < 250):
                        pass  # Keep existing alpha
                    elif hasattr(self, 'fixed_silhouette_mask') and self.fixed_silhouette_mask is not None:
                        img[:, :, 3] = self.fixed_silhouette_mask
                    
                    frames[name] = img
        
        if frames:
            self.mouth_frames_female = frames
            print(f"Female mouth frames loaded: {list(frames.keys())}")
        else:
            print("No female mouth frames found")

    def _switch_face(self):
        """Switch between robot and female face"""
        if self.current_face == 'robot' and self.mouth_frames_female:
            self.current_face = 'female'
            self.mouth_frames = self.mouth_frames_female
            print("Switched to FEMALE face")
        elif self.mouth_frames_robot:
            self.current_face = 'robot'
            self.mouth_frames = self.mouth_frames_robot
            print("Switched to ROBOT face")
        
        # Save current face to file for voice hook to read
        state_file = os.path.join(SCRIPT_DIR, "current_face.txt")
        try:
            with open(state_file, 'w') as f:
                f.write(self.current_face)
        except:
            pass

    def _setup_window(self, config):
        """Configure hologram window"""
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowTransparentForInput |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.label = QLabel(self)
        self.label.setFixedSize(self.final_width, self.final_height)
        self.setFixedSize(self.final_width, self.final_height)

        # Position - center of center screen for multi-monitor setups
        if 'x' in config and 'y' in config:
            self.move(config['x'], config['y'])
        else:
            screens = QApplication.screens()
            if len(screens) >= 3:
                # Use middle screen (index 1 for 3 screens)
                center_screen = screens[1].geometry()
            elif len(screens) == 2:
                # Use second screen
                center_screen = screens[1].geometry()
            else:
                # Single screen
                center_screen = screens[0].geometry()

            # Center on that screen
            x = center_screen.x() + (center_screen.width() - self.final_width) // 2
            y = center_screen.y() + (center_screen.height() - self.final_height) // 2
            self.move(x, y)

        # Opacity
        if 'opacity' in config:
            self.setWindowOpacity(config['opacity'])

        # Apply saved display scale
        if 'display_scale' in config:
            self.display_scale = config['display_scale']
            new_w = int(self.final_width * self.display_scale)
            new_h = int(self.final_height * self.display_scale)
            self.setFixedSize(new_w, new_h)
            self.label.setFixedSize(new_w, new_h)

        mode_str = "ANIMATED" if self.use_animated_mouth else "STATIC"
        print(f"\n=== AMPLITUDE LIP SYNC MODE ({mode_str}) ===")
        print(f"Size: {self.final_width}x{self.final_height}")
        print(f"Frames loaded: {list(self.mouth_frames.keys())}")
        if self.use_animated_mouth:
            print(f"Animation frames per position: {self.mouth_video_length}")
        print(f"Audio queue: ENABLED (phrases complete before next)")
        print(f"Ctrl+drag to move, Alt+drag to resize (up=bigger, down=smaller)")
        print(f"Ctrl+Q to quit")
        print(f"UDP port 5112: play_sync <audio>, quit")

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}

    def _save_config(self):
        try:
            config = {
                "x": self.x(),
                "y": self.y(),
                "width": self.target_width,
                "opacity": self.windowOpacity(),
                "display_scale": self.display_scale
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except:
            pass

    def _check_modifier_keys(self):
        """Check for modifier key combinations (Ctrl+Q quit, Ctrl drag, Alt resize)"""
        ctrl_held = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        alt_held = (user32.GetAsyncKeyState(VK_MENU) & 0x8000) != 0
        shift_held = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
        q_held = (user32.GetAsyncKeyState(VK_Q) & 0x8000) != 0

        # Ctrl+Alt+Shift to switch faces
        import time as time_mod
        now = time_mod.time()
        if ctrl_held and alt_held and shift_held and now > self.face_switch_cooldown:
            self._switch_face()
            self.face_switch_cooldown = now + 0.5  # 500ms cooldown

        # Ctrl+Q to quit
        if ctrl_held and q_held:
            print("Ctrl+Q - quitting overlay")
            self.running = False
            self.queue_processor_running = False
            QApplication.quit()
            return

        # Alt+drag to resize
        if alt_held and not self.resize_enabled:
            self.resize_enabled = True
            self.drag_enabled = False  # Disable drag while resizing
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.show()
            self.setCursor(Qt.SizeVerCursor)
        elif not alt_held and self.resize_enabled:
            self.resize_enabled = False
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
            self._save_config()

        # Ctrl+drag to move (only if not resizing)
        if ctrl_held and not self.drag_enabled and not self.resize_enabled:
            self.drag_enabled = True
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.show()
            self.setCursor(Qt.OpenHandCursor)
        elif not ctrl_held and self.drag_enabled:
            self.drag_enabled = False
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
            self._save_config()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.resize_enabled:
                self.resize_start_y = event.globalPos().y()
                self.resize_start_size = self.width()
                event.accept()
            elif self.drag_enabled:
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if self.resize_enabled:
                # Drag up = bigger, drag down = smaller
                delta_y = self.resize_start_y - event.globalPos().y()
                size_change = delta_y  # 1 pixel drag = 1 pixel size change
                new_width = max(200, min(1200, self.resize_start_size + size_change))

                # Calculate new height maintaining aspect ratio
                aspect = self.final_height / self.final_width
                new_height = int(new_width * aspect)

                # Resize window and label
                self.setFixedSize(new_width, new_height)
                self.label.setFixedSize(new_width, new_height)

                # Update scale for frame display
                self.display_scale = new_width / self.final_width
                event.accept()
            elif self.drag_enabled:
                self.move(event.globalPos() - self.drag_position)
                event.accept()

    def mouseReleaseEvent(self, event):
        if self.drag_enabled:
            self.setCursor(Qt.OpenHandCursor)
            self._save_config()
        elif self.resize_enabled:
            self._save_config()

    def _get_frame_for_position(self, position_name):
        """Get the current frame for a mouth position (handles both static and animated)"""
        frames_data = self.mouth_frames.get(position_name)
        if frames_data is None:
            return None

        if self.use_animated_mouth:
            # Animated: get frame at current synchronized index
            frame_list = frames_data
            if isinstance(frame_list, list) and len(frame_list) > 0:
                idx = self.mouth_frame_idx % len(frame_list)
                return frame_list[idx]
            return None
        else:
            # Static: return the single frame directly
            return frames_data

    def _get_blended_frame(self, amplitude):
        """Get mouth frame based on amplitude (0.0 to 1.0)

        MOUTH REGION COMPOSITING: Only swaps mouth area, keeps forehead static.
        Uses 'closed' as base frame, composites mouth region from target position.
        """
        # Determine target mouth position
        if amplitude < 0.08:
            position = 'closed'
        elif amplitude < 0.18:
            position = 'slight'
        elif amplitude < 0.35:
            position = 'medium'
        else:
            position = 'wide'

        # Get base (closed) and target frames
        base_frame = self._get_frame_for_position('closed')
        target_frame = self._get_frame_for_position(position)

        if base_frame is None:
            return target_frame if target_frame is not None else list(self.mouth_frames.values())[0]

        # If closed position, just return base
        if position == 'closed' or target_frame is None:
            return base_frame

        # MOUTH REGION COMPOSITING
        # Copy base, only swap mouth area from target
        result = base_frame.copy()
        h, w = result.shape[:2]

        # Mouth region bounds - FACE SPECIFIC
        if self.current_face == 'female':
            # Female android - mouth only, exclude nose
            y_start = int(h * 0.52)  # Below nose, at upper lip
            y_end = int(h * 0.62)    # Below chin
            x_start = int(w * 0.35)  # Tighter mouth width
            x_end = int(w * 0.65)    # Tighter mouth width
        else:
            # Robot - mouth is lower in frame
            y_start = int(h * 0.65)  # Upper lip area
            y_end = int(h * 0.85)    # Below chin
            x_start = int(w * 0.30)  # Left side of mouth
            x_end = int(w * 0.70)    # Right side of mouth

        # Create feathered elliptical mask for smooth blending
        mask_h = y_end - y_start
        mask_w = x_end - x_start
        mask = np.zeros((mask_h, mask_w), dtype=np.float32)

        # Ellipse centered in mask region
        center = (mask_w // 2, mask_h // 2)
        axes = (mask_w // 2 - 8, mask_h // 2 - 8)
        cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, -1)

        # Feather edges with Gaussian blur
        mask = cv2.GaussianBlur(mask, (31, 31), 0)

        # Extract mouth regions
        base_mouth = result[y_start:y_end, x_start:x_end].astype(np.float32)
        target_mouth = target_frame[y_start:y_end, x_start:x_end].astype(np.float32)

        # Blend using mask (4 channels: BGRA)
        mask_4ch = mask[:, :, np.newaxis]
        blended_mouth = base_mouth * (1 - mask_4ch) + target_mouth * mask_4ch

        # Place blended mouth back
        result[y_start:y_end, x_start:x_end] = blended_mouth.astype(np.uint8)

        return result

    def _blend_frames(self, frame1_name, frame2_name, alpha):
        """Blend between two frames - ONLY in mouth region"""
        f1 = self._get_frame_for_position(frame1_name)
        f2 = self._get_frame_for_position(frame2_name)

        if f1 is None or f2 is None:
            if f1 is not None:
                return f1
            if f2 is not None:
                return f2
            return self._get_frame_for_position('closed')

        alpha = max(0.0, min(1.0, alpha))

        # Use closed mouth as base, only blend mouth region
        base_frame = self._get_frame_for_position('closed')
        base = (base_frame if base_frame is not None else f1).copy()
        h, w = base.shape[:2]

        # Very tight - just lips only
        y_start = int(h * 0.68)  # Upper lip
        y_end = int(h * 0.78)    # Lower lip/chin
        x_start = int(w * 0.40)  # Just mouth width
        x_end = int(w * 0.60)    # Just mouth width

        # Blend only the mouth region
        mouth_region_f1 = f1[y_start:y_end, x_start:x_end]
        mouth_region_f2 = f2[y_start:y_end, x_start:x_end]
        blended_mouth = cv2.addWeighted(mouth_region_f1, 1 - alpha, mouth_region_f2, alpha, 0)

        # Create feathered mask for smooth edges
        mask = np.zeros((y_end - y_start, x_end - x_start), dtype=np.float32)
        cv2.ellipse(mask,
                    (mask.shape[1]//2, mask.shape[0]//2),
                    (mask.shape[1]//2 - 5, mask.shape[0]//2 - 5),
                    0, 0, 360, 1.0, -1)
        mask = cv2.GaussianBlur(mask, (21, 21), 0)
        mask = mask[:, :, np.newaxis]

        # Apply mask to blend smoothly
        base_mouth = base[y_start:y_end, x_start:x_end].astype(np.float32)
        blended_mouth = blended_mouth.astype(np.float32)
        result_mouth = base_mouth * (1 - mask) + blended_mouth * mask
        base[y_start:y_end, x_start:x_end] = result_mouth.astype(np.uint8)

        return base

    def _idle_blink(self):
        """Placeholder for idle animation - not used with video idle"""
        pass


    def _apply_breathing(self, frame):
        """Apply subtle breathing animation - vertical scale oscillation"""
        if not self.breathing_enabled:
            return frame
        
        elapsed = time.time() - self.start_time
        # Breathing: ~13 breaths per minute (0.22 Hz), 0.5% scale variation
        breath_scale = 1.0 + 0.005 * math.sin(2 * math.pi * elapsed * 0.22)
        
        h, w = frame.shape[:2]
        center = (w // 2, h // 2)
        
        # Create scale matrix
        M = cv2.getRotationMatrix2D(center, 0, breath_scale)
        
        # Apply transform
        result = cv2.warpAffine(frame, M, (w, h), 
                                borderMode=cv2.BORDER_REPLICATE,
                                flags=cv2.INTER_LINEAR)
        return result
    
    def _apply_blink_overlay(self, frame):
        """Blink disabled - placeholder"""
        return frame

    def _update_display(self):
        """Update display - idle video when not talking, mouth frames when talking"""
        if self.audio_playing:
            # Talking mode: use amplitude-driven mouth frames
            self.current_amplitude += (self.target_amplitude - self.current_amplitude) * self.amplitude_smoothing
            frame = self._get_blended_frame(self.current_amplitude)

            # Advance synchronized mouth frame index for animated mode
            if self.use_animated_mouth:
                self.mouth_frame_idx += 1
        else:
            # Idle mode: play video loop with procedural animation
            if self.idle_frames:
                frame = self.idle_frames[self.idle_frame_idx % len(self.idle_frames)]
                self.idle_frame_idx += 1
            else:
                # Fallback to closed mouth if no idle video
                frame = self._get_frame_for_position('closed')

            # Reset mouth frame index when not talking (sync with idle)
            if self.use_animated_mouth:
                self.mouth_frame_idx = self.idle_frame_idx
            
            # Apply procedural animations during idle
            frame = self._apply_breathing(frame)
            frame = self._apply_blink_overlay(frame)

        # Display it
        self._display_frame(frame)

    def _display_frame(self, frame):
        """Display a frame"""
        if frame is None:
            return

        h, w = frame.shape[:2]
        ch = frame.shape[2] if len(frame.shape) > 2 else 1

        if ch == 4:
            # BGRA -> RGBA
            frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGBA)
            q_img = QImage(frame_rgba.data, w, h, ch * w, QImage.Format_RGBA8888)
        else:
            # BGR -> RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            q_img = QImage(frame_rgb.data, w, h, 3 * w, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(q_img)

        # Scale pixmap if window has been resized
        if self.display_scale != 1.0:
            new_w = int(w * self.display_scale)
            new_h = int(h * self.display_scale)
            pixmap = pixmap.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.label.setPixmap(pixmap)

    def play_with_audio(self, audio_path):
        """Queue audio for playback - ensures phrases complete before next plays"""
        if not AUDIO_AVAILABLE:
            print("No audio support")
            return

        # Add to queue instead of playing immediately
        queue_size = self.audio_queue.qsize()
        self.audio_queue.put(audio_path)
        print(f"Queued audio ({queue_size + 1} in queue): {os.path.basename(audio_path)}")

    def _process_audio_queue(self):
        """Process audio queue - plays items one at a time, waiting for completion"""
        print("Audio queue processor started")

        while self.queue_processor_running:
            try:
                # Wait for next audio item (with timeout to allow checking running flag)
                try:
                    audio_path = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Play this audio and WAIT for it to complete
                self._play_audio_now(audio_path)

                # Mark task as done
                self.audio_queue.task_done()

            except Exception as e:
                print(f"Queue processor error: {e}")

        print("Audio queue processor stopped")

    def _play_audio_now(self, audio_path):
        """Play audio synchronously - blocks until audio completes"""
        try:
            print(f"Playing: {os.path.basename(audio_path)}")
            data, samplerate = sf.read(audio_path)

            # Mono conversion
            if len(data.shape) > 1:
                data = data.mean(axis=1)

            # Normalize
            max_amp = np.max(np.abs(data))
            if max_amp > 0:
                data = data / max_amp

            self.audio_playing = True

            # Calculate amplitude per frame (30fps display)
            fps = 30
            samples_per_frame = int(samplerate / fps)
            total_frames = len(data) // samples_per_frame

            # Start audio playback
            sd.play(data, samplerate)

            # Update amplitude synchronously (blocking)
            frame_idx = 0
            while frame_idx < total_frames and self.audio_playing and self.queue_processor_running:
                start = frame_idx * samples_per_frame
                end = start + samples_per_frame
                chunk = data[start:end]

                # RMS amplitude
                rms = np.sqrt(np.mean(chunk**2))
                self.target_amplitude = min(1.0, rms * 2.5)  # Amplitude boost factor

                frame_idx += 1
                time.sleep(1.0 / fps)

            # Wait for audio to actually finish
            sd.wait()

            # Fade out
            self.target_amplitude = 0.0
            self.audio_playing = False
            print(f"Completed: {os.path.basename(audio_path)}")

        except Exception as e:
            print(f"Audio error: {e}")
            self.audio_playing = False
            self.target_amplitude = 0.0

    def _udp_server(self):
        """Listen for commands"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 5112))
        print("UDP server on port 5112")

        while self.running:
            try:
                sock.settimeout(1.0)
                data, addr = sock.recvfrom(4096)
                cmd = data.decode().strip()

                if cmd == 'quit':
                    self.running = False
                    self.signal_bridge.quit_signal.emit()
                    break
                elif cmd.startswith('play_sync '):
                    audio_path = cmd[10:].strip()
                    print(f"Received play_sync: {audio_path}")
                    self.play_with_audio(audio_path)
                elif cmd == 'test':
                    # Test animation
                    print("Test animation")
                    self.target_amplitude = 0.8
                    threading.Timer(0.5, lambda: setattr(self, 'target_amplitude', 0.0)).start()

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"UDP error: {e}")

    def closeEvent(self, event):
        self.running = False
        self.queue_processor_running = False
        self.audio_playing = False  # Stop any playing audio
        sd.stop()  # Stop sounddevice
        self._save_config()
        print("Overlay closed")
        event.accept()


def main():
    print("Data Overlay - Amplitude Lip Sync")
    print("=" * 40)

    parser = argparse.ArgumentParser()
    parser.add_argument('--width', type=int, default=None,
                        help='Target width in pixels. Omit for native resolution.')
    parser.add_argument('--character', type=str, default=None,
                        help='Specific character to load (folder name in characters/)')
    args = parser.parse_args()

    print(f"Audio available: {AUDIO_AVAILABLE}")
    print(f"Mouth frames dir: {MOUTH_FRAMES_DIR}")
    if args.width:
        print(f"Target width: {args.width}px")
    else:
        print("Resolution: NATIVE (no scaling)")

    app = QApplication(sys.argv)
    overlay = AmplitudeOverlay(width=args.width, character=args.character)
    overlay.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
