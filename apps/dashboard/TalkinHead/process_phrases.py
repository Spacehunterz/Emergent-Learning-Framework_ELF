#!/usr/bin/env python
"""
Phrase Video Processor - Background Removal with True Alpha

Processes all phrase videos in the Phrases/ directory, creating PNG sequences
with true alpha transparency using rembg AI segmentation.

Usage:
    # Process all phrases
    python process_phrases.py --all

    # Process specific phrase folder
    python process_phrases.py --phrase completed

    # Process single video file
    python process_phrases.py --video "Phrases/completed/Complete.mp4"

    # Process idle video
    python process_phrases.py --idle

    # List all phrases and their status
    python process_phrases.py --status

Outputs:
    For each video.mp4, creates video_frames/ directory with PNG sequence.
    The ivy_overlay.py automatically detects and uses these PNG sequences.
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# Add rembg path for GPU support
SCRIPT_DIR = Path(__file__).parent
REMBG_ENV = SCRIPT_DIR / "rembg_env"
CUDNN_BIN = REMBG_ENV / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin"
CUBLAS_BIN = REMBG_ENV / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin"

# Set up PATH for GPU libraries
if CUDNN_BIN.exists():
    os.environ["PATH"] = f"{CUDNN_BIN};{CUBLAS_BIN};{os.environ.get('PATH', '')}"

# Import rembg after PATH setup
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print("WARNING: rembg not available. Run from rembg_env or install rembg.")

PHRASES_DIR = SCRIPT_DIR / "Phrases"


def get_frames_dir(video_path: Path) -> Path:
    """Get the frames directory path for a video file."""
    return video_path.parent / f"{video_path.stem}_frames"


def is_processed(video_path: Path) -> bool:
    """Check if a video has already been processed to PNG sequence."""
    frames_dir = get_frames_dir(video_path)
    if not frames_dir.exists():
        return False
    # Check if there are actual PNG files
    png_count = len(list(frames_dir.glob("*.png")))
    return png_count > 0


def process_video(video_path: Path, force: bool = False) -> bool:
    """
    Process a single video to PNG sequence with alpha.

    Args:
        video_path: Path to video file
        force: If True, reprocess even if already done

    Returns:
        True if successful, False otherwise
    """
    if not REMBG_AVAILABLE:
        print("ERROR: rembg not available")
        return False

    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        return False

    frames_dir = get_frames_dir(video_path)

    # Skip if already processed (unless forced)
    if is_processed(video_path) and not force:
        print(f"Already processed: {video_path.name} -> {frames_dir.name}")
        return True

    print(f"\nProcessing: {video_path}")

    # Create temp directory for frame extraction
    temp_dir = video_path.parent / f"_temp_{video_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Extract frames from video
        print("  Extracting frames...")
        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-qscale:v", "2",
            str(temp_dir / "frame_%06d.png")
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  ERROR extracting frames: {result.stderr}")
            return False

        # Get frame list
        frames = sorted(temp_dir.glob("*.png"))
        print(f"  Found {len(frames)} frames")

        if not frames:
            print("  ERROR: No frames extracted")
            return False

        # Step 2: Create output directory
        frames_dir.mkdir(parents=True, exist_ok=True)

        # Step 3: Process each frame with rembg
        print("  Removing backgrounds...")
        for i, frame_path in enumerate(tqdm(frames, desc="  Processing", leave=False)):
            # Load frame
            img = Image.open(frame_path)

            # Remove background - returns RGBA with transparent background
            img_nobg = remove(img)

            # Save as PNG with alpha
            out_path = frames_dir / f"frame_{i:06d}.png"
            img_nobg.save(out_path, "PNG")

        print(f"  Done! Created {len(frames)} PNG frames in {frames_dir.name}")
        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

    finally:
        # Cleanup temp files
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def process_phrase_folder(phrase_name: str, force: bool = False) -> dict:
    """
    Process all videos in a phrase folder.

    Args:
        phrase_name: Name of phrase folder (e.g., "completed")
        force: Reprocess even if already done

    Returns:
        Dict with success/fail counts
    """
    phrase_dir = PHRASES_DIR / phrase_name
    if not phrase_dir.exists():
        print(f"Phrase folder not found: {phrase_dir}")
        return {"success": 0, "failed": 0, "skipped": 0}

    videos = list(phrase_dir.glob("*.mp4"))
    print(f"\n=== Processing phrase: {phrase_name} ({len(videos)} videos) ===")

    results = {"success": 0, "failed": 0, "skipped": 0}

    for video in videos:
        if is_processed(video) and not force:
            results["skipped"] += 1
        elif process_video(video, force):
            results["success"] += 1
        else:
            results["failed"] += 1

    return results


def process_all_phrases(force: bool = False) -> dict:
    """Process all phrase folders."""
    if not PHRASES_DIR.exists():
        print(f"Phrases directory not found: {PHRASES_DIR}")
        return {}

    # Find all phrase folders (directories in Phrases/)
    phrase_folders = [d for d in PHRASES_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")]

    print(f"Found {len(phrase_folders)} phrase folders")

    total_results = {"success": 0, "failed": 0, "skipped": 0}

    for folder in sorted(phrase_folders):
        results = process_phrase_folder(folder.name, force)
        for key in total_results:
            total_results[key] += results.get(key, 0)

    return total_results


def process_idle(force: bool = False) -> bool:
    """Process the idle video."""
    idle_video = SCRIPT_DIR / "idle.mp4"
    if not idle_video.exists():
        # Try idle_pingpong.mp4
        idle_video = SCRIPT_DIR / "idle_pingpong.mp4"

    if not idle_video.exists():
        print("No idle video found (idle.mp4 or idle_pingpong.mp4)")
        return False

    # Output to idle_frames/
    frames_dir = SCRIPT_DIR / "idle_frames"

    if frames_dir.exists() and not force:
        png_count = len(list(frames_dir.glob("*.png")))
        if png_count > 0:
            print(f"Idle already processed: {png_count} frames in idle_frames/")
            return True

    return process_video(idle_video, force)


def show_status():
    """Show processing status of all videos."""
    print("\n=== TalkinHead Video Processing Status ===\n")

    # Idle video
    idle_frames = SCRIPT_DIR / "idle_frames"
    if idle_frames.exists():
        count = len(list(idle_frames.glob("*.png")))
        print(f"[OK] idle_frames/: {count} PNG frames")
    else:
        print("[--] idle: NOT PROCESSED")

    # Phrase folders
    if PHRASES_DIR.exists():
        for phrase_dir in sorted(PHRASES_DIR.iterdir()):
            if not phrase_dir.is_dir() or phrase_dir.name.startswith("_"):
                continue

            print(f"\n{phrase_dir.name}/:")
            videos = list(phrase_dir.glob("*.mp4"))

            for video in sorted(videos):
                frames_dir = get_frames_dir(video)
                if frames_dir.exists():
                    count = len(list(frames_dir.glob("*.png")))
                    print(f"  [OK] {video.stem}: {count} PNG frames")
                else:
                    print(f"  [--] {video.stem}: NOT PROCESSED")


def main():
    parser = argparse.ArgumentParser(
        description="Process TalkinHead videos for true alpha transparency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python process_phrases.py --all          # Process everything
    python process_phrases.py --phrase completed  # Process one folder
    python process_phrases.py --idle         # Process idle video
    python process_phrases.py --status       # Show what's processed
    python process_phrases.py --all --force  # Reprocess everything
        """
    )

    parser.add_argument("--all", action="store_true", help="Process all phrase videos")
    parser.add_argument("--phrase", type=str, help="Process specific phrase folder")
    parser.add_argument("--video", type=str, help="Process specific video file")
    parser.add_argument("--idle", action="store_true", help="Process idle video")
    parser.add_argument("--status", action="store_true", help="Show processing status")
    parser.add_argument("--force", action="store_true", help="Reprocess even if already done")

    args = parser.parse_args()

    # Default to showing status if no args
    if not any([args.all, args.phrase, args.video, args.idle, args.status]):
        parser.print_help()
        print("\n")
        show_status()
        return

    if args.status:
        show_status()
        return

    if not REMBG_AVAILABLE:
        print("ERROR: rembg not available.")
        print("Run with: ./rembg_env/Scripts/python process_phrases.py ...")
        sys.exit(1)

    # Process as requested
    if args.video:
        success = process_video(Path(args.video), args.force)
        sys.exit(0 if success else 1)

    if args.idle:
        success = process_idle(args.force)
        if not args.all:
            sys.exit(0 if success else 1)

    if args.phrase:
        results = process_phrase_folder(args.phrase, args.force)
        print(f"\nResults: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped")
        sys.exit(0 if results['failed'] == 0 else 1)

    if args.all:
        # Process idle first
        process_idle(args.force)

        # Process all phrases
        results = process_all_phrases(args.force)
        print(f"\n=== TOTAL: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped ===")
        sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == "__main__":
    main()
