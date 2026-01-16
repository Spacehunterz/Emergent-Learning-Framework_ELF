#!/bin/bash
#
# prd.sh: PRD management tool
#
# Handles: create, show, edit, add, remove, validate
#

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PRD_FILE="$REPO_ROOT/prd.json"
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

show_prd() {
    if [ ! -f "$PRD_FILE" ]; then
        echo "No prd.json found"
        return 1
    fi

    $PYTHON_CMD << EOFPYTHON
import json
with open('$PRD_FILE') as f:
    prd = json.load(f)

print(f"\n{prd['name']}")
print(f"Version: {prd['version']}")
print(f"Description: {prd['description']}\n")
print("Stories:")
print("-" * 70)

for story in prd.get('stories', []):
    status_icon = {
        'pending': '[ ]',
        'in_progress': '[~]',
        'done': '[X]',
        'blocked': '[!]'
    }.get(story['status'], '[ ]')

    print(f"{status_icon} [{story['priority']}] {story['id']}: {story['title']}")
    print(f"     Status: {story['status']}")

print("-" * 70)
completed = sum(1 for s in prd['stories'] if s['status'] == 'done')
print(f"\nProgress: {completed}/{len(prd['stories'])} stories complete")
EOFPYTHON
}

validate_prd() {
    if [ ! -f "$PRD_FILE" ]; then
        echo "PRD not found: $PRD_FILE"
        return 1
    fi

    $PYTHON_CMD << EOFPYTHON
import json
import sys

try:
    with open('$PRD_FILE') as f:
        prd = json.load(f)

    errors = []
    warnings = []

    if 'stories' not in prd:
        errors.append("Missing 'stories' key")
    elif len(prd['stories']) == 0:
        errors.append("No stories defined")

    seen_ids = set()
    for idx, story in enumerate(prd.get('stories', [])):
        if not story.get('id'):
            errors.append(f"Story {idx}: missing 'id'")
        elif story['id'] in seen_ids:
            errors.append(f"Story {idx}: duplicate id '{story['id']}'")
        else:
            seen_ids.add(story['id'])

        if not story.get('title'):
            errors.append(f"Story {story.get('id', idx)}: missing 'title'")

        if story.get('status') not in ['pending', 'in_progress', 'done', 'blocked']:
            errors.append(f"Story {story.get('id', idx)}: invalid status '{story.get('status')}'")

        if not story.get('acceptance_criteria'):
            warnings.append(f"Story {story.get('id', idx)}: no acceptance criteria defined")
        elif len(story.get('acceptance_criteria', [])) < 3:
            warnings.append(f"Story {story.get('id', idx)}: only {len(story.get('acceptance_criteria', []))} criteria (recommend 3+)")

        # Validate narrative format for STORY-* entries
        if story.get('id', '').startswith('STORY-'):
            desc = story.get('description', '')
            if not ('As a' in desc and 'I want' in desc and 'so that' in desc):
                warnings.append(f"Story {story.get('id', idx)}: description should follow 'As a X, I want Y, so that Z' format")

    if errors:
        print("ERRORS:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    if warnings:
        print("WARNINGS:")
        for warn in warnings:
            print(f"  - {warn}")

    if not errors:
        print("PRD is valid")
        sys.exit(0)

except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOFPYTHON
}

create_prd() {
    if [ -f "$PRD_FILE" ]; then
        read -p "prd.json already exists. Overwrite? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi

    bash "$(dirname "${BASH_SOURCE[0]}")/init-ralph.sh" "$@"
}

main() {
    local cmd="${1:-show}"

    case "$cmd" in
        show)
            show_prd
            ;;
        validate)
            validate_prd
            ;;
        create)
            create_prd "${@:2}"
            ;;
        *)
            echo "Usage: prd.sh [show|validate|create]"
            exit 1
            ;;
    esac
}

main "$@"
