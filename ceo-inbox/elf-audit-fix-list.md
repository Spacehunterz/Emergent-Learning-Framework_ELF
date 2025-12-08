# ELF Audit Fix List - 91 Issues

**Created:** 2025-12-08
**Status:** PENDING CEO REVIEW - Ready to fix

## Quick Reference

```
CRITICAL: 1 | HIGH: 10 | MEDIUM: 42 | LOW: 38 | TOTAL: 91
```

## Phase 1: CRITICAL/SECURITY (13 items) - DO FIRST

| ID | Issue | Location | Fix |
|----|-------|----------|-----|
| S1 | `eval()` instead of `safe_eval_condition()` | conductor.py:879 | Replace with safe_eval_condition() |
| S2 | SQL injection via f-string | conductor.py:638-670 | Use parameterized query |
| S3 | TOCTOU race in file locks | blackboard.py:45-85 | Atomic lock + symlink check |
| S4 | Path traversal in files_modified | conductor.py:710-745 | Validate paths against root |
| S5 | Event log corruption silently skipped | event_log.py:233-253 | Add strict mode flag |
| S6 | No max length on condition string | conductor.py:39-69 | Add MAX_CONDITION_LENGTH |
| S7 | LIKE wildcards not escaped | query.py:~656-700 | Escape %, _, \ |
| S8 | Connection pool no validation | query.py:163-205 | Validate before reuse |
| S9 | TOCTOU in shell atomic ops | security.sh:141-175 | Use atomic_mkdir pattern |
| Q1 | Bare `except:` clause | query.py:204 | Specify exception type |
| Q2 | Bare `except Exception: pass` | conductor.py:886-888 | Add logging |
| Q3 | 3x identical exception handlers | event_log.py:101,116,121 | Extract helper |
| Q4 | _apply_event 13+ elif branches | event_log.py:327-480 | Split into handlers |

## Phase 2: COORDINATION (10 items)

| ID | Issue | Location | Fix |
|----|-------|----------|-----|
| C1 | Finding ID divergence | blackboard/event_log | Use sequence-based IDs both |
| C2 | Silent event log failures | blackboard_v2.py:68-73 | Raise or notify on failure |
| C3 | Cursor uses array index | blackboard.py | Change to sequence number |
| C4 | Context value type mismatch | both systems | Normalize to {value:, updated_at:} |
| C5 | No "failed" task status | event_log.py | Add task.failed event |
| C6 | Orphaned cursors | blackboard.py | Clean on deregister |
| C7 | No finding TTL | blackboard.py | Add expires_at field |
| C8 | No divergence detection | blackboard_v2.py | Auto-validate periodically |
| C10 | No ID match validation | blackboard_v2.py | Add to validate_state |
| C14 | No crash recovery tests | tests/ | Add recovery test suite |

## Phase 3: CODE QUALITY (8 items)

| ID | Issue | Location | Fix |
|----|-------|----------|-----|
| Q5 | Missing return type | conductor.py:39 | Add -> bool |
| Q6 | Missing return type | conductor.py:85 | Add -> None |
| Q7 | Missing return type | event_log.py:327 | Add -> Dict |
| Q8 | Generic Optional[Any] | event_log.py:77 | Specify lock type |
| Q9 | No test suite | repo-wide | Create tests/ with pytest |
| Q10 | Embedded tests | event_log.py:514-573 | Move to test file |
| Q11 | Embedded tests | blackboard_v2.py:347-375 | Move to test file |
| Q15 | run_workflow too long | conductor.py:850-895 | Extract methods |

## Phase 4: DOCUMENTATION (17 items)

| ID | Issue | Fix |
|----|-------|-----|
| D1 | README too long | Add TL;DR at top |
| D2 | Quick Start not quick | Add 30-second version |
| D3 | No Learning Loop diagram | Add ASCII diagram |
| D4 | Golden Rules no "why" | Add brief explanations |
| D5 | Key Phrases undersold | Clarify auto vs manual |
| D6 | Swarm jargon unexplained | Lead with use case |
| D7 | No First Use Guide | Create FIRST_USE.md |
| D8 | No troubleshooting | Add TROUBLESHOOTING.md |
| D9 | No multi-agent guide | Add step-by-step |
| D10 | No example projects | Add USE_CASES.md |
| D11 | No Operations Guide | Add OPERATIONS.md |
| D12 | Token costs not quantified | Add analytics |
| D13 | No API docs link | Point to /docs |
| D14 | Golden Rules not customizable | Document how |
| D15 | No existing setup guide | Add migration guide |
| D16 | No ADR | Create ADR.md |
| D17 | Prerequisites no expected output | Show examples |

## Phase 5: UX POLISH (29 items)

### Installation (I1-I12)
- I1: No "prerequisites met" confirmation
- I2: --no-dashboard meaning unclear
- I3: No directory count confirmation
- I4: Settings modification vague
- I5: No progress indication
- I6: No settings.json validation
- I7: Error recovery hints missing
- I8: "setup script" doesn't exist
- I9: Dashboard errors unclear
- I10: Missing prereqs shown as errors
- I11: No time indication
- I12: Next steps not copy-paste

### Dashboard (U1-U14)
- U1: Empty state no explanation (HIGH)
- U2: "Disconnected" no reason
- U3: "Runs" tab name ambiguous
- U4: Stats values unexplained
- U5: No "what now?" on Overview
- U6: Heuristic actions hidden
- U7: Query examples not clickable (MEDIUM)
- U8: No dashboard tutorial
- U9: WebSocket reconnect unclear
- U10: Export not discoverable
- U11: No metric tooltips
- U12: No getting started card
- U13: No API docs link
- U14: No dark/light toggle

### Uninstall (X1-X3)
- X1: Manual settings edit required
- X2: Backup meaning unclear
- X3: CLAUDE.md removal risky

## Phase 6: NICE-TO-HAVE (14 items)

| ID | Issue |
|----|-------|
| S10 | Weak entropy in backoff |
| S11 | MD5 instead of SHA-256 |
| S12 | No SECURITY.md |
| S13 | No secrets management |
| Q12 | 27 methods x 3 duplicated |
| Q13 | Pool size undocumented |
| Q14 | No Python version req |
| Q16 | Unquoted shell vars |
| Q17 | Missing SQLite pragmas |
| Q18 | No mypy configured |
| C9 | Timestamp precision diff |
| C11 | O(n) delta query scan |
| C12 | No Phase 2 cutover plan |
| C13 | No scale limits documented |

---

## Commands to Start

```bash
# View this file
cat ~/.claude/emergent-learning/ceo-inbox/elf-audit-fix-list.md

# Start Phase 1
cd /tmp/ELF-compare
# Fix S1 first (critical)
```

## Repo Locations

- **Public:** /tmp/ELF-compare (cloned)
- **Private:** ~/.claude/emergent-learning
