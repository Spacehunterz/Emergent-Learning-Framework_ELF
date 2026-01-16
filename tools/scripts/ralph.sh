#!/bin/bash
#
# Ralph Loop: Autonomous AI task executor
#
# Spawns fresh Claude Code sessions to complete stories from prd.json
# Each iteration: read PRD → find incomplete → spawn session → update PRD → repeat
#
# Usage:
#   bash ralph.sh                  # Run until all stories complete or max iterations
#   bash ralph.sh --max-iterations 5
#   bash ralph.sh --prd custom-prd.json
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
PRD_FILE="${REPO_ROOT}/prd.json"
PROMPT_FILE="${REPO_ROOT}/prompt.md"
PROGRESS_FILE="${REPO_ROOT}/progress.txt"
MAX_ITERATIONS=20
ITERATION=0

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# ELF Observation settings
ELF_BASE="${HOME}/.claude/emergent-learning"
ELF_SESSION_DIR="${REPO_ROOT}/.elf/sessions"
SESSION_ID=$(date +%Y%m%d_%H%M%S)
CHECKPOINT_INTERVAL=5  # Run observation checkpoint every N iterations

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --prd) PRD_FILE="$2"; shift 2 ;;
            --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done
}

check_prerequisites() {
    if [ ! -f "$PRD_FILE" ]; then
        echo "❌ PRD file not found: $PRD_FILE"
        echo "   Create one with: bash $SCRIPT_DIR/init-ralph.sh"
        exit 1
    fi

    if ! $PYTHON_CMD -c "import json" 2>/dev/null; then
        echo "❌ Python not found or json module unavailable"
        exit 1
    fi

    if ! command -v claude-code &> /dev/null; then
        echo "⚠️  claude-code not found in PATH"
        echo "   Ralph Loop needs Claude Code CLI to spawn sessions"
    fi
}

# -----------------------------------------------------------------------------
# ELF Observation Functions
# -----------------------------------------------------------------------------

setup_elf_logging() {
    mkdir -p "$ELF_SESSION_DIR"
    echo "[ELF] Session logging enabled: ${ELF_SESSION_DIR}/loop_${SESSION_ID}_*.log"
}

elf_checkpoint() {
    # Run mid-session pattern extraction (accumulate without promotion)
    local iteration="$1"
    local log_file="${ELF_SESSION_DIR}/loop_${SESSION_ID}_${iteration}.log"

    if [ -f "$log_file" ]; then
        echo "[ELF] Checkpoint: extracting patterns from iteration $iteration"
        $PYTHON_CMD -m src.observe observe --session "$log_file" --dry-run 2>/dev/null || true
    fi
}

elf_distill() {
    # Run end-of-session distillation
    echo ""
    echo "[ELF] Session complete. Running pattern distillation..."

    # Extract patterns from all loop logs
    for log in "${ELF_SESSION_DIR}"/loop_${SESSION_ID}_*.log; do
        if [ -f "$log" ]; then
            $PYTHON_CMD -m src.observe observe --session "$log" 2>/dev/null || true
        fi
    done

    # Run distillation with auto-append to golden rules
    $PYTHON_CMD -m src.observe distill --run --auto-append 2>/dev/null || true
}

find_incomplete_story() {
    $PYTHON_CMD << PYSCRIPT
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    for story in prd.get('stories', []):
        if story['status'] in ['pending', 'in_progress']:
            print(f"{story['id']}:{story['title']}")
            sys.exit(0)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYSCRIPT
}

get_story_details() {
    local story_id="$1"
    $PYTHON_CMD << PYSCRIPT
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    for story in prd.get('stories', []):
        if story['id'] == '$story_id':
            print(json.dumps(story, indent=2))
            sys.exit(0)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYSCRIPT
}

generate_prompt() {
    local story_id="$1"
    local story_json="$2"

    cat > "$PROMPT_FILE" << 'EOF'
# Ralph Loop Iteration

You are executing a single story from the PRD. Your job is to:
1. Read the story details below
2. Implement the complete solution
3. Test thoroughly
4. Update progress.txt with what you learned
5. Exit when done

The next iteration will read your work and the updated progress.txt.

---

## Story

EOF

    echo "$story_json" | $PYTHON_CMD -c "import json, sys; story = json.load(sys.stdin); print(f'# {story[\"title\"]}\n\n{story[\"description\"]}')" >> "$PROMPT_FILE"

    cat >> "$PROMPT_FILE" << 'EOF'

## Acceptance Criteria

EOF
    echo "$story_json" | $PYTHON_CMD -c "import json, sys; story = json.load(sys.stdin); print('\n'.join([f'- {c}' for c in story.get('acceptance_criteria', [])]))" >> "$PROMPT_FILE"

    cat >> "$PROMPT_FILE" << 'EOF'

## Files to Change

EOF
    echo "$story_json" | $PYTHON_CMD -c "import json, sys; story = json.load(sys.stdin); print('\n'.join([f'- {f}' for f in story.get('files', [])]))" >> "$PROMPT_FILE"

    cat >> "$PROMPT_FILE" << 'EOF'

## Progress Tracking

After you complete this story:
1. Run all tests and quality checks
2. Commit your changes with a clear message
3. Append your learnings to progress.txt in this format:

```
## [Date] - [Story ID]: [What You Did]
- Key learning 1
- Key learning 2
- Any issues encountered
```

Remember: Keep context fresh. Focus on THIS story only. Document your work so the next iteration understands what happened.

---

EOF
}

update_story_status() {
    local story_id="$1"
    local new_status="$2"

    $PYTHON_CMD << PYSCRIPT
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    for story in prd.get('stories', []):
        if story['id'] == '$story_id':
            story['status'] = '$new_status'
            break

    with open('$PRD_FILE', 'w') as f:
        json.dump(prd, f, indent=2)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYSCRIPT
}

count_completed() {
    $PYTHON_CMD << PYSCRIPT
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    count = sum(1 for story in prd.get('stories', []) if story['status'] == 'done')
    print(count)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYSCRIPT
}

count_total() {
    $PYTHON_CMD << PYSCRIPT
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    print(len(prd.get('stories', [])))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYSCRIPT
}

main() {
    parse_args "$@"
    check_prerequisites
    setup_elf_logging

    echo "═══════════════════════════════════════════════════════════"
    echo "RALPH LOOP - Autonomous Story Executor (with ELF)"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "PRD: $PRD_FILE"
    echo "Max iterations: $MAX_ITERATIONS"
    echo "Session ID: $SESSION_ID"
    echo ""

    while [ $ITERATION -lt $MAX_ITERATIONS ]; do
        ITERATION=$((ITERATION + 1))
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "ITERATION $ITERATION"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        COMPLETED=$(count_completed)
        TOTAL=$(count_total)
        echo "Progress: $COMPLETED/$TOTAL stories completed"
        echo ""

        if [ "$COMPLETED" -eq "$TOTAL" ]; then
            echo "✅ ALL STORIES COMPLETE"
            echo ""
            echo "Learnings recorded in: $PROGRESS_FILE"
            elf_distill  # Run final distillation
            exit 0
        fi

        STORY_LINE=$(find_incomplete_story)
        if [ -z "$STORY_LINE" ]; then
            echo "✅ No incomplete stories found"
            exit 0
        fi

        STORY_ID="${STORY_LINE%%:*}"
        STORY_TITLE="${STORY_LINE#*:}"

        echo "📌 Next story: [$STORY_ID] $STORY_TITLE"
        echo ""

        STORY_JSON=$(get_story_details "$STORY_ID")
        generate_prompt "$STORY_ID" "$STORY_JSON"

        update_story_status "$STORY_ID" "in_progress"

        LOG_FILE="${ELF_SESSION_DIR}/loop_${SESSION_ID}_${ITERATION}.log"

        echo "🔄 Spawning fresh Claude Code session..."
        echo "   → Reading: $PROMPT_FILE"
        echo "   → Will update: progress.txt"
        echo "   → Logging to: $LOG_FILE"
        echo ""

        # Capture Claude output for ELF observation
        if claude-code --dangerously-skip-permissions < "$PROMPT_FILE" 2>&1 | tee "$LOG_FILE"; then
            update_story_status "$STORY_ID" "done"
            echo ""
            echo "✅ Story complete: [$STORY_ID] $STORY_TITLE"
        else
            echo ""
            echo "⚠️  Story did not complete cleanly. Checking progress..."
            CURRENT_STATUS=$(get_story_status "$STORY_ID")
            if [ "$CURRENT_STATUS" != "done" ]; then
                update_story_status "$STORY_ID" "blocked"
                echo "❌ Marked as blocked: [$STORY_ID]"
                echo "   Check progress.txt for details"
                elf_distill  # Run distillation before exit
                exit 1
            fi
        fi

        # Mid-session checkpoint every N iterations
        if [ $((ITERATION % CHECKPOINT_INTERVAL)) -eq 0 ]; then
            elf_checkpoint "$ITERATION"
        fi

        echo ""
        if [ $ITERATION -lt $MAX_ITERATIONS ]; then
            echo "Continuing to next story..."
            echo ""
        fi
    done

    echo ""
    echo "⚠️  Max iterations ($MAX_ITERATIONS) reached"
    COMPLETED=$(count_completed)
    TOTAL=$(count_total)
    echo "Completed: $COMPLETED/$TOTAL stories"
    echo ""
    elf_distill  # Run final distillation
    echo ""
    echo "Review progress.txt for details and continue with:"
    echo "  bash $SCRIPT_DIR/ralph.sh"
}

get_story_status() {
    local story_id="$1"
    $PYTHON_CMD << PYSCRIPT
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    for story in prd.get('stories', []):
        if story['id'] == '$story_id':
            print(story['status'])
            sys.exit(0)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYSCRIPT
}

main "$@"
