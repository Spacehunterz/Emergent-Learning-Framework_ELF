#!/bin/bash
# Check Backup Health
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/.claude/backups/emergent-learning}"
echo "Checking backups in $BACKUP_ROOT..."

if [ ! -d "$BACKUP_ROOT" ]; then
    echo "ERROR: Backup root directory not found."
    exit 1
fi

# Check for backups created in the last 24 hours
if find "$BACKUP_ROOT" -name "*.tar.gz" -mtime -1 -print -quit | grep -q .; then
    echo "OK: Recent backup found (< 24h)."
    exit 0
else
    echo "WARNING: No backup found from the last 24 hours."
    exit 1
fi
