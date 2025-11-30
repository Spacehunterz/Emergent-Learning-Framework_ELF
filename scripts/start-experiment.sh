#!/bin/bash
# Start a new experiment in the Emergent Learning Framework

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
EXPERIMENTS_DIR="$BASE_DIR/experiments/active"

# Ensure experiments directory exists
mkdir -p "$EXPERIMENTS_DIR"

# Prompt for inputs
echo "=== Start Experiment ==="
echo ""

read -p "Experiment Name: " name
if [ -z "$name" ]; then
    echo "Error: Name cannot be empty"
    exit 1
fi

read -p "Hypothesis: " hypothesis
if [ -z "$hypothesis" ]; then
    echo "Error: Hypothesis cannot be empty"
    exit 1
fi

read -p "Success Criteria: " success_criteria

read -p "Failure Criteria: " failure_criteria

# Generate folder name
timestamp=$(date +%Y%m%d-%H%M%S)
folder_name=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
folder_path="$EXPERIMENTS_DIR/${timestamp}_${folder_name}"
relative_folder="experiments/active/${timestamp}_${folder_name}"

# Create experiment folder
mkdir -p "$folder_path"

# Create hypothesis.md
cat > "$folder_path/hypothesis.md" <<EOF
# Experiment: $name

**Started**: $(date +%Y-%m-%d)
**Status**: Active

## Hypothesis

$hypothesis

## Success Criteria

$success_criteria

## Failure Criteria

$failure_criteria

## Variables

[What parameters are we varying?]

## Controls

[What are we keeping constant?]

## Methodology

[How will we conduct this experiment?]

## Expected Outcomes

[What do we expect to learn?]
EOF

# Create log.md
cat > "$folder_path/log.md" <<EOF
# Experiment Log: $name

## Cycle 1

**Date**: $(date +%Y-%m-%d)
**Status**: Planned

### Try

[What did we attempt?]

### Break

[What did we observe? What broke?]

### Analysis

[What does this tell us?]

### Learning

[What heuristic or insight emerged?]

---

EOF

echo "Created experiment folder: $folder_path"

# Insert into database
sqlite3 "$DB_PATH" <<SQL
INSERT INTO experiments (name, hypothesis, status, folder_path)
VALUES (
    '$name',
    '$hypothesis',
    'active',
    '$relative_folder'
);
SQL

experiment_id=$(sqlite3 "$DB_PATH" "SELECT last_insert_rowid();")
echo "Database record created (ID: $experiment_id)"

# Git commit
cd "$BASE_DIR"
if [ -d ".git" ]; then
    git add "$folder_path"
    git add "$DB_PATH"
    git commit -m "experiment: Start '$name'" -m "Hypothesis: $hypothesis" || echo "No changes to commit"
    echo "Git commit created"
else
    echo "Warning: Not a git repository. Skipping commit."
fi

echo ""
echo "Experiment started successfully!"
echo "Folder: $folder_path"
echo "Edit hypothesis at: $folder_path/hypothesis.md"
echo "Log cycles at: $folder_path/log.md"
