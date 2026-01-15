#!/usr/bin/env python3
"""
Database backup utility for Emergent Learning Framework.

Creates timestamped backups of the ELF database with automatic rotation.
Uses SQLite's online backup API for safe concurrent backup.

Usage:
    python backup-db.py                    # Backup with defaults
    python backup-db.py --keep 10          # Keep last 10 backups
    python backup-db.py --backup-dir /path # Custom backup directory
    python backup-db.py --list             # List existing backups
    python backup-db.py --restore BACKUP   # Restore from backup file
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ELF paths
ELF_PATH = Path.home() / ".claude" / "emergent-learning"
DEFAULT_DB_PATH = ELF_PATH / "memory" / "index.db"
DEFAULT_BACKUP_DIR = ELF_PATH / "backups"
DEFAULT_KEEP_COUNT = 7  # Keep last 7 backups by default


def backup_database(
    db_path: Path = DEFAULT_DB_PATH,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    keep_count: int = DEFAULT_KEEP_COUNT
) -> Path:
    """
    Create a backup of the database using SQLite's online backup API.

    Args:
        db_path: Path to the database to backup
        backup_dir: Directory to store backups
        keep_count: Number of backups to retain (oldest deleted)

    Returns:
        Path to the created backup file
    """
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    # Create backup directory if needed
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"elf_backup_{timestamp}.db"
    backup_path = backup_dir / backup_name

    # Perform backup using SQLite's online backup API
    # This is safe even while the database is in use
    try:
        source_conn = sqlite3.connect(str(db_path))
        dest_conn = sqlite3.connect(str(backup_path))

        with dest_conn:
            source_conn.backup(dest_conn)

        source_conn.close()
        dest_conn.close()

        print(f"Backup created: {backup_path}")

    except sqlite3.Error as e:
        print(f"Error creating backup: {e}", file=sys.stderr)
        if backup_path.exists():
            backup_path.unlink()
        sys.exit(1)

    # Rotate old backups
    rotate_backups(backup_dir, keep_count)

    return backup_path


def rotate_backups(backup_dir: Path, keep_count: int) -> None:
    """
    Remove old backups, keeping only the most recent keep_count.

    Args:
        backup_dir: Directory containing backups
        keep_count: Number of backups to retain
    """
    backups = sorted(
        backup_dir.glob("elf_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    # Delete backups beyond keep_count
    for old_backup in backups[keep_count:]:
        try:
            old_backup.unlink()
            print(f"Rotated out old backup: {old_backup.name}")
        except OSError as e:
            print(f"Warning: Could not delete {old_backup}: {e}", file=sys.stderr)


def list_backups(backup_dir: Path = DEFAULT_BACKUP_DIR) -> list[dict]:
    """
    List all available backups with metadata.

    Args:
        backup_dir: Directory containing backups

    Returns:
        List of backup info dicts with name, size, and date
    """
    if not backup_dir.exists():
        print("No backups directory found.")
        return []

    backups = sorted(
        backup_dir.glob("elf_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not backups:
        print("No backups found.")
        return []

    results = []
    print(f"\nBackups in {backup_dir}:\n")
    print(f"{'Name':<30} {'Size':>12} {'Date':<20}")
    print("-" * 65)

    for backup in backups:
        stat = backup.stat()
        size_mb = stat.st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(stat.st_mtime)

        results.append({
            "name": backup.name,
            "path": str(backup),
            "size_bytes": stat.st_size,
            "modified": mtime.isoformat()
        })

        print(f"{backup.name:<30} {size_mb:>10.2f} MB {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\nTotal: {len(backups)} backup(s)")
    return results


def restore_backup(
    backup_file: str,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    db_path: Path = DEFAULT_DB_PATH
) -> bool:
    """
    Restore a database from a backup file.

    Args:
        backup_file: Name or full path of backup file
        backup_dir: Directory containing backups (if backup_file is just a name)
        db_path: Path to restore the database to

    Returns:
        True if restore succeeded
    """
    # Resolve backup path
    backup_path = Path(backup_file)
    if not backup_path.is_absolute():
        backup_path = backup_dir / backup_file

    if not backup_path.exists():
        print(f"Error: Backup not found: {backup_path}", file=sys.stderr)
        return False

    # Safety: backup current database before restore
    if db_path.exists():
        safety_backup = db_path.with_suffix(".db.pre_restore")
        try:
            source_conn = sqlite3.connect(str(db_path))
            dest_conn = sqlite3.connect(str(safety_backup))
            with dest_conn:
                source_conn.backup(dest_conn)
            source_conn.close()
            dest_conn.close()
            print(f"Safety backup created: {safety_backup}")
        except sqlite3.Error as e:
            print(f"Warning: Could not create safety backup: {e}", file=sys.stderr)

    # Perform restore
    try:
        source_conn = sqlite3.connect(str(backup_path))
        dest_conn = sqlite3.connect(str(db_path))

        with dest_conn:
            source_conn.backup(dest_conn)

        source_conn.close()
        dest_conn.close()

        print(f"Restored database from: {backup_path}")
        return True

    except sqlite3.Error as e:
        print(f"Error restoring backup: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="ELF Database Backup Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                         # Create backup with defaults
    %(prog)s --keep 10               # Keep last 10 backups
    %(prog)s --list                  # Show all backups
    %(prog)s --restore elf_backup_20240115_120000.db
        """
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Database path (default: {DEFAULT_DB_PATH})"
    )

    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"Backup directory (default: {DEFAULT_BACKUP_DIR})"
    )

    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP_COUNT,
        help=f"Number of backups to keep (default: {DEFAULT_KEEP_COUNT})"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all existing backups"
    )

    parser.add_argument(
        "--restore",
        type=str,
        metavar="BACKUP",
        help="Restore from specified backup file"
    )

    args = parser.parse_args()

    if args.list:
        list_backups(args.backup_dir)
    elif args.restore:
        success = restore_backup(args.restore, args.backup_dir, args.db_path)
        sys.exit(0 if success else 1)
    else:
        backup_database(args.db_path, args.backup_dir, args.keep)


if __name__ == "__main__":
    main()
