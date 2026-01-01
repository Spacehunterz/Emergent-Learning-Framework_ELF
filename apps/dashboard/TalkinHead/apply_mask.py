#!/usr/bin/env python3
"""
Apply alpha mask to phrase frames.

Usage:
    python apply_mask.py <phrase_name>     # Apply to Phrases/<phrase_name>/*_frames/
    python apply_mask.py --all             # Apply to ALL phrase frame directories
    python apply_mask.py --path <dir>      # Apply to specific directory

Examples:
    python apply_mask.py completed         # Mask all completed phrase frames
    python apply_mask.py goodbye           # Mask all goodbye phrase frames
    python apply_mask.py --all             # Mask everything in Phrases/
    python apply_mask.py --path idle_frames  # Mask idle frames directly
"""

import cv2
import shutil
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MASK_FILE = SCRIPT_DIR / "frame_000000fixedmask.png"
PHRASES_DIR = SCRIPT_DIR / "Phrases"


def load_mask():
    """Load the mask and return its alpha channel."""
    if not MASK_FILE.exists():
        print(f"ERROR: Mask file not found: {MASK_FILE}")
        return None

    mask = cv2.imread(str(MASK_FILE), cv2.IMREAD_UNCHANGED)
    if mask is None or mask.shape[2] != 4:
        print(f"ERROR: Invalid mask file (needs RGBA)")
        return None

    print(f"Mask loaded: {mask.shape[1]}x{mask.shape[0]}")
    return mask[:, :, 3]


def apply_mask_to_directory(frame_dir: Path, mask_alpha, backup=True):
    """Apply mask alpha to all PNG frames in a directory."""
    if not frame_dir.is_dir():
        print(f"  SKIP: Not a directory: {frame_dir}")
        return 0

    frames = sorted(frame_dir.glob("*.png"))
    if not frames:
        print(f"  SKIP: No PNG files in {frame_dir.name}")
        return 0

    # Create backup if requested and doesn't exist
    if backup:
        backup_dir = frame_dir.parent / f"{frame_dir.name}_backup"
        if not backup_dir.exists():
            shutil.copytree(frame_dir, backup_dir)
            print(f"  Backed up: {frame_dir.name}")

    processed = 0
    errors = 0

    for frame_path in frames:
        if frame_path.suffix == '.bak':
            continue
        try:
            frame = cv2.imread(str(frame_path), cv2.IMREAD_UNCHANGED)
            if frame is None:
                errors += 1
                continue

            # Ensure RGBA
            if frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

            # Check dimensions
            if frame.shape[:2] != mask_alpha.shape:
                print(f"    SKIP: {frame_path.name} size mismatch")
                errors += 1
                continue

            # Apply mask
            frame[:, :, 3] = mask_alpha
            cv2.imwrite(str(frame_path), frame)
            processed += 1

        except Exception as e:
            print(f"    ERROR: {frame_path.name}: {e}")
            errors += 1

    print(f"  {frame_dir.name}: {processed} frames" + (f" ({errors} errors)" if errors else ""))
    return processed


def apply_to_phrase(phrase_name: str, mask_alpha):
    """Apply mask to all _frames directories in a phrase folder."""
    phrase_dir = PHRASES_DIR / phrase_name

    if not phrase_dir.is_dir():
        print(f"ERROR: Phrase directory not found: {phrase_dir}")
        return 0

    frame_dirs = [d for d in phrase_dir.iterdir() if d.is_dir() and d.name.endswith('_frames')]

    if not frame_dirs:
        print(f"ERROR: No _frames directories in {phrase_name}")
        return 0

    print(f"\nProcessing phrase: {phrase_name} ({len(frame_dirs)} frame directories)")

    total = 0
    for frame_dir in sorted(frame_dirs):
        total += apply_mask_to_directory(frame_dir, mask_alpha)

    return total


def apply_to_all(mask_alpha):
    """Apply mask to all phrase frame directories."""
    if not PHRASES_DIR.is_dir():
        print(f"ERROR: Phrases directory not found: {PHRASES_DIR}")
        return 0

    phrase_dirs = [d for d in PHRASES_DIR.iterdir() if d.is_dir()]

    print(f"\nProcessing ALL phrases ({len(phrase_dirs)} phrase directories)")

    total = 0
    for phrase_dir in sorted(phrase_dirs):
        frame_dirs = [d for d in phrase_dir.iterdir() if d.is_dir() and d.name.endswith('_frames')]
        if frame_dirs:
            print(f"\n{phrase_dir.name}:")
            for frame_dir in sorted(frame_dirs):
                total += apply_mask_to_directory(frame_dir, mask_alpha)

    return total


def main():
    parser = argparse.ArgumentParser(description="Apply alpha mask to phrase frames")
    parser.add_argument("phrase", nargs="?", help="Phrase name (e.g., 'completed', 'goodbye')")
    parser.add_argument("--all", action="store_true", help="Apply to all phrases")
    parser.add_argument("--path", type=str, help="Direct path to frames directory")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backups")

    args = parser.parse_args()

    # Load mask
    mask_alpha = load_mask()
    if mask_alpha is None:
        return 1

    total = 0

    if args.all:
        total = apply_to_all(mask_alpha)
    elif args.path:
        path = Path(args.path)
        if not path.is_absolute():
            path = SCRIPT_DIR / path
        total = apply_mask_to_directory(path, mask_alpha, backup=not args.no_backup)
    elif args.phrase:
        total = apply_to_phrase(args.phrase, mask_alpha)
    else:
        parser.print_help()
        return 1

    print(f"\n{'='*40}")
    print(f"Total frames processed: {total}")
    return 0


if __name__ == "__main__":
    exit(main())
