# Changelog

All notable changes to the Emergent Learning Framework will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-16

### Added
- Dashboard application with cosmic view visualization
- Golden rules system for constitutional principles
- Heuristics tracking with confidence scoring
- Failure/success recording and analysis
- CEO escalation workflow via ceo-inbox/
- Agent personas (Architect, Creative, Researcher, Skeptic)
- Database-backed memory system (SQLite)
- Session hooks for Claude Code integration
- WebSocket real-time updates
- Knowledge graph visualization
- Learning velocity analytics
- Assumptions, invariants, and spike tracking

### Infrastructure
- `install.sh` / `install.ps1` - Installation scripts
- `update.sh` / `update.ps1` - Simple update scripts
- `scripts/migrate_db.py` - Database migration runner
- ELF MCP server for claude-flow integration

---

## Versioning Policy

- **Major (X.0.0)**: Breaking changes to database schema or configuration
- **Minor (0.X.0)**: New features, backward-compatible
- **Patch (0.0.X)**: Bug fixes, documentation updates
