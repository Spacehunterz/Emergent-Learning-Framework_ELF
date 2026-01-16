#!/bin/bash
#
# init-ralph.sh: Bootstrap Ralph Loop for a project
#
# Creates prd.json, progress.txt, and prompt.md
# Initializes stories from user input or defaults
#
# Usage:
#   bash init-ralph.sh                    # Interactive mode
#   bash init-ralph.sh --project "My App" --stories "file.txt"
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

PROJECT_NAME=""
STORIES_FILE=""
INTERACTIVE=true

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project) PROJECT_NAME="$2"; INTERACTIVE=false; shift 2 ;;
            --stories) STORIES_FILE="$2"; shift 2 ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done
}

prompt_project_name() {
    if [ -n "$PROJECT_NAME" ]; then
        return
    fi

    read -p "Project name: " PROJECT_NAME
    if [ -z "$PROJECT_NAME" ]; then
        PROJECT_NAME="Untitled Project"
    fi
}

prompt_stories() {
    if [ -n "$STORIES_FILE" ]; then
        return
    fi

    cat << 'EOF'

Enter stories one per line (blank line to finish):
Format: [PRIORITY] Story ID: Story Title
Example: 1 FEAT-001: Implement authentication

EOF

    STORIES=()
    while true; do
        read -p "Story: " story
        if [ -z "$story" ]; then
            if [ ${#STORIES[@]} -eq 0 ]; then
                echo "⚠️  No stories entered. Using defaults..."
                create_default_stories
                return
            fi
            break
        fi
        STORIES+=("$story")
    done

    create_stories_from_input "${STORIES[@]}"
}

create_default_stories() {
    cat > "$REPO_ROOT/prd.json" << 'EOF'
{
  "name": "My Project",
  "version": "1.0.0",
  "description": "Bootstrap PRD created with init-ralph.sh",
  "created_at": "2026-01-15",
  "stories": [
    {
      "id": "TASK-001",
      "title": "Project Setup",
      "description": "Initialize project structure and basic infrastructure",
      "priority": 1,
      "status": "pending",
      "acceptance_criteria": [
        "Project structure is organized",
        "README documents the project",
        "CI/CD is configured",
        "Development environment is ready"
      ],
      "files": [
        "README.md",
        ".github/workflows/ci.yml",
        "package.json"
      ]
    },
    {
      "id": "TASK-002",
      "title": "Core Feature Implementation",
      "description": "Implement the primary feature or module",
      "priority": 2,
      "status": "pending",
      "acceptance_criteria": [
        "Feature works end-to-end",
        "Tests cover main paths",
        "Documentation is complete",
        "Code review approved"
      ],
      "files": [
        "src/core.ts",
        "tests/core.test.ts"
      ]
    },
    {
      "id": "TASK-003",
      "title": "Testing and Quality",
      "description": "Ensure code quality and test coverage",
      "priority": 3,
      "status": "pending",
      "acceptance_criteria": [
        "Unit tests pass",
        "Integration tests pass",
        "Code coverage > 80%",
        "Linting passes"
      ],
      "files": [
        "tests/",
        ".eslintrc.json",
        "jest.config.js"
      ]
    },
    {
      "id": "TASK-004",
      "title": "Documentation and Release",
      "description": "Final documentation, release notes, and deployment",
      "priority": 4,
      "status": "pending",
      "acceptance_criteria": [
        "API documentation complete",
        "Release notes written",
        "Version bumped",
        "Published to registry/registry"
      ],
      "files": [
        "docs/",
        "CHANGELOG.md",
        "package.json"
      ]
    }
  ]
}
EOF
}

create_stories_from_input() {
    local stories=("$@")
    local python_script=$(cat << 'PYSCRIPT'
import json
from datetime import datetime

prd = {
    "name": "$PROJECT_NAME",
    "version": "1.0.0",
    "description": "PRD created with init-ralph.sh",
    "created_at": datetime.now().isoformat(),
    "stories": []
}

stories_input = """$STORIES_JSON"""

for idx, line in enumerate(stories_input.strip().split('\n'), 1):
    if not line.strip():
        continue

    parts = line.split(':', 1)
    if len(parts) == 2:
        header = parts[0].strip()
        title = parts[1].strip()
        story_id = f"TASK-{idx:03d}"

        story = {
            "id": story_id,
            "title": title,
            "description": f"Story: {title}",
            "priority": idx,
            "status": "pending",
            "acceptance_criteria": [
                "Requirements are met",
                "Tests pass",
                "Code review approved"
            ],
            "files": [
                f"src/task-{idx}.ts",
                f"tests/task-{idx}.test.ts"
            ]
        }
        prd['stories'].append(story)

with open('$REPO_ROOT/prd.json', 'w') as f:
    json.dump(prd, f, indent=2)

print(f"Created PRD with {len(prd['stories'])} stories")
PYSCRIPT
)

    STORIES_JSON=$(printf '%s\n' "${stories[@]}")

    python3 << EOF
import json
from datetime import datetime

prd = {
    "name": "$PROJECT_NAME",
    "version": "1.0.0",
    "description": "PRD created with init-ralph.sh",
    "created_at": datetime.now().isoformat(),
    "stories": []
}

stories_input = """$(printf '%s\n' "${stories[@]}")"""

for idx, line in enumerate(stories_input.strip().split('\n'), 1):
    if not line.strip():
        continue

    parts = line.split(':', 1)
    if len(parts) == 2:
        title = parts[1].strip()
        story_id = f"TASK-{idx:03d}"

        story = {
            "id": story_id,
            "title": title,
            "description": f"Story: {title}",
            "priority": idx,
            "status": "pending",
            "acceptance_criteria": [
                "Requirements are met",
                "Tests pass",
                "Code review approved"
            ],
            "files": [
                f"src/task-{idx}.ts",
                f"tests/task-{idx}.test.ts"
            ]
        }
        prd['stories'].append(story)

with open('$REPO_ROOT/prd.json', 'w') as f:
    json.dump(prd, f, indent=2)

print(f"✓ Created PRD with {len(prd['stories'])} stories")
EOF
}

create_progress_file() {
    cat > "$REPO_ROOT/progress.txt" << 'EOF'
# Ralph Loop Progress Tracking

This file is append-only. Each iteration adds its learnings here.
It serves as the institutional memory bridging fresh Claude Code sessions.

## How to Use

Each session should append an entry like:

```
## [ISO Date] - [Story ID]: [Brief Title]
- Learning 1
- Learning 2
- Issue encountered and resolution
```

---

## Session History

(Entries appear here as each iteration completes)

---

## Patterns Learned

(Reusable insights discovered during iterations)

---

## Known Issues

(Tracking problems discovered during iterations)

---

## Next Steps

(Guidance for future iterations)

---

Generated by init-ralph.sh
Ralph Loop Version: 1.0.0
EOF
}

create_prompt_template() {
    cat > "$REPO_ROOT/prompt.md" << 'EOF'
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

(Story details will be filled in by ralph.sh for each iteration)

## Acceptance Criteria

(Criteria will be filled in by ralph.sh for each iteration)

## Files to Change

(Files will be listed by ralph.sh for each iteration)

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

main() {
    parse_args "$@"

    echo "═══════════════════════════════════════════════════════════"
    echo "Ralph Loop Bootstrap"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    if [ "$INTERACTIVE" = true ]; then
        prompt_project_name
        echo ""
        prompt_stories
    else
        create_default_stories
    fi

    create_progress_file
    create_prompt_template

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "✅ Ralph Loop Initialized"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Files created:"
    echo "  • prd.json       - Product Requirements Document"
    echo "  • progress.txt   - Learnings across sessions"
    echo "  • prompt.md      - Template for story iteration"
    echo ""
    echo "Next steps:"
    echo "  1. Review prd.json and update stories as needed"
    echo "  2. Run: bash $SCRIPT_DIR/ralph.sh"
    echo "  3. Each iteration: ralph.sh spawns a fresh claude-code session"
    echo "  4. Sessions read prompt.md and update progress.txt"
    echo ""
    echo "To run Ralph Loop:"
    echo "  bash $SCRIPT_DIR/ralph.sh              # Run all stories"
    echo "  bash $SCRIPT_DIR/ralph.sh --max-iterations 5  # Stop after 5 iterations"
    echo ""
}

main "$@"
