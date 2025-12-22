#!/bin/bash
# ELF Update Script - Simple and safe
# Usage: ./update.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================"
echo "  ELF Update"
echo "================================"
echo ""

# Check we're in a git repo
if [ ! -d ".git" ]; then
    echo "Error: Not a git repository. Manual update required."
    exit 1
fi

# Show current version
if [ -f "VERSION" ]; then
    echo -e "Current version: ${GREEN}$(cat VERSION)${NC}"
fi

# Backup database
echo ""
echo -e "${YELLOW}[1/3]${NC} Backing up database..."
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
if [ -f "memory/index.db" ]; then
    cp memory/index.db "memory/index.db.backup.$BACKUP_DATE"
    echo "  Backed up to: memory/index.db.backup.$BACKUP_DATE"
else
    echo "  No database found, skipping backup"
fi

# Pull updates
echo ""
echo -e "${YELLOW}[2/3]${NC} Pulling updates..."
if [ -n "$(git status --porcelain)" ]; then
    echo "  Stashing local changes..."
    git stash
    STASHED=true
else
    STASHED=false
fi

git pull origin main

if [ "$STASHED" = true ]; then
    echo "  Restoring local changes..."
    git stash pop || echo -e "${YELLOW}  Warning: Merge conflicts in stashed changes. Run 'git stash show -p' to review.${NC}"
fi

# Run migrations
echo ""
echo -e "${YELLOW}[3/3]${NC} Running database migrations..."
if [ -f "scripts/migrate_db.py" ]; then
    python3 scripts/migrate_db.py memory/index.db || python scripts/migrate_db.py memory/index.db
else
    echo "  No migration script found, skipping"
fi

# Done
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  Update complete!${NC}"
echo -e "${GREEN}================================${NC}"
if [ -f "VERSION" ]; then
    echo -e "Now at version: ${GREEN}$(cat VERSION)${NC}"
fi
echo ""
echo "Restart Claude Code to pick up changes."
