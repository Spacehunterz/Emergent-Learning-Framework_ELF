# Golden Rules

Golden Rules are constitutional principles all agents follow.

## Built-in Rules

1. **Query Before Acting** - Always check the building first
2. **Document Failures Immediately** - Record while context is fresh
3. **Extract Heuristics** - Document the WHY, not just outcomes
4. **Break It Before Shipping** - Test destructively before release
5. **Escalate Uncertainty** - Ask when unsure about big decisions

## Adding Project-Specific Rules

**Step 1:** Identify the pattern
- Validated 10+ times
- Applies broadly to your project
- Saves significant time when followed

## Promoting Heuristics

When a heuristic has proven itself (confidence > 0.9, validations > 10):

1. Check confidence
2. Edit golden-rules.md
3. Update CLAUDE.md to reference it

## Best Practices

**Good rules:**
- "Validate user input before processing"
- "Check file existence before reading"

**Bad rules:**
- "Use Joi schema with these exact fields" (too specific)
- "Be careful with files" (not actionable)

---

# Community Rules Library

Battle-tested rules you can cherry-pick for your setup. Copy what applies to your stack.

## Code Quality

- **Zero-Dependency Preference**: Prefer zero-dependency solutions. Justify any new dependencies.
- **No Code Comments**: Do not write comments. Use descriptive names. Put "why" in commit messages.
- **Design for Testability**: Avoid tight coupling. Design so components can be tested in isolation.
- **No Scope Creep**: Preserve working code paths when refactoring. No "while we are here" changes.

## Architecture

- **Outline Before Multi-File Changes**: For multi-file changes, outline the plan before implementing.
- **Backward Compatibility**: Maintain backward compatibility for public APIs.

## Multi-Agent

- **Read Coordination Skill First**: Read coordination SKILL.md before multi-agent tasks.
- **Blackboard Architecture**: Prefer blackboard architecture for cross-agent communication.
- **Document Handoffs**: Document agent roles and handoff protocols explicitly.
- **Consider Race Conditions**: Identify potential race conditions in concurrent code.

## Debugging

- **Reproduce Before Fixing**: Reproduce the bug before attempting to fix it.
- **Binary Search to Isolate**: Use binary search - disable half the code to isolate bugs.

## Security

- **Never Log Potential Secrets**: Never log/print variables that might contain secrets.
- **Validate at Boundaries Only**: Validate external input at system boundaries, not everywhere.

## Token Efficiency

- **No Unnecessary Code Repeats**: Avoid repeating large code blocks unnecessarily.
- **Targeted Diffs Over Rewrites**: Use targeted diffs instead of full file rewrites.
- **Reference Previous Context**: Reference previous context rather than re-explaining.

---

# Domain-Specific Rules

## Python

- **Check Venv Before Pip**: Always activate/check virtual environment before pip operations.
- **Use Python -m**: Use python -m module over direct script execution.

## JavaScript/TypeScript

- **Check ESM vs CJS**: Check for type: module in package.json before adding imports.
- **Await Every Promise**: await every Promise - do not let them float.

## Rust

- **Justify Unsafe Blocks**: Justify any unsafe blocks with safety invariants documented.
- **thiserror Over String Errors**: Prefer thiserror over string errors for library code.
- **Audit Unwrap**: Audit unwrap()/expect() in non-prototype code.

## Windows

- **Forward Slashes in Code**: Use forward slashes in code paths.
- **Check CRLF on Silent Failures**: When scripts fail silently, check for CRLF line ending issues.

## Database

- **Transactions for Multi-Step Writes**: Always use transactions for multi-step write operations.
- **Check Existing Migrations First**: Check for existing migrations before creating schema changes.

## Docker

- **Order Dockerfile by Change Frequency**: Order commands by change frequency - rarely-changed first.

---

# Claude Code Windows Rules

Workarounds for known Windows issues.

- **PowerShell Over Git Bash**: Use PowerShell, not Git Bash for Claude Code on Windows.
- **No Unicode in Filenames**: Avoid unicode characters in filenames on Windows (issue #14180).
- **Test Hooks After Setup**: Explicitly test hooks after setting them up on Windows (issue #14219).
- **Run From Project Root**: Run Claude Code from project root, not nested directories (issue #14243).
- **Unique MCP Tool Names**: Ensure tool names are unique across all MCP servers (issue #14146).
- **Break Long Operations Under 5 Minutes**: Tools fail after 5 minutes on Windows 10 (issue #14235).
- **WSL Projects in Linux Filesystem**: Store projects in /home/, not /mnt/c/ when using WSL.
- **Force Kill on Stream Closed**: If Claude says stopped but tokens keep flowing, force kill (issue #14229).
- **Native Installer Over npm**: Use native PowerShell installer instead of npm install on Windows.
