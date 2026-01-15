"""
Admin Router - CEO inbox, export, open-in-editor.
"""

import logging
import re
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from models import ActionResult, OpenInEditorRequest
from utils import get_db, dict_from_row

router = APIRouter(prefix="/api", tags=["admin"])
logger = logging.getLogger(__name__)

# Path will be set from main.py
EMERGENT_LEARNING_PATH = None
ALLOWED_OPEN_PATHS = []


def set_paths(elf_path: Path):
    """Set the paths for admin operations."""
    global EMERGENT_LEARNING_PATH, ALLOWED_OPEN_PATHS
    EMERGENT_LEARNING_PATH = elf_path
    ALLOWED_OPEN_PATHS = [
        elf_path.resolve(),
        Path.home().resolve(),
    ]


def _is_path_allowed(file_path: Path) -> bool:
    """
    Check if a path is within allowed directories.

    Prevents path traversal attacks by validating the resolved path
    is within one of the allowed base directories.
    """
    try:
        resolved = file_path.resolve()

        if not resolved.exists():
            return False

        if resolved.is_symlink():
            resolved = resolved.resolve(strict=True)

        for allowed_base in ALLOWED_OPEN_PATHS:
            try:
                resolved.relative_to(allowed_base)
                return True
            except ValueError:
                continue

        return False
    except (OSError, RuntimeError):
        return False


@router.get("/ceo-inbox")
async def get_ceo_inbox():
    """Get CEO inbox items (pending decisions)."""
    if EMERGENT_LEARNING_PATH is None:
        raise HTTPException(status_code=500, detail="Paths not configured")

    ceo_inbox_path = EMERGENT_LEARNING_PATH / "ceo-inbox"
    items = []

    if not ceo_inbox_path.exists():
        return items

    for file_path in ceo_inbox_path.glob("*.md"):
        if file_path.name == "TEMPLATE.md":
            continue

        try:
            content = file_path.read_text(encoding='utf-8')

            # Parse frontmatter-style metadata from content
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            priority_match = re.search(r'\*\*Priority:\*\*\s*(\w+)', content)
            status_match = re.search(r'\*\*Status:\*\*\s*(\w+)', content)
            date_match = re.search(r'\*\*Date:\*\*\s*([\d-]+)', content)

            # Get first paragraph after title as summary
            summary_match = re.search(r'^##\s+Context\s*\n+(.+?)(?=\n\n|\n##)', content, re.MULTILINE | re.DOTALL)
            summary = summary_match.group(1).strip()[:200] if summary_match else ""

            items.append({
                "filename": file_path.name,
                "title": title_match.group(1) if title_match else file_path.stem,
                "priority": priority_match.group(1) if priority_match else "Medium",
                "status": status_match.group(1) if status_match else "Pending",
                "date": date_match.group(1) if date_match else None,
                "summary": summary,
                "path": str(file_path)
            })
        except Exception as e:
            logger.error(f"Error reading CEO inbox item {file_path}: {e}")
            continue

    # Sort by priority (Critical > High > Medium > Low) then by date
    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    items.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["date"] or ""))

    return items


@router.get("/ceo-inbox/{filename}")
async def get_ceo_inbox_item(filename: str):
    """Get full content of a CEO inbox item."""
    if EMERGENT_LEARNING_PATH is None:
        raise HTTPException(status_code=500, detail="Paths not configured")

    if not re.match(r'^[\w\-]+\.md$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    ceo_inbox_dir = (EMERGENT_LEARNING_PATH / "ceo-inbox").resolve()
    file_path = (ceo_inbox_dir / filename).resolve()

    try:
        file_path.relative_to(ceo_inbox_dir)
    except ValueError:
        logger.warning(f"Path traversal blocked in ceo-inbox: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        content = file_path.read_text(encoding='utf-8')
        return {"filename": filename, "content": content}
    except Exception as e:
        logger.error(f"Error reading CEO inbox item {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read item")


@router.get("/export/{export_type}")
async def export_data(export_type: str, format: str = "json"):
    """Export data in various formats."""
    with get_db() as conn:
        cursor = conn.cursor()

        if export_type == "heuristics":
            cursor.execute("""
                SELECT id, domain, rule, explanation, confidence,
                       times_validated, times_violated, is_golden,
                       source_type, created_at, updated_at
                FROM heuristics
                ORDER BY confidence DESC
            """)
            data = [dict_from_row(r) for r in cursor.fetchall()]

        elif export_type == "runs":
            cursor.execute("""
                SELECT id, workflow_id, workflow_name, status, phase,
                       total_nodes, completed_nodes, failed_nodes,
                       started_at, completed_at, created_at
                FROM workflow_runs
                ORDER BY created_at DESC
            """)
            data = [dict_from_row(r) for r in cursor.fetchall()]

        elif export_type == "learnings":
            cursor.execute("""
                SELECT id, type, filepath, title, summary, domain, severity, created_at
                FROM learnings
                ORDER BY created_at DESC
            """)
            data = [dict_from_row(r) for r in cursor.fetchall()]

        elif export_type == "full":
            # Full export includes everything
            data = {
                "exported_at": datetime.now().isoformat(),
                "heuristics": [],
                "learnings": [],
                "runs": [],
                "trails": [],
                "metrics_summary": {}
            }

            cursor.execute("SELECT * FROM heuristics ORDER BY confidence DESC")
            data["heuristics"] = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM learnings ORDER BY created_at DESC")
            data["learnings"] = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT 100")
            data["runs"] = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT location, SUM(strength) as total_strength, COUNT(*) as count
                FROM trails
                GROUP BY location
                ORDER BY total_strength DESC
                LIMIT 100
            """)
            data["trails"] = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT metric_type, COUNT(*) as count
                FROM metrics
                GROUP BY metric_type
            """)
            data["metrics_summary"] = {r["metric_type"]: r["count"] for r in cursor.fetchall()}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown export type: {export_type}")

        return data


@router.post("/open-in-editor")
async def open_in_editor(request: OpenInEditorRequest) -> ActionResult:
    """Open a file in VS Code."""
    try:
        filepath = request.filepath
        line_number = request.line_number

        file_path = Path(filepath)

        if not _is_path_allowed(file_path):
            logger.warning(f"Path traversal blocked: {filepath}")
            return ActionResult(success=False, message="Access denied: path not in allowed directories")

        if line_number:
            subprocess.Popen(["code", "-g", f"{file_path}:{line_number}"])
        else:
            subprocess.Popen(["code", "-g", str(file_path)])

        return ActionResult(success=True, message=f"Opened {filepath} in VS Code")
    except Exception as e:
        logger.error(f"Error opening file in editor: {e}", exc_info=True)
        return ActionResult(success=False, message="Failed to open file in editor. Please try again.")


# ==============================================================================
# Database Backup Endpoints
# ==============================================================================

DEFAULT_BACKUP_KEEP_COUNT = 7


def _get_backup_dir() -> Path:
    """Get the backup directory path."""
    if EMERGENT_LEARNING_PATH is None:
        raise HTTPException(status_code=500, detail="Paths not configured")
    return EMERGENT_LEARNING_PATH / "backups"


def _get_db_path() -> Path:
    """Get the database path."""
    if EMERGENT_LEARNING_PATH is None:
        raise HTTPException(status_code=500, detail="Paths not configured")
    return EMERGENT_LEARNING_PATH / "memory" / "index.db"


def _perform_backup(keep_count: int = DEFAULT_BACKUP_KEEP_COUNT) -> dict:
    """
    Perform database backup using SQLite's online backup API.
    Safe for concurrent use.
    """
    db_path = _get_db_path()
    backup_dir = _get_backup_dir()

    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found")

    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"elf_backup_{timestamp}.db"
    backup_path = backup_dir / backup_name

    try:
        source_conn = sqlite3.connect(str(db_path))
        dest_conn = sqlite3.connect(str(backup_path))

        with dest_conn:
            source_conn.backup(dest_conn)

        source_conn.close()
        dest_conn.close()

        # Rotate old backups
        backups = sorted(
            backup_dir.glob("elf_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        deleted = []
        for old_backup in backups[keep_count:]:
            try:
                old_backup.unlink()
                deleted.append(old_backup.name)
            except OSError:
                pass

        return {
            "backup_file": backup_name,
            "backup_path": str(backup_path),
            "size_bytes": backup_path.stat().st_size,
            "rotated_out": deleted,
            "created_at": datetime.now().isoformat()
        }

    except sqlite3.Error as e:
        if backup_path.exists():
            backup_path.unlink()
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}")


@router.post("/backup")
async def create_backup(keep_count: int = DEFAULT_BACKUP_KEEP_COUNT) -> dict:
    """
    Create a database backup.

    Args:
        keep_count: Number of backups to retain (default: 7)

    Returns:
        Backup metadata including file path and size
    """
    return _perform_backup(keep_count)


@router.get("/backups")
async def list_backups() -> dict:
    """
    List all available database backups.

    Returns:
        List of backup files with metadata
    """
    backup_dir = _get_backup_dir()

    if not backup_dir.exists():
        return {"backups": [], "total": 0}

    backups = sorted(
        backup_dir.glob("elf_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    backup_list = []
    for backup in backups:
        stat = backup.stat()
        backup_list.append({
            "name": backup.name,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    return {
        "backups": backup_list,
        "total": len(backup_list),
        "backup_dir": str(backup_dir)
    }


@router.post("/backup/restore/{backup_name}")
async def restore_backup(backup_name: str) -> ActionResult:
    """
    Restore database from a backup file.

    Creates a safety backup of current database before restoring.

    Args:
        backup_name: Name of backup file to restore (e.g., elf_backup_20240115_120000.db)

    Returns:
        ActionResult indicating success or failure
    """
    # Validate backup name format to prevent path traversal
    if not re.match(r'^elf_backup_\d{8}_\d{6}\.db$', backup_name):
        return ActionResult(success=False, message="Invalid backup name format")

    backup_dir = _get_backup_dir()
    db_path = _get_db_path()
    backup_path = backup_dir / backup_name

    if not backup_path.exists():
        return ActionResult(success=False, message=f"Backup not found: {backup_name}")

    # Create safety backup before restore
    safety_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safety_backup = backup_dir / f"pre_restore_{safety_timestamp}.db"

    try:
        if db_path.exists():
            source_conn = sqlite3.connect(str(db_path))
            dest_conn = sqlite3.connect(str(safety_backup))
            with dest_conn:
                source_conn.backup(dest_conn)
            source_conn.close()
            dest_conn.close()
            logger.info(f"Safety backup created: {safety_backup}")

        # Perform restore
        source_conn = sqlite3.connect(str(backup_path))
        dest_conn = sqlite3.connect(str(db_path))

        with dest_conn:
            source_conn.backup(dest_conn)

        source_conn.close()
        dest_conn.close()

        logger.info(f"Database restored from: {backup_name}")
        return ActionResult(
            success=True,
            message=f"Database restored from {backup_name}. Safety backup: {safety_backup.name}"
        )

    except sqlite3.Error as e:
        logger.error(f"Restore failed: {e}", exc_info=True)
        return ActionResult(success=False, message=f"Restore failed: {e}")
