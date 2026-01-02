#!/usr/bin/env python
"""
Video background removal with TRUE ALPHA channel.
Outputs PNG sequence with transparency for reliable alpha support.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from PIL import Image
from rembg import remove
from tqdm import tqdm

def process_video(input_path: str, output_dir: str = None):
    """
    Process video: extract frames, remove background with AI, save as PNG sequence.

    Args:
        input_path: Path to input video
        output_dir: Directory for output PNGs (default: input_frames/)
    """
    input_path = Path(input_path)
    if output_dir is None:
        output_dir = input_path.parent / f"{input_path.stem}_frames"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Temp dir for extraction
    temp_dir = input_path.parent / f"_temp_{input_path.stem}"
    frames_in = temp_dir / "frames_in"
    frames_in.mkdir(parents=True, exist_ok=True)

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
        print("Removing backgrounds (AI segmentation with alpha)...")
        for i, frame_path in enumerate(tqdm(frames, desc="Processing")):
            # Load frame
            img = Image.open(frame_path)

            # Remove background - returns RGBA with transparent background
            img_nobg = remove(img)

            # Save as PNG with alpha
            out_path = output_dir / f"frame_{i:06d}.png"
            img_nobg.save(out_path, "PNG")

        print(f"Done! Output: {output_dir}")
        print(f"{len(frames)} PNG frames with TRUE alpha transparency.")

    finally:
        # Cleanup temp files
        print("Cleaning up temp files...")
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_video_png.py <input_video> [output_dir]")
        print("Example: python process_video_png.py idle.mp4 idle_frames")
        sys.exit(1)

    input_file = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None

    process_video(input_file, output)
