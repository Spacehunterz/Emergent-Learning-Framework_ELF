#!/bin/bash
# Emergent Learning Framework - Update Script
# Run with: chmod +x update.sh && ./update.sh
#
# Features:
# - Hybrid support: git-based or standalone updates
# - Interactive conflict resolution for customized files
# - Database schema migrations
# - Automatic backup with rollback on failure
# - Dashboard customization detection

set -e

# ============================================================================
# SECTION 1: SETUP & COLORS
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
EMERGENT_LEARNING_DIR="$CLAUDE_DIR/emergent-learning"
VERSION_FILE="$EMERGENT_LEARNING_DIR/VERSION"
DB_PATH="$EMERGENT_LEARNING_DIR/memory/index.db"
STOCK_HASHES_FILE="$SCRIPT_DIR/.stock-hashes"
GITHUB_REPO="Spacehunterz/Emergent-Learning-Framework_ELF"
GITHUB_API="https://api.github.com/repos/$GITHUB_REPO"

# Backup directory (will be set during backup phase)
BACKUP_DIR=""

# Track if we need to rollback
ROLLBACK_NEEDED=false

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Emergent Learning Framework Updater${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ============================================================================
# SECTION 2: HELPER FUNCTIONS
# ============================================================================

# Detect whether this is a git clone or standalone install
detect_install_type() {
    if [ -d "$SCRIPT_DIR/.git" ]; then
        echo "git"
    else
        echo "standalone"
    fi
}

# Get currently installed version
get_current_version() {
    if [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE"
    else
        echo "0.0.0"
    fi
}

# Get latest version from GitHub
get_latest_version() {
    local install_type="$1"

    if [ "$install_type" = "git" ]; then
        # Use git to get latest tag
        git fetch --tags origin 2>/dev/null
        git describe --tags --abbrev=0 origin/main 2>/dev/null || echo "0.0.0"
    else
        # Use GitHub API
        if command -v curl &>/dev/null; then
            curl -s "$GITHUB_API/releases/latest" 2>/dev/null | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/' || echo "0.0.0"
        elif command -v wget &>/dev/null; then
            wget -qO- "$GITHUB_API/releases/latest" 2>/dev/null | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/' || echo "0.0.0"
        else
            echo "0.0.0"
        fi
    fi
}

# Compare semver versions: returns 0 if v1 >= v2, 1 otherwise
version_gte() {
    local v1="$1"
    local v2="$2"

    # Remove 'v' prefix if present
    v1="${v1#v}"
    v2="${v2#v}"

    # Simple string comparison works for semver if properly formatted
    [ "$(printf '%s\n' "$v1" "$v2" | sort -V | tail -n1)" = "$v1" ]
}

# Compute SHA256 hash of a file
compute_file_hash() {
    local file="$1"
    if [ -f "$file" ]; then
        if command -v sha256sum &>/dev/null; then
            sha256sum "$file" | cut -d' ' -f1
        elif command -v shasum &>/dev/null; then
            shasum -a 256 "$file" | cut -d' ' -f1
        else
            echo "no-hash-tool"
        fi
    else
        echo "file-not-found"
    fi
}

# Check if a file has been modified from stock
is_file_modified() {
    local file="$1"
    local relative_path="${file#$EMERGENT_LEARNING_DIR/}"

    if [ ! -f "$STOCK_HASHES_FILE" ]; then
        # No stock hashes file - can't determine, assume not modified
        return 1
    fi

    local stock_hash=$(grep "^[a-f0-9]* *$relative_path$" "$STOCK_HASHES_FILE" 2>/dev/null | cut -d' ' -f1)

    if [ -z "$stock_hash" ]; then
        # File not in stock hashes - not tracked, assume not modified
        return 1
    fi

    local current_hash=$(compute_file_hash "$file")

    [ "$current_hash" != "$stock_hash" ]
}

# Create backup of critical files
create_backup() {
    BACKUP_DIR="$HOME/.claude/emergent-learning-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    echo -e "${YELLOW}[Backup]${NC} Creating backup at $BACKUP_DIR"

    # Backup database
    if [ -f "$DB_PATH" ]; then
        cp "$DB_PATH" "$BACKUP_DIR/"
        echo -e "  ${GREEN}✓${NC} Database (index.db)"
    fi

    # Backup golden rules
    if [ -f "$EMERGENT_LEARNING_DIR/memory/golden-rules.md" ]; then
        cp "$EMERGENT_LEARNING_DIR/memory/golden-rules.md" "$BACKUP_DIR/"
        echo -e "  ${GREEN}✓${NC} Golden rules"
    fi

    # Backup CEO inbox
    if [ -d "$EMERGENT_LEARNING_DIR/ceo-inbox" ]; then
        cp -r "$EMERGENT_LEARNING_DIR/ceo-inbox" "$BACKUP_DIR/"
        echo -e "  ${GREEN}✓${NC} CEO inbox"
    fi

    # Backup settings.json
    if [ -f "$CLAUDE_DIR/settings.json" ]; then
        cp "$CLAUDE_DIR/settings.json" "$BACKUP_DIR/"
        echo -e "  ${GREEN}✓${NC} settings.json"
    fi

    # Backup CLAUDE.md
    if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
        cp "$CLAUDE_DIR/CLAUDE.md" "$BACKUP_DIR/"
        echo -e "  ${GREEN}✓${NC} CLAUDE.md"
    fi

    # Backup VERSION
    if [ -f "$VERSION_FILE" ]; then
        cp "$VERSION_FILE" "$BACKUP_DIR/"
        echo -e "  ${GREEN}✓${NC} VERSION"
    fi

    echo ""
}

# Rollback from backup
rollback() {
    if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
        echo -e "${RED}[Error]${NC} No backup directory found for rollback"
        return 1
    fi

    echo -e "${YELLOW}[Rollback]${NC} Restoring from backup..."

    # Restore database
    if [ -f "$BACKUP_DIR/index.db" ]; then
        cp "$BACKUP_DIR/index.db" "$DB_PATH"
        echo -e "  ${GREEN}✓${NC} Database restored"
    fi

    # Restore golden rules
    if [ -f "$BACKUP_DIR/golden-rules.md" ]; then
        cp "$BACKUP_DIR/golden-rules.md" "$EMERGENT_LEARNING_DIR/memory/"
        echo -e "  ${GREEN}✓${NC} Golden rules restored"
    fi

    # Restore CEO inbox
    if [ -d "$BACKUP_DIR/ceo-inbox" ]; then
        rm -rf "$EMERGENT_LEARNING_DIR/ceo-inbox"
        cp -r "$BACKUP_DIR/ceo-inbox" "$EMERGENT_LEARNING_DIR/"
        echo -e "  ${GREEN}✓${NC} CEO inbox restored"
    fi

    # Restore settings.json
    if [ -f "$BACKUP_DIR/settings.json" ]; then
        cp "$BACKUP_DIR/settings.json" "$CLAUDE_DIR/"
        echo -e "  ${GREEN}✓${NC} settings.json restored"
    fi

    # Restore VERSION
    if [ -f "$BACKUP_DIR/VERSION" ]; then
        cp "$BACKUP_DIR/VERSION" "$VERSION_FILE"
        echo -e "  ${GREEN}✓${NC} VERSION restored"
    fi

    echo -e "${GREEN}[OK]${NC} Rollback complete"
}

# Error handler for automatic rollback
on_error() {
    echo ""
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}  Update Failed!${NC}"
    echo -e "${RED}============================================${NC}"
    echo ""

    if [ "$ROLLBACK_NEEDED" = true ]; then
        rollback
    fi

    echo ""
    echo -e "${YELLOW}Your previous installation has been restored.${NC}"
    echo -e "${YELLOW}Please report this issue at: https://github.com/$GITHUB_REPO/issues${NC}"
    exit 1
}

# Set up error trap
trap on_error ERR

# Interactive prompt for file conflicts
prompt_conflict() {
    local file="$1"
    local new_file="$2"
    local relative_path="${file#$EMERGENT_LEARNING_DIR/}"

    while true; do
        echo ""
        echo -e "${CYAN}┌─────────────────────────────────────────────────────────────┐${NC}"
        echo -e "${CYAN}│${NC} File modified: ${YELLOW}$relative_path${NC}"
        echo -e "${CYAN}│${NC}"
        echo -e "${CYAN}│${NC} Your version differs from the update."
        echo -e "${CYAN}│${NC}"
        echo -e "${CYAN}│${NC} [U] Update (overwrite your changes)"
        echo -e "${CYAN}│${NC} [K] Keep (preserve your version, may miss fixes)"
        echo -e "${CYAN}│${NC} [D] Diff (show differences, then ask again)"
        echo -e "${CYAN}│${NC} [B] Backup + Update (save yours as .user-backup)"
        echo -e "${CYAN}│${NC}"
        echo -e "${CYAN}└─────────────────────────────────────────────────────────────┘${NC}"
        echo -n "Choice [U/K/D/B]: "
        read -r choice

        case "${choice^^}" in
            U)
                cp "$new_file" "$file"
                echo -e "  ${GREEN}✓${NC} Updated $relative_path"
                return 0
                ;;
            K)
                echo -e "  ${YELLOW}→${NC} Kept your version of $relative_path"
                return 0
                ;;
            D)
                echo ""
                echo -e "${CYAN}--- Your version${NC}"
                echo -e "${GREEN}+++ New version${NC}"
                diff "$file" "$new_file" || true
                echo ""
                ;;
            B)
                cp "$file" "$file.user-backup"
                cp "$new_file" "$file"
                echo -e "  ${GREEN}✓${NC} Updated $relative_path (your version saved as .user-backup)"
                return 0
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter U, K, D, or B.${NC}"
                ;;
        esac
    done
}

# Check dashboard for modifications
check_dashboard_modifications() {
    local dashboard_dir="$EMERGENT_LEARNING_DIR/dashboard-app"
    local modified_count=0

    if [ ! -d "$dashboard_dir" ]; then
        return 0
    fi

    # Check key dashboard files
    local dashboard_files=(
        "frontend/src/App.tsx"
        "frontend/src/components/AlertsPanel.tsx"
        "frontend/src/components/cosmic-view/CosmicView.tsx"
        "backend/main.py"
    )

    for file in "${dashboard_files[@]}"; do
        if is_file_modified "$dashboard_dir/$file"; then
            ((modified_count++))
        fi
    done

    return $modified_count
}

# Run database migrations
run_migrations() {
    local migrations_dir="$SCRIPT_DIR/scripts/migrations"
    local migrate_script="$SCRIPT_DIR/scripts/migrate_db.py"

    if [ ! -f "$migrate_script" ]; then
        echo -e "  ${YELLOW}→${NC} No migration script found, skipping"
        return 0
    fi

    if [ ! -d "$migrations_dir" ]; then
        echo -e "  ${YELLOW}→${NC} No migrations directory found, skipping"
        return 0
    fi

    echo -e "${YELLOW}[Migrations]${NC} Checking database schema..."

    # Determine Python command
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "  ${YELLOW}→${NC} Python not found, skipping migrations"
        return 0
    fi

    $PYTHON_CMD "$migrate_script" "$DB_PATH"
}

# ============================================================================
# SECTION 3: PRE-FLIGHT CHECKS
# ============================================================================

echo -e "${YELLOW}[Step 1/6]${NC} Pre-flight checks..."

# Check if ELF is installed
if [ ! -d "$EMERGENT_LEARNING_DIR" ]; then
    echo -e "${RED}[Error]${NC} ELF not installed at $EMERGENT_LEARNING_DIR"
    echo -e "${YELLOW}Run install.sh first to install ELF.${NC}"
    exit 1
fi

# Detect install type
INSTALL_TYPE=$(detect_install_type)
echo -e "  Install type: ${GREEN}$INSTALL_TYPE${NC}"

# Get versions
CURRENT_VERSION=$(get_current_version)
echo -e "  Current version: ${CYAN}$CURRENT_VERSION${NC}"

echo -e "  Checking for updates..."
LATEST_VERSION=$(get_latest_version "$INSTALL_TYPE")
echo -e "  Latest version: ${CYAN}$LATEST_VERSION${NC}"

# Check if update is needed
if version_gte "$CURRENT_VERSION" "$LATEST_VERSION" && [ "$CURRENT_VERSION" != "0.0.0" ]; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Already up to date!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "Installed version: ${CYAN}$CURRENT_VERSION${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}[OK]${NC} Update available: $CURRENT_VERSION → $LATEST_VERSION"
echo ""

# ============================================================================
# SECTION 4: BACKUP
# ============================================================================

echo -e "${YELLOW}[Step 2/6]${NC} Creating backup..."
create_backup
ROLLBACK_NEEDED=true

# ============================================================================
# SECTION 5: CUSTOMIZATION DETECTION
# ============================================================================

echo -e "${YELLOW}[Step 3/6]${NC} Detecting customizations..."

MODIFIED_FILES=()

# Check tracked files
TRACKED_FILES=(
    "scripts/record-heuristic.sh"
    "scripts/record-failure.sh"
    "scripts/record-success.sh"
    "hooks/learning-loop/pre_tool_learning.py"
    "hooks/learning-loop/post_tool_learning.py"
    "query/query.py"
)

for relative_file in "${TRACKED_FILES[@]}"; do
    full_path="$EMERGENT_LEARNING_DIR/$relative_file"
    if [ -f "$full_path" ] && is_file_modified "$full_path"; then
        MODIFIED_FILES+=("$relative_file")
        echo -e "  ${YELLOW}Modified:${NC} $relative_file"
    fi
done

# Check dashboard
DASHBOARD_MODIFIED=false
if check_dashboard_modifications; then
    DASHBOARD_MODIFIED=true
    echo -e "  ${YELLOW}⚠️  Dashboard has local modifications${NC}"
fi

if [ ${#MODIFIED_FILES[@]} -eq 0 ] && [ "$DASHBOARD_MODIFIED" = false ]; then
    echo -e "  ${GREEN}No customizations detected${NC}"
fi

echo ""

# Warn about dashboard modifications
if [ "$DASHBOARD_MODIFIED" = true ]; then
    echo -e "${YELLOW}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│${NC} Dashboard has been modified locally."
    echo -e "${YELLOW}│${NC} Updating will overwrite your changes."
    echo -e "${YELLOW}│${NC}"
    echo -e "${YELLOW}│${NC} [Y] Yes, update dashboard (overwrite my changes)"
    echo -e "${YELLOW}│${NC} [N] No, skip dashboard update (keep my changes)"
    echo -e "${YELLOW}└─────────────────────────────────────────────────────────────┘${NC}"
    echo -n "Update dashboard? [y/N]: "
    read -r dashboard_choice

    if [[ ! "${dashboard_choice^^}" =~ ^Y ]]; then
        echo -e "  ${YELLOW}→${NC} Dashboard update will be skipped"
        SKIP_DASHBOARD=true
    else
        SKIP_DASHBOARD=false
    fi
    echo ""
fi

# ============================================================================
# SECTION 6: UPDATE EXECUTION
# ============================================================================

echo -e "${YELLOW}[Step 4/6]${NC} Updating files..."

if [ "$INSTALL_TYPE" = "git" ]; then
    # Git-based update
    cd "$SCRIPT_DIR"

    # Check for local changes
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "  ${YELLOW}Stashing local changes...${NC}"
        git stash
        STASHED=true
    else
        STASHED=false
    fi

    # Pull latest
    echo -e "  Pulling latest from origin..."
    git pull origin main

    # Pop stash if we stashed
    if [ "$STASHED" = true ]; then
        echo -e "  ${YELLOW}Restoring local changes...${NC}"
        if ! git stash pop; then
            echo -e "  ${YELLOW}⚠️  Merge conflicts detected in stashed changes${NC}"
            echo -e "  ${YELLOW}   Run 'git stash show -p' to see your changes${NC}"
            echo -e "  ${YELLOW}   Run 'git stash drop' after resolving${NC}"
        fi
    fi

    echo -e "  ${GREEN}✓${NC} Git update complete"

else
    # Standalone update - download release
    echo -e "  Downloading latest release..."

    TEMP_DIR=$(mktemp -d)
    RELEASE_URL="https://github.com/$GITHUB_REPO/archive/refs/tags/$LATEST_VERSION.tar.gz"

    if command -v curl &>/dev/null; then
        curl -sL "$RELEASE_URL" | tar -xz -C "$TEMP_DIR" --strip-components=1
    elif command -v wget &>/dev/null; then
        wget -qO- "$RELEASE_URL" | tar -xz -C "$TEMP_DIR" --strip-components=1
    else
        echo -e "${RED}[Error]${NC} Neither curl nor wget found"
        exit 1
    fi

    # Update files, handling conflicts
    UPDATE_DIRS=(
        "query"
        "scripts"
        "hooks"
        "conductor"
        "agents"
        "templates"
    )

    for dir in "${UPDATE_DIRS[@]}"; do
        if [ -d "$TEMP_DIR/$dir" ]; then
            # Check each file for modifications
            find "$TEMP_DIR/$dir" -type f | while read -r new_file; do
                relative="${new_file#$TEMP_DIR/}"
                existing="$EMERGENT_LEARNING_DIR/$relative"

                if [ -f "$existing" ] && is_file_modified "$existing"; then
                    prompt_conflict "$existing" "$new_file"
                else
                    mkdir -p "$(dirname "$existing")"
                    cp "$new_file" "$existing"
                fi
            done
        fi
    done

    # Update dashboard if not skipped
    if [ "$SKIP_DASHBOARD" != true ] && [ -d "$TEMP_DIR/dashboard-app" ]; then
        echo -e "  Updating dashboard..."
        rm -rf "$EMERGENT_LEARNING_DIR/dashboard-app"
        cp -r "$TEMP_DIR/dashboard-app" "$EMERGENT_LEARNING_DIR/"
        echo -e "  ${GREEN}✓${NC} Dashboard updated"
    fi

    # Clean up
    rm -rf "$TEMP_DIR"

    echo -e "  ${GREEN}✓${NC} Standalone update complete"
fi

echo ""

# ============================================================================
# SECTION 7: DATABASE MIGRATION
# ============================================================================

echo -e "${YELLOW}[Step 5/6]${NC} Running database migrations..."
run_migrations
echo ""

# ============================================================================
# SECTION 8: POST-UPDATE
# ============================================================================

echo -e "${YELLOW}[Step 6/6]${NC} Post-update tasks..."

# Update dependencies
echo -e "  Installing Python dependencies..."
if command -v pip3 &>/dev/null; then
    pip3 install -q peewee aiosqlite 2>/dev/null || true
elif command -v pip &>/dev/null; then
    pip install -q peewee aiosqlite 2>/dev/null || true
fi

# Update dashboard dependencies if dashboard was updated
if [ "$SKIP_DASHBOARD" != true ] && [ -d "$EMERGENT_LEARNING_DIR/dashboard-app/frontend" ]; then
    echo -e "  Installing dashboard dependencies..."
    cd "$EMERGENT_LEARNING_DIR/dashboard-app/frontend"
    if command -v bun &>/dev/null; then
        bun install --silent 2>/dev/null || true
    elif command -v npm &>/dev/null; then
        npm install --silent 2>/dev/null || true
    fi
    cd "$SCRIPT_DIR"
fi

# Write new VERSION file
echo "$LATEST_VERSION" > "$VERSION_FILE"
echo -e "  ${GREEN}✓${NC} Updated VERSION to $LATEST_VERSION"

# Validate settings.json
if [ -f "$CLAUDE_DIR/settings.json" ]; then
    if python3 -c "import json; json.load(open('$CLAUDE_DIR/settings.json'))" 2>/dev/null || \
       python -c "import json; json.load(open('$CLAUDE_DIR/settings.json'))" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} settings.json validated"
    else
        echo -e "  ${YELLOW}⚠️${NC} settings.json may be invalid"
    fi
fi

# Mark rollback as no longer needed (success path)
ROLLBACK_NEEDED=false

echo ""

# ============================================================================
# DONE
# ============================================================================

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Update Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Updated from ${CYAN}$CURRENT_VERSION${NC} to ${CYAN}$LATEST_VERSION${NC}"
echo ""
echo -e "Backup saved at: ${CYAN}$BACKUP_DIR${NC}"
echo ""

# Show changelog hint
if [ -f "$SCRIPT_DIR/CHANGELOG.md" ]; then
    echo -e "View what's new: ${CYAN}cat $SCRIPT_DIR/CHANGELOG.md${NC}"
    echo ""
fi

echo "Next steps:"
echo "  # Restart the dashboard to see changes:"
echo "  cd ~/.claude/emergent-learning/dashboard-app && ./run-dashboard.sh"
echo ""
