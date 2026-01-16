#!/bin/bash
#
# story.sh: Interactive user story management
#
# Handles: new, show, view, update, list, export
#

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PRD_FILE="$REPO_ROOT/prd.json"
PYTHON_CMD="python3"

if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

get_next_story_id() {
    $PYTHON_CMD << 'EOFPY'
import json
try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    existing_ids = [s['id'] for s in prd.get('stories', []) if s['id'].startswith('STORY-')]
    if not existing_ids:
        print("STORY-001")
    else:
        nums = []
        for sid in existing_ids:
            try:
                num = int(sid.split('-')[1])
                nums.append(num)
            except (IndexError, ValueError):
                pass
        next_num = max(nums, default=0) + 1
        print(f"STORY-{next_num:03d}")
except Exception as e:
    print("STORY-001")
EOFPY
}

create_story() {
    if [ ! -f "$PRD_FILE" ]; then
        echo "Error: prd.json not found at $PRD_FILE"
        return 1
    fi

    NEXT_ID=$(get_next_story_id)

    read -p "Story ID [$NEXT_ID]: " STORY_ID
    STORY_ID="${STORY_ID:-$NEXT_ID}"

    echo "Create narrative: 'As a X, I want Y, so that Z'"
    read -p "User role (As a): " USER_ROLE
    read -p "Desired action (I want to): " DESIRED_ACTION
    read -p "Business value (So that): " BUSINESS_VALUE

    DESCRIPTION="As a $USER_ROLE, I want to $DESIRED_ACTION, so that $BUSINESS_VALUE"

    SUGGESTED_TITLE=$(echo "$DESIRED_ACTION" | sed 's/^./\U&/' | head -c 50)
    read -p "Title [$SUGGESTED_TITLE]: " TITLE
    TITLE="${TITLE:-$SUGGESTED_TITLE}"

    read -p "Priority [1=high, 2=normal, 3=low, default=2]: " PRIORITY
    PRIORITY="${PRIORITY:-2}"

    read -p "Files (comma-separated, optional): " FILES

    echo "Add acceptance criteria (blank line to finish, need at least 1):"
    CRITERIA_ARRAY=()
    while true; do
        read -p "  - " criterion
        [ -z "$criterion" ] && break
        CRITERIA_ARRAY+=("$criterion")
    done

    if [ ${#CRITERIA_ARRAY[@]} -eq 0 ]; then
        echo "Error: Need at least 1 acceptance criterion"
        return 1
    fi

    add_story_to_prd "$STORY_ID" "$TITLE" "$DESCRIPTION" "$PRIORITY" "$FILES" "${CRITERIA_ARRAY[@]}"
}

add_story_to_prd() {
    local story_id="$1"
    local title="$2"
    local description="$3"
    local priority="$4"
    local files="$5"
    shift 5
    local criteria=("$@")

    $PYTHON_CMD << EOFPYTHON
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    if any(s['id'] == '$story_id' for s in prd.get('stories', [])):
        print(f"Error: Story ID '$story_id' already exists", file=sys.stderr)
        sys.exit(1)

    desc = """$description"""
    if not ('As a' in desc and 'I want' in desc and 'so that' in desc):
        print("Warning: Description should follow 'As a X, I want Y, so that Z' format", file=sys.stderr)

    file_list = [f.strip() for f in '$files'.split(',') if f.strip()]

    criteria_list = [
        $(IFS=$'\n'; for c in "${criteria[@]}"; do printf '"%s",' "$(echo "$c" | sed 's/"/\\"/g')"; done | sed 's/,$//')
    ]

    story = {
        "id": "$story_id",
        "title": "$title",
        "description": desc,
        "priority": int('$priority'),
        "status": "pending",
        "acceptance_criteria": criteria_list,
        "files": file_list
    }

    prd['stories'].append(story)

    with open('$PRD_FILE', 'w') as f:
        json.dump(prd, f, indent=2)

    print(f"✓ Created story: [{story['id']}] {story['title']}")

except json.JSONDecodeError as e:
    print(f"Error: Invalid prd.json - {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOFPYTHON
}

show_stories() {
    if [ ! -f "$PRD_FILE" ]; then
        echo "Error: prd.json not found"
        return 1
    fi

    $PYTHON_CMD << EOFPY
import json
import sys
try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    stories = prd.get('stories', [])
    completed = sum(1 for s in stories if s['status'] == 'done')

    print(f"\nSTORIES ({len(stories)} total, {completed} complete)")
    print("=" * 70)

    for story in stories:
        status_icon = {
            'pending': '[ ]',
            'in_progress': '[~]',
            'done': '[X]',
            'blocked': '[!]'
        }.get(story['status'], '[ ]')

        print(f"{status_icon} [P{story['priority']}] {story['id']}: {story['title']}")
        print(f"     Status: {story['status']} | Files: {len(story.get('files', []))}\n")

    print("=" * 70)

except Exception as e:
    print(f"Error: {e}", file=__import__('sys').stderr)
    __import__('sys').exit(1)
EOFPY
}

view_story() {
    local story_id="$1"

    if [ ! -f "$PRD_FILE" ]; then
        echo "Error: prd.json not found"
        return 1
    fi

    if [ -z "$story_id" ]; then
        echo "Usage: story view <STORY-ID>"
        return 1
    fi

    $PYTHON_CMD << EOFPY
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    story = next((s for s in prd.get('stories', []) if s['id'] == '$story_id'), None)

    if not story:
        print(f"Error: Story '$story_id' not found", file=sys.stderr)
        sys.exit(1)

    priority_name = {1: 'High', 2: 'Medium', 3: 'Low'}.get(story['priority'], str(story['priority']))

    print("\n" + "=" * 70)
    print(f"{story['id']}: {story['title']}")
    print("=" * 70)
    print(f"\nDescription:")
    print(f"  {story['description']}")
    print(f"\nPriority: {story['priority']} ({priority_name})")
    print(f"Status: {story['status']}")
    print(f"\nAcceptance Criteria:")
    for criterion in story.get('acceptance_criteria', []):
        print(f"  - {criterion}")

    files = story.get('files', [])
    if files:
        print(f"\nFiles:")
        for f in files:
            print(f"  - {f}")
    else:
        print(f"\nFiles: (none specified)")

    print("\n" + "=" * 70 + "\n")

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOFPY
}

update_story() {
    local story_id="$1"

    if [ ! -f "$PRD_FILE" ]; then
        echo "Error: prd.json not found"
        return 1
    fi

    if [ -z "$story_id" ]; then
        echo "Usage: story update <STORY-ID>"
        return 1
    fi

    echo "Update story $story_id (blank = no change)"
    read -p "Status [pending|in_progress|done|blocked]: " NEW_STATUS
    read -p "Priority [1-3]: " NEW_PRIORITY

    $PYTHON_CMD << EOFPY
import json
import sys

try:
    story_id = '$story_id'
    new_status = '$NEW_STATUS'.strip()
    new_priority = '$NEW_PRIORITY'.strip()

    with open('$PRD_FILE') as f:
        prd = json.load(f)

    found = False
    for story in prd.get('stories', []):
        if story['id'] == story_id:
            found = True
            if new_status and new_status in ['pending', 'in_progress', 'done', 'blocked']:
                story['status'] = new_status
            elif new_status:
                print(f"Warning: Invalid status '{new_status}', keeping current", file=sys.stderr)

            if new_priority and new_priority in ['1', '2', '3']:
                story['priority'] = int(new_priority)
            elif new_priority:
                print(f"Warning: Invalid priority '{new_priority}', keeping current", file=sys.stderr)
            break

    if not found:
        print(f"Error: Story '{story_id}' not found", file=sys.stderr)
        sys.exit(1)

    with open('$PRD_FILE', 'w') as f:
        json.dump(prd, f, indent=2)

    print(f"✓ Updated story {story_id}")

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOFPY
}

list_stories() {
    local filter_priority=""
    local filter_status=""
    local filter_file=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --priority) filter_priority="$2"; shift 2 ;;
            --status) filter_status="$2"; shift 2 ;;
            --files) filter_file="$2"; shift 2 ;;
            *) shift ;;
        esac
    done

    if [ ! -f "$PRD_FILE" ]; then
        echo "Error: prd.json not found"
        return 1
    fi

    $PYTHON_CMD << EOFPY
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    stories = prd.get('stories', [])

    if '$filter_priority':
        stories = [s for s in stories if s['priority'] == int('$filter_priority')]
    if '$filter_status':
        stories = [s for s in stories if s['status'] == '$filter_status']
    if '$filter_file':
        stories = [s for s in stories if '$filter_file' in s.get('files', [])]

    if not stories:
        print("No stories match filter criteria")
        sys.exit(0)

    print(f"\nFiltered Stories ({len(stories)} total):")
    print("=" * 70)
    for story in stories:
        status_icon = {
            'pending': '[ ]',
            'in_progress': '[~]',
            'done': '[X]',
            'blocked': '[!]'
        }.get(story['status'], '[ ]')
        print(f"{status_icon} [P{story['priority']}] {story['id']}: {story['title']}")
    print("━" * 70 + "\n")

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOFPY
}

export_stories() {
    if [ ! -f "$PRD_FILE" ]; then
        echo "Error: prd.json not found"
        return 1
    fi

    $PYTHON_CMD << EOFPY
import json
from datetime import datetime
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    stories = prd.get('stories', [])
    total = len(stories)
    done = sum(1 for s in stories if s['status'] == 'done')
    in_progress = sum(1 for s in stories if s['status'] == 'in_progress')
    pending = sum(1 for s in stories if s['status'] == 'pending')
    blocked = sum(1 for s in stories if s['status'] == 'blocked')

    print("# Product Requirements - User Stories\n")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    print("## Summary\n")
    print(f"- **Total Stories:** {total}")
    print(f"- **Complete:** {done} ({done*100//total if total else 0}%)")
    print(f"- **In Progress:** {in_progress} ({in_progress*100//total if total else 0}%)")
    print(f"- **Pending:** {pending} ({pending*100//total if total else 0}%)")
    print(f"- **Blocked:** {blocked} ({blocked*100//total if total else 0}%)\n")

    by_priority = {}
    for story in stories:
        p = story['priority']
        if p not in by_priority:
            by_priority[p] = []
        by_priority[p].append(story)

    for priority in sorted(by_priority.keys()):
        priority_name = {1: 'High', 2: 'Medium', 3: 'Low'}.get(priority, str(priority))
        print(f"## Priority {priority} ({priority_name})\n")

        for story in by_priority[priority]:
            status_symbol = {
                'pending': '[PENDING]',
                'in_progress': '[IN_PROGRESS]',
                'done': '[DONE]',
                'blocked': '[BLOCKED]'
            }.get(story['status'], '[?]')

            print(f"### {status_symbol} {story['id']}: {story['title']}\n")
            print(f"**Status:** {story['status'].upper()}\n")
            print(story['description'] + "\n")

            print(f"**Acceptance Criteria:**\n")
            for c in story.get('acceptance_criteria', []):
                print(f"- {c}")

            files = story.get('files', [])
            if files:
                print(f"\n**Files:**\n")
                for f in files:
                    print(f"- `{f}`")

            print("\n---\n")

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOFPY
}

main() {
    local cmd="${1:-show}"

    case "$cmd" in
        new)
            create_story
            ;;
        show)
            show_stories
            ;;
        view)
            view_story "$2"
            ;;
        update)
            update_story "$2"
            ;;
        list)
            shift
            list_stories "$@"
            ;;
        export)
            export_stories
            ;;
        *)
            echo "Usage: story.sh [new|show|view|update|list|export]"
            echo ""
            echo "Commands:"
            echo "  new                 Create new story interactively"
            echo "  show                List all stories"
            echo "  view <STORY-ID>    Show story details"
            echo "  update <STORY-ID>  Update story status/priority"
            echo "  list [OPTIONS]      Filter stories"
            echo "    --priority N      Filter by priority (1-3)"
            echo "    --status STATUS   Filter by status (pending/in_progress/done/blocked)"
            echo "    --files PATH      Find stories touching a file"
            echo "  export              Export to markdown"
            exit 1
            ;;
    esac
}

main "$@"
