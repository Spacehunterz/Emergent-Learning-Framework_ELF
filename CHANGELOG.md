# Changelog

All notable changes to the Emergent Learning Framework will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
