# Changelog

All notable changes to the Emergent Learning Framework will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.3] - 2026-01-15

### Added
- **Golden Rules Auto-Sync Infrastructure** - Automatic database synchronization with markdown source
  - `scripts/sync-golden-rules.py` - Manual sync script for golden rules markdown to database
  - `scripts/verify-hooks.py` - Hook verification and auto-installation utility
  - `scripts/install-hooks.py` - Hook template installation from `.hooks-templates/`
  - `.hooks-templates/` - Versioned hook templates for distribution and auto-install
  - `.hooks-templates/PostToolUse/sync-golden-rules.py` - Post-tool hook for auto-sync
  - `.hooks-templates/README.md` - Hook development and troubleshooting documentation
- **Hook Auto-Installation for New Users** - Seamless hook setup during first install
  - Hooks automatically installed from templates during setup
  - `/checkin` command verifies hooks are present and auto-installs if missing
  - Zero manual configuration needed for new users
- **Checkin Integration** - Hook verification integrated into checkin workflow
  - Added `verify_hooks()` method as Step 1b in checkin process
  - Auto-installs missing hooks with [OK] status message
  - Safety net ensures framework hooks always present

### Fixed
- **Golden Rules Synchronization Lag** - Markdown and database now stay in sync
  - Previously markdown had 30 golden rules but database had stale count (55)
  - Post-tool hook now detects changes and syncs automatically
  - Database is updated after each tool execution if markdown changed

## [0.3.12] - 2026-01-05

### Added
- **Game Leaderboard** - Full leaderboard system for the space shooter game
  - `GET /api/game/leaderboard` - Top N scores with pagination and user info
  - `GET /api/game/leaderboard/around-me` - Scores centered on current user
  - React `Leaderboard.tsx` component with sci-fi styling
  - Crown/Medal icons for top 3, user highlighting, loading states
  - Anti-cheat filtering with configurable MAX_VALID_SCORE
  - Performance index `idx_game_state_score_desc` for fast queries
- **Comprehensive API Reference** - Complete documentation for all public APIs
  - `docs/api/index.md` - API overview and quick start guide
  - `docs/api/QuerySystem.md` - All 30+ async query methods with examples
  - `docs/api/Models.md` - Documentation for all 22 database models
  - `docs/api/Hooks.md` - Hook development guide with 28 security patterns
  - `docs/api/Conductor.md` - Workflow orchestration and swarm coordination
- **Database Schema Documentation** - `docs/database/schema.md` with 50+ tables, ERD, and migration notes
- **Developer Guides**
  - `docs/guides/testing.md` - Test organization, fixtures, coverage requirements
  - `docs/guides/performance.md` - Query optimization, indexing, token cost analysis
  - `docs/guides/extensions.md` - Custom hooks, mixins, personas, dashboard plugins
- **CONTRIBUTING.md** - Developer onboarding, code style guide, PR workflow
- **Test Infrastructure** - Test files for critical bugs (WebSocket stress, auto-capture rollback, broadcast race)

### Fixed
- **SQL Injection Vulnerability** - Added whitelist-based validation in `main.py`
  - `ALLOWED_TABLE_CONFIGS` dictionary with valid tables, columns, and order_by fields
  - `_validate_query_params()` function with O(1) frozenset lookups
  - Blocks all SQL injection attempts in dynamic query building
- **Path Traversal Vulnerability** - Hardened `admin.py` file access
  - `_is_path_allowed()` validates paths against allowed directories
  - Symlink resolution with `strict=True` for security
  - Defense-in-depth for `/ceo-inbox/{filename}` endpoint
- **Python 3.14 Test Compatibility** - Fixed `test_auto_capture_rollback.py`
  - Added `@contextmanager` decorator to mock context functions
  - Removed monkey-patching of read-only sqlite3 attributes
  - Added `gc.collect()` retry loop for Windows file locking in `conftest.py`

### Changed
- **Documentation Organization** - Moved analysis docs to `docs/analysis/`
  - CRITICAL_BUGS_QUICKREF.md, DEBUG_ANALYSIS_REPORT.md
  - DOCUMENTATION_ARCHITECTURE_ANALYSIS.md, TEST_SUMMARY.md
- **Gitignore** - Added `**/rembg_env/` pattern for Python virtual environments

## [0.3.11] - 2026-01-05

### Fixed
- **Exponential Backoff in Auto-Capture** - Added backoff (2^n up to 300s) on consecutive errors to prevent tight error loops
- **Session ID Validation** - UUID format validation before subprocess calls in summarizer
- **Fraud Detector Error Propagation** - `_store_fraud_report` now returns bool; response actions only execute on successful storage
- **Thread-Safe Session Index** - Added `threading.RLock` protecting `_index` across all methods (scan, list, get)
- **Timeline Event Type Validation** - Validate `event_type` against enum before TypeScript cast
- **Subprocess Timeout Handling** - Explicit `TimeoutExpired` handling with specific error messages in summarizers
- **Session Corruption Tracking** - New `is_partial` and `corruption_count` fields in `SessionMetadata` for JSON parse errors
- **SQLite JSON Queries** - Replaced fragile `LIKE '%"outcome": "unknown"%'` with `json_extract(output_json, '$.outcome')`
- **Editor Error Toast** - Show notification when "open in editor" fails instead of silent failure

## [0.3.10] - 2026-01-05

### Added
- **Heuristic Validation Tracking** - New `scripts/validate-heuristic.py` script
  - Track when heuristics are validated (worked) or violated (failed)
  - `--validate` / `--violate` flags to record outcomes
  - `--recalc` to adjust confidence based on validation ratio
  - `--list` to view all heuristics with validation stats

### Fixed
- **Unicode Encoding Error (Windows)** - Added `encoding='utf-8'` to file operations in `record-heuristic.py`
- **Package Manager Fallback** - `start.ps1` now detects bun first, falls back to npm if unavailable
- **Windows Rollup Dependency** - Added platform-specific Rollup binaries to `optionalDependencies` in frontend `package.json`

## [0.3.9] - 2026-01-04

### Changed
- **Swarm Skill** - Complete rewrite with full agent pool (~100+ specialized agents)
  - Replaced 4-agent pattern (Researcher/Architect/Creative/Skeptic) with domain-based selection
  - Added `ultrathink` mode: 15-25 agents for maximum depth analysis
  - Added `focused` mode: 4-8 agents for targeted domain analysis
  - Added `quick` mode: 2-4 agents for fast surveys
  - Domain-to-agent mapping table (Python, TypeScript, Security, Databases, etc.)
  - Async-first execution rules documented
  - Anti-patterns section to prevent common mistakes

## [0.3.2] - 2025-12-28

### Fixed
- **Checkin Skill** - Use Python for session summarization to avoid MSYS bash escaping issues
  - Added database health check display
  - Added last session summary display
  - ELF banner and dashboard prompt on first checkin

## [0.3.1] - 2025-12-25

### Fixed
- **Windows Installer** - Fixed PowerShell Join-Path syntax errors for new users
  - Join-Path now correctly uses 2 parameters instead of 3
  - Fixed venv Python path, pip path, and hook path resolution
  - Database validation now uses venv Python with all dependencies
- **Python Script Installation** - Installer now copies all 21 Python scripts from tools/scripts/
  - Fixes pre-commit hook failures (check-invariants.py missing)
  - Ensures recording scripts (record-heuristic.py, etc.) are available
- **Watcher Module Installation** - Tiered watcher system now properly installed
  - src/watcher/ copied to ~/.claude/emergent-learning/watcher/
  - start-watcher.sh updated to use correct installed paths
  - Fixes "launcher.py not found" error when starting watcher

## [0.2.0] - 2025-12-16

### Added
- **Async Query Engine** - Complete migration to async architecture using peewee-aio
- **ELF MCP Server** - Native MCP integration for claude-flow
- **Step-file Workflows** - Resumable task architecture with frontmatter state
- **Party Definitions** - Agent team compositions for complex tasks
- **Golden Rule Categories** - Filter rules by domain/category
- **Customization Layer** - User-specific config overrides
- **Update System** - Simple update.sh/update.ps1 with database migrations

### Changed
- Cosmic view now default (persisted to localStorage)
- Modular query system architecture (Phase 1-6 refactor)
- Zustand store with persistence middleware

### Fixed
- Windows compatibility (ASCII-only CLI output)
- Clean exit when dashboard servers already running
- Workflow engine import handling
- Hook directory structure

## [0.1.2] - 2025-12-14

### Added
- Dashboard UI overhaul with cosmic theme
- Learning pipeline automation
- File operations tracking for hotspot analysis

## [0.1.1] - 2025-12-13

### Added
- Initial dashboard application
- Golden rules and heuristics system
- CEO escalation workflow

## [0.1.0] - 2025-12-12

### Added
- Initial release
- Core ELF framework
- Installation scripts
- Basic query system

---

## Versioning Policy

- **Major (X.0.0)**: Breaking changes to database schema or configuration
- **Minor (0.X.0)**: New features, backward-compatible
- **Patch (0.0.X)**: Bug fixes, documentation updates
