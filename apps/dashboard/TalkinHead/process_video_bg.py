#!/usr/bin/env python
"""
Video background removal script using rembg.
Extracts subject with AI segmentation, preserves internal colors,
places on solid black background.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from PIL import Image
from rembg import remove
from tqdm import tqdm

def process_video(input_path: str, output_path: str = None, bg_color: tuple = (0, 0, 0)):
    """
    Process video: extract frames, remove background with AI, composite on solid color.

    Args:
        input_path: Path to input video
        output_path: Path for output video (default: input_nobg.mp4)
        bg_color: RGB tuple for background color (default: black)
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_nobg{input_path.suffix}"
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

        # Step 2: Process each frame with rembg
        print("Removing backgrounds (AI segmentation)...")
        for frame_path in tqdm(frames, desc="Processing"):
            # Load frame
            img = Image.open(frame_path)

            # Remove background (returns RGBA with transparent background)
            img_nobg = remove(img)

            # Create solid background
            bg = Image.new("RGBA", img_nobg.size, (*bg_color, 255))

            # Composite subject onto background
            result = Image.alpha_composite(bg, img_nobg)

            # Convert to RGB and save
            result = result.convert("RGB")
            result.save(frames_out / frame_path.name)

        # Step 3: Get original video info for reassembly
        probe = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "csv=p=0",
            str(input_path)
        ], capture_output=True, text=True, check=True)
        fps = probe.stdout.strip()

        # Step 4: Reassemble video
        print(f"Reassembling video at {fps} fps...")
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", fps,
            "-i", str(frames_out / "frame_%06d.png"),
            "-i", str(input_path),  # Get audio from original
            "-map", "0:v",
            "-map", "1:a?",  # Audio if present
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-c:a", "aac",
            str(output_path)
        ], check=True, capture_output=True)

        print(f"Done! Output: {output_path}")

    finally:
        # Cleanup temp files
        print("Cleaning up temp files...")
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_video_bg.py <input_video> [output_video]")
        print("Example: python process_video_bg.py idle.mp4 idle_black.mp4")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    process_video(input_file, output_file)
