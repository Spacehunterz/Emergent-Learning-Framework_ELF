#!/bin/bash
# Verify Backup Integrity

BACKUP_ROOT="${BACKUP_ROOT:-$HOME/.claude/backups/emergent-learning}"
echo "Verifying backups in $BACKUP_ROOT..."

if [ ! -d "$BACKUP_ROOT" ]; then
    echo "ERROR: Backup root directory not found."
    exit 1
fi

latest_backup=$(ls -t "$BACKUP_ROOT"/*.tar.gz 2>/dev/null | head -n1)

if [ -z "$latest_backup" ]; then
    echo "ERROR: No backups found."
    exit 1
fi

echo "Verifying latest backup: $latest_backup"
if tar -tzf "$latest_backup" >/dev/null 2>&1; then
    echo "SUCCESS: Backup integrity verified."
    exit 0
else
    echo "ERROR: Backup verification failed (corrupt archive)."
    exit 1
fi
