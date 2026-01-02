#!/usr/bin/env python
"""
Video background removal with TRUE ALPHA channel.
Uses rembg AI segmentation to create transparency mask,
preserving internal dark colors in the subject.
Outputs WebM with alpha transparency.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from PIL import Image
from rembg import remove
from tqdm import tqdm
import numpy as np

def process_video(input_path: str, output_path: str = None):
    """
    Process video: extract frames, remove background with AI, save with alpha.

    Args:
        input_path: Path to input video
        output_path: Path for output video (default: input_alpha.webm)
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_alpha.webm"
    output_path = Path(output_path)

    # Create temp directories
    temp_dir = input_path.parent / f"_temp_{input_path.stem}"
    frames_in = temp_dir / "frames_in"
    frames_out = temp_dir / "frames_out"

    frames_in.mkdir(parents=True, exist_ok=True)
    frames_out.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Extract frames
        print(f"Extracting frames from {input_path.name}...")
        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_path),
            "-qscale:v", "2",
            str(frames_in / "frame_%06d.png")
        ], check=True, capture_output=True)

        # Get frame list
        frames = sorted(frames_in.glob("*.png"))
        print(f"Found {len(frames)} frames")

        # Step 2: Process each frame with rembg - keep transparency
        print("Removing backgrounds (AI segmentation with alpha)...")
        for frame_path in tqdm(frames, desc="Processing"):
            # Load frame
            img = Image.open(frame_path)

            # Remove background - returns RGBA with transparent background
            img_nobg = remove(img)

            # Save as PNG with alpha channel preserved
            img_nobg.save(frames_out / frame_path.name, "PNG")

        # Step 3: Get original video info for reassembly
        probe = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "csv=p=0",
            str(input_path)
        ], capture_output=True, text=True, check=True)
        fps = probe.stdout.strip()

        # Step 4: Reassemble as WebM with alpha transparency
        print(f"Reassembling video at {fps} fps with alpha channel...")
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", fps,
            "-i", str(frames_out / "frame_%06d.png"),
            "-i", str(input_path),  # Get audio from original
            "-map", "0:v",
            "-map", "1:a?",  # Audio if present
            "-c:v", "libvpx-vp9",  # VP9 supports alpha
            "-pix_fmt", "yuva420p",  # YUVA = with alpha
            "-crf", "20",
            "-b:v", "0",
            "-c:a", "libopus",
            str(output_path)
        ], check=True, capture_output=True)

        print(f"Done! Output: {output_path}")
        print(f"This video has TRUE alpha transparency.")

    finally:
        # Cleanup temp files
        print("Cleaning up temp files...")
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_video_alpha.py <input_video> [output_video]")
        print("Example: python process_video_alpha.py idle.mp4 idle_alpha.webm")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    process_video(input_file, output_file)
