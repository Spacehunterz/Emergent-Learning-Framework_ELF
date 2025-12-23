#!/bin/bash
# Uninstall Script
# WARNING: This will remove the framework and data.

read -p "Are you sure you want to uninstall ELF? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "To proceed with uninstallation, please manually delete the directory:"
echo "rm -rf \"${ELF_BASE_PATH:-$HOME/.claude/emergent-learning}\""
echo "rm -rf \"$HOME/.claude/backups/emergent-learning\""
echo ""
echo "Automatic uninstallation is currently disabled for safety."
